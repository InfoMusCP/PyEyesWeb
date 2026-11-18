"""Rarity of the newest value of a signal, with three methods.

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
    ``measure="contrast"`` across the inputs (a *contrast* between the signals). A rare value gives a large index
    :cite:`mancas2008real`. The term :math:`B` divides by the number of bins :math:`K` (the "Max(M)" of the paper's
    eq. 4, which the paper does not define; reading it as :math:`K` keeps the index comparable across windows and
    inputs). The feature keeps its own memory, one sample per call. The default bins assume a signal in
    :math:`[0, 1]`: rescale other signals to :math:`[0, 1]` or give their own ``bins``. A value above the sum of the
    bin widths is outside the bins.

    ``"mode_distance"``: rarity of the newest sample of a window of one scalar stream. The histogram of the window of
    :math:`N` samples has :math:`\max(\lfloor\sqrt{N}\rfloor, 1)` equal-width bins. With :math:`i_{\mathrm{mode}}` the
    bin of the most populated bin, :math:`i_{\mathrm{last}}` the bin of the newest sample and :math:`p` the fraction of
    the window in a bin,

    .. math::

        R = \alpha \, |i_{\mathrm{mode}} - i_{\mathrm{last}}| \, (p_{\mathrm{mode}} - p_{\mathrm{last}}).

    It is zero when the newest sample is in the most common bin and grows with its distance from it and with how much
    less frequent its bin is :cite:`niewiadomski2019embodied` (sec. 3.1). It needs no bin widths: the bins span the
    smallest and largest values of the window, so one outlier stretches them, and the values differ from the paper's
    Fig. 1, whose bins span the fixed range :math:`[0, 1]`, on a window that does not span it. The frequencies are
    fractions of the window (the paper uses counts): multiply :math:`\alpha` by :math:`N` for the paper's scale. The
    paper used windows of 100 frames; the default here is 50.

    ``"novelty"``: how unusual the movement of the last ``pattern`` samples is compared with the movement of the recent
    past, for any signal (a speed, an energy, a position, several features together). The two methods above measure how
    rare the current *level* is: a change of shape inside a bin, or a movement that stays among values already seen, is
    invisible to them. This method compares *patterns*. At every sample it takes the last ``pattern`` samples (one
    point every ``step`` samples, all channels) as a pattern, and compares it with the patterns of the last ``memory``
    samples, leaving out the newest ``pattern / 2`` of them, which overlap it. Each channel is divided by its standard
    deviation over the memory, so no channel dominates because of its unit; the distance between two patterns is
    Euclidean. With :math:`d` the mean distance from the current pattern to its ``neighbours`` nearest patterns,

    .. math::

        R = \frac{d}{\operatorname{median}(d \text{ over the last } \mathtt{memory} \text{ samples})},

    so the value is dimensionless and about 1 for a movement as familiar as usual; it is larger for a movement that has not
    happened in the memory, and ``0`` when the pattern is exactly in the memory. A repeated movement becomes familiar
    (its patterns enter the memory) and its rarity falls back to about 1; a movement not done for ``memory`` samples is
    new again. With ``shape=True`` the newest sample is subtracted from the pattern, so only the *shape* of the movement
    counts, not where it happens (use it for positions); without it the level is part of the pattern (use it for scalars
    such as a speed or an energy). It is not an EyesWeb block: it is new in this library (design review 2026-11-17).

    Use ``"information"`` to reproduce EyesWeb or to compare several signals with chosen bin widths; use
    ``"mode_distance"`` for a self-contained score of one stream; use ``"novelty"`` to find unusual gestures.

    Parameters
    ----------
    method : {"information", "mode_distance", "novelty"}, optional
        Formula. Defaults to ``"information"``. Which of the other parameters apply depends on the method; all are
        keyword-only.
    number_of_inputs : int, optional
        ``"information"`` and ``"novelty"``: number of scalar signals per sample. ``measure="contrast"`` needs at least 2.
        Defaults to ``2`` (``"information"``) and ``1`` (``"novelty"``). *(structural)*
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
        ``"mode_distance"`` only: scaling factor :math:`\alpha`, greater than 0, dimensionless. Defaults to ``0.5``
        (the paper does not give its value). *(live)*
    memory : int, optional
        ``"novelty"`` only: samples of patterns kept for the comparison, at least ``3 * pattern``. Defaults to ``300``.
        It is the time after which a movement that has not been repeated is new again. *(structural)*
    pattern : int, optional
        ``"novelty"`` only: samples of one pattern, at least 2: how long a gesture is. Defaults to ``30``. *(structural)*
    neighbours : int, optional
        ``"novelty"`` only: number of nearest patterns averaged, at least 1. Defaults to ``5``. *(live)*
    step : int, optional
        ``"novelty"`` only: samples between two points of a pattern, at least 1 (a larger step is cheaper). Defaults to
        ``1``. *(structural)*
    shape : bool, optional
        ``"novelty"`` only: compare the shape of the pattern, not its position (subtract the newest sample). Defaults to
        ``False``. *(structural)*

    Notes
    -----
    **Inputs.** ``"information"`` and ``"novelty"``: one sample of ``number_of_inputs`` values per call. ``"mode_distance"``:
    one value per call, buffered over ``window`` samples and computed every ``hop`` samples.

    **Outputs.** ``rarity``: for ``"information"`` shape ``(number_of_inputs,)``, :math:`R` per input (a larger
    value is rarer), together with a ``timestamp`` in seconds (``NaN`` when not given); for ``"mode_distance"`` a
    scalar :math:`R \ge 0`, higher meaning more atypical; for ``"novelty"`` a scalar :math:`R \ge 0`, about 1 for a
    familiar movement.

    **Statuses.** ``"information"`` with ``measure="rarity"``: the memory starts filled with zeros, so the result is
    ``WARMING_UP`` (``"the memory holds k of window values"``; the numbers are given but are artefacts) until
    ``window`` samples have been seen; a value above the sum of ``bins`` (or ``NaN``) keeps the previous bin and gives
    ``INVALID_INPUT`` (``"value outside the bins"``), whose outputs are empty; a non-finite value is ``INVALID_INPUT``.
    ``"mode_distance"``: ``WARMING_UP`` while the window holds fewer than 2 samples (and while the first window
    fills), ``NO_OUTPUT`` between two hops, ``INVALID_INPUT`` while the window holds a ``NaN`` or an infinite value
    (until that sample leaves the window). ``"novelty"``: ``WARMING_UP`` (``"the memory is filling"``) until the memory holds
    twice the pattern length of patterns to compare with (``pattern - 1 + 2 * pattern + pattern // 2 - 1`` samples),
    ``INVALID_INPUT`` for a ``NaN`` or infinite sample, which is not used. ``reset()`` clears the memory and the bin
    indices, so ``run`` is a pure function of the recording.

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

    The ``"novelty"`` method sees a pause in an oscillation that the other two cannot (a pause at the middle of the cycle
    stays inside the values already seen):

    >>> import numpy as np
    >>> oscillation = np.sin(2 * np.pi * np.arange(220) / 20)
    >>> oscillation[150:160] = 0.0                                          # ten samples of pause
    >>> novelty = Rarity(method="novelty", memory=90, pattern=10).run(oscillation)
    >>> bool(novelty.status[0] == 1 and novelty.status[-1] == 0)            # WARMING_UP at first, then OK
    True
    >>> round(float(max(novelty.rarity[100:150])), 1), round(float(max(novelty.rarity[150:175])), 1)
    (1.0, 15.5)
    """

    _SWITCH = ("method", "information")
    _variants = {}

    @property
    def method(self) -> Literal["information", "mode_distance", "novelty"]:
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
        if not np.all(values <= np.cumsum(self._param("bins", [0.3, 0.3, 0.4]))[-1]):  # also NaN; not a value of the memory
            return self._result(status=Status.INVALID_INPUT, reason="value outside the bins", rarity=rarity, timestamp=timestamp)
        self._filled += uses_memory
        if uses_memory and self._filled < memory:
            return self._result(status=Status.WARMING_UP, reason=f"the memory holds {self._filled} of {memory} values",
                               rarity=rarity, timestamp=timestamp)
        return self._result(rarity=rarity, timestamp=timestamp)

