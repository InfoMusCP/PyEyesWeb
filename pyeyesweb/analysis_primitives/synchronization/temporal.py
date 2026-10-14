"""Temporal synchronization (EyesWeb GestureProcessingSynchronization)."""

from typing import Any, Dict

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

_sync = core.sync


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="TemporalSynchronization")
class TemporalSynchronization(FrameFeature):
    """EyesWeb TemporalSynchronization, one sample per call.

    Input: `synchronization`, one value per input (`number_of_inputs`, default 3).

    Outputs `progression` in [0, 1], `step` counter, `state` (number of leading inputs above threshold) and
    `efficiency_step`, valid only when the progression reaches 1.
    """
    _core_class = _sync.TemporalSynchronization
    _core_names = {"number_of_inputs": "input_number"}

    def _inputs(self) -> Inputs:
        number_of_inputs = int(self._param("number_of_inputs", 3))  # C++ default
        return Inputs(Input("synchronization", InputKind.SAMPLE, (number_of_inputs,), doc="one synchronisation value per input"))

    def _schema(self) -> Schema:
        return Schema(Output("progression"), Output("step", kind=int), Output("state", kind=int),
                      Output("efficiency_step", doc="only when progression == 1"))

    def _to_result(self, raw: Dict[str, Any], timestamp: float) -> Result:
        return self.result(progression=raw["progression"], step=raw["step"], state=raw["state"],
                           efficiency_step=raw["efficiency_step"], timestamp=timestamp)


__all__ = ["TemporalSynchronization"]
