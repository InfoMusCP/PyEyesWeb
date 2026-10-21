"""Ensemble dominance: who leads a group, from the complexity indices of its participants.

The dominance of a participant is read from the complexity of its movement, measured by the complexity index of
``MultiScaleEntropy`` (Glowinski et al., 2010).
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.HIGH_LEVEL)
class EnsembleDominance(FrameFeature):
    r"""Dominance scores and leader of an ensemble from the complexity indices of its participants.

    Identifies the leader of a group from the complexity of the movement of its members: the participant whose movement
    is the least complex, that is the most regular and predictable, acts as the anchor around which the others behave
    more reactively, and is taken as the leader. Given the complexity indices :math:`CI_i` of the :math:`N` participants
    (for example the ``complexity_index`` output of ``MultiScaleEntropy``), the dominance score of participant :math:`i`
    is

    .. math::

        D_i = 1 - \frac{CI_i}{\max_j CI_j},

    so that the participant with the lowest index has the highest score and the one with the highest index has score 0.
    If no index is positive every score is 0. The leader is the participant with the lowest complexity index (the first
    one in case of a tie).

    Input: the complexity indices of the ``N`` participants, one value each, in one call; ``process(frame, *,
    timestamp=None)`` with ``frame`` of shape ``(N,)``. A participant whose index is NaN (for example a constant signal)
    is ignored. The feature has no parameters and keeps no state.

    Notes
    -----
    **Outputs.** ``dominance_score``: ``(N,)``, dimensionless, in [0, 1] (NaN for an ignored participant), 1 minus each
    index over the largest one. ``leader_index``: position of the leader among the participants, ``-1`` when no
    participant has an index. ``leader_complexity``: the complexity index of the leader, in the unit of the input.

    **Statuses.** ``INVALID_INPUT`` for an infinite index; NaN is data, not an error.

    Corrected in the core: a NaN complexity index no longer zeroes every score and becomes the leader; such a
    participant is ignored (score NaN, never the leader).

    References
    ----------
    :cite:`glowinski2010multi`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.high_level import EnsembleDominance
    >>> result = EnsembleDominance().process([2.0, 1.0, 3.0])
    >>> print(np.round(result.dominance_score, 2), result.leader_index)
    [0.33 0.67 0.  ] 1
    """
    _core_class = core.motion.EnsembleDominance

    def _inputs(self) -> Inputs:
        return Inputs(Input("complexity_index", InputKind.SAMPLE, (None,), doc="complexity index of each participant",
                            allow_non_finite=True))  # NaN: a participant without a complexity index, ignored

    def _schema(self) -> Schema:
        return Schema(Output("dominance_score", (None,), doc="1 - CI / max(CI) of each participant"),
                      Output("leader_index", kind=int, doc="participant with the lowest complexity index, -1 if none"),
                      Output("leader_complexity", unit="<input>", doc="complexity index of the leader"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        indices = np.asarray(frame, dtype=float).reshape(-1)
        if np.isinf(indices).any():
            return self._no_output(Status.INVALID_INPUT, "infinite values", timestamp)
        dominance_score, leader_index, leader_complexity = self._block.process(indices)
        return self._result(dominance_score=dominance_score, leader_index=leader_index,
                           leader_complexity=leader_complexity, timestamp=timestamp)


__all__ = ['EnsembleDominance']
