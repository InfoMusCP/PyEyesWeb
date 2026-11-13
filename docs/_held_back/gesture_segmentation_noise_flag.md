<!-- Sections cut from docs/theory/gesture_segmentation.md for the early release (2026-11-13). -->

### The noise flag

A skeleton tracker may lose a joint, and the speed of a joint that jumps about at random gives an intensity that looks like a
gesture and is not. The `noise` input is a second stream, one flag for each sample, that is true while the motion is judged to
be noise, and while it is set no gesture can start. The flag is computed by
{py:class}`~pyeyesweb.low_level.MotionNoiseDetector` (output `is_noisy`) on the same frames ({doc}`kinematics_energy`). With several joints the detector is decided by the
alphabetically last joint name: this is the behaviour of the underlying EyesWeb block, and only one joint decides.
Without a flag the feature segments any one-dimensional signal. The call is `process(intensity, noise=False, *, timestamp=None)`
and `run(intensity, noise=None, *, timestamps=None)`.

