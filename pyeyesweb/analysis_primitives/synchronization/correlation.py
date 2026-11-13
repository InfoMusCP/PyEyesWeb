"""Correlation-based synchronization matrices.

`GeneralisedAutoCorrelation` runs on a static series and is a windowed feature (``window``, ``hop``);
`PartialRecurrenceSynchronization` transforms a correlation matrix (for instance ``numpy.corrcoef`` of the curves of
`GeneralisedAutoCorrelation`), one matrix per call. Their results are ``OK`` unless the docstring of the feature says otherwise.
"""

from typing import Any, Optional

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


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="PARS (PartialRecurrenceSynchronizationMatrix)")
class PartialRecurrenceSynchronization(FrameFeature):
    r"""Partial correlation of a correlation matrix: the direct synchronization between each pair of signals.

    Takes a correlation matrix :math:`C` (for instance ``numpy.corrcoef``) and removes the part of each pairwise correlation that is
    explained by the other signals of the group, so that two signals that are only linked through a third one are
    not reported as synchronized. With :math:`P = C^{-1}`,

    .. math::

        S_{kl} = \frac{|P_{kl}|}{\sqrt{P_{kk}\,P_{ll}}},

    the absolute value of the partial correlation between :math:`k` and :math:`l` (:cite:`varni2010system`, eq. 4).
    The input is the matrix of the synchronization indices of the pairs; in the paper, the CPR index: ``np.corrcoef``
    of the recurrence-rate curves of ``GeneralisedAutoCorrelation`` (Varni eq. 3, signed). The feature does not compute
    it.

    The feature has no parameters.

    Notes
    -----
    **Inputs.** ``process(correlations_matrix, *, timestamp=None)`` takes one square matrix (kind ``MATRIX``; a
    non-square matrix raises ``ValueError``); ``run(correlations_matrix, *, timestamps=None)`` takes
    ``(T, n, n)``.

    **Outputs.** ``synchronization_matrix`` (dimensionless, shape ``(n, n)`` with ``n`` taken from the input):
    symmetric, entries in [0, 1].

    **Statuses.** ``INVALID_INPUT`` for a NaN or infinite entry; for a matrix too ill-conditioned to invert (2-norm
    condition number, as ``numpy.linalg.cond``, above :math:`10^{12}`; for example constant or perfectly collinear
    signals); and for a matrix that is not positive definite (a diagonal entry of :math:`P` not positive, so it is not
    a correlation matrix). Otherwise ``OK``. The original block did not invert :math:`C` (corrected in the core), and
    the first port gave zeros in the undefined cases.

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
        return Inputs(Input("correlations_matrix", InputKind.MATRIX, (None, None), doc="square correlation matrix"))

    def _schema(self) -> Schema:
        return Schema(Output("synchronization_matrix", (None, None), doc="partial recurrence synchronisation matrix"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        matrix = np.asarray(frame, dtype=float)
        if matrix.ndim == 2 and matrix.shape[0] != matrix.shape[1]:
            raise ValueError(f"PartialRecurrenceSynchronization: the matrix must be square, got shape {matrix.shape}")
        if reason := non_finite(matrix):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        self._condition = np.linalg.cond(matrix) if matrix.size else 1.0  # names the reason of a NaN result
        return super()._process(matrix, timestamp)

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        if np.isnan(raw).any() and not self._condition <= 1e12:
            return self._no_output(Status.INVALID_INPUT, "ill-conditioned matrix (condition number above 1e12)", timestamp)
        if np.isnan(raw).any():
            return self._no_output(Status.INVALID_INPUT, "not positive definite: not a correlation matrix", timestamp)
        return self._result(synchronization_matrix=raw, timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="generalised_auto_correlation")
class GeneralisedAutoCorrelation(_SeriesBlock):
    r"""Recurrence rate of a multichannel series as a function of the lag: how self-similar a movement is in time.

    For a window of :math:`N` states :math:`x_i` (one value per channel) the recurrence rate at lag :math:`\tau`
    is the fraction of samples whose state returns within :math:`\epsilon` after :math:`\tau` samples, the
    probability of recurrence of :cite:`varni2010system` (eq. 2) and :cite:`marwan2007recurrence` (eq. 111),

    .. math::

        \mathrm{RR}(\tau) = \frac{1}{N - \tau}\,
        \#\{\, i < N - \tau \;:\; \lVert x_i - x_{i+\tau} \rVert \le \epsilon \,\},

    with the Euclidean norm over the channels; a distance equal to :math:`\epsilon` counts, as in
    ``RecurrencePlot``, of which :math:`\mathrm{RR}(\tau)` is the density of one diagonal. A periodic movement shows
    peaks of :math:`\mathrm{RR}(\tau)` at the multiples of its period. The curve of two signals is what their
    synchronization index compares (the CPR of :cite:`varni2010system`, eq. 3): ``np.corrcoef`` of the two curves. With ``output_type="function_of_tau"`` the feature returns :math:`\mathrm{RR}` at
    the lags 1 to ``max_lag``; with ``output_type="scalar"`` it returns the single value at lag ``lag``.

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
        Whether to return the recurrence rate for a range of lags or for the single lag ``lag`` (default
        ``"function_of_tau"``). *(structural)*
    lag : int, optional
        Lag in samples of the single value of ``output_type="scalar"`` (default 1), smaller than ``window``. *(live)*
    max_lag : int, optional
        Largest lag in samples of ``output_type="function_of_tau"``, which returns the lags 1 to ``max_lag``
        (default 10), smaller than ``window``. *(structural)*

    Notes
    -----
    **Inputs.** ``process(signal, *, timestamp=None)`` takes one sample of ``C`` channels; ``run(signal,
    *, timestamps=None)`` takes ``(T, C)``.

    **Outputs.** ``recurrence_rate`` (dimensionless, in [0, 1]) and ``taus`` (integer, samples): the lag of each
    entry; both have the size of the lag range (a single entry for ``"scalar"``).

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) while the first window fills, ``NO_OUTPUT`` between two
    windows when ``hop > 1``, ``INVALID_INPUT`` for NaN or infinite values. ``lag`` and ``max_lag`` must be
    smaller than ``window``; otherwise the constructor or the setter raises ``ValueError`` (the original block cut the
    lag range silently to two thirds of the window). A large lag rests on few pairs (:math:`N - \tau`); a common
    guideline keeps the lags below about :math:`N/4`.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.sin(2 * np.pi * np.arange(50) / 50)[:, None]
    >>> rec = GeneralisedAutoCorrelation(window=50, max_lag=3, epsilon=0.1).run(x)
    >>> rec.recurrence_rate[-1].round(2), rec.taus[-1]
    (array([0.61, 0.25, 0.21]), array([1, 2, 3]))
    """
    _core_class = _sync.GeneralisedAutoCorrelation
    _finite_inputs = True

    def _build_block(self, params: Optional[dict] = None) -> Any:
        params = self._params if params is None else params
        for name in ("lag", "max_lag"):  # checked here: the core message also names its first lag, which is not public
            if name in params and int(params[name]) < 1:
                raise ValueError(f"GeneralisedAutoCorrelation: {name} must be >= 1, got {params[name]}")
        return super()._build_block(params)

    def _window_changed(self) -> None:
        self._invalidate_block()  # the block fixes the series length (and the lag spread) at its first call; it holds no history

    def _minimum_window(self, **overrides: Any) -> int:
        params = {**self._params, **overrides}
        if params.get("output_type") == _OutputType.SCALAR:
            return int(params.get("lag", 1)) + 1  # C++ default
        return int(params.get("max_lag", 10)) + 1  # the lags 1..max_lag need max_lag < window

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("recurrence_rate", (None,), doc="fraction of recurring samples per lag"),
                      Output("taus", (None,), kind=int, unit="samples", doc="lag of each recurrence rate"))

    def _to_result(self, raw: np.ndarray, timestamp: float) -> Result:
        scalar = self._param("output_type", None) == _OutputType.SCALAR
        first = int(self._param("lag", 1)) if scalar else 1  # C++ defaults
        return self._result(recurrence_rate=raw, taus=np.arange(first, first + len(raw)), timestamp=timestamp)


__all__ = ["PartialRecurrenceSynchronization", "GeneralisedAutoCorrelation"]
