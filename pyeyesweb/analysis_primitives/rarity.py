"""Rarity of the newest value of a signal, with two methods.

This module implements the [Rarity][pyeyesweb.analysis_primitives.rarity.Rarity] feature: how typical or atypical the
current state is relative to a memory of past states. The formula is chosen by `method`.
"""

from typing import Any, Literal, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.base.core_feature import CoreFeature, FrameFeature, VariantFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.utils.validators import validate_numeric


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="rarityindex (Rarity)")
class Rarity(VariantFeature, CoreFeature):
    r"""Rarity of the newest value of a signal within a memory of past values, by ``method``.

    Rarity measures how atypical the current state of a movement is with respect to what happened before: a value
    that has been seen often in the recent past is common, a value that has hardly occurred is rare. It can flag the
    unusual movement within a performance. The two methods are different formulas (neither is a special case of the
    other) and have different parameters and outputs; a parameter of the other method raises an error.

    ``"information"`` (default): each of ``number_of_inputs`` scalar signals is discretised into bins of the widths
    ``bins``, and the index of each input is

    .. math::

        R = -\ln (A B + 10^{-16}),

    where :math:`A` and :math:`B` are two probability terms estimated from the occupancy of the bins: with
    ``measure="rarity"`` from a memory of the last ``window`` values of the same input (a *rarity* across time), with
    ``measure="contrast"`` across the inputs (a *contrast* between the signals). A rare value gives a large index.
    The feature keeps its own memory, one sample per call. A value above the sum of the bin widths is outside the
    bins.

    ``"mode_distance"``: rarity of the newest sample of a window of one scalar stream. The histogram of the window of
    :math:`N` samples has :math:`\max(\lfloor\sqrt{N}\rfloor, 1)` equal-width bins. With :math:`i_{\mathrm{mode}}` the
    bin of the most populated bin, :math:`i_{\mathrm{last}}` the bin of the newest sample and :math:`p` the fraction of
    the window in a bin,

    .. math::

        R = \alpha \, |i_{\mathrm{mode}} - i_{\mathrm{last}}| \, (p_{\mathrm{mode}} - p_{\mathrm{last}}).

    It is zero when the newest sample is in the most common bin and grows with its distance from it and with how much
    less frequent its bin is. It needs no bin widths.

    Use ``"information"`` to reproduce EyesWeb or to compare several signals with chosen bin widths; use
    ``"mode_distance"`` for a self-contained score of one stream.

    Parameters
    ----------
    method : {"information", "mode_distance"}, optional
        Formula. Defaults to ``"information"``. Which of the other parameters apply depends on the method; all are
        keyword-only.
    number_of_inputs : int, optional
        ``"information"`` only: number of scalar signals per sample. ``measure="contrast"`` needs at least 2.
        Defaults to ``2``. *(structural)*
    measure : {"rarity", "contrast"}, optional
        ``"information"`` only: rarity across the last ``window`` values of each input, or contrast across the
        inputs. Defaults to ``"rarity"``. *(live)*
    window : int, optional
        ``"information"``: length of the memory in samples, at least 2 for ``measure="rarity"`` (``50`` by default).
        The core sizes the memory when it is built and cannot resize it, so changing it restarts the memory. *(structural)* ``"mode_distance"``: samples per window (``50`` by default); changing it on a running
        feature keeps the newest samples. *(live)*
    bins : sequence of float, optional
        ``"information"`` only: widths of the successive bins, in the units of the signals. Defaults to
        ``(0.3, 0.3, 0.4)``, which covers signals in ``[0, 1]``. *(structural)*
    hop : int, optional
        ``"mode_distance"`` only: new samples between two windows. Defaults to ``1``. *(live)*
    alpha : float, optional
        ``"mode_distance"`` only: scaling factor :math:`\alpha`, greater than 0, dimensionless. Defaults to ``0.5``.
        *(live)*

    Notes
    -----
    **Inputs.** ``"information"``: one sample of ``number_of_inputs`` values per call. ``"mode_distance"``: one value
    per call, buffered over ``window`` samples and computed every ``hop`` samples.

    **Outputs.** ``rarity``: for ``"information"`` shape ``(number_of_inputs,)``, :math:`R` per input (a larger
    value is rarer), together with a ``timestamp`` in seconds (``NaN`` when not given); for ``"mode_distance"`` a
    scalar :math:`R \ge 0`, higher meaning more atypical.

    **Statuses.** ``"information"`` with ``measure="rarity"``: the memory starts filled with zeros, so the result is
    ``WARMING_UP`` (``"the memory holds k of window values"``; the numbers are given but are artefacts) until
    ``window`` samples have been seen; a value above the sum of ``bins`` (or ``NaN``) keeps the previous bin and gives
    ``INVALID_INPUT`` (``"value outside the bins"``) with the numbers kept; a non-finite value is ``INVALID_INPUT``.
    ``"mode_distance"``: ``WARMING_UP`` while the window holds fewer than 2 samples (and while the first window
    fills), ``NO_OUTPUT`` between two hops, ``INVALID_INPUT`` while the window holds a ``NaN`` or an infinite value
    (until that sample leaves the window). ``reset()`` clears the memory and the bin indices, so ``run`` is a pure
    function of the recording.

    Corrected in the core: ``reset()`` kept the previous bin indices; a contrast with one input, or a rarity with a
    memory of one value, divided 0 by 0 and gave ``NaN``: both combinations are invalid and raise ``ValueError`` at
    construction.

    Examples
    --------
    >>> from pyeyesweb.analysis_primitives import Rarity
    >>> contrast = Rarity(measure="contrast", number_of_inputs=2)
    >>> contrast.process([0.1, 0.5]).rarity.round(3)
    array([1.099, 1.099])
    >>> rarity = Rarity(method="mode_distance", window=10, alpha=1.0)
    >>> rarity.run([0.0, 0.1, 0.0, 0.1, 0.0, 0.1, 0.0, 0.1, 0.0, 1.0])[-1].rarity
    1.6
    """

    _SWITCH = ("method", "information")
    _variants = {}

    @property
    def method(self) -> Literal["information", "mode_distance"]:
        return self._variant


