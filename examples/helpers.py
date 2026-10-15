"""Plotting and signal helpers shared by the tutorials (not part of the library, not installed).

CONVENTIONS OF THE TUTORIALS (the long form is the section "WP7 stage 1 conventions" of DOCS_PLAN.md)
-----------------------------------------------------------------------------------------------------
* A tutorial is ``examples/<NN_layer>/plot_<NN>_<name>.py``, a sphinx-gallery percent script: the module docstring is the
  title (underlined with ``=``) and the card text; ``# %%`` opens a cell; the comment lines under ``# %%`` are reStructuredText
  (a section: ``# Title`` then ``# -----``). Numbers are global (01..10), folders are the layers.
* ``import helpers`` works in the docs build (``docs/conf.py`` puts ``examples/`` on ``sys.path``) and from a checkout
  (``PYTHONPATH=examples``); a downloaded notebook fetches this file in its first cell. Keep it below 250 lines, public API
  only, one short docstring per function, no maintainer-only helpers.
* Data come from ``pyeyesweb.datasets`` (never a path): ``load_qualisys_trial(7, start=0, stop=15)``. Qualisys positions
  are millimetres: say so, and convert with ``trial.to_units("m")`` or declare ``units="mm"`` on the feature.
* Time on every axis is seconds; label axes with units; one concept per figure; ``# sphinx_gallery_thumbnail_number = N``
  picks the card; synthetic data use ``numpy.random.default_rng(seed)``; a script runs in under 60 s.
* Plot with ``plot_recorder`` (one axis per output, non-OK spans shaded by ``shade_status``); nothing else is imported
  from the library but the public packages (no name starting with ``_``).
"""

import matplotlib.pyplot as plt
import numpy as np

__all__ = ["STATUS_COLORS", "draw_skeleton", "plot_recorder", "shade_status", "show_frames", "speed",
           "synthetic_silhouette", "use_style", "vertical_axis"]

#: Colour of the spans that are not OK, by integer status (``Status.WARMING_UP`` is 1, ``NO_OUTPUT`` 2, ``INVALID_INPUT`` 3).
STATUS_COLORS = {1: "#e0b04a", 2: "#9aa8b6", 3: "#d9534f"}

#: Bones of the 20-joint skeleton of ``load_qualisys_trial`` (names as in ``trial.labels``).
SKELETON_EDGES = [
    ("Head", "Neck"), ("Neck", "Spine"), ("Spine", "Pelvis"),
    ("Neck", "Left_Shoulder"), ("Left_Shoulder", "Left_Elbow"), ("Left_Elbow", "Left_Wrist"), ("Left_Wrist", "Left_Hand"),
    ("Neck", "Right_Shoulder"), ("Right_Shoulder", "Right_Elbow"), ("Right_Elbow", "Right_Wrist"), ("Right_Wrist", "Right_Hand"),
    ("Pelvis", "Left_Hip"), ("Left_Hip", "Left_Knee"), ("Left_Knee", "Left_Ankle"), ("Left_Ankle", "Left_Foot"),
    ("Pelvis", "Right_Hip"), ("Right_Hip", "Right_Knee"), ("Right_Knee", "Right_Ankle"), ("Right_Ankle", "Right_Foot"),
]