class _NoveltyRarity(Rarity, FrameFeature, variant="novelty"):
    """Rarity of the newest pattern of ``number_of_inputs`` signals within a memory of patterns (method ``"novelty"``).

    Input: one sample of ``number_of_inputs`` values per call. See ``Rarity``.
    """
    _core_class = core.motion.NoveltyRarity

    def __init__(self, *, method: str = "novelty", number_of_inputs: int = 1, **params: Any):
        super().__init__(number_of_inputs=number_of_inputs, **params)

    def _number_of_inputs(self) -> int:
        return int(self._param("number_of_inputs", 1))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signals", InputKind.SAMPLE, (self._number_of_inputs(),), doc="one value per signal"))

    def _schema(self) -> Schema:
        return Schema(Output("rarity", doc="distance to the nearest patterns of the memory, relative to its median; about 1 = familiar"))

    def _process(self, sample: Any, timestamp: Optional[float]) -> Result:
        values = np.asarray(sample, dtype=float).ravel()
        if reason := non_finite(values):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        rarity = self._block.process(values)
        if rarity is None:
            return self._no_output(Status.WARMING_UP, "the memory is filling", timestamp)
        return self._result(rarity=rarity, timestamp=timestamp)


for _variant in (_ModeDistanceRarity, _InformationRarity, _NoveltyRarity):
    _variant.__name__ = Rarity.__name__


__all__ = ["Rarity"]
