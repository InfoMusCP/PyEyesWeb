# Mid-level features

Layer 3 describes a gesture: a movement unit that lasts from half a second to about three seconds, with a beginning and an
end. Where a low-level feature gives a value for each frame, a mid-level feature needs the unit as a whole, or the time over
which a quantity builds up, and gives one value for the gesture.

The early release has no mid-level feature: the segmentation of gestures, `GestureSegmenter`, is held back until its noise test
is finished, and the suddenness, impulsivity and space-occupation features are held back while they are investigated. The
background is in {doc}`../concepts/layers` and {doc}`../theory/framework`. The signals that a mid-level feature will take
are the outputs of layers 1 and 2, for example the kinetic energy of a skeleton ({py:class}`~pyeyesweb.low_level.KineticEnergy`)
and the peaks of a signal ({py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`, {doc}`../theory/gesture_segmentation`).
