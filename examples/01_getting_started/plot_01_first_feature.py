"""
Your first feature
==================

Load a motion-capture recording, compute the speed of a hand and the kinetic energy of the whole body, and look at the
results as a table and as figures.

:Goals: load an example recording; create a feature and read what it takes and returns; compute it one sample at a
        time (``process``) and on a whole recording (``run``); plot and tabulate the result (``Recorder``).
:Prerequisites: Python and NumPy; ``pip install pyeyesweb`` (see :doc:`/getting_started/install`).
:Data: trial 7 of the example session (clapping hands, Qualisys, 100 Hz), from second 4 to second 19.
:Time: about 15 minutes.
"""

# %%
# Load a recording
# ----------------
# The example recordings are motion-capture takes of one performer, exported by Qualisys at 100 frames per second.
# :func:`~pyeyesweb.datasets.load_qualisys_trial` returns a :class:`~pyeyesweb.datasets.QualisysTrial`: an array of
# positions with the names of the joints, the sampling rate and the unit. Trial 7 is a clapping movement: the performer
# stands still for the first few seconds and then claps. We keep seconds 4 to 19 of the recording; the clock of the loaded
# trial starts again at 0.

from pyeyesweb.datasets import load_qualisys_trial

trial = load_qualisys_trial(7, start=4, stop=19)
print(trial.task, "-", trial.condition)
print("positions:", trial.positions.shape, "= (frames, joints, x y z), in", trial.units)
print("sampling rate:", trial.sampling_rate, "Hz, duration:", trial.duration, "s, starting at", trial.offset, "s of the recording")
print("joints:", ", ".join(trial.labels))

# %%
# The 41 markers of the recording have been averaged into 20 joints (``Head``, ``Neck``, ... ``Right_Foot``). Positions are
# in **millimetres**, as Qualisys exports them: we will say so to the features that need to know. The figure shows six
# frames of the movement as stick figures.

import matplotlib.pyplot as plt
import numpy as np

from helpers import plot_recorder, show_frames

fig = show_frames(trial, [0, 150, 250, 350, 450, 550], cols=6, size=2.2)

# %%
# **Takeaway.** A recording is an array of shape (frames, joints, 3) plus a sampling rate and a unit.

# %%
# Look at one joint
# -----------------
# A feature of one point takes the positions of one joint: an array of shape ``(frames, 3)``.
# ``trial.joint(name)`` returns it. Here are the three coordinates of the right hand against time, in seconds.

hand = trial.joint("Right_Hand")
time = trial.timestamps
print("right hand:", hand.shape, "first position (mm):", hand[0])

fig, ax = plt.subplots()
ax.plot(time, hand)
ax.set_xlabel("time (s)")
ax.set_ylabel("position (mm)")
ax.legend(["x", "y", "z"], ncol=3, loc="upper right")
ax.set_title("Right hand, trial 7")

# %%
# **Takeaway.** Positions and times are plain NumPy arrays; ``trial.timestamps`` gives the time of every frame in seconds.

# %%
# Create a feature
# ----------------
# A feature is a Python object, configured when it is created. :class:`~pyeyesweb.low_level.Kinematics` computes the
# velocity, acceleration or jerk of a point from its positions (see :doc:`/theory/kinematics_energy`). Two parameters matter
# here: ``sampling_rate`` (frames per second) and ``units``, the unit of the positions we will give it. Our data are in
# millimetres, so we say ``units="mm"``.

from pyeyesweb.low_level import Kinematics

kinematics = Kinematics(sampling_rate=100, units="mm")

# %%
# Before it sees any data, a feature describes itself. ``inputs`` is what one call receives, ``outputs`` what it returns
# (with units), ``parameters`` how it is configured.

print(kinematics.inputs)
print(kinematics.outputs)
print(dict(kinematics.parameters))

# %%
# **Takeaway.** ``inputs``, ``outputs`` and ``parameters`` are known before any data arrives.

# %%
# Process one sample
# ------------------
# ``process`` takes one sample and returns a :class:`~pyeyesweb.data_models.Result`. The feature keeps its state between calls,
# as it would in a live loop. The time of the sample, in seconds, goes in the keyword ``timestamp``.

result = kinematics.process(hand[0], timestamp=time[0])
print(result)
print("status:", result.status, "| velocity:", round(float(result.velocity), 3), "mm/s")

# %%
# The ``status`` says whether the result holds a value (``OK``), and the value of every output is an attribute of the result.
# Feed the next few samples; the velocity of the right hand starts to change as the hand moves.

for index in range(1, 4):
    result = kinematics.process(hand[index], timestamp=time[index])
    print(f"t = {time[index]:.2f} s  status = {result.status}  velocity = {result.velocity:8.3f} mm/s")

# %%
# **Takeaway.** ``process`` is the live interface: one sample in, one ``Result`` out.

# %%
# Run a whole recording
# ---------------------
# When the data are already recorded, ``run`` applies the same computation to all of them and returns a
# :class:`~pyeyesweb.data_models.Recorder`: one row per sample. ``run`` starts from a fresh state, so the first rows of the
# loop above are not carried over.

speed = kinematics.run(hand, timestamps=time)
print(speed)
print("peak velocity of the right hand:", round(float(speed.velocity.max())), "mm/s at",
      round(float(time[np.argmax(speed.velocity)]), 2), "s")

