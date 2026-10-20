# Entropy, rarity and periodicity

Expressive movement is partly a matter of how predictable it is. A steady walk repeats itself and is easy to anticipate; an
improvised gesture is not. A single unexpected movement in an otherwise regular performance stands out. The features of this
family quantify these three ideas on a one-dimensional signal, for example the speed of a joint, the kinetic energy of the
whole body, or the output of a peak detector:

| Idea | Quantity | Features |
|---|---|---|
| Irregularity of the signal | sample entropy | {py:class}`~pyeyesweb.analysis_primitives.SampleEntropy` |
| Irregularity across time scales | multi-scale entropy, complexity index | {py:class}`~pyeyesweb.analysis_primitives.CoarseGraining`, {py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy` |
| How unusual the current value is | rarity | {py:class}`~pyeyesweb.analysis_primitives.Rarity` |
| Repetition at a period | periods and their power | {py:class}`~pyeyesweb.analysis_primitives.Periodicity` |
| Equal spacing of events | regularity of a pulse train | {py:class}`~pyeyesweb.analysis_primitives.BinaryPulsesRegularity` |

All of them are analysis primitives: they take a signal (one value, or one value per channel, per call) and do not care what
it represents. Except for the instantaneous rarity they work on a window of $N$ samples that slides by a hop $H$
(notation in {doc}`notation`), so they return `WARMING_UP` until the first window is full and `NO_OUTPUT` between two hops
(see {doc}`../concepts/results`). They do not use the sampling rate: lags, periods and scales are counted in samples.

## Sample entropy

Sample entropy measures how unlikely it is that two stretches of the signal that are close to each other for $k$ samples are
still close at the next sample **[citation needed]** (sample entropy, Richman and Moorman). Take the templates $u_k(i)=(x_i,\dots,x_{i+k-1})$ of
length $k$ in a window. Two templates match when every pair of corresponding samples differs by less than a tolerance $r$
(Chebyshev distance). With $B_k$ the number of matching pairs of templates of length $k$, and $A_k$ the number of those pairs
that still match when both are extended by one sample (that is, the number of matching pairs of length $k+1$), the entry for
the template length $k$ is

$$
\mathrm{SampEn}_k = -\ln\frac{A_k}{B_k}, \qquad k=1,\dots,m ,
$$

in nats, where $m$ is `embedding_dimension`. A regular signal, in which a match is usually followed by another match, gives
a ratio $A_k/B_k$ close to 1 and a value close to 0; an irregular signal gives a large value. The value is `inf` or `NaN` when
too few pairs match (a short window, or a tolerance that is too small).

{py:class}`~pyeyesweb.analysis_primitives.SampleEntropy` returns the whole vector $\mathrm{SampEn}_1,\dots,\mathrm{SampEn}_m$,
entry $k-1$ for the template length $k$. The tolerance is `tolerance` in the unit of the signal, or, when it is not given,
`relative_tolerance` (default 0.2) times the standard deviation of the window, so that the result does not depend on the scale
of the signal. One correction of the core: the counts for $k\ge2$ are now properly shifted from one length to the next, and the
default tolerance became relative.

The estimate is only stable on windows of a few hundred samples or more; the number of matches, and so the reliability, falls
quickly with $k$.

## Multi-scale entropy and the complexity index

A signal can be irregular only at the finest scale. White noise has a high sample entropy, but averaging it over longer and
longer stretches destroys its structure and its entropy drops; a signal that remains irregular when observed more slowly
(for example one with structure at several time scales) is called complex {cite}`costa2005multiscale`. Multi-scale entropy
makes this precise in two steps.

**Coarse graining.** For a scale $\tau$ the window $x_1,\dots,x_N$ is replaced by the means of non-overlapping groups of $\tau$
samples,

$$
y^{(\tau)}_j = \frac1\tau\sum_{i=(j-1)\tau+1}^{j\tau} x_i, \qquad j=1,\dots,\lfloor N/\tau\rfloor ,
$$

which is the series seen at the slower sampling rate $f_s/\tau$. {py:class}`~pyeyesweb.analysis_primitives.CoarseGraining`
returns this series for a window, one row per channel; a remainder of fewer than $\tau$ samples is dropped. As in the EyesWeb
block it recomputes the series on the first full window and then every `factor` windows, so with a hop larger than 1 several
of the windows in between have the status `NO_OUTPUT`.

**Entropy curve and complexity index.** {py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy` normalises each signal to unit
standard deviation, coarse-grains it at the scales $\tau=1,\dots,\tau_{\max}$ (`max_scale`) and computes the sample entropy
$E(\tau)$ of each scale (the template length is `embedding_dimension`, the tolerance `tolerance` times the standard deviation of
the normalised series). A scale is used while its coarse-grained series has at least `minimum_points` samples. The
complexity index is the area under the curve by the trapezoid rule,

$$
\mathrm{CI}=\sum_{\tau=1}^{\tau_{\max}-1}\frac{E(\tau)+E(\tau+1)}{2} ,
$$

so it is larger when the entropy stays high across scales. It is non-negative, and `NaN` for a constant signal, which has no
entropy. The feature takes one value per signal per call (a frame of several signals gives one index each), and the indices
of the members of a group are the input of the dominance analysis in {doc}`dominance` {cite}`glowinski2010mse`.
The entropies come from the sample entropy of the core, so they differ from those of the pure-Python 1.x release by $O(1/N)$.

The default window (3000 samples) and `minimum_points` (500) reflect how much data entropy estimates need; with smaller
windows lower both and expect a coarser estimate at the largest scales.

```{doctest}
>>> from pyeyesweb.analysis_primitives import SampleEntropy, MultiScaleEntropy
>>> rng = np.random.default_rng(7)
>>> samples = np.arange(1200)
>>> noise = rng.normal(size=1200)                                             # irregular at every scale
>>> oscillation = np.sin(2 * np.pi * samples / 50) + 0.1 * rng.normal(size=1200)  # regular, with a little noise
>>> for name, signal in [("noise", noise), ("oscillation", oscillation)]:
...     sampen = SampleEntropy(window=200, embedding_dimension=2).run(signal)[-1].sample_entropy
...     mse = MultiScaleEntropy(window=1200, max_scale=6, minimum_points=100).run(signal)[-1]
...     print(name, sampen.round(2), mse.complexity_index.round(2), mse.scale_entropies.round(2))
noise [2.18 2.19] [12.55] [[2.47 2.46 2.44 2.5  2.77 2.27]]
oscillation [2.04 0.74] [2.54] [[0.96 0.71 0.59 0.48 0.13 0.3 ]]
```

The noise keeps an entropy between 2.3 and 2.8 at all six scales, so its index is large; the oscillation, which is easy to
predict once a few samples are known, has a lower entropy at the finest scale and a small index.

## Rarity

Rarity tells how atypical the newest value of a signal is with respect to the values that preceded it: a value that has
occurred often in the recent past is common, a value that has hardly occurred is rare. It can flag the unusual movement in a
performance. Rarity is one of the mid-level qualities used in the sonification study of {cite}`niewiadomski2019embodied`.
{py:class}`~pyeyesweb.analysis_primitives.Rarity` offers two different formulas, selected by `method`; they are not special
cases of one another, they have different parameters and a parameter of the other method raises an error.

`method="information"` (the EyesWeb rarity, the default) discretises each of `number_of_inputs` scalar signals into bins of
the widths `bins` and gives, for each input,

$$
R=-\ln(AB+10^{-16}),
$$

where $A$ and $B$ are two probability terms estimated from the occupancy of the bins **[citation needed]** (the EyesWeb rarity
and contrast measures). With `measure="rarity"` they are estimated from a memory of the last `window` values of the same
input, so $R$ is a rarity across time; with `measure="contrast"` they are estimated across the inputs, so $R$ is a contrast
between signals. A rare value gives a large $R$. The feature keeps its own memory, one sample per call; the memory starts
filled with zeros, so until `window` samples have been seen the status is `WARMING_UP` and the numbers are artefacts.

`method="mode_distance"` is a self-contained score for one stream. The histogram of the window of $N$ samples has
$\max(\lfloor\sqrt N\rfloor,1)$ equal-width bins. With $i_{\mathrm{mode}}$ the index of the most populated bin,
$i_{\mathrm{last}}$ the bin of the newest sample and $p$ the fraction of the window in a bin,

$$
R=\alpha\,\lvert i_{\mathrm{mode}}-i_{\mathrm{last}}\rvert\,(p_{\mathrm{mode}}-p_{\mathrm{last}}),
$$

with `alpha` a gain. $R=0$ when the newest sample is in the most common bin and grows with its distance from it and with how
much less frequent its own bin is. It needs no bin widths. Use `"information"` to reproduce EyesWeb or to compare several
signals with chosen bin widths, and `"mode_distance"` for a score of a single stream.

Both methods report `INVALID_INPUT` for a non-finite value. With `"information"`, a value beyond the sum of the bin widths is
outside the bins: it keeps the previous bin and the call is `INVALID_INPUT` (reason `"value outside the bins"`).

```{doctest}
>>> from pyeyesweb.analysis_primitives import Rarity
>>> rarity = Rarity(method="mode_distance", window=20, alpha=1.0)
>>> stream = np.tile([0.0, 0.1], 20)                  # a regular back-and-forth
>>> stream[-1] = 1.0                                  # and then a sudden large value
>>> recording = rarity.run(stream)
>>> recording.rarity[-3:].round(2)
array([0. , 0. , 2.7])
```

## Periodicity

Periodic movements, such as steady steps or a repeated gesture, repeat after a fixed number of samples.
{py:class}`~pyeyesweb.analysis_primitives.Periodicity` finds the periods of each channel of a window with the Periodicity
Transform **[citation needed]** (Periodicity Transform, Sethares and Staley), which decomposes a signal into periodic components. It returns two arrays of
shape `(channels, columns)`: the detected `periods` in samples and their normalised `powers`, where a perfectly periodic signal
has a power of 1 and unused entries are $-1$. The number of columns depends on the method (`"small2large"`, from the smallest
period upward, or `"mbest"`, the `best_periods` best periods) and on the window, so these two outputs are not part of the
numeric table of the recording. Convert a period to seconds by dividing it by the sampling rate $f_s$. A window should contain
several repetitions of the period of interest.

```{doctest}
>>> from pyeyesweb.analysis_primitives import Periodicity
>>> signal = np.tile([1.0] + [0.0] * 24, 8)                  # a pulse every 25 samples (0.25 s at 100 Hz)
>>> result = Periodicity(window=200).run(signal)[-1]
>>> result.periods[0, :2], result.powers[0, :2].round(2)
(array([25., -1.]), array([ 1., -1.]))
```

The pulse train has one period and a power of 1. A sinusoid of the same period, run on the same window, is reported at the
neighbouring periods 24 and 26 samples with powers well below 1 (0.42 and 0.28): read the power as the strength of the repetition at that period, and look for the smallest
period with a high power.

## Regularity of a pulse train

A pulse is a non-zero sample of a single-channel signal: a step, a beat, or the `is_peak` flag of
{py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`. {py:class}`~pyeyesweb.analysis_primitives.BinaryPulsesRegularity`
asks whether the pulses of a window are equally spaced. The distance between the first two pulses of the window is the
reference interval; the window is regular when at least three pulses are found and every later interval differs from the
reference by at most `threshold` samples. It returns `is_regular`, the `pulse_count` and `is_regularity_detected`, a trigger
that is true on the first window that is regular after one that was not. It measures the regularity of a rhythm, such as a
steady walk or a metronomic gesture, and complements the periodicity, which finds the period but does not require the events
to be equally spaced.

```{doctest}
>>> from pyeyesweb.analysis_primitives import BinaryPulsesRegularity
>>> feature = BinaryPulsesRegularity(window=12, threshold=1)
>>> steady = np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], dtype=float)
>>> uneven = np.array([1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0], dtype=float)
>>> for pulses in (steady, uneven):
...     result = feature.run(pulses)[-1]
...     print(result.is_regular, result.pulse_count)
True 4
False 4
```

## Practical notes

- Window length decides everything here. Entropy and periodicity need windows of several repetitions of the behaviour (a
  few hundred samples for sample entropy, thousands for multi-scale entropy); a short window yields `NaN`/`inf` entropies
  or unstable periods. Choose the window in seconds and convert it with $N=\lceil T f_s\rceil$.
- The outputs of the windowed features refer to the last complete window, and the `timestamp` is that of its newest sample.
  Passing `hop` larger than 1 saves computation and gives `NO_OUTPUT` between windows.
- Sample entropy and multi-scale entropy assume a stationary signal over the window; trends and changes of level inflate the
  entropy. Remove a trend, or work on the speed rather than on the position.
- Entropy values are in nats and depend on the template length and the tolerance: compare only values computed with the same
  settings.
- A constant signal has no entropy (`NaN` for the multi-scale index) and no period.

## Further reading

Multi-scale entropy was introduced for physiological signals {cite}`costa2005multiscale` and applied to movement in the
study of dominance in social creative activities {cite}`glowinski2010mse`. The derived features are described in
{doc}`dominance`; the generated pages of the API reference list every parameter.
