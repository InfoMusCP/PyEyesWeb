# High-level features

Layer 4 is the layer of qualities that an observer perceives and that a group can show: who leads, how people move together,
what a movement communicates. Its timescale is three seconds and above, and it asks for context and, often, for several
people. The conceptual model ({doc}`../theory/framework`) places it above the measures of a movement unit, and the library
follows the model: a high-level feature does not read a skeleton, it reads the values that lower layers produce. This layer
has {{ n_high_level }} feature today.

```{feature-table} high_level
```

## What the layer contains

{py:class}`~pyeyesweb.high_level.EnsembleDominance` identifies the leader of a group from the complexity of the movement of its
members: the participant whose movement is the least complex, the most regular and predictable, acts as an anchor around which
the others behave more reactively. It takes one complexity index per participant, for example the `complexity_index` of
{py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy`, and returns a dominance score in $[0, 1]$ for each participant, the
position of the leader and its complexity. The method follows the study of social creative activities in
{cite}`glowinski2010mse`. Theory: {doc}`../theory/dominance`.

The measures of the interaction itself, such as how synchronised a group is, are not in this layer. They are
analysis primitives, because they take any signal, and are found in {doc}`analysis_primitives`; applied to the outputs of
layers 2 and 3 of several people they describe the group. The mapping of such values onto an expressive quality is the
work of the application, often with a trained model, and the library gives the inputs of that mapping.

## A typical pipeline

Two participants move at the same time. One makes a regular movement (a sine); the movement of the other is irregular
(a sine with noise). The complexity of each is measured by {py:class}`~pyeyesweb.analysis_primitives.MultiScaleEntropy` on a
window of the signals, and the dominance follows from the two indices.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.analysis_primitives import MultiScaleEntropy
>>> from pyeyesweb.high_level import EnsembleDominance
>>> rng = np.random.default_rng(0)
>>> n = np.arange(600)
>>> regular = np.sin(2 * np.pi * n / 50)
>>> irregular = np.sin(2 * np.pi * n / 50) + 0.8 * rng.standard_normal(600)
>>> signals = np.column_stack([regular, irregular])                  # one column per participant
>>> entropy = MultiScaleEntropy(window=600, max_scale=6, minimum_points=100)
>>> index = entropy.run(signals).complexity_index[-1]
>>> np.round(index, 2).tolist()
[1.06, 10.36]
>>> result = EnsembleDominance().process(index)
>>> np.round(result.dominance_score, 2).tolist(), int(result.leader_index)
([0.9, 0.0], 0)
```

The participant with the lower index, the regular one, is the leader and has the higher score. The scores are relative to the
group: they say nothing about one participant alone, and a participant whose index is NaN (a constant signal, which has no
entropy) is ignored.

## What to know before choosing

- The input of the layer is a complexity index per participant, computed over a window long enough for the multi-scale entropy
  (3000 samples by default, at least `max_scale * minimum_points`), so the dominance is a measure of a stretch of seconds
  to minutes, not of a frame.
- The scores are dimensionless and only meaningful for comparing the members of one group over the same window.
- The leader is the participant with the lowest index (the first in a tie), or `-1` when no participant has an index.

Hands-on: see {ref}`sphx_glr_tutorials_05_analysis_primitives_plot_08_primitives.py`, which applies `EnsembleDominance` to the complexity of several signals.
