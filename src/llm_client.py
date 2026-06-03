import os
import re
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def get_llm_model(*env_names):
    """Return the configured LLM model, checking `env_names` in order then
    falling back to ``LLM_MODEL``. Re-runs ``load_dotenv`` so callers that
    didn't load .env at import time still pick it up."""
    load_dotenv()
    for env_name in env_names:
        value = os.environ.get(env_name)
        if value:
            return value
    value = os.environ.get("LLM_MODEL")
    if value:
        return value
    checked = ", ".join((*env_names, "LLM_MODEL")) or "LLM_MODEL"
    raise ValueError(f"Set one of these environment variables first: {checked}.")


@dataclass
class LLMResponse:
    content: str
    model: str
    latency_ms: float
    tokens: Optional[int] = None


_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client


def call_openrouter(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> LLMResponse:
    start_time = time.perf_counter()

    client = get_client()
    resolved_model = model or get_llm_model()
    response = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else None

    return LLMResponse(
        content=content,
        model=resolved_model,
        latency_ms=latency_ms,
        tokens=tokens,
    )


def parse_action(response: LLMResponse) -> str:
    """Extract L/M/H from the response; fall back to 'M' on any failure."""
    if not response.content:
        return "M"

    content = response.content.strip().upper()
    if content in {"L", "M", "H"}:
        return content

    match = re.search(r"\b(?:ACTION|FINAL|CHOICE)\s*[:=]\s*([LMH])\b", content)
    if match:
        return match.group(1)

    matches = re.findall(r"\b([LMH])\b", content)
    return matches[-1] if matches else "M"


def parse_json_action(response: LLMResponse) -> dict:
    """Parse {action, reason} JSON; fall back to {'M', 'parse_failed'}."""
    import json

    if not response.content:
        return {"action": "M", "reason": "parse_failed"}

    try:
        data = json.loads(response.content)
        if "action" in data and data["action"] in ["L", "M", "H"]:
            return data
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{[^}]*"action"\s*:\s*["\']?([LMH])["\']?', response.content, re.IGNORECASE)
    if match:
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', response.content)
        return {
            "action": match.group(1),
            "reason": reason_match.group(1) if reason_match else "fallback",
        }

    return {"action": "M", "reason": "parse_failed"}


def parse_per_dept_actions(response: LLMResponse, dept_names: list[str], fallback: str = "M") -> dict:
    """Parse per-department action JSON ({dept_name: "L|M|H", ..., reason}).
    On failure, apply `fallback` to every department."""
    import json

    result = {name: fallback for name in dept_names}
    result["reason"] = "parse_failed"

    if not response.content:
        return result

    content = response.content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content)

    json_candidates = [content]
    object_match = re.search(r"\{.*\}", content, re.DOTALL)
    if object_match:
        json_candidates.append(object_match.group(0))

    for candidate in json_candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        for name in dept_names:
            action = data.get(name, fallback)
            if isinstance(action, str):
                action = action.strip().upper()
            result[name] = action if action in ["L", "M", "H"] else fallback
        result["reason"] = data.get("reason", "")
        return result

    # Loose JSON or prose with per-dept assignments.
    found_any = False
    for name in dept_names:
        pattern = rf"{re.escape(name)}[\"'\s:=-]+([LMH])\b"
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            result[name] = match.group(1).upper()
            found_any = True
    if found_any:
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', content)
        result["reason"] = reason_match.group(1) if reason_match else "loose_assignment_fallback"
        return result

    # Single global action -> broadcast to all departments.
    match = re.search(r'"action"\s*:\s*["\']?([LMH])["\']?', content, re.IGNORECASE)
    if match:
        global_action = match.group(1).upper()
        for name in dept_names:
            result[name] = global_action
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', response.content)
        result["reason"] = reason_match.group(1) if reason_match else "global_fallback"

    return result
