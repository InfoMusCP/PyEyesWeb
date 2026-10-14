"""Ensemble dominance: who leads a group, from the complexity indices of its participants (Glowinski et al., 2010)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.HIGH_LEVEL)
class EnsembleDominance(FrameFeature):
    """Dominance scores and leader of an ensemble from the complexity indices of its participants.

    Input: the complexity indices of the `N` participants, one value each (for example `MultiScaleEntropy`'s
    `complexity_index`), in one call. Stateless.

    Returns
    -------
    Result
        `dominance_score`, shape `(N,)`: `1 - CI / max(CI)` of each participant (all 0 when no index is positive); `leader_index`,
        the participant with the lowest complexity index (the first on a tie, `-1` if none); `leader_complexity`, its index.
        A participant whose complexity index is `NaN` (a constant signal) is ignored: its score is `NaN`, and it is never the
        leader. `Status.INVALID_INPUT` for an infinite index.

    References
    ----------
    Glowinski et al. (2010). Multi-scale entropy analysis of dominance in
    social creative activities. ACM Multimedia, 1035-1038.
    """
    _core_class = core.motion.EnsembleDominance

    def _inputs(self) -> Inputs:
        return Inputs(Input("complexity_index", InputKind.SAMPLE, (None,), doc="complexity index of each participant"))

    def _schema(self) -> Schema:
        return Schema(Output("dominance_score", (None,), doc="1 - CI / max(CI) of each participant"),
                      Output("leader_index", kind=int, doc="participant with the lowest complexity index, -1 if none"),
                      Output("leader_complexity", doc="complexity index of the leader"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        indices = np.asarray(frame, dtype=float).reshape(-1)
        if np.isinf(indices).any():
            return self.no_output(Status.INVALID_INPUT, "infinite values", timestamp)
        dominance_score, leader_index, leader_complexity = self._block.process(indices)
        return self.result(dominance_score=dominance_score, leader_index=leader_index,
                           leader_complexity=leader_complexity, timestamp=timestamp)


__all__ = ['EnsembleDominance']
