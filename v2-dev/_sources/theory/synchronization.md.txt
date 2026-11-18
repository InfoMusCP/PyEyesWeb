# Synchronization

Two dancers who move in unison, a quartet that breathes together, two hands that keep the same rhythm: synchronization is the
degree to which the movements of several participants, or of several parts of the same body, are coordinated in time. There is
no single measure of it, because coordination can mean different things: the signals rise and fall together, their phases
stay locked, their discrete events occur at the same moments, their trajectories visit the same states. The seven features of
this family are organised here by **what is compared**.

| What is compared | Quantity | Features |
|---|---|---|
| The phases of two signals | phase locking value | {py:class}`~pyeyesweb.analysis_primitives.PhaseLockingValue` |
| Two or more series of events | event synchronization | {py:class}`~pyeyesweb.analysis_primitives.EventSynchronization`, {py:class}`~pyeyesweb.analysis_primitives.EventSynchronizationMECS` |
| The states visited by one or two movements | recurrence | {py:class}`~pyeyesweb.analysis_primitives.RecurrencePlot`, {py:class}`~pyeyesweb.analysis_primitives.CrossRecurrencePlot`, {py:class}`~pyeyesweb.analysis_primitives.GeneralisedAutoCorrelation` |
| The members of a group | partial correlation | {py:class}`~pyeyesweb.analysis_primitives.PartialRecurrenceSynchronization` |

Notation is that of {doc}`notation`: samples are indexed by $n$, a window has $N$ samples and slides by a hop $H$. With one
exception that is stated below, the measures work on such a window, return `WARMING_UP` until it is full and `NO_OUTPUT` between
two hops (see {doc}`../concepts/results`), and count time in samples (`lag`, `max_lag` and event intervals), not in seconds. A pair
of signals is passed to `process` one sample of each per call, and to `run` as two series of the same length. Inputs to
the measures are one signal per participant: for 2D or 3D data, reduce each participant to a scalar first, for example the
speed from {py:class}`~pyeyesweb.low_level.Kinematics`.

Synchronization measures assume that the coordination is stationary over the window. Choose the window so that it contains
several cycles of the movement and so that the coordination does not change within it.

## Phase

For oscillatory movement, such as the swing of two arms or the steps of two walkers, synchronization is often a matter of
phase: the signals may have different amplitudes and a constant lag and still be perfectly coordinated. The phase locking
value (PLV) measures this {cite}`lachaux1999measuring`; it has been applied to the movement of groups in
{cite}`sabharwal2022husync`. The PLV of Lachaux et al. averages over repeated trials at each instant; movement data has no
repeated trials, so the feature computes the single-trial form, the PLV over time within a window, also called the *mean
phase coherence* {cite}`mormann2000mean`. Each window of each signal is optionally band-pass filtered, its mean is removed,
it is tapered with a Hann window, and the instantaneous phase $\phi(n)$ is taken from the analytic signal obtained with the
Hilbert transform,

$$
z_x(n)=x(n)+i\,\mathcal{H}[x(n)],\qquad \phi_x(n)=\arg z_x(n),\qquad \Delta\phi(n)=\phi_x(n)-\phi_y(n),
$$

and the PLV is the length of the mean phasor of the phase difference over the middle 80 % of the $N$ samples of the
window (the 10 % at each end, distorted by the edges of the Hilbert transform, are left out, as in Mormann et al.),

$$
\mathrm{PLV}=\left|\frac{1}{N-2k}\sum_{n=k+1}^{N-k}e^{\,i\,\Delta\phi(n)}\right|\in[0,1],\qquad k=\lfloor 0.1N\rfloor .
$$

It is 1 when the phase difference is constant over the window (perfect locking, whatever the offset), and close to 0 when it is
spread uniformly (no phase relation). {py:class}`~pyeyesweb.analysis_primitives.PhaseLockingValue` implements it and
returns `phase_locking_value` for the last complete window.

The Hilbert phase is only meaningful for **narrow-band, oscillatory** signals; Lachaux et al. band-pass at $f\pm2$ Hz before
taking it. On broadband data the value is not a phase relation: independent white noise gives about 0.08 on 200 samples, but
independent random walks about 0.57, because each window is dominated by one slow trend. Nothing is filtered unless
`low_frequency` and `high_frequency` (with the `sampling_rate`) are given, so either band-limit the signals first or pass the
band, and use windows of several whole periods. A constant signal has no phase: the result is `INVALID_INPUT`.

