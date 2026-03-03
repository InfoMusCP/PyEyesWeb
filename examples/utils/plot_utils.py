import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional


def plot_feature_timeseries(
        results_list: List[Dict[str, Any]],
        metrics_to_plot: Optional[List[str]] = None,
        title: str = "Feature Analysis"
) -> None:
    """Renders static time-series plots for specific flattened feature metrics."""
    df = pd.DataFrame(results_list)

    # 1. Determine which metrics to plot
    if metrics_to_plot:
        # Keep only the metrics that actually exist in the DataFrame
        metrics = [m for m in metrics_to_plot if m in df.columns]
        missing = [m for m in metrics_to_plot if m not in df.columns]
        if missing:
            print(f"Warning: The following metrics were not found and will be skipped: {missing}")
    else:
        # Fallback: plot everything except validity flags (can be messy!)
        metrics = [col for col in df.columns if 'is_valid' not in col]

    if not metrics:
        print("No valid metrics found to plot.")
        return

    # 2. Create subplots dynamically
    fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 3 * len(metrics)), sharex=True)
    axes = np.atleast_1d(axes)  # Ensure axes is iterable even if len == 1

    fig.suptitle(title, fontsize=16, y=0.95 + (0.01 * len(metrics)))

    # 3. Plot each metric
    for ax, metric in zip(axes, metrics):
        ax.plot(df.index, df[metric], label=metric, color="#2E86C1", linewidth=1.5)

        # Clean up metric names
        clean_title = metric.replace("_", " ").title()
        ax.set(title=clean_title, ylabel="Value")

        # --- NEW: Robust Y-Axis Scaling ---
        # Caps the top of the plot at the 99.5th percentile to ignore extreme 1-frame spikes
        y_min = df[metric].min()
        y_max = df[metric].quantile(0.995)
        if y_max > y_min:  # Prevent crash if data is completely flat
            margin = (y_max - y_min) * 0.1
            ax.set_ylim(y_min - margin, y_max + margin)
        # ----------------------------------

        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Frame")
    plt.tight_layout()
    plt.show()