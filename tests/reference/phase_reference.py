"""Phase Synchronization analysis for paired signals.

This module implements the [Synchronization][pyeyesweb.analysis_primitives.synchronization.Synchronization]
feature, which measures the phase locking between two or more time series
using the Phase Locking Value (PLV).
"""

import numpy as np

from pyeyesweb.catalog import Layer, describe
from legacy_base import DynamicFeature
from pyeyesweb.data_models.results import Output, Schema, Status
from legacy_utils import compute_phase_synchronization
from pyeyesweb.utils.validators import validate_and_normalize_filter_params


@describe(Layer.ANALYSIS_PRIMITIVE)
class SynchronizationReference(DynamicFeature):
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

    OUTPUTS = Schema(
        Output("plv", doc="Phase Locking Value in [0, 1]; 1 is perfect phase synchronization."),
    )

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

    def compute(self, window_data: np.ndarray) :
        """Compute the Phase Locking Value (PLV) for the window.

        Parameters
        ----------
        window_data : numpy.ndarray of shape (Time, N_signals, N_dims)
            Input motion data.

        Returns
        -------
        Result
            Output `plv` (float in `[0, 1]`). `Status.INVALID_INPUT` if fewer than 2 signals are present.
        """
        # Flatten to (Time, Signals)
        data = window_data.reshape(window_data.shape[0], -1)

        if data.shape[1] < 2:
            return self.no_output(Status.INVALID_INPUT, "fewer than 2 signals")

        # Assumes compute_phase_synchronization expects a 2D array of (Time, N_Signals)
        plv = compute_phase_synchronization(data, self.filter_params)
        return self.result(plv=float(plv))


__all__ = ["SynchronizationReference"]