```{doctest}
>>> from pyeyesweb.analysis_primitives import PhaseLockingValue
>>> time = np.arange(200) / 100.0
>>> reference = np.sin(2 * np.pi * 3.0 * time)
>>> locked = np.sin(2 * np.pi * 3.0 * time + 0.5)                 # same rhythm, shifted by 0.5 rad
>>> drifting = np.sin(2 * np.pi * 4.3 * time)                     # a different rhythm
>>> plv = PhaseLockingValue(window=200, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0)
>>> round(float(plv.run(reference, locked).phase_locking_value[-1]), 2)
0.99
>>> plv.reset()
>>> round(float(plv.run(reference, drifting).phase_locking_value[-1]), 2)
0.04
```

## Event series

Many movement data are discrete events rather than signals: the onsets of gestures, the beats of a performer, the peaks found
by {py:class}`~pyeyesweb.analysis_primitives.ScalarPeakDetector`. Event synchronization measures the coordination of two such
series without assuming a fixed rhythm {cite}`quiroga2002event`. In the input a
non-zero sample is an event. With $m_x$ and $m_y$ events in the first and in the second series, and $c(y|x)$ the number of events
of the second series that follow an event of the first within `max_lag` samples (and $c(x|y)$ the converse), the feature
{py:class}`~pyeyesweb.analysis_primitives.EventSynchronization` reports

$$
Q=\frac{c(x|y)+c(y|x)}{\sqrt{m_x m_y}}\in[0,1],\qquad q=\frac{c(y|x)-c(x|y)}{\sqrt{m_x m_y}}\in[-1,1].
$$

$Q=1$ means that every event of each series has a partner in the other. $q>0$ means that the first series leads, $q<0$ that the
second does; simultaneous events count for $Q$ but not for $q$. The outputs are `synchronization` ($Q$) and `delay` ($q$).

The feature works on consecutive windows that do not overlap: `hop` equals `window` (its default) and any other value raises
`ValueError`. It gives one result per window (`OK` once per window) and no `NO_OUTPUT`, the exception to the sliding windows of
the family. By default each window is evaluated on its own; with `reset_every_buffer=False` the counts accumulate across
windows, so the value of a window describes the whole recording up to its end (the cumulative index of the paper).

$Q$ depends strongly on `max_lag`: the same two series give a low $Q$ with a small `max_lag` and a $Q$ close to 1 with a large
one, so choose `max_lag` from the lags that count as simultaneous in your data.

Corrected in the core: the result follows the definition above, with the coincidence window $0<\text{lag}\le$ `max_lag`, the
sign of the delay given here, and each event credited exactly once.

{py:class}`~pyeyesweb.analysis_primitives.EventSynchronizationMECS` (multi-event-class synchronization) extends the measure
to `number_of_inputs` series that carry events of several classes (for example one channel per type of gesture) {cite}`alborno2019multi`. For every class and every pair of series, the coincidences
$S_{ij}$ are the pairs of events less than `max_lag` samples apart, weighted by the `kernel` (by default linear, $1-d/$`max_lag`,
the kernel of the paper); with $m_i$ and $m_j$ the event counts of the two series the
pair term is $\min\!\big(1,S_{ij}/\sqrt{m_im_j}\big)$, and the synchronization of the class is the mean of the pair terms over
the $M(M-1)/2$ pairs of the $M$ series. The normalisation by $\sqrt{m_im_j}$ departs from the paper's $m_im_j$, with which two
identical trains never reach 1. It returns the `synchronization` of each class and the number of `events` of each class
in the window, summed over the series, and also needs non-overlapping windows. As in the paper, the last `max_lag` samples of
a window are carried into the next one, so pairs across the boundary are found; it has no `reset_every_buffer`, and it depends
on `max_lag` in the same way. Only the synchronization within each class is computed (the former "version 2" of the
algorithm); the inter-class part of the paper is not implemented.

```{doctest}
>>> from pyeyesweb.analysis_primitives import EventSynchronization
>>> first, second = np.zeros(60), np.zeros(60)
>>> first[[5, 25, 45]] = 1                    # three events of the first performer
>>> second[[7, 27, 56]] = 1                   # the second follows two of them within 3 samples
>>> record = EventSynchronization(window=60, max_lag=3).run(first, second)
>>> round(float(record.synchronization[-1]), 2), round(float(record.delay[-1]), 2)
(0.67, 0.67)
```

