<!-- Sections cut from docs/theory/kinematics_energy.md for the early release (2026-11-13). -->

### Motion noise

A skeleton tracker that loses a joint or mixes its labels produces speeds that jump about at random, and the energy of such
a signal is not movement. {py:class}`~pyeyesweb.low_level.MotionNoiseDetector` tests for this. For each watched joint it
keeps the last 10 speeds and computes their variance; the variance is averaged over 5 frames, and the motion is flagged
as noisy when the mean exceeds `noise_threshold` (a threshold on that variance, written as the block does in square metres and scaled by
`units`). A still body, a uniform drift and the first 14 frames are never flagged. The output `is_noisy` is a boolean,
valid on every call. Two quirks of the original block are kept: with several joints only the alphabetically last joint name that has a full window
counts (whatever the order of `labels`; this is the behaviour of the underlying EyesWeb block, only one joint decides), and the flag stays false until 14 speeds have been seen. Corrected in the core: `reset()` clears the speed windows.

```{doctest}
>>> from pyeyesweb.low_level.motion_noise import MotionNoiseDetector
>>> rng = np.random.default_rng(0)
>>> jumping = rng.normal(scale=0.3, size=(40, 1, 3))                  # a joint that jumps about
>>> feature = MotionNoiseDetector(labels=["hand"], sampling_rate=50.0)
>>> bool(feature.run(np.zeros((40, 1, 3))).is_noisy[-1]), bool(feature.run(jumping).is_noisy[-1])
(False, True)
```

The flag is the `noise` input of {py:class}`~pyeyesweb.mid_level.GestureSegmenter`, which refuses to open a gesture
while it is set ({doc}`gesture_segmentation`).

