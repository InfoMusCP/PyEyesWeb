# Dominance

In a group that moves together (a string quartet, a dance ensemble, a team), some members lead and others follow. Dominance
analysis asks which member acts as the leader, from the movement alone. The approach implemented in PyEyesWeb is the one of
{cite}`glowinski2010mse`, in which the leader is the participant whose movement is the **least complex**: the most regular
and predictable movement acts as an anchor around which the others behave more reactively, and therefore with higher
complexity. The analysis has two stages, each a separate feature:

1. the complexity of the movement of every participant, as the complexity index of the multi-scale entropy of a signal such as
   the speed of the head or of a hand ({py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy`, described in
   {doc}`entropy_rarity_periodicity`);
2. the comparison of the indices of the group, which gives a dominance score per participant and the leader
   ({py:class}`~pyeyesweb.high_level.EnsembleDominance`).

## Definition

Let $\mathrm{CI}_i$ be the complexity index of participant $i=1,\dots,M$ (notation in {doc}`notation`), computed over the same
window of the signals of all participants. The dominance score of participant $i$ is

$$
D_i = 1-\frac{\mathrm{CI}_i}{\max_j \mathrm{CI}_j},
$$

so that the participant with the lowest complexity index has the highest score, the one with the highest index has score 0, and
all scores lie in $[0,1]$. If no index is positive every score is 0. The leader is the participant with the lowest index (the
first one, in case of a tie), and the feature reports its position and its complexity index.

Two consequences follow from the definition. First, the score is relative to the group: it says how much less complex a
participant is than the most complex one, not how regular the participant is in absolute terms, and adding a participant who is
more complex than everybody changes all the scores. Second, the scores are only comparable when the indices are: the same
signal type, window length, sampling rate, scales and tolerance for every participant. Feed the group with one
{py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy`, which takes one value per signal and so guarantees identical
settings.

## What the feature returns

{py:class}`~pyeyesweb.high_level.EnsembleDominance` has no parameters and keeps no state. One call takes the $M$ complexity
indices (one number per participant) and returns

- `dominance_score`: $(M,)$ values in $[0,1]$, dimensionless;
- `leader_index`: the position of the leader among the participants, counted from 0, or $-1$ when no participant has an
  index;
- `leader_complexity`: the complexity index of the leader, in the unit of the input.

A participant whose index is `NaN` (a constant signal has no entropy, so a participant who does not move at all gives `NaN`)
is ignored: its score is `NaN` and it is never the leader. An infinite index is `INVALID_INPUT`. In the core this was corrected:
a `NaN` index used to set every score to 0 and to become the leader.

## Example

Three participants move at 100 Hz: the first with a regular oscillation and a little noise, the second with the same
oscillation and more noise, and the third with an irregular movement of larger amplitude (the amplitude does not matter,
since each signal is normalised). The complexity index of each is computed over a window of 12 seconds and passed to the dominance feature.

```{doctest}
>>> from pyeyesweb.analysis_primitives import MultiScaleEntropy
>>> from pyeyesweb.high_level import EnsembleDominance
>>> rng = np.random.default_rng(11)
>>> samples = np.arange(1200)
>>> first = np.sin(2 * np.pi * samples / 50) + 0.1 * rng.normal(size=1200)
>>> second = np.sin(2 * np.pi * samples / 50) + 0.4 * rng.normal(size=1200)
>>> third = 5.0 * rng.normal(size=1200)
>>> group = np.column_stack([first, second, third])               # one column per participant
>>> complexity = MultiScaleEntropy(window=1200, max_scale=6, minimum_points=100).run(group)[-1].complexity_index
>>> complexity.round(2)
array([ 2.34,  7.94, 11.92])
>>> dominance = EnsembleDominance().process(complexity)
>>> dominance.dominance_score.round(2), dominance.leader_index, round(float(dominance.leader_complexity), 2)
(array([0.8 , 0.33, 0.  ]), 0, 2.34)
```

The regular participant has the lowest index, the highest dominance score and is the leader; the participant with the
irregular movement has the highest index and the score 0, and the participant in between has an intermediate score.

## Practical notes

- Complexity needs data: with the default settings of `MultiScaleEntropy` (a window of 3000 samples and at least 500 points
  at the largest scale) the window is 30 s at 100 Hz. Estimates on shorter windows are noisier; reduce `minimum_points` and
  `max_scale` together with the window and keep them identical for the whole group.
- Run the dominance feature at the rate at which you want a leader (once per window of the entropy). It needs no window of its
  own.
- The input signal is a choice of the analysis; the speed of a body part is a natural one.
  Reduce 2D or 3D positions to a speed with {py:class}`~pyeyesweb.low_level.Kinematics` first (see
  {doc}`kinematics_energy`).
- A group with a single participant has a dominance score of 0 for it (its index is the maximum) and the participant is the
  leader.
- The leadership found is a statement about complexity, not about causality. For the direction of the influence between two
  signals, see the nonlinear interdependence in {doc}`synchronization`.

## Further reading

The dominance analysis from multi-scale entropy is described in {cite}`glowinski2010mse`; the multi-scale entropy itself
is introduced in {cite}`costa2005multiscale`.