## Recurrence

Recurrence analysis compares a movement with itself or with another movement in the space of states {cite}`marwan2007recurrence`, and the lab uses it to measure the synchronization of a group
{cite}`varni2010system`. For a window of states $\mathbf{x}_n$ (one value per
channel, for example the posture of a participant), the recurrence plot is the binary matrix

$$
R_{ij}=\Theta\big(\epsilon_i-\lVert\mathbf{x}_i-\mathbf{x}_j\rVert_p\big),\qquad
\lVert\mathbf{v}\rVert_p=\Big(\sum_c|v_c|^p\Big)^{1/p},
$$

with $\Theta$ the Heaviside step, $\Theta(0)=1$ (a distance equal to $\epsilon$ is a recurrence, as in
{cite}`marwan2007recurrence`, eq. 10), $p$ the `order` and $\epsilon_i$ the
threshold of row $i$ (`epsilon`, or one per row with `use_multiple_epsilons`, in the recurrence plot only). The diagonal is 1. A periodic movement draws
diagonal lines, whose spacing is the period; a movement that stays in one posture draws blocks.
{py:class}`~pyeyesweb.analysis_primitives.RecurrencePlot` returns the matrix of the last complete window as
`recurrence_matrix`, of shape $(N,N)$.

The cross-recurrence plot compares two multichannel signals with the same channels, for example two participants performing
the same gesture: $R_{ij}=\Theta(\epsilon-\lVert\mathbf{x}_i-\mathbf{y}_j\rVert_p)$, with $\mathbf{x}$ from the first signal
and $\mathbf{y}$ from the second, and one threshold $\epsilon$ (`epsilon`) for every row. Long diagonal lines mean that the two follow the same trajectory, possibly with a time shift, and
the offset of the line from the main diagonal is that shift. {py:class}`~pyeyesweb.analysis_primitives.CrossRecurrencePlot`
returns `cross_recurrence_matrix`. In both, the core corrected the `order`, which used to be ignored (the distance was always
Euclidean).

```{eval-rst}
.. plot::
   :context: close-figs
   :include-source: true

   import matplotlib.pyplot as plt
   import numpy as np
   from pyeyesweb.analysis_primitives import CrossRecurrencePlot, RecurrencePlot

   n = np.arange(100)
   phase = 2 * np.pi * n / 25
   leader = np.column_stack([np.sin(phase), np.cos(phase)])                          # a circular movement, 2 channels
   follower = np.column_stack([np.sin(phase - 0.8), np.cos(phase - 0.8)])            # the same, 0.8 rad (about 3 samples) later

   self_plot = RecurrencePlot(window=100, epsilon=0.2).run(leader).recurrence_matrix[-1]
   cross_plot = CrossRecurrencePlot(window=100, epsilon=0.2).run(leader, follower).cross_recurrence_matrix[-1]

   fig, (left, right) = plt.subplots(1, 2, figsize=(6.4, 3.2))
   left.imshow(self_plot, origin="lower", cmap="Greys")
   left.set_title("recurrence plot")
   right.imshow(cross_plot, origin="lower", cmap="Greys")
   right.set_title("cross-recurrence plot")
   for axis in (left, right):
       axis.set_xlabel("sample j")
   left.set_ylabel("sample i")
   fig.tight_layout()
```

The first plot shows diagonal lines spaced by the period of 25 samples; in the second the diagonals are displaced from the
main one by the delay between the two movements (0.8 rad of a cycle of 25 samples, about 3 samples).

The recurrence plot is a picture. {py:class}`~pyeyesweb.analysis_primitives.GeneralisedAutoCorrelation` reduces the
recurrence of a window of $N$ multichannel states to a number as a function of the lag $\tau$ in samples: the recurrence rate

$$
\mathrm{RR}(\tau)=\frac1{N-\tau}\,\#\big\{\,i<N-\tau:\ \lVert\mathbf{x}_i-\mathbf{x}_{i+\tau}\rVert\le\epsilon\,\big\},
$$

the fraction of states that return within $\epsilon$ after $\tau$ samples. A periodic movement has peaks of $\mathrm{RR}$ at
the multiples of its period. With `output_type="function_of_tau"` the feature returns the rates at the lags 1 to `max_lag` (and
the lags in `taus`); with `output_type="scalar"` it returns the rate at the single lag `lag`.

