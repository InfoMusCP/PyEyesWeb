# Gesture segmentation

A movement recorded over seconds or minutes is a stream of samples, but it is perceived and described as a sequence of
units: a wave, a step, a strike, separated by moments of stillness. To say how long a gesture lasted, how energetic it was or
how smooth, the stream must first be cut into gestures. Segmentation is therefore the step that takes a movement from the
low-level layer, where there is one value for each sample, to the mid-level layer, where there is one value for each movement
unit ({doc}`framework`).

The segmentation of an intensity signal into gestures and pauses, `GestureSegmenter`, is held back from the early release
until its noise test is finished, so no mid-level feature is released yet. The released feature of the family is
{py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`, which finds the peaks of a signal; the peaks locate events
inside a gesture or between gestures. The symbols are those of {doc}`notation`.

## Peaks of a signal

A gesture often contains events: the moment of maximum speed, the stroke of a beat. {py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`
keeps a buffer of the last `window` samples (5 by default) of a scalar signal and reports a peak when the buffered signal shows a fall after
a rise, each larger than `threshold`: the threshold is a swing (the largest minus the smallest value of the buffer), not a level,
and only maxima are reported, not minima. The output is `is_peak`, true on the sample at which the peak is reported, with a delay of up to
`window` samples after the maximum, once the fall is in the buffer. It is an analysis primitive because it knows
nothing of bodies, and its output, a stream of events, is the input of the measures of regularity and synchronization of
events ({doc}`entropy_rarity_periodicity`, {doc}`synchronization`). Corrected in the core: the running maximum was seeded with
the smallest positive number, so a signal that stays at or below 0 never produced a peak.

```{doctest}
>>> from pyeyesweb.analysis_primitives import ScalarPeakDetector
>>> detector = ScalarPeakDetector(window=3, threshold=0.5)
>>> [detector.process(value).is_peak for value in [0, 1, 3, 1, 0, 0, 2, 0, 0, 0]]
[False, False, False, False, True, False, False, False, True, False]
```

The peaks are reported on samples 4 and 8, two samples after the maxima at samples 2 and 6.

## How to read the output

| Feature | Output | Unit | Meaning |
|---|---|---|---|
| `ScalarPeakDetector` | `is_peak` | none | a peak was found on this sample |

The peak is reported after the maximum, by the delay of the buffer, so the output is available after the event it describes.
A recording is analysed offline with `run`; in a stream, the output of each call is acted upon as it arrives.

## Further reading

The framework in which segmentation is the step from layer 2 to layer 3: {cite}`camurri2016dancer`. A related method for the
identification of salient moments in motion capture data: {cite}`romano2024computational`. The EyesWeb library from which these
blocks come: {cite}`camurri2003eyesweb`.