class _ModeDistanceRarity(MinimumWindow, WindowedFeature, Rarity, variant="mode_distance"):
    r"""Rarity of the latest sample relative to the window distribution (method ``"mode_distance"``).

    Input: one value per call, buffered over ``window`` samples and computed every ``hop`` samples. See ``Rarity``.
    """

    _OUTPUTS = Schema(Output("rarity", doc="Rarity score >= 0; higher values indicate more atypical movement."))

    _core_class = core.motion.HistogramRarity
    _lazy_block = True

    def __init__(self, window: int = 50, hop: int = 1, *, alpha: float = 0.5, method: str = "mode_distance"):
        super().__init__(window=window, hop=hop)
        self._check_window()
        self.alpha = alpha

    def _minimum_window(self) -> int:
        return 2

    @property
    def alpha(self) -> float:
        """Scaling factor for rarity."""
        return self._params["alpha"]

    @alpha.setter
    def alpha(self, value: float):
        if validate_numeric(value, "alpha") <= 0:
            raise ValueError(f"alpha must be > 0, got {value}")
        self._set_param("alpha", float(value))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        """Compute rarity of the newest sample of a window within the window distribution.

        `series` is one complete window, `(1, window)`, the newest sample last (flattened to 1-D); `timestamp` is the
        timestamp of the window (seconds). `Status.WARMING_UP` when fewer than 2 samples are present.
        """
        samples = np.ascontiguousarray(series, dtype=float).ravel()
        if len(samples) < 2:
            return self._no_output(Status.WARMING_UP, "fewer than 2 samples", timestamp)
        if reason := non_finite(samples):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._result(rarity=self._block.process(samples), timestamp=timestamp)


class _InformationRarity(Rarity, FrameFeature, variant="information"):
    """Rarity or contrast of ``number_of_inputs`` scalar signals (method ``"information"``).

    Input: one sample of ``number_of_inputs`` values per call. See ``Rarity``.
    """
    _core_class = core.motion.RarityIndex
    _core_names = {"window": "data_memory", "measure": "type"}
    _filled = 0  # samples written to the memory since it was last empty (measure "rarity" only)

    def reset(self) -> None:
        super().reset()
        self._filled = 0

    def _state_lost(self) -> None:
        super()._state_lost()
        self._filled = 0

    def __init__(self, *, method: str = "information", **params: Any):
        super().__init__(**params)

    def _number_of_inputs(self) -> int:
        return int(self._param("number_of_inputs", 2))  # C++ default

    def _inputs(self) -> Inputs:
        return Inputs(Input("signals", InputKind.SAMPLE, (self._number_of_inputs(),), doc="one value per signal"))

    def _schema(self) -> Schema:
        return Schema(Output("rarity", self._number_of_inputs(), doc="-log(A * B + 1e-16) for each input"))

    def _process(self, sample: Any, timestamp: Optional[float]) -> Result:
        values = np.asarray(sample, dtype=float).ravel()
        rarity = np.asarray(self._block.process(values), dtype=float)
        memory = int(self._param("window", 50))  # C++ defaults
        uses_memory = self._param("measure", core.motion.RarityType.RARITY) == core.motion.RarityType.RARITY
        self._filled += uses_memory
        if not np.all(values <= np.cumsum(self._param("bins", [0.3, 0.3, 0.4]))[-1]):  # also NaN
            return self._result(status=Status.INVALID_INPUT, reason="value outside the bins", rarity=rarity, timestamp=timestamp)
        if uses_memory and self._filled < memory:
            return self._result(status=Status.WARMING_UP, reason=f"the memory holds {self._filled} of {memory} values",
                               rarity=rarity, timestamp=timestamp)
        return self._result(rarity=rarity, timestamp=timestamp)

for _variant in (_ModeDistanceRarity, _InformationRarity):
    _variant.__name__ = Rarity.__name__


__all__ = ["Rarity"]