```{doctest}
>>> from pyeyesweb.analysis_primitives import GeneralisedAutoCorrelation
>>> states = np.sin(2 * np.pi * np.arange(200) / 50)[:, None]      # a movement with a period of 50 samples
>>> for lag in (25, 50):
...     rate = GeneralisedAutoCorrelation(window=200, output_type="scalar", lag=lag, epsilon=0.1).run(states).recurrence_rate[-1]
...     print(lag, round(float(rate[0]), 2))
25 0.04
50 1.0
```

## Group synchronization

For a group of $M$ participants the question is how the members are coordinated pair by pair.

**Correlation.** The starting point is the matrix $C$ of the Pearson correlations $C_{kl}=\rho(s_k,s_l)$ of the signals (one per
participant or per body segment) over a window. It is `numpy.corrcoef`: the entries are signed and lie in $[-1,1]$, with 1 on
the diagonal. A signal that is constant over the window has no defined correlation, and its row and column are `NaN`.

**Direct synchronization.** Two participants can correlate only because both follow a third one. With $P=C^{-1}$,
{py:class}`~pyeyesweb.analysis_primitives.PartialRecurrenceSynchronization` removes the part of each correlation that the other
signals explain and returns the absolute partial correlation

$$
S_{kl}=\frac{|P_{kl}|}{\sqrt{P_{kk}P_{ll}}},
$$

{cite}`varni2010system` (eq. 4). It takes the matrix as input, so it is applied to the output of `numpy.corrcoef`; it has
no window of its own. In the paper the matrix holds the CPR index of each pair, `numpy.corrcoef` of the recurrence-rate
curves of {py:class}`~pyeyesweb.analysis_primitives.GeneralisedAutoCorrelation` (Varni eq. 3). A matrix with a `NaN` entry,
a matrix too ill-conditioned to invert (condition number above $10^{12}$, as for constant or perfectly collinear signals)
and a matrix that is not positive definite (a diagonal entry of $P$ not positive, so not a correlation matrix) are
`INVALID_INPUT`.

In the example the signal $b$ follows $a$ and $c$ follows $b$ with noise. All three are correlated, but $a$ and $c$ only through
$b$, which the partial correlation shows.

```{doctest}
>>> from pyeyesweb.analysis_primitives import PartialRecurrenceSynchronization
>>> rng = np.random.default_rng(5)
>>> a = rng.normal(size=300)
>>> b = a + 0.7 * rng.normal(size=300)
>>> c = b + 0.7 * rng.normal(size=300)
>>> correlations = np.corrcoef(np.column_stack([a, b, c])[-300:].T)      # the last 300 samples, one row per signal
>>> correlations.round(2)
array([[1.  , 0.81, 0.68],
       [0.81, 1.  , 0.85],
       [0.68, 0.85, 1.  ]])
>>> PartialRecurrenceSynchronization().process(correlations).synchronization_matrix.round(2)
array([[1.  , 0.61, 0.04],
       [0.61, 1.  , 0.7 ],
       [0.04, 0.7 , 1.  ]])
```

## Choosing a measure

- Continuous signals, oscillatory and narrow-band: the phase locking value. Continuous signals with an arbitrary coupling:
  the nonlinear interdependence, or the partial correlation for a group.
- Discrete events with a known tolerance in samples: event synchronization (two series) or MECS (several classes). Events
  without a natural tolerance: SPIKE-synchronization.
- Whole-body or multichannel states, to see where and when two movements revisit the same posture: cross-recurrence.

## Practical notes

- Reduce every participant to a scalar signal (or one vector per sample for the recurrence measures) and give all participants
  the same sampling rate, preferably from one clock. Resample before the measure if the streams differ.
- The window should hold several cycles of the movement. `window`, `lag` and `max_lag` are in samples: $N=\lceil T f_s\rceil$ for a
  window of $T$ seconds.
- A `NaN` or infinite value gives `INVALID_INPUT` and no output; the Notes of each feature in the API reference give the
  exact rule.
- All values are dimensionless. The synchronization of surrogate signals (shuffled, or shifted by more than a cycle) gives a
  baseline for a significance threshold that no measure provides on its own.

## Further reading

The phase locking value comes from {cite}`lachaux1999measuring`, its single-trial form is defined in
{cite}`mormann2000mean`, and its use for movement in groups is shown in {cite}`sabharwal2022husync`; recurrence-based
synchronization of a group is described in {cite}`varni2010system`; the generated pages of the API reference list every parameter of the features.
