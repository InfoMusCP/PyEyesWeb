"""
Synchronization of events
=========================

Often what is shared between two people is a set of moments, not a continuous curve: the instants of a clap, of a step, of a
change of direction. This second tutorial on synchronization turns the movement of two hands into **trains of events** and
measures how far the events of one train meet those of the other, within a chosen tolerance.

:Goals: extract events from a movement with a peak detector; measure event synchronization (two trains, several event
        classes).
:Prerequisites: :ref:`sphx_glr_tutorials_05_analysis_primitives_plot_09a_synchronization_signals.py` and
                :ref:`sphx_glr_tutorials_05_analysis_primitives_plot_08_primitives.py` (the peak detector).
:Data: trials 7 (clapping hands, synchronised) and 8 (unsynchronised), seconds 5 to 21 of the example session.
:Time: about 25 minutes.
"""

# %%
# From movement to events
# -----------------------
# In the clapping task both hands swing horizontally (the ``x`` axis of the recordings) towards and away from each other. In
# trial 7 the claps are synchronised, in trial 8 they are not. We turn each hand into an **event train**: a series with one
# value per sample, where a non-zero value is an event. The events are the maxima of each swing, found online with
# :class:`~pyeyesweb.analysis_primitives.ScalarPeakDetector` on the position of the hand around its mean, in metres, with a
# buffer of 0.4 s (40 samples) and a swing of at least 5 cm. A peak is reported when the buffer already holds the samples that
# follow it, so the markers come up to a few tenths of a second after the maximum. Time is in seconds; ``max_lag`` and the windows below are in samples
# (100 per second).

import matplotlib.pyplot as plt
import numpy as np

from pyeyesweb.analysis_primitives import ScalarPeakDetector
from pyeyesweb.datasets import load_qualisys_trial

trials = {"trial 7 (synchronised)": 7, "trial 8 (unsynchronised)": 8}
positions, trains = {}, {}
for name, number in trials.items():
    trial = load_qualisys_trial(number, start=5, stop=21).to_units("m")
    hands = {side: trial.joint(f"{side}_Hand") for side in ("Left", "Right")}
    positions[name] = hands
    # one train per hand and per axis: (samples, 3)
    trains[name] = {
        side: np.column_stack([
            ScalarPeakDetector(window=40, threshold=limit).run(hands[side][:, axis] - hands[side][:, axis].mean()).is_peak.astype(float)
            for axis, limit in enumerate((0.05, 0.02, 0.03))
        ])
        for side in hands
    }
stamps = trial.timestamps
sampling_rate = trial.sampling_rate
print("events of the left and right hand along x:", {name: (int(t["Left"][:, 0].sum()), int(t["Right"][:, 0].sum())) for name, t in trains.items()})

fig, axes = plt.subplots(2, 1, figsize=(8, 4), sharex=True, sharey=True)
for ax, name in zip(axes, trials):
    for side, color in (("Left", "C0"), ("Right", "C1")):
        x = positions[name][side][:, 0]
        events = np.flatnonzero(trains[name][side][:, 0])
        ax.plot(stamps, x - x.mean(), color=color, lw=0.8, label=f"{side.lower()} hand")
        ax.plot(stamps[events], (x - x.mean())[events], "v", color=color, ms=4)
    ax.set_xlim(stamps[0], stamps[0] + 6)
    ax.set_ylabel("x - mean (m)")
    ax.set_title(name, fontsize=9, loc="left")
axes[0].legend(fontsize=7, ncol=2)
axes[-1].set_xlabel("time (s)")
fig.tight_layout()

# %%
# **Takeaway.** An event train is a series with a non-zero value at each event; the peak detector makes one from a movement.

# %%
# Event synchronization: do the events of one hand have a partner?
# -----------------------------------------------------------------
# :class:`~pyeyesweb.analysis_primitives.EventSynchronization` looks, for each event of one train, for an event of the other
# within ``max_lag`` samples. ``synchronization`` (Q) is 1 when every event has a partner and 0 when none has; ``delay`` (q)
# is positive when the first train leads and negative when the second does. Because it accumulates events, consecutive
# windows may not overlap (``hop`` is the window); ``reset_every_buffer=True`` makes every window independent. We use windows
# of 4 s (400 samples) and ``max_lag=30`` (0.3 s).

from pyeyesweb.analysis_primitives import EventSynchronization

