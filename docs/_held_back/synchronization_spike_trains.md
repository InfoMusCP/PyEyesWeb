<!-- Sections cut from docs/theory/synchronization.md for the early release (2026-11-13). -->

## Spike trains

A spike train is an event series for which a good coincidence window is not known in advance, as in the firing of neurons or
in irregular gestures. SPIKE-synchronization has no time-scale
parameter: coincidence is decided adaptively from the local spike intervals. Each spike receives a coincidence
indicator, 1 if it coincides with a spike of another train and 0 if it does not; the degree of synchronization is the mean of
the indicator over all the spikes of all the trains (a spike shared by two trains counts twice), and the distance is
$1-\text{degree}$. {py:class}`~pyeyesweb.analysis_primitives.SpikeSynchronization` takes `number_of_inputs` trains in one of two
modes. In `"binary"` mode each call gives one sample with a channel per train (non-zero is a spike), and the feature also
returns the `profile`, the coincidence indicator of the merged spikes at each sample (-1 where no train has a spike). In
`"timings"` mode each call takes a matrix whose rows are the spike times of the trains (positive and increasing, in any unit)
and nothing is carried from one call to the next; it is `OK` for every call. The core fixed in this feature the swap of the
degree and the distance in binary mode and the use of distinct spike positions instead of all spikes in the mean.

```{doctest}
>>> from pyeyesweb.analysis_primitives.synchronization.events import SpikeSynchronization
>>> trains = np.zeros((50, 2))
>>> trains[[5, 20, 35], 0] = 1
>>> trains[[5, 21, 40], 1] = 1
>>> record = SpikeSynchronization(window=50).run(trains)
>>> float(record.degree[-1]), float(record.distance[-1])
(1.0, 0.0)
```

