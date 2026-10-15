"""Temporal synchronization: progression of a staged synchronization process."""

from typing import Any, Dict

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

_sync = core.sync


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="TemporalSynchronization")
class TemporalSynchronization(FrameFeature):
    r"""Progression of a staged synchronization process, from a chain of synchronization values, one sample per call.

    Follows how far a group (or a chain of body segments) has progressed towards full synchronization, when its
    members synchronize one after the other. Each call takes the ``number_of_inputs`` synchronization values (for
    example the entries of `PartialRecurrenceSynchronization`, or one `PhaseLockingValue` per participant) and
    compares each with its threshold; the ``state`` is the number of leading inputs, in order, that are at or above
    their threshold, and the ``progression`` rises from 0 to 1 as the stages are completed, reaching 1 when all
    the inputs are above their thresholds. The weights of the stages are ``stage_weights``.

    Parameters
    ----------
    number_of_inputs : int, optional
        Number of synchronization values per call, hence of stages (default 3). *(structural)*
    max_steps : int, optional
        Number of steps (calls) after which the process is considered too slow; used only by ``efficiency_step``
        (default 0: no limit). *(live)*
    stage_weights : sequence of int, optional
        Weights of the stages of the progression, ``number_of_inputs + 1`` values (default ``None``: the defaults of the
        core); any other length raises ``ValueError``. *(live)*
    thresholds : sequence of float, optional
        Threshold of each input, in the unit of the synchronization values (default ``None``: 0 for every input).
        *(live)*

    Notes
    -----
    **Inputs.** ``process(synchronization, *, timestamp=None)`` takes ``number_of_inputs`` values;
    ``run(synchronization, *, timestamps=None)`` takes ``(T, number_of_inputs)``.

    **Outputs.** ``progression`` (dimensionless, in [0, 1]); ``step`` (count): number of calls so far, 1 at the first;
    ``state`` (count, in ``0..number_of_inputs``): number of leading inputs above their threshold; ``efficiency_step``
    (dimensionless): valid only when ``progression`` is 1 (``NaN`` and flagged invalid otherwise), it is
    ``step / (number_of_inputs + 1)`` when ``max_steps`` is 0 and ``(max_steps - step) / (max_steps -
    number_of_inputs - 1)`` otherwise, so that completing in ``number_of_inputs + 1`` steps gives 1.

    **Statuses.** ``INVALID_INPUT`` (``"NaN or infinite values"``) for a NaN or infinite input; otherwise ``OK``.

    **Corrected in the core.** A threshold of 0 (the default) gave an infinite or NaN progression for a negative
    input; the progression is now finite.

    Examples
    --------
    >>> sync = TemporalSynchronization(thresholds=[0.5, 0.5, 0.5])
    >>> frames = [(.6, .1, .1), (.6, .6, .1), (.6, .6, .6)]
    >>> [(round(float(r.progression), 2), int(r.state)) for r in map(sync.process, frames)]
    [(0.4, 1), (0.73, 2), (1.0, 3)]
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
        return self._result(progression=raw["progression"], step=raw["step"], state=raw["state"],
                           efficiency_step=raw["efficiency_step"], timestamp=timestamp)


__all__ = ["TemporalSynchronization"]
