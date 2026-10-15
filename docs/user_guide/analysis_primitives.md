# Analysis primitives

The analysis primitives are the measures that belong to no layer of the conceptual model ({doc}`../theory/framework`) because
they know nothing of bodies, skeletons or geometry: they take any scalar, vector or event signal and describe it. How regular a
signal is, how periodic, how rare its latest value is, how two signals move together. They can be applied to a layer-1
signal, to the output of a low-level feature or to a mid-level one, and they have no timescale of their own; the timescale is
that of the signal and of the window you give. The group has {{ n_analysis_primitives }} features; this page helps to
choose among them. The groups are described in {doc}`../concepts/layers`.

```{feature-table} analysis_primitives
```

## Which feature for which question

**How regular or complex is the signal?** {py:class}`~pyeyesweb.analysis_primitives.SampleEntropy` measures the irregularity of a
window; {py:class}`~pyeyesweb.analysis_primitives.CoarseGraining` produces the same signal at a slower scale;
{py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy` combines both into a curve over scales and a complexity index
{cite}`costa2005multiscale`, the input of the dominance analysis of {doc}`high_level`.
{py:class}`~pyeyesweb.analysis_primitives.Rarity` tells how rare the newest value is within a memory of past values.
Theory: {doc}`../theory/entropy_rarity_periodicity`.

**Is it periodic, and are the pulses regular?** {py:class}`~pyeyesweb.analysis_primitives.Periodicity` finds the periods of
each channel of a window by the Periodicity Transform, with their normalised power;
{py:class}`~pyeyesweb.analysis_primitives.BinaryPulsesRegularity` tells whether the pulses of a window are equally spaced. For
the peaks of a signal use {py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`, which flags the samples at which a peak
has been found. Theory: {doc}`../theory/entropy_rarity_periodicity` and {doc}`../theory/gesture_segmentation`.

**Do two or more signals move together?** The synchronization measures are the largest family and are chosen by the kind of
signal.

- Continuous signals: {py:class}`~pyeyesweb.analysis_primitives.PhaseLockingValue` for the phase relation of two signals in a
  band, {py:class}`~pyeyesweb.analysis_primitives.CorrelationsMatrix` and
  {py:class}`~pyeyesweb.analysis_primitives.PartialRecurrenceSynchronization` for the correlation of a group and the direct
  link of each pair, and {py:class}`~pyeyesweb.analysis_primitives.NonlinearInterdependence` when the relation is not linear.
- Recurrence: {py:class}`~pyeyesweb.analysis_primitives.RecurrencePlot` for when a movement returns to a state it visited,
  {py:class}`~pyeyesweb.analysis_primitives.CrossRecurrencePlot` for when one movement visits states of another, and
  {py:class}`~pyeyesweb.analysis_primitives.GeneralisedAutoCorrelation` for the recurrence rate as a function of the lag.
- Events: {py:class}`~pyeyesweb.analysis_primitives.EventSynchronization`,
  {py:class}`~pyeyesweb.analysis_primitives.EventSynchronizationMECS` and
  {py:class}`~pyeyesweb.analysis_primitives.SpikeSynchronization` for trains of events, and
  {py:class}`~pyeyesweb.analysis_primitives.SequenceDetector` for a given sequence of integer events in a stream.
- Staged processes: {py:class}`~pyeyesweb.analysis_primitives.TemporalSynchronization` follows the progression of a
  synchronization process from a chain of synchronization values.

Theory: {doc}`../theory/synchronization`. The synchronization of a group of musicians is the setting of
{cite}`sabharwal2022husync`.

## A typical pipeline

A primitive takes any series, such as the output of another feature, a joint coordinate or a respiration trace. Here a sine
and white noise are measured by the sample entropy of the last window, for template length 2: the regular signal has the
lower entropy.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.analysis_primitives import SampleEntropy
>>> rng = np.random.default_rng(1)
>>> n = np.arange(400)
>>> regular = np.sin(2 * np.pi * n / 40)
>>> irregular = rng.standard_normal(400)
>>> entropy = SampleEntropy(window=200, embedding_dimension=2)
>>> a = entropy.run(regular).sample_entropy[-1, -1]               # template length 2, last window
>>> b = entropy.run(irregular).sample_entropy[-1, -1]
>>> round(float(a), 2), round(float(b), 2)
(0.39, 2.19)
```

## What to know before choosing

- A window feature takes `window` samples and `hop`, and is `WARMING_UP` until the window is full
  ({doc}`../concepts/results`). Choose the window in seconds first and multiply by the sampling rate: some metrics have
  minimum lengths, which the constructors check.
- Primitives work on arrays and know nothing of units: the unit of the output follows from the input and is stated on each
  API page.
- Synchronization measures take several signals in one call; event measures take trains of events, not continuous signals:
  build them first, for instance with `ScalarPeakDetector`.
- Time is in seconds, and a feature that needs a rate takes `sampling_rate` ({doc}`../concepts/time_units_parameters`).

% TODO(WP7): gallery link
