# src/plotting.py

import matplotlib.pyplot as plt


def plot_liquidity_histories(histories_by_mechanism, output_path=None):
    """
    Plot liquidity reserve level over time for several mechanisms.

    histories_by_mechanism:
        dictionary where:
            key = mechanism name
            value = simulation history
    """

    plt.figure(figsize=(10, 6))

    for mechanism_name, history in histories_by_mechanism.items():
        timesteps = [step["t"] for step in history]
        reserves = [step["new_reserve"] for step in history]

        plt.plot(timesteps, reserves, label=mechanism_name)

    plt.xlabel("Time step")
    plt.ylabel("Liquidity reserve level")
    plt.title("Liquidity reserve sustainability by coordination mechanism")
    plt.legend()
    plt.grid(True)

    if output_path:
        plt.savefig(output_path, bbox_inches="tight")

    plt.show()