# %%
# ``plot_recorder`` (from ``helpers.py`` next to this script) draws every output of a recorder against time, and shades the
# rows that are not ``OK``. Here every row is ``OK``, so nothing is shaded.

fig = plot_recorder(speed, t=time, title="Right hand velocity (Kinematics)")

# %%
# **Takeaway.** ``run`` is the offline interface and gives the same numbers as a loop of ``process`` calls.

# %%
# A feature of the whole body
# ---------------------------
# :class:`~pyeyesweb.low_level.KineticEnergy` takes a whole skeleton, one frame of shape ``(joints, 3)`` per call, and
# measures the amount of motion of the body: fast joints count more, and each joint has a weight (see
# :doc:`/theory/kinematics_energy`). The trial knows its joints, so ``trial.skeleton`` gives the description the feature needs.
#
# This feature has no ``units`` parameter: it works in the unit of its input. We convert the positions to metres, so that the
# energy is in the usual units (a weight of 1 for every joint makes it joules per kilogram).

from pyeyesweb.low_level import KineticEnergy

metres = trial.to_units("m")
energy = KineticEnergy(skeleton=trial.skeleton, sampling_rate=100)
body = energy.run(metres.positions, timestamps=time)
print(body)
print("outputs:", energy.outputs)

# %%
fig = plot_recorder(body, t=time, title="Kinetic energy of the whole body (KineticEnergy)")

# %%
# **Takeaway.** A feature of the whole body takes frames of shape (joints, 3); give it the unit it expects.

# %%
# From a recorder to a table
# --------------------------
# A recorder is a table with one row per sample. ``recorder[k]`` is the result of sample ``k``, ``recorder["velocity"]``
# (or ``recorder.velocity``) is a column as a NumPy array, ``to_frame()`` a pandas ``DataFrame`` with the status names and
# ``to_numpy()`` the numbers. The last result that was ``OK`` stays in ``feature.latest``.

print(speed[100])
print(speed.to_frame().iloc[[0, 1, 100, 500]])
print(speed.to_numpy().shape, "| latest:", kinematics.latest)

# %%
# Put the two features side by side: the hand moves when the body does. The energy peaks at the claps, where the hands move
# fastest.

# sphinx_gallery_thumbnail_number = 5
fig, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(8, 4.4))
top.plot(time, speed.velocity, color="C0")
top.set_ylabel("hand velocity (mm/s)")
bottom.plot(time, body.kinetic_energy, color="C1")
bottom.set_ylabel("body energy (J/kg)")
bottom.set_xlabel("time (s)")
fig.suptitle("Trial 7, clapping: one joint and the whole body")

# %%
# **Takeaway.** A ``Recorder`` is a table of results; every output is a column, and the status of each row is kept.

# %%
# Try it
# ------
# 1. Compute the velocity of the **left** hand with the same ``Kinematics`` object (``run`` resets it) and plot it together
#    with the right hand. Do the two hands move at the same time?
# 2. Ask ``Kinematics`` for the **acceleration** instead of the velocity (parameter ``output_type``; the output is then named
#    ``acceleration``). At what time is the right hand accelerating most?
# 3. Load trial 8 (the same movement, unsynchronized) from second 5 to second 15 and compare its mean kinetic energy with that
#    of trial 7 over the same seconds.

# %%
# Solutions
# ---------
# Exercise 1. The same feature object, another joint.

left = kinematics.run(trial.joint("Left_Hand"), timestamps=time)
fig, ax = plt.subplots()
ax.plot(time, speed.velocity, label="right hand")
ax.plot(time, left.velocity, label="left hand")
ax.set_xlabel("time (s)")
ax.set_ylabel("velocity (mm/s)")
ax.legend()

# %%
# The two hands rise and fall together: in a clap they meet and part at the same instants.

# %%
# Exercise 2. ``output_type="acceleration"`` makes the output ``acceleration``.

acceleration = Kinematics(sampling_rate=100, units="mm", output_type="acceleration").run(hand, timestamps=time)
peak = int(np.argmax(np.abs(acceleration.acceleration)))
print(f"largest acceleration: {acceleration.acceleration[peak]:.0f} mm/s^2 at {time[peak]:.2f} s")

# %%
# Exercise 3. Another trial, the same seconds, the same feature.

other = load_qualisys_trial(8, start=5, stop=15).to_units("m")
same = load_qualisys_trial(7, start=5, stop=15).to_units("m")
mean_energy = {}
for name, recording in (("synchronized (trial 7)", same), ("unsynchronized (trial 8)", other)):
    mean_energy[name] = energy.run(recording.positions, timestamps=recording.timestamps).kinetic_energy.mean()
    print(f"{name}: mean kinetic energy {mean_energy[name]:.2f} J/kg")

# %%
# Next steps
# ----------
# * :doc:`/concepts/results`: the objects returned by ``process`` and ``run`` in detail.
# * :doc:`/theory/kinematics_energy`: the definitions behind :class:`~pyeyesweb.low_level.Kinematics` and
#   :class:`~pyeyesweb.low_level.KineticEnergy`.
# * :doc:`/api/low_level`: every feature of the layer, with its parameters, inputs and outputs.
# * The next tutorial, :ref:`sphx_glr_tutorials_01_getting_started_plot_02_the_contract.py`, goes through the rules that every feature follows.
