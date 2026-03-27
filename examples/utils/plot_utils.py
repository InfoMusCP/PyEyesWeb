import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import ipywidgets as widgets
from IPython.display import display
import cv2
from pathlib import Path
from typing import List, Dict, Any, Optional


def plot_feature_timeseries(
    results_list: List[Dict[str, Any]],
    metrics_to_plot: Optional[List[str]] = None,
    title: str = "Feature Analysis",
) -> None:
    """Renders static time-series plots for specific flattened feature metrics."""
    df = pd.DataFrame(results_list)

    # 1. Determine which metrics to plot
    if metrics_to_plot:
        # Keep only the metrics that actually exist in the DataFrame
        metrics = [m for m in metrics_to_plot if m in df.columns]
        missing = [m for m in metrics_to_plot if m not in df.columns]
        if missing:
            print(
                f"Warning: The following metrics were not found and will be skipped: {missing}"
            )
    else:
        # Fallback: plot everything except validity flags (can be messy!)
        metrics = [col for col in df.columns if "is_valid" not in col]

    if not metrics:
        print("No valid metrics found to plot.")
        return

    # 2. Create subplots dynamically
    fig, axes = plt.subplots(
        len(metrics), 1, figsize=(12, 3 * len(metrics)), sharex=True
    )
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


def plot_stick_figure_3d(
    pos_tensor: np.ndarray,
    marker_names: List[str],
    frame_idx: int = 0,
    standard: bool = False,
    ax=None,
):
    """
    Plots a 3D stick figure for a specific frame.
    If standard=True, it connects the joints using generic human skeleton mappings.
    """
    STANDARD_CONNECTIONS = [
        ("Head", "Neck"),
        ("Neck", "Spine"),
        ("Spine", "Pelvis"),
        ("Neck", "Left_Shoulder"),
        ("Left_Shoulder", "Left_Elbow"),
        ("Left_Elbow", "Left_Wrist"),
        ("Left_Wrist", "Left_Hand"),
        ("Neck", "Right_Shoulder"),
        ("Right_Shoulder", "Right_Elbow"),
        ("Right_Elbow", "Right_Wrist"),
        ("Right_Wrist", "Right_Hand"),
        ("Pelvis", "Left_Hip"),
        ("Left_Hip", "Left_Knee"),
        ("Left_Knee", "Left_Ankle"),
        ("Left_Ankle", "Left_Foot"),
        ("Pelvis", "Right_Hip"),
        ("Right_Hip", "Right_Knee"),
        ("Right_Knee", "Right_Ankle"),
        ("Right_Ankle", "Right_Foot"),
    ]

    if ax is None:
        fig = plt.figure(figsize=(8, 8))
        ax = fig.add_subplot(111, projection="3d")

    frame_data = pos_tensor[frame_idx]

    # Scatter all valid points
    ax.scatter(frame_data[:, 0], frame_data[:, 1], frame_data[:, 2], c="blue", s=20)

    if standard:
        marker_idx_map = {name: i for i, name in enumerate(marker_names)}
        for bone1, bone2 in STANDARD_CONNECTIONS:
            if bone1 in marker_idx_map and bone2 in marker_idx_map:
                idx1, idx2 = marker_idx_map[bone1], marker_idx_map[bone2]
                x = [frame_data[idx1, 0], frame_data[idx2, 0]]
                y = [frame_data[idx1, 1], frame_data[idx2, 1]]
                z = [frame_data[idx1, 2], frame_data[idx2, 2]]

                # Check for NaNs
                if not np.isnan(x).any():
                    ax.plot(x, y, z, c="red", linewidth=2)

    ax.set_title(f"3D Skeleton (Frame {frame_idx})")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")

    # Set equal aspect ratio
    max_range = (
        np.array(
            [
                frame_data[:, 0].max() - frame_data[:, 0].min(),
                frame_data[:, 1].max() - frame_data[:, 1].min(),
                frame_data[:, 2].max() - frame_data[:, 2].min(),
            ]
        ).max()
        / 2.0
    )

    if not np.isnan(max_range):
        mid_x = (frame_data[:, 0].max() + frame_data[:, 0].min()) * 0.5
        mid_y = (frame_data[:, 1].max() + frame_data[:, 1].min()) * 0.5
        mid_z = (frame_data[:, 2].max() + frame_data[:, 2].min()) * 0.5

        ax.set_xlim(mid_x - max_range, mid_x + max_range)
        ax.set_ylim(mid_y - max_range, mid_y + max_range)
        ax.set_zlim(mid_z - max_range, mid_z + max_range)


def display_video_notebook(video_path: str | Path):
    """
    Displays a video in a notebook with an interactive slider.
    Useful as a fallback for .avi files that don't play natively.
    """
    path = str(Path(video_path).resolve())
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Failed to open video at {path}")
        return

    # Read first frame to initialize
    ret, frame = cap.read()
    if not ret:
        print("Empty video")
        return

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    image_widget = widgets.Image(format="jpg")
    slider = widgets.IntSlider(
        min=0,
        max=max(0, frame_count - 1),
        step=1,
        description="Frame:",
        continuous_update=False,
    )

    def on_val_change(change):
        cap.set(cv2.CAP_PROP_POS_FRAMES, change["new"])
        r, f = cap.read()
        if r:
            f_rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            _, b = cv2.imencode(".jpg", f_rgb)
            image_widget.value = b.tobytes()

    slider.observe(on_val_change, names="value")

    # Set initial frame
    f_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    _, b = cv2.imencode(".jpg", f_rgb)
    image_widget.value = b.tobytes()

    display(widgets.VBox([slider, image_widget]))
