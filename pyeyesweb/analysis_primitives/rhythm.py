"""Regularity of a pulse train (EyesWeb BinaryPulsesRegularity)."""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="binary_pulses_regularity (BinaryPulsesRegularity)")
class BinaryPulsesRegularity(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Whether the pulses of a window are equally spaced.

    A pulse is a non-zero sample of a single-channel signal (a step, a beat, the ``is_peak`` flag of
    ``ScalarPeakDetector``). With :math:`I` the intervals between consecutive pulses of a window, in samples, the window
    is regular when it holds at least three pulses and the spread of the intervals is below ``threshold``,

    .. math::

        \max(I) - \min(I) < \mathtt{threshold},

    as in :cite:`niewiadomski2019embodied` (sec. 3.2). It measures the regularity of a rhythm, such as a steady walk or
    a metronomic gesture. The rule does not depend on the order of the intervals; a steady drift (intervals 5, 6, 7, 8)
    is not regular.

    Parameters
    ----------
    window : int
        Samples per window, at least 3 (three pulses are needed). Changing it on a running feature keeps the newest
        samples. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
    threshold : int, optional
        Largest spread of the intervals that is still regular, in samples, exclusive, at least 1. Defaults to ``1``:
        the intervals must be equal; ``2`` accepts intervals that differ by one sample. *(live)*

    Notes
    -----
    **Inputs.** One value per call (a single channel); a non-zero value is a pulse.

    **Outputs.** ``is_regular`` (bool): the intervals between the pulses are equal within ``threshold``;
    ``pulse_count`` (int, at least 0): number of pulses (non-zero samples) in the window;
    ``is_regularity_detected`` (bool): ``is_regular`` on the first window after a window that was not regular (a
    trigger).

    The original block compared every interval with the first one (within ``threshold``, inclusive), which accepted a
    spread up to twice the threshold and depended on the first interval; its threshold ``t`` is ``t + 1`` here.

    **Statuses.** ``WARMING_UP`` while the first window fills, ``NO_OUTPUT`` between two hops, ``INVALID_INPUT`` for a
    window that holds a ``NaN`` or an infinite value.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import BinaryPulsesRegularity
    >>> feature = BinaryPulsesRegularity(window=10)
    >>> result = feature.run(np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1.0]))[-1]
    >>> result.is_regular, result.pulse_count
    (True, 4)
    """
    _core_class = core.base.BinaryPulsesRegularity
    MIN_WINDOW = 3
    _INPUTS = Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call; a non-zero value is a pulse"))
    _OUTPUTS = Schema(Output("is_regular", kind=bool, doc="the intervals between the pulses are equal within the threshold"),
                     Output("pulse_count", kind=int, doc="number of pulses in the window"),
                     Output("is_regularity_detected", kind=bool, doc="first regular window after a window that was not"))

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        if reason := non_finite(series):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        regular, pulse_count, detected = self._block.process(np.asarray(series, dtype=float))
        return self._result(timestamp=timestamp, is_regular=regular, pulse_count=pulse_count, is_regularity_detected=detected)


__all__ = ["BinaryPulsesRegularity"]
