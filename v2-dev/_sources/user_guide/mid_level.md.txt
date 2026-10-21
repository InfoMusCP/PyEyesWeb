# Mid-level features

Layer 3 describes a gesture: a movement unit that lasts from half a second to about three seconds, with a beginning and an
end. Where a low-level feature gives a value for each frame, a mid-level feature needs the unit as a whole, or the time over
which a quantity builds up, and gives one value for the gesture: where it starts and ends, how long it lasts, how sudden or
impulsive it is, how much of the space it occupied. The layer has {{ n_mid_level }} features; this page helps to choose among
them. The background is in {doc}`../concepts/layers` and {doc}`../theory/framework`.

```{feature-table} mid_level
```

## Which feature for which question

**Where are the gestures?** {py:class}`~pyeyesweb.mid_level.GestureSegmenter` turns an intensity signal, typically the
kinetic energy of a skeleton, into the start and the end of gestures, with an optional flag that keeps noise from opening a
gesture. {py:class}`~pyeyesweb.mid_level.MotionDuration` measures the length of the motion phases and of the pauses of its
output. Most of the other features of this layer are computed over a gesture, so segmentation is usually the first step.
Theory: {doc}`../theory/gesture_segmentation`.

**How sudden or impulsive is it?** {py:class}`~pyeyesweb.mid_level.Suddenness` fits a stable distribution to the speeds
of a trajectory and tells how heavy the tail of the distribution is, that is how often the movement has abrupt speed changes.
{py:class}`~pyeyesweb.mid_level.SuddennessImpulsivity` gives the direction change of the trajectory when it is also sudden, and
{py:class}`~pyeyesweb.mid_level.ContractionImpulsivity` the change per second of the contraction index over a short, energetic
gesture. Theory: {doc}`../theory/impulsivity_suddenness`. The quality of impulsivity is defined in {cite}`mazzarino2009need`.

**How is the space occupied?** {py:class}`~pyeyesweb.mid_level.PositionDependingPotentials` and
{py:class}`~pyeyesweb.mid_level.RegionDependingPotentials` turn the grid cells hit by a point
({py:class}`~pyeyesweb.physical_signals.HitCellDetector`, layer 1) into potentials with a memory of past hits: a cell that is
visited often keeps a high potential and the potential decays where nobody goes. Theory: {doc}`../theory/shape_symmetry_balance`.

## A typical pipeline

The mid-level features are fed by the outputs of layers 1 and 2. A point makes two reaches of 0.4 m, with pauses before and
between them. Its kinetic energy is the intensity that the segmenter takes, and the segmentation signal goes to
`MotionDuration`.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.low_level import KineticEnergy
>>> from pyeyesweb.mid_level import GestureSegmenter, MotionDuration
>>> rate = 50.0
>>> time = np.arange(0.0, 8.0, 1.0 / rate)
>>> def reach(start, stop, amplitude):
...     s = np.clip((time - start) / (stop - start), 0.0, 1.0)
...     return amplitude * (10 * s**3 - 15 * s**4 + 6 * s**5)      # minimum-jerk profile
>>> x = reach(1.0, 3.0, 0.4) - reach(5.0, 7.0, 0.4)
>>> position = np.column_stack([x, np.zeros_like(x), np.zeros_like(x)])
>>> energy = KineticEnergy(labels=["hand"], weights={"hand": 1.0}, sampling_rate=rate).run(position[:, None, :])
>>> round(float(energy.kinetic_energy.max()), 3)
0.07
>>> segmentation = GestureSegmenter(firing_threshold=0.005).run(energy.kinetic_energy)
>>> (np.flatnonzero(segmentation.is_gesture_start) / rate).tolist()     # seconds
[1.42, 5.42]
>>> (np.flatnonzero(segmentation.is_gesture_end) / rate).tolist()
[2.82, 6.82]
>>> durations = MotionDuration(sampling_rate=rate).run(segmentation.is_gesturing.astype(float))
>>> float(np.nanmax(durations.motion_duration)), float(np.nanmax(durations.pause_duration))
(1.4, 2.6)
```

The first gesture is found from 1.42 s to 2.82 s, although the reach lasts from 1.0 s to 3.0 s: the segmenter smooths the
intensity and declares a gesture while it is at least `firing_threshold` (in the unit of the intensity), so the start is late
by a few samples and the slow beginning and end of a reach, where the energy is low, are left out. The threshold fixes how much
of the movement counts as a gesture. The gestures can then be cut from the signals of layer 2 and summarised, for
example with {py:class}`~pyeyesweb.low_level.SpectralArcLength` on the speed of each gesture, or measured by the
suddenness features.

## What to know before choosing

- A mid-level feature takes the signals of one unit of movement, but it does not cut them for you: most of them work on a
  window you size to the gesture, in samples, or on a signal that you segmented.
- The time-dependent features take `sampling_rate` or timestamps; without a rate the durations are in samples
  ({doc}`../concepts/time_units_parameters`).
- The potentials need the cells of `HitCellDetector`, a layer-1 feature, and keep a memory across calls: `reset()` them
  between recordings.

Hands-on: see {ref}`sphx_glr_tutorials_04_mid_level_plot_07_gestures.py`.
