"""Periodicity of a signal (EyesWeb PeriodicityIndex)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema


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
        Threshold on the normalised power below which a period is not reported, dimensionless. Defaults to ``0.2``.
        *(live)*
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
    in samples, and its normalised power. Unused entries are ``-1``. The ``powers`` of a perfectly periodic
    signal is 1.

    **Statuses.** ``WARMING_UP`` while the first window fills, ``NO_OUTPUT`` between two hops, otherwise ``OK``.

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
    _core_names = {"method": "algorithm"}

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
        raw = self._block.process(np.asarray(series, dtype=float), 0.0)
        return self._result(periods=raw[0::2], powers=raw[1::2], timestamp=timestamp)


__all__ = ["Periodicity"]
