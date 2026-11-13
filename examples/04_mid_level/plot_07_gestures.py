"""
Gestures and their durations
============================

A recording is a stream of samples, but people describe movement in units: a wave, a strike, a pause. This tutorial cuts a
recording into gestures and measures how long gestures and pauses last.

:Goals: segment a recording into gestures with ``KineticEnergy`` and ``GestureSegmenter``; choose the threshold for the
        signal; measure motion and pause durations.
:Prerequisites: :ref:`sphx_glr_tutorials_01_getting_started_plot_02_the_contract.py`.
:Data: trials 21, 22 and 25 of the example session (impulsive, light and slow movement), seconds 0 to 24.
:Time: about 15 minutes.
"""

# %%
# Data used in this tutorial
# --------------------------
# Mid-level features describe a **movement unit** that lasts between half a second and a few seconds (see
# :doc:`/concepts/layers`). They are built on signals of the layers below, such as the kinetic energy of the body. We use
# trial 21 of the example session, where the performer reacts quickly to an unexpected signal by hiding an object behind the
# back, so the recording is a series of short, sharp gestures separated by calm. Positions are converted to **metres**
# and time is in seconds.

import matplotlib.pyplot as plt
import numpy as np

from helpers import shade_status, speed
from pyeyesweb.datasets import load_qualisys_trial

trial = load_qualisys_trial(21, start=0, stop=24).to_units("m")
time = trial.timestamps
print(trial.positions.shape, "frames x joints x coordinates | duration", trial.duration, "s | rate", trial.sampling_rate, "Hz")

# %%
# Segmenting gestures
# -------------------
# A **gesture** is a period in which the body moves enough. The *intensity* of the movement is a number per sample that says
# how much the body moves; here it is the kinetic energy of the skeleton, computed by
# :class:`~pyeyesweb.low_level.KineticEnergy` (energy per unit of mass, see :doc:`/theory/kinematics_energy`).
# :class:`~pyeyesweb.mid_level.GestureSegmenter` smooths it with a Savitzky-Golay filter and declares a gesture while the
# smoothed intensity is at least ``firing_threshold``, in the unit of the intensity. The pipeline is skeleton, energy,
# segmenter:

from pyeyesweb.low_level import KineticEnergy
from pyeyesweb.mid_level import GestureSegmenter

energy = KineticEnergy(skeleton=trial.skeleton, sampling_rate=100).run(trial.positions, timestamps=time)
segmenter = GestureSegmenter(firing_threshold=1.0)
gestures = segmenter.run(energy.kinetic_energy, timestamps=time)
print(gestures)
starts = time[gestures.is_gesture_start]
print("gestures:", len(starts), "| start times (s):", starts.round(2))

# %%
# The segmenter needs 10 samples before it can smooth, so its first 10 results are ``WARMING_UP`` (yellow). The outputs are
# ``smoothed_intensity``, ``is_gesturing`` (true during a gesture) and ``is_gesture_start`` and ``is_gesture_end``, true on the
# sample that opens or closes a gesture.

# sphinx_gallery_thumbnail_number = 1
fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
top.plot(time, speed(trial.joint("Right_Hand"), 100), lw=0.8, label="Right_Hand")
top.plot(time, speed(trial.joint("Pelvis"), 100), lw=0.8, label="Pelvis")
top.set_ylabel("speed (m/s)")
top.legend(loc="upper right")
bottom.plot(time, energy.kinetic_energy, color="0.7", lw=0.6, label="kinetic energy")
bottom.plot(time, gestures.smoothed_intensity, lw=1.2, label="smoothed")
bottom.axhline(segmenter.firing_threshold, color="C3", ls="--", lw=0.8, label="firing threshold")
for ax in (top, bottom):
    edges = np.flatnonzero(np.diff(np.r_[0, gestures.is_gesturing.astype(int), 0]))
    for a, b in zip(edges[::2], edges[1::2]):
        ax.axvspan(time[a], time[min(b, len(time) - 1)], color="C2", alpha=0.25, lw=0)
shade_status(bottom, time, gestures.status)
bottom.set_ylim(-1, 15)
bottom.set_ylabel("kinetic energy (J/kg)")
bottom.set_xlabel("time (s)")
bottom.legend(loc="upper right", ncol=3, fontsize=8)
top.set_title("Trial 21: gestures (green) found from the kinetic energy of the whole body")

# %%
# **Takeaway.** The segmenter turns a one-dimensional intensity into start and end times; the kinetic energy of the skeleton is
# a natural intensity.

