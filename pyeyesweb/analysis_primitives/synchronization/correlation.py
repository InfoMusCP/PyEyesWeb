"""Correlation-based synchronization matrices.

`CorrelationsMatrix` and `GeneralisedAutoCorrelation` run on a static series and are windowed features (``window``,
``hop``); `PartialRecurrenceSynchronization` transforms the matrix that `CorrelationsMatrix` returns, one matrix per
call. Their results are ``OK`` unless the docstring of the feature says otherwise.
"""

from itertools import count
from typing import Any, Optional, Sequence

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import non_finite

from ._blocks import _SeriesBlock

_sync = core.sync
_OutputType = _sync.GeneralisedAutoCorrelationOutputType


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="CorrelationsMatrix (CPRMatrix)")
class CorrelationsMatrix(_SeriesBlock):
    r"""Matrix of positive Pearson correlations between the signals of a group over a sliding window.

    Describes how much each pair among ``number_of_inputs`` movement signals (for example one signal per
    participant, or per body segment) varies together over the window. For the signals :math:`s_k` the entry
    :math:`(k, l)` of the matrix is

    .. math::

        C_{kl} = \max\left(0, \; \rho(s_k, s_l)\right) \;\; (k \ne l), \qquad C_{kk} = 1,

    where :math:`\rho` is the Pearson correlation coefficient over the ``window`` samples: anti-correlation is
    reported as 0, so :math:`C_{kl} \in [0, 1]`. The matrix is the input of `PartialRecurrenceSynchronization`.

    Parameters
    ----------
    window : int
        Samples per analysis window, at least 2 (no default). Changing it keeps the newest samples; a larger window
        warms up again. *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    number_of_inputs : int, optional
        Number of signals (default 4); the size of the frame and of the matrix. *(structural)*

    Notes
    -----
    **Inputs.** ``process(signals, *, timestamp=None)`` takes one frame of ``number_of_inputs`` values;
    ``run(signals, *, timestamps=None)`` takes ``(T, number_of_inputs)``.

    **Outputs.** ``correlations_matrix`` (dimensionless, shape ``(number_of_inputs, number_of_inputs)``): symmetric,
    ones on the diagonal, entries in [0, 1].

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for a NaN or infinite value in the window or in the result. A signal
    that is constant over the window has no defined correlation: its row and column are 0 outside the diagonal.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.sin(2 * np.pi * np.arange(50) / 50)
    >>> matrix = CorrelationsMatrix(window=50, number_of_inputs=3)
    >>> matrix.run(np.column_stack([a, 2 * a, -a])).correlations_matrix[-1].round(2)
    array([[1., 1., 0.],
           [1., 1., 0.],
           [0., 0., 1.]])
    """
    _core_class = _sync.CorrelationsMatrix
    _core_names = {"number_of_inputs": "n_inputs"}
    _finite_inputs = True

    def _minimum_window(self, **overrides: Any) -> int:
        return 2  # a correlation needs two samples

    def _state_lost(self) -> None:
        super()._state_lost()
        self._buffer, self._pushed = None, 0  # a new `number_of_inputs` is a new frame size: the buffer starts again

    def _inputs(self) -> Inputs:
        return Inputs(Input("signals", InputKind.SAMPLE, (int(self._param("number_of_inputs", 4)),),  # C++ default
                            doc="one value per signal"))

    def _schema(self) -> Schema:
        number_of_inputs = int(self._param("number_of_inputs", 4))  # C++ default
        return Schema(Output("correlations_matrix", (number_of_inputs, number_of_inputs), doc="CPR matrix"))

    def _call_block(self, args: Sequence[Any]) -> np.ndarray:
        return self._block.process(list(args[0]))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._finite_result(correlations_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="PARS (PartialRecurrenceSynchronizationMatrix)")
