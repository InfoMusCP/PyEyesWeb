"""Recurrence plots of a series of states and cross-recurrence plots of two series.

Both are computed on a window of samples and are windowed features (``window``, ``hop``).
"""

from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema

from ._blocks import _SeriesBlock

_sync = core.sync


class _Epsilons:
    """Mixin, placed before the series block, of the plots with one threshold per sample: `multiple_epsilons=None` is
    `epsilon` for each of the `window` samples (the core wants one value per sample when `use_multiple_epsilons`)."""

    def __init__(self, window: int, hop: int = 1, *, multiple_epsilons: Optional[Sequence[float]] = None, **params: Any):
        super().__init__(window, hop, multiple_epsilons=multiple_epsilons, **params)

    def _block_params(self, params: dict) -> dict:
        if params.get("multiple_epsilons") is None:
            params = {**params, "multiple_epsilons": [params.get("epsilon", 0.5)] * self.window}  # C++ default
        return super()._block_params(params)

    def _window_changed(self) -> None:
        if self._params.get("multiple_epsilons") is None:
            self._invalidate_block()  # one epsilon per sample of the new window


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="RecurrencePlot (RecurrenceMatrix)")
class RecurrencePlot(_Epsilons, _SeriesBlock):
    r"""Recurrence plot of a window of states: when a movement returns close to a state it has visited before.

    Visualizes and stores the recurrences of a multichannel movement signal, for example the posture or the position of
    a participant, as a binary matrix whose entry :math:`(i, j)` is 1 when the states at samples :math:`i` and
    :math:`j` of the window are closer than a threshold,

    .. math::

        R_{ij} = \Theta\left(\epsilon_i - \lVert x_i - x_j \rVert_p\right), \qquad
        \lVert v \rVert_p = \Big(\sum_c |v_c|^p\Big)^{1/p},

    with :math:`\Theta` the Heaviside step (a distance equal to :math:`\epsilon` is not a recurrence), :math:`p` the
    ``order`` and :math:`\epsilon_i` the threshold of row :math:`i` (``epsilon`` unless ``use_multiple_epsilons``).
    The diagonal is 1. Periodic movements give diagonal lines, whose spacing is the period.

    Parameters
    ----------
    window : int
        Samples per analysis window (no default). Changing it keeps the newest samples; a larger window warms up
        again. *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    multiple_epsilons : sequence of float, optional
        One threshold per sample of the window, in the unit of the signal, used when ``use_multiple_epsilons`` is
        ``True``; the threshold of row :math:`i` is ``multiple_epsilons[i]``. ``None`` (default) means ``epsilon``
        for every sample of the window. *(live)*
    order : float, optional
        Order :math:`p` of the Minkowski distance, positive (default 2: Euclidean); ``numpy.inf`` gives the maximum
        norm. *(live)*
    epsilon : float, optional
        Recurrence threshold, in the unit of the signal (default 0.5). *(live)*
    use_multiple_epsilons : bool, optional
        Use ``multiple_epsilons`` instead of ``epsilon`` (default ``False``). *(live)*

    Notes
    -----
    **Inputs.** ``process(series, *, timestamp=None)`` takes one sample of ``C`` channels (the state vector);
    ``run(series, *, timestamps=None)`` takes ``(T, C)``.

    **Outputs.** ``recurrence_matrix`` (0/1, shape ``(window, window)``): the plot of the last complete window.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for NaN or infinite values.

    **Corrected in the core.** ``order`` was ignored (every order above 0 gave the Euclidean distance); it is the
    Minkowski order.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sin(0.5 * np.arange(30))[:, None]
    >>> matrix = RecurrencePlot(window=30, epsilon=0.3).run(x).recurrence_matrix[-1]
    >>> matrix.shape, round(float(matrix.mean()), 2)
    ((30, 30), 0.27)
    """
    _core_class = _sync.RecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("recurrence_matrix", (None, None), doc="recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(recurrence_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="CrossRecurrencePlot (CrossRecurrenceMatrix)")
class CrossRecurrencePlot(_Epsilons, _SeriesBlock):
    r"""Cross-recurrence plot of two windows of states: when one movement visits states of the other.

    Compares two multichannel movement signals with the same channels, for example two participants performing the
    same gesture, as a binary matrix whose entry :math:`(i, j)` is 1 when the state :math:`x_i` of the first window and
    the state :math:`y_j` of the second one are closer than a threshold,

    .. math::

        R_{ij} = \Theta\left(\epsilon_i - \lVert x_i - y_j \rVert_p\right),

    with the distance and the thresholds defined as for `RecurrencePlot`. Long diagonal lines mean that the two
    signals follow the same trajectory, possibly with a time shift.

    Parameters
    ----------
    window : int
        Samples per analysis window (no default). Changing it keeps the newest samples; a larger window warms up
        again. *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    multiple_epsilons : sequence of float, optional
        One threshold per sample of the window, in the unit of the signal, used when ``use_multiple_epsilons`` is
        ``True``; the threshold of row :math:`i` is ``multiple_epsilons[i]``. ``None`` (default) means ``epsilon``
        for every sample of the window. *(live)*
    order : float, optional
        Order :math:`p` of the Minkowski distance, positive (default 2: Euclidean); ``numpy.inf`` gives the maximum
        norm. *(live)*
    epsilon : float, optional
        Recurrence threshold, in the unit of the signal (default 0.5). *(live)*
    use_multiple_epsilons : bool, optional
        Use ``multiple_epsilons`` instead of ``epsilon`` (default ``False``). *(live)*

    Notes
    -----
    **Inputs.** ``process(first_series, second_series, *, timestamp=None)`` takes one sample of ``C`` channels of each
    series; ``run(first_series, second_series, *, timestamps=None)`` takes two ``(T, C)`` series.

    **Outputs.** ``cross_recurrence_matrix`` (0/1, shape ``(window, window)``): the plot of the last complete
    window.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for NaN or infinite values.

    **Corrected in the core.** ``order`` was ignored (every order above 0 gave the Euclidean distance), and the rows of
    a plot of two series of different length were scrambled.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sin(0.5 * np.arange(30))[:, None]
    >>> matrix = CrossRecurrencePlot(window=30, epsilon=0.3).run(x, x).cross_recurrence_matrix[-1]
    >>> matrix.shape, round(float(matrix.mean()), 2)
    ((30, 30), 0.27)
    """
    _core_class = _sync.CrossRecurrencePlot
    _finite_inputs = True

    def _inputs(self) -> Inputs:
        return Inputs(Input("first_series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"),
                      Input("second_series", InputKind.SAMPLE, (None,), doc="state vector, one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("cross_recurrence_matrix", (None, None), doc="cross-recurrence matrix, 1 = recurrence"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(cross_recurrence_matrix=raw, timestamp=timestamp)


__all__ = ["RecurrencePlot", "CrossRecurrencePlot"]
