"""Periodicity of a signal (EyesWeb PeriodicityIndex)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="PeriodicityIndex (Periodicity)")
class Periodicity(MinimumWindow, WindowedFeature, CoreFeature):
    """Periods and their normalised power for each channel of a window, by the Periodicity Transform.

    The Periodicity Transform decomposes a signal into periodic components and reports how strongly the signal
    repeats at each period: a regular movement (a steady pulse, a repeated gesture) gives a period with a power
    close to 1, an aperiodic movement gives no period. It is computed on every channel of a window of consecutive
    samples. The periods are expressed in samples.

    Parameters
    ----------
    window : int
        Samples per window, at least 2. Changing it on a running feature keeps the newest samples. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
    method : {"small2large", "mbest"}, optional
        Search strategy of the transform: ``"small2large"`` (periods from the smallest to the largest) or
        ``"mbest"`` (the ``best_periods`` best periods). Defaults to ``"small2large"``.
    threshold : float, optional
        Threshold on the normalised power below which a period is not reported (``"small2large"``), dimensionless.
        Defaults to ``0.1``, the upper end of the range ``0.01 < T < 0.1`` advised by :cite:`sethares1999periodicity`
        (p. 2957); the original block used ``0.2``. *(live)*
    best_periods : int, optional
        Number of periods searched by ``"mbest"``. Defaults to ``10``.
    sort_by_power : bool, optional
        Whether the reported periods are sorted by power. Defaults to ``False``.

    Notes
    -----
    **Inputs.** One sample per call, with one value per channel; ``run`` takes a recording of shape
    ``(samples, channels)``.

    **Outputs.** ``periods`` and ``powers``, both of shape ``(channels, columns)`` (``columns`` depends on the
    method and the window, so they are not part of ``to_array()``): entry ``k`` of channel ``c`` is a detected period,
    in samples, and its normalised power. The ``powers`` of a perfectly periodic signal is 1. Unused entries are ``-1``
    with ``"small2large"``; ``"mbest"`` always fills its ``best_periods`` columns, padding with period 0 and power 0,
    and its last entries can be periods of noise-level power.

    **Statuses.** ``WARMING_UP`` while the first window fills, ``NO_OUTPUT`` between two hops, ``INVALID_INPUT`` when
    no channel has a period to find (every channel constant over the window, or ``"mbest"`` on fewer than 3 samples),
    otherwise ``OK``; a constant channel among others gives ``-1`` (``"small2large"``) or ``0`` (``"mbest"``) entries and
    the ``reason`` names it.

    **Differences from the paper** :cite:`sethares1999periodicity`, kept from the original block: the projection on a
    period averages the partial last repetition too (an exact least-squares projection; the paper's eq. 7 uses complete
    repetitions only), and ``"mbest"`` searches periods up to a third of the window, not half (at least three
    repetitions; the lab's use, :cite:`mancini2012computing`, only accepts periods well below half the window) and
    refines its list differently. ``"mbest"`` can report a multiple of the true period first (a train of period 5 can
    give 10); the paper's M-Best-gamma variant, more robust to this, is not implemented.

    **Real time.** About 11 ms per call for a window of 1024 samples with ``hop=1``, too slow for 100 Hz; use a
    ``hop`` above 1 or a smaller window.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import Periodicity
    >>> pulses = np.tile([1.0, 0.0, 0.0, 0.0, 0.0], 8)
    >>> result = Periodicity(window=40).run(pulses)[-1]
    >>> print(result.periods[0, 0], round(result.powers[0, 0], 3))
    5.0 1.0
    """
    _core_class = core.motion.PeriodicityIndex

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _minimum_window(self) -> int:
        return 2

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("periods", (None, None), unit="samples", doc="detected periods in samples, -1 = unused"),
                      Output("powers", (None, None), doc="normalised power of each period, -1 = unused"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        series = np.atleast_2d(np.asarray(series, dtype=float))
        if self.method == "mbest" and series.shape[1] < 3:
            return self._no_output(Status.INVALID_INPUT, "mbest needs at least 3 samples", timestamp)
        constant = np.flatnonzero(np.ptp(series, axis=1) == 0)
        if len(constant) == len(series):
            return self._no_output(Status.INVALID_INPUT, "constant window: no period", timestamp)
        raw = self._block.process(series, 0.0)
        periods, powers = raw[0::2].copy(), raw[1::2].copy()
        powers[constant] = np.where(np.isnan(powers[constant]), 0.0, powers[constant])  # mbest gives NaN for no signal
        reason = "constant channel(s) " + ", ".join(map(str, constant)) + ": no period" if len(constant) else ""
        return self._result(periods=periods, powers=powers, timestamp=timestamp, reason=reason)


__all__ = ["Periodicity"]