fig, axes = plt.subplots(1, 2, figsize=(8, 3))
for name in trials:
    left, right = trains[name]["Left"][:, 0], trains[name]["Right"][:, 0]
    recorder = EventSynchronization(window=400, max_lag=30, reset_every_buffer=True).run(left, right, timestamps=stamps)
    index = np.flatnonzero(recorder.ok)
    axes[0].plot(recorder.timestamps[index], recorder.synchronization[index], "o-", label=name)
    axes[1].plot(recorder.timestamps[index], recorder.delay[index], "o-", label=name)
    print(f"{name:<26} Q per window: {np.round(recorder.synchronization[index], 2)}")
# sphinx_gallery_thumbnail_number = 2
axes[0].set_ylabel("Q, synchronization")
axes[1].set_ylabel("q, delay (+: left leads)")
for ax in axes:
    ax.set_xlabel("end of the 4 s window (s)")
axes[0].legend(fontsize=7)
fig.tight_layout()

# %%
# The only parameter that defines "at the same time" is ``max_lag``. The same recordings over the whole 16 s with three
# tolerances:

for max_lag in (5, 15, 30):
    values = [float(EventSynchronization(window=1600, max_lag=max_lag).run(trains[name]["Left"][:, 0], trains[name]["Right"][:, 0])[-1].synchronization) for name in trials]
    print(f"max_lag = {max_lag:>2} samples ({max_lag / sampling_rate:.2f} s): Q = {values[0]:.2f} (trial 7), {values[1]:.2f} (trial 8)")

# %%
# **Takeaway.** Q is the share of events that have a partner within ``max_lag``; choose ``max_lag`` in samples to say how close "together"
# is.

# %%
# Several kinds of events: MECS
# -----------------------------
# A gesture can have several kinds of events. :class:`~pyeyesweb.analysis_primitives.EventSynchronizationMECS` takes one series
# per participant, each with one channel per **event class**, and returns for each class the synchronization of the
# series and the number of ``events``. Here there are two participants (the hands) and three classes, the swings along
# ``x``, along the vertical ``y`` and along the depth ``z``. It accumulates over windows, so we give it one window for the whole
# recording.

from pyeyesweb.analysis_primitives import EventSynchronizationMECS

classes = ["x (side)", "y (vertical)", "z (depth)"]
mecs = {}
for name in trials:
    mecs[name] = EventSynchronizationMECS(window=1600, max_lag=30, number_of_event_classes=3).run(
        trains[name]["Left"], trains[name]["Right"], timestamps=stamps)[-1]
    print(f"{name:<26} synchronization per class {np.round(mecs[name].synchronization, 2)}, events {mecs[name].events.astype(int)}")

fig, ax = plt.subplots(figsize=(8, 3))
for offset, name in zip((-0.2, 0.2), trials):
    ax.bar(np.arange(3) + offset, mecs[name].synchronization, width=0.4, label=name)
ax.set_xticks(range(3), classes)
ax.set_ylabel("synchronization of the class")
ax.legend(fontsize=7)
fig.tight_layout()

# %%
# The ``kernel`` (``"uniform"``, ``"linear"`` or ``"gaussian"``) sets how a coincidence is weighted by its lag.
#
# **Takeaway.** MECS gives one synchronization per class of events, for any number of participants.

# %%
# Try it
# ------
# 1. Swap the two trains in ``EventSynchronization(window=1600, max_lag=30)`` on the two trials. What happens to Q and to
#    q?

# %%
# Solutions
# ---------
# Exercise 1. Q counts the pairs in both directions, so it does not change; q is the difference of the two directions, so it
# changes sign.

for name in trials:
    left, right = trains[name]["Left"][:, 0], trains[name]["Right"][:, 0]
    forward = EventSynchronization(window=1600, max_lag=30).run(left, right)[-1]
    swapped = EventSynchronization(window=1600, max_lag=30).run(right, left)[-1]
    print(f"{name:<26} Q = {forward.synchronization:.2f} and {swapped.synchronization:.2f}, "
          f"q = {forward.delay:+.2f} and {swapped.delay:+.2f}")

# %%
# Next steps
# ----------
# * :doc:`/theory/synchronization`: the definitions of every measure and how to choose one.
# * :doc:`/api/analysis_primitives`: every parameter of these features.
# * :ref:`sphx_glr_tutorials_06_capstone_plot_10_capstone.py`: a real-time loop and a batch analysis that combine features of several layers.