class PartialRecurrenceSynchronization(FrameFeature):
    r"""Partial correlation of a correlation matrix: the direct synchronization between each pair of signals.

    Takes the matrix :math:`C` of `CorrelationsMatrix` and removes the part of each pairwise correlation that is
    explained by the other signals of the group, so that two signals that are only linked through a third one are
    not reported as synchronized. With :math:`P = C^{-1}`,

    .. math::

        S_{kl} = \frac{|P_{kl}|}{\sqrt{P_{kk}\,P_{ll}}},

    the absolute value of the partial correlation between :math:`k` and :math:`l`. An entry is 0 when a diagonal
    entry of :math:`P` is not positive, and the whole matrix is 0 when :math:`C` is singular (for example constant
    or perfectly collinear signals).

    The feature has no parameters.

    Notes
    -----
    **Inputs.** ``process(correlations_matrix, *, timestamp=None)`` takes one square matrix (kind ``MATRIX``; a
    non-square matrix raises ``ValueError``); ``run(correlations_matrix, *, timestamps=None)`` takes
    ``(T, n, n)``.

    **Outputs.** ``synchronization_matrix`` (dimensionless, shape ``(n, n)`` with ``n`` taken from the input):
    symmetric, entries in [0, 1].

    **Statuses.** ``INVALID_INPUT`` for a NaN or infinite entry; otherwise ``OK``.

    Examples
    --------
    >>> import numpy as np
    >>> pars = PartialRecurrenceSynchronization()
    >>> pars.process(np.array([[1, .8, .5], [.8, 1, .6], [.5, .6, 1]])).synchronization_matrix.round(2)
    array([[1.  , 0.72, 0.04],
           [0.72, 1.  , 0.38],
           [0.04, 0.38, 1.  ]])
    """
    _core_class = _sync.PARS

    def _inputs(self) -> Inputs:
        return Inputs(Input("correlations_matrix", InputKind.MATRIX, (None, None), doc="square matrix of CorrelationsMatrix"))

    def _schema(self) -> Schema:
        return Schema(Output("synchronization_matrix", (None, None), doc="partial recurrence synchronisation matrix"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        matrix = np.asarray(frame, dtype=float)
        if matrix.ndim == 2 and matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"PartialRecurrenceSynchronization: the matrix must be square, got shape {matrix.shape}")
        if reason := non_finite(matrix):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return super()._process(matrix, timestamp)

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        return self._result(synchronization_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="generalised_auto_correlation")
class GeneralisedAutoCorrelation(_SeriesBlock):
    r"""Recurrence rate of a multichannel series as a function of the lag: how self-similar a movement is in time.

    For a window of :math:`N` states :math:`x_i` (one value per channel) the recurrence rate at lag :math:`\tau`
    is the fraction of samples whose state returns within :math:`\epsilon` after :math:`\tau` samples,

    .. math::

        \mathrm{RR}(\tau) = \frac{1}{N - \tau}\,
        \#\{\, i < N - \tau \;:\; \lVert x_i - x_{i+\tau} \rVert \le \epsilon \,\},

    with the Euclidean norm over the channels. A periodic movement shows peaks of :math:`\mathrm{RR}(\tau)` at
    the multiples of its period. With ``output_type="function_of_tau"`` the feature returns :math:`\mathrm{RR}` for
    ``tau_spread`` consecutive lags starting at ``tau_min``; with ``output_type="scalar"`` it returns the single
    value at lag ``tau``.

    Parameters
    ----------
    window : int
        Samples per analysis window (no default); see Notes for the shortest window. Changing it keeps the newest
        samples; a larger window warms up again. *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    epsilon : float, optional
        Recurrence threshold, in the unit of the signal (default 0.1). *(live)*
    output_type : {"function_of_tau", "scalar"}, optional
        Whether to return the recurrence rate for a range of lags or for the single lag ``tau`` (default
        ``"function_of_tau"``). *(structural)*
    tau : int, optional
        Lag in samples of the single value of ``output_type="scalar"`` (default 1). *(live)*
    tau_min : int, optional
        First lag in samples of ``output_type="function_of_tau"`` (default 1); ``set_tau_min`` changes it at run
        time. *(live)*
    tau_spread : int, optional
        Number of lags returned by ``output_type="function_of_tau"`` (default 10), limited to two thirds of the
        window. *(structural)*

    Notes
    -----
    **Inputs.** ``process(signal, *, timestamp=None)`` takes one sample of ``C`` channels; ``run(signal,
    *, timestamps=None)`` takes ``(T, C)``.

    **Outputs.** ``recurrence_rate`` (dimensionless, in [0, 1]) and ``taus`` (integer, samples): the lag of each
    entry; both have the size of the lag range (a single entry for ``"scalar"``).

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for NaN or infinite values. The window must be longer than
    ``tau_min`` plus the (limited) ``tau_spread``, and at least 2 samples for ``"scalar"``; a shorter window raises
    ``ValueError``.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sin(2 * np.pi * np.arange(50) / 50)[:, None]
    >>> rec = GeneralisedAutoCorrelation(window=50, tau_spread=3, epsilon=0.1).run(x)
    >>> rec.recurrence_rate[-1].round(2), rec.taus[-1]
    (array([0.61, 0.25, 0.21]), array([1, 2, 3]))
    """
    _core_class = _sync.GeneralisedAutoCorrelation
    _finite_inputs = True

    def _minimum_window(self, **overrides: Any) -> int:
        params = {**self._params, **overrides}
        if params.get("output_type") == _OutputType.SCALAR:
            return 2
        tau_min, spread = int(params.get("tau_min", 1)), int(params.get("tau_spread", 10))  # C++ defaults
        # the core clamps the spread to 2N/3 and wants tau_min + spread < N
        return next(size for size in count(1) if tau_min + min(spread, 2 * size // 3) < size)

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("recurrence_rate", (None,), doc="fraction of recurring samples per lag"),
                      Output("taus", (None,), kind=int, unit="samples", doc="lag of each recurrence rate"))

    def set_tau_min(self, tau_min: int) -> None:
        """Change the first lag, in samples, at run time (equivalent to assigning ``tau_min``)."""
        self._set_param("tau_min", int(tau_min))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        scalar = self._param("output_type", None) == _OutputType.SCALAR
        first = int(self._param("tau" if scalar else "tau_min", 1))  # C++ defaults
        return self._result(recurrence_rate=raw, taus=np.arange(first, first + len(raw)), timestamp=timestamp)


__all__ = ["CorrelationsMatrix", "PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation"]
