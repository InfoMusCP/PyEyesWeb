"""Phase Synchronization analysis for paired signals.

This module implements the [Synchronization][pyeyesweb.analysis_primitives.synchronization.Synchronization]
feature, which measures the phase locking between two or more time series
using the Phase Locking Value (PLV).
"""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.signal_processing import compute_phase_synchronization, validate_and_normalize_filter_params


@dataclass(slots=True)
class SynchronizationResult(FeatureResult):
    """Output contract for Phase Synchronization.
    
    Attributes
    ----------
    plv : float
        The Phase Locking Value in `[0, 1]`. A value of `1.0` indicates
        perfect phase synchronization; `0.0` indicates no synchronization.
    """
    plv: float = 0.0


class Synchronization(DynamicFeature):
    """Real-time phase synchronization analyzer for paired signals.

    !!! note
        Computes the Phase Locking Value (PLV) between multiple signals after
        optional bandpass filtering and Hilbert transform.

    Read more in the [User Guide](../../user_guide/theoretical_framework/analysis_primitives/synchronization.md).

    Parameters
    ----------
    filter_params : dict, optional
        Parameters for the bandpass filter applied before phase estimation.
        See [validate_and_normalize_filter_params](../utils/signal_processing.md#validate_and_normalize_filter_params)
        for details.

    Examples
    --------
    >>> sync = Synchronization(filter_params={'low': 1.0, 'high': 10.0})
    """

    def __init__(self, filter_params=None):
        super().__init__()
        self.filter_params = filter_params

    @property
    def filter_params(self):
        """Parameters for the bandpass pre-filter."""
        return self._filter_params

    @filter_params.setter
    def filter_params(self, value):
        self._filter_params = validate_and_normalize_filter_params(value)

    def compute(self, window_data: np.ndarray) -> SynchronizationResult:
        """Compute the Phase Locking Value (PLV) for the window.

        Parameters
        ----------
        window_data : numpy.ndarray of shape (Time, N_signals, N_dims)
            Input motion data.

        Returns
        -------
        SynchronizationResult
            Result containing the PLV.  Returns
            `SynchronizationResult(is_valid=False)` if fewer than 2 signals
            are present.
        """
        # Flatten to (Time, Signals)
        data = window_data.reshape(window_data.shape[0], -1)

        if data.shape[1] < 2:
            return SynchronizationResult(is_valid=False)

        # Assumes compute_phase_synchronization expects a 2D array of (Time, N_Signals)
        plv = compute_phase_synchronization(data, self.filter_params)
        return SynchronizationResult(plv=float(plv))