def use_style():
    """Figure style of the tutorials: dpi 90, light grid, 8 x 3 inch default figure. Called when this module is imported."""
    plt.rcParams.update({"figure.dpi": 90, "axes.grid": True, "grid.alpha": 0.25, "figure.figsize": (8, 3),
                         "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})
    np.set_printoptions(precision=4, suppress=True, linewidth=100)


use_style()


def speed(positions, sampling_rate):
    """Speed of a point (or of each joint) from its positions, by central differences.

    Parameters
    ----------
    positions : array, shape (frames, 3) or (frames, joints, 3)
    sampling_rate : float
        Frames per second; the result is in position units per second.

    Returns
    -------
    array, shape (frames,) or (frames, joints)
    """
    return np.linalg.norm(np.gradient(np.asarray(positions, dtype=float), 1.0 / sampling_rate, axis=0), axis=-1)


def vertical_axis(trial):
    """Index (0, 1 or 2) of the axis along which the head is highest above the feet (``y`` in the Qualisys recordings)."""
    difference = trial.joint("Head") - trial.joint("Left_Foot")
    return int(np.argmax(np.abs(difference.mean(axis=0))))


def shade_status(ax, t, status, codes=(1, 2, 3)):
    """Shade the spans of an axis where the status is not OK: yellow warming up, grey no output, red invalid input.

    Parameters
    ----------
    ax : matplotlib axes
    t : array, shape (n,)
        Time of each row, in seconds.
    status : array of int, shape (n,)
        ``recorder.status`` (0 is OK).
    codes : tuple of int
        Which statuses to shade (default all three).
    """
    status = np.asarray(status)
    for code in codes:
        color = STATUS_COLORS[code]
        mask = status == code
        if mask.any():
            edges = np.flatnonzero(np.diff(np.r_[0, mask.astype(int), 0]))
            for a, b in zip(edges[::2], edges[1::2]):
                ax.axvspan(t[a], t[min(b, len(t) - 1)], color=color, alpha=0.25, lw=0)


def plot_recorder(recorder, names=None, t=None, height=2.0, title=None):
    """One axis per output of a ``Recorder`` against time in seconds: the ``OK`` rows are drawn (joined across the rows
    between two windows), the warm-up is shaded yellow and the invalid input red.

    Parameters
    ----------
    recorder : pyeyesweb.data_models.Recorder
    names : list of str, optional
        Outputs to draw (default: the fixed-shape outputs of the schema).
    t : array, optional
        Time of each row in seconds (default: ``recorder.timestamps`` if they were given, else the row number).
    height : float
        Height of each axis in inches.
    title : str, optional

    Returns
    -------
    matplotlib.figure.Figure
    """
    names = names or [o.name for o in recorder.schema.fixed_outputs]
    if t is None:
        t = recorder.timestamps if np.isfinite(recorder.timestamps).all() else np.arange(len(recorder))
    fig, axes = plt.subplots(len(names), 1, figsize=(8, height * len(names)), sharex=True, squeeze=False)
    for ax, name in zip(axes[:, 0], names):
        y = np.asarray(recorder[name], dtype=float)
        ok = np.asarray(recorder.status) == 0
        ax.plot(np.asarray(t)[ok], y[ok].reshape(ok.sum(), -1), lw=1)
        shade_status(ax, np.asarray(t), recorder.status, codes=(1, 3))
        ax.set_ylabel(name)
    axes[-1, 0].set_xlabel("time (s)")
    if title:
        axes[0, 0].set_title(title)
    fig.tight_layout()
    return fig


def draw_skeleton(frame, labels, ax=None, plane=(0, 1), color="k", lw=1.5, units="mm"):
    """Draw one frame ``(joints, 3)`` of the 20-joint skeleton as a stick figure on the plane of two axes (indices 0-2)."""
    ax = ax or plt.gca()
    where = {name: frame[i] for i, name in enumerate(labels)}
    for a, b in SKELETON_EDGES:
        if a in where and b in where:
            ax.plot([where[a][plane[0]], where[b][plane[0]]], [where[a][plane[1]], where[b][plane[1]]], color=color, lw=lw)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xlabel(f"{'xyz'[plane[0]]} ({units})")
    ax.set_ylabel(f"{'xyz'[plane[1]]} ({units})")
    return ax


def show_frames(trial, frames, cols=4, size=2.4):
    """Small multiples of a ``QualisysTrial``: the stick figure at the given frame numbers, front view (x against the vertical)."""
    plane = (int(next(i for i in range(3) if i != vertical_axis(trial))), vertical_axis(trial))
    rows = int(np.ceil(len(frames) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(size * cols, size * 1.4 * rows), squeeze=False)
    for ax, f in zip(axes.ravel(), frames):
        draw_skeleton(trial.positions[f], trial.labels, ax, plane, units=trial.units)
        ax.set_title(f"{f / trial.sampling_rate:.2f} s", fontsize=9)
    for ax in axes.ravel()[len(frames):]:
        ax.axis("off")
    fig.tight_layout()
    return fig


def synthetic_silhouette(height=240, width=320, shift=0, arm_row=75, leg_slant=0.3):
    """A synthetic body as a 0 / 255 ``uint8`` mask (the example data hold only motion capture): head, trunk, an arm bar at
    row ``arm_row``, a straight left leg and a slanted right leg. ``shift`` moves it to the right (pixels)."""
    rows, columns = np.mgrid[:height, :width]
    body = (columns - 160 - shift) ** 2 / 18 ** 2 + (rows - 40) ** 2 / 22 ** 2 <= 1
    body |= (abs(columns - 160 - shift) <= 28) & (rows >= 60) & (rows <= 140)
    body |= (abs(rows - arm_row) <= 7) & (columns >= 80 + shift) & (columns <= 240 + shift)
    body |= (abs(columns - 147 - shift) <= 9) & (rows > 140) & (rows <= 225)
    body |= (abs(columns - 173 - shift - (rows - 140) * leg_slant) <= 9) & (rows > 140) & (rows <= 225)
    return (body * 255).astype(np.uint8)
