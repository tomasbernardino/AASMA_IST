import os
import re
import time
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI


@dataclass
class LLMResponse:
    content: str
    model: str
    latency_ms: float
    tokens: Optional[int] = None


_client = None


def get_client() -> OpenAI:
    """Return OpenRouter client (lazy initialization)."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client


def call_openrouter(
    messages: list[dict],
    model: str = "openai/gpt-4o-mini",
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> LLMResponse:
    """
    Call OpenRouter API and return structured response.
    
    Parameters:
        messages: List of message dicts with 'role' and 'content'
        model: OpenRouter model identifier
        temperature: Sampling temperature
        max_tokens: Max tokens in response
        
    Returns:
        LLMResponse with content, model, latency, and token count
    """
    start_time = time.perf_counter()
    
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    latency_ms = (time.perf_counter() - start_time) * 1000
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else None
    
    return LLMResponse(
        content=content,
        model=model,
        latency_ms=latency_ms,
        tokens=tokens,
    )


def parse_action(response: LLMResponse) -> str:
    """
    Parse LLM response to extract action: L, M, or H.
    
    Falls back to 'M' if parsing fails.
    """
    if not response.content:
        return "M"
    
    match = re.search(r"[LMH]", response.content.upper())
    return match.group(0) if match else "M"


def parse_json_action(response: LLMResponse) -> dict:
    """
    Parse LLM response expecting JSON with 'action' and 'reason' fields.
    
    Falls back to default if parsing fails.
    """
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
    """
    Parse LLM response expecting per-department action JSON.

    Expected format:
        {
          "Growth Department": "H",
          "Risk Department": "L",
          ...
          "reason": "brief explanation"
        }

    Falls back to applying the fallback action to all departments if parsing fails.
    """
    import json

    result = {name: fallback for name in dept_names}
    result["reason"] = "parse_failed"

    if not response.content:
        return result

    try:
        data = json.loads(response.content)
        for name in dept_names:
            action = data.get(name, fallback)
            result[name] = action if action in ["L", "M", "H"] else fallback
        result["reason"] = data.get("reason", "")
        return result
    except json.JSONDecodeError:
        pass

    # Fallback: try to find a single global action and apply to all
    match = re.search(r'"action"\s*:\s*["\']?([LMH])["\']?', response.content, re.IGNORECASE)
    if match:
        global_action = match.group(1).upper()
        for name in dept_names:
            result[name] = global_action
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', response.content)
        result["reason"] = reason_match.group(1) if reason_match else "global_fallback"

    return result