# %%
# What the parameters do
# ----------------------
# ``firing_threshold`` is the sensitivity: the lower it is, the more of the recording counts as gesture. ``filter_window_length``
# (5, 7 or 9) sets the smoothing and must be odd and shorter than the 10 samples of the filter. The threshold is in the unit
# of the intensity, so it has to be chosen for the signal. Trial 25, a deliberately slow movement, has far less energy than
# trial 21:

slow = load_qualisys_trial(25, start=0, stop=24).to_units("m")
slow_energy = KineticEnergy(skeleton=slow.skeleton, sampling_rate=100).run(slow.positions, timestamps=slow.timestamps)
print(f"{'firing_threshold':>17} {'trial 21 gestures':>18} {'% of time':>10} {'trial 25 gestures':>18} {'% of time':>10}")
for threshold in (0.1, 0.5, 1.0, 2.0, 4.0):
    fast = GestureSegmenter(firing_threshold=threshold).run(energy.kinetic_energy)
    calm = GestureSegmenter(firing_threshold=threshold).run(slow_energy.kinetic_energy)
    print(f"{threshold:>17} {int(fast.is_gesture_start.sum()):>18} {100 * fast.is_gesturing.mean():>10.0f} "
          f"{int(calm.is_gesture_start.sum()):>18} {100 * calm.is_gesturing.mean():>10.0f}")

# %%
# **Takeaway.** Choose ``firing_threshold`` in the unit of the intensity.

# %%
# How long do gestures and pauses last?
# -------------------------------------
# :class:`~pyeyesweb.mid_level.MotionDuration` takes the ``is_gesturing`` signal (non-zero is motion, zero is pause) and reports
# the length of a phase when it ends: a motion duration when a pause begins, a pause duration when a motion begins. With
# ``sampling_rate`` the durations are in seconds. Most samples have status ``NO_OUTPUT``, because only the sample that ends a
# phase has something to report.

from pyeyesweb.mid_level import MotionDuration

durations = MotionDuration(sampling_rate=100).run(gestures.is_gesturing.astype(float), timestamps=time)
motion = durations.motion_duration[~np.isnan(durations.motion_duration)]
pause = durations.pause_duration[~np.isnan(durations.pause_duration)]
print(durations)
print(f"{len(motion)} motion phases, median {np.median(motion):.2f} s | {len(pause)} pauses, median {np.median(pause):.2f} s")

fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(time, gestures.is_gesturing * 0.5, color="0.6", lw=0.8, label="is_gesturing (input)")
ax.stem(time[~np.isnan(durations.motion_duration)], motion, linefmt="C2-", markerfmt="C2o", basefmt=" ", label="motion duration")
ax.stem(time[~np.isnan(durations.pause_duration)], pause, linefmt="C0-", markerfmt="C0o", basefmt=" ", label="pause duration")
ax.set_xlabel("time (s)")
ax.set_ylabel("duration (s)")
ax.legend(loc="upper right")
ax.set_title("Each stem appears when a phase ends and says how long it lasted")

# %%
# **Takeaway.** ``MotionDuration`` turns the on/off signal of the segmenter into the durations of motion and of pause.

# %%
# Try it
# ------
# 1. Segment trial 22 (light movement) with ``firing_threshold`` 0.5 and 2.0. How many gestures are found, and how much of the
#    time is spent gesturing, in each case?

# %%
# Solutions
# ---------
# Exercise 1. The lower threshold accepts more of the recording as gesture.

light = load_qualisys_trial(22, start=0, stop=24).to_units("m")
light_energy = KineticEnergy(skeleton=light.skeleton, sampling_rate=100).run(light.positions, timestamps=light.timestamps)
for threshold in (0.5, 2.0):
    found = GestureSegmenter(firing_threshold=threshold).run(light_energy.kinetic_energy)
    print(f"threshold {threshold}: {int(found.is_gesture_start.sum())} gestures, {100 * found.is_gesturing.mean():.0f}% of the time")

# %%
# Next steps
# ----------
# * :doc:`/theory/gesture_segmentation`: the definitions behind the features of this tutorial.
# * :doc:`/user_guide/mid_level`: every mid-level feature with its parameters.
# * :ref:`sphx_glr_tutorials_05_analysis_primitives_plot_08_primitives.py`: the next tutorial turns to the analysis primitives:
#   entropy, rarity and periodicity of a signal.
