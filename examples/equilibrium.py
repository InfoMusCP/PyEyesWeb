"""
Interactive equilibrium simulation using matplotlib.

This script provides a visual demonstration of the `Equilibrium` class.
It creates an interactive 2D plot where the user can move the mouse to
simulate the barycenter position, and the system evaluates whether the
barycenter is within the equilibrium ellipse defined by two feet.

The ellipse is dynamically updated in position, orientation, and color:
- Green if the barycenter is within the ellipse.
- Red if the barycenter is outside.

The equilibrium value (in [0, 1]) is displayed in real-time.

Examples
--------
Run the script:

    $ python demo_equilibrium.py

Then move the mouse cursor inside the figure window to simulate barycenter
movements.

Notes
-----
- Requires `matplotlib` for visualization.
- Uses `numpy` for vector operations.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import sys, os
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pyeyesweb.low_level.equilibrium import Equilibrium

# --- Setup test parameters ---
left_foot = np.array([120, 200, 0])
"""numpy.ndarray: 3D coordinates (x, y, z) of the left foot in millimeters."""

right_foot = np.array([800, 600, 0])
"""numpy.ndarray: 3D coordinates (x, y, z) of the right foot in millimeters."""

eq = Equilibrium(margin_mm=100, y_weight=0.5)
"""Equilibrium: instance of the equilibrium evaluator."""

# --- Setup matplotlib figure ---
fig, ax = plt.subplots()
ax.set_xlim(-200, 1000)
ax.set_ylim(-200, 800)
ax.set_aspect('equal')
ax.set_title("Equilibrium. Move the barycenter with mouse.")

# Plot the two feet as blue points
ax.plot(left_foot[0], left_foot[1], 'bo', markersize=8)
ax.plot(right_foot[0], right_foot[1], 'bo', markersize=8)

# Ellipse ROI (initial placeholder)
roi_ellipse = Ellipse((0, 0), 0, 0,
                      fill=True, facecolor='green', alpha=0.2,
                      edgecolor='green', linewidth=2)
ax.add_patch(roi_ellipse)

# Red point for barycenter
baricentro_plot, = ax.plot([], [], 'ro', markersize=8)

# Text showing equilibrium value
eq_text = ax.text(0.02, 1.02, "", transform=ax.transAxes, fontsize=12)

def on_move(event):
    """
    Handle mouse movement and update equilibrium visualization.

    Parameters
    ----------
    event : matplotlib.backend_bases.MouseEvent
        The mouse event containing the current cursor position.
        Only `event.xdata` and `event.ydata` are used.

    Behavior
    --------
    - Computes equilibrium value and ellipse angle based on the
      simulated barycenter.
    - Updates ellipse position, size, orientation, and color.
    - Updates barycenter position on the plot.
    - Updates equilibrium value text.
    """
    if not event.inaxes:
        return

    baricentro = np.array([event.xdata, event.ydata, 0])

    value, angle = eq(left_foot, right_foot, baricentro)

    ps = np.array(left_foot)[:2]
    pd = np.array(right_foot)[:2]
    min_xy = np.minimum(ps, pd) - eq.margin
    max_xy = np.maximum(ps, pd) + eq.margin
    center = (min_xy + max_xy) / 2
    half_sizes = (max_xy - min_xy) / 2
    a = half_sizes[0]
    b = half_sizes[1] * eq.y_weight

    roi_ellipse.set_center(center)
    roi_ellipse.width = 2 * a
    roi_ellipse.height = 2 * b
    roi_ellipse.angle = angle
    roi_ellipse.set_facecolor('green' if value > 0 else 'red')
    roi_ellipse.set_edgecolor('green' if value > 0 else 'red')

    baricentro_plot.set_data(baricentro[0], baricentro[1])

    eq_text.set_text(f"Equilibrium value = {value:.2f}")

    fig.canvas.draw_idle()

# Connect mouse motion event
fig.canvas.mpl_connect('motion_notify_event', on_move)

# Run interactive visualization
plt.show()
