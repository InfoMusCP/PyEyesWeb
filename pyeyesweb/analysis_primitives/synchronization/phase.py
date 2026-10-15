"""Phase synchronization of two signals.

`PhaseLockingValue` measures how consistently the instantaneous phases of two band-limited signals keep a constant
offset, the Phase Locking Value (PLV).
"""

from typing import Optional

from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb._core import core
from pyeyesweb.utils.validators import validate_and_normalize_filter_params

from ._blocks import _TrainPairBlock, _train


@describe(Layer.ANALYSIS_PRIMITIVE)
class PhaseLockingValue(_TrainPairBlock):
    r"""Phase Locking Value of two signals, from the Hilbert phases of their (optionally band-passed) series.

    The Phase Locking Value quantifies phase synchronization between two movement signals, for example the
    oscillation of two dancers' hands or of two body segments, independently of their amplitudes. Each window of
    each signal is optionally band-pass filtered, the instantaneous phase :math:`\phi(t)` is taken from the
    analytic signal obtained with the Hilbert transform, and the PLV is the length of the mean phasor of the phase
    difference over the :math:`N` samples of the window:

    .. math::

        z_x(t) = x(t) + i\,\mathcal{H}[x(t)], \qquad \phi_x(t) = \arg z_x(t), \qquad
        \Delta\phi(t) = \phi_x(t) - \phi_y(t),

    .. math::

        \mathrm{PLV} = \left| \frac{1}{N} \sum_{t=1}^{N} e^{\,i\,\Delta\phi(t)} \right| \in [0, 1].

    A value of 1 means that the phase difference is constant over the window (perfect phase locking, whatever the
    offset); a value near 0 means that it is uniformly spread (no phase relation).

    The Hilbert phase is only meaningful for narrow-band signals: on broadband movement data the PLV stays near 1
    whatever the coupling. Nothing is filtered unless ``low_frequency`` and ``high_frequency`` are given, so band-limit
    the signals first or pass the band. For 2D or 3D data reduce each participant to one signal first, for example
    the tangential ``velocity`` output of ``Kinematics``, or the projection on the dominant axis of the movement.

    Parameters
    ----------
    window : int
        Samples per analysis window (no default). Changing it keeps the newest samples; a larger window warms up
        again. With a filter band the window must be at least 28 samples (the zero-phase filter pads the series by
        three times its length). *(live)*
    hop : int, optional
        Samples between two results, ``1 <= hop <= window`` (default 1). *(live)*
    low_frequency, high_frequency : float, optional
        Lower and upper edge, in Hz, of the band-pass filter applied to each window before the phase is estimated.
        The filter is a fixed 4th-order Butterworth band-pass applied forwards and backwards (zero phase), so it
        adds no phase distortion. Both or neither must be given (default
        ``None``: no filtering); ``0 < low_frequency < high_frequency < sampling_rate / 2``. *(live)*
    sampling_rate : float, optional
        Sampling rate of the signals in Hz (default ``None``). Required when a filter band is given, unused
        otherwise. *(live)*

    Notes
    -----
    **Inputs.** ``process(first_signal, second_signal, *, timestamp=None)`` takes one scalar of each signal per call;
    ``run(first_signal, second_signal, *, timestamps=None)`` takes two 1-D series.

    **Outputs.** ``phase_locking_value`` (dimensionless, in [0, 1]): the PLV of the last complete window.

    **Statuses.** ``WARMING_UP`` (``"k of N samples"``) until the first window of ``window`` samples is full,
    ``NO_OUTPUT`` between two windows when ``hop > 1``, ``INVALID_INPUT`` when a sample of the window is NaN or
    infinite. A constant signal has no defined phase evolution: the block reports 1 for two constant windows.

    The measure assumes that the phase relation is stationary over the window.

    References
    ----------
    :cite:`varni2010system`, :cite:`sabharwal2022husync`

    Examples
    --------
    >>> import numpy as np
    >>> t = np.arange(200) / 100.0
    >>> x = np.sin(2 * np.pi * 3 * t)
    >>> locked, drifting = np.sin(2 * np.pi * 3 * t + 0.5), np.sin(2 * np.pi * 4.3 * t)
    >>> plv = PhaseLockingValue(window=200, low_frequency=1.0, high_frequency=10.0, sampling_rate=100.0)
    >>> round(float(plv.run(x, locked).phase_locking_value[-1]), 2)
    0.98
    >>> plv.reset()
    >>> round(float(plv.run(x, drifting).phase_locking_value[-1]), 2)
    0.15
    """

    _OUTPUTS = Schema(
        Output("phase_locking_value", doc="Phase Locking Value in [0, 1]; 1 is perfect phase synchronization."),
    )

    _core_class = core.sync.PhaseLockingValue
    _finite_inputs = True

    def __init__(self, window: int, hop: int = 1, *, low_frequency: Optional[float] = None,
                 high_frequency: Optional[float] = None, sampling_rate: Optional[float] = None):
        if (low_frequency is None) != (high_frequency is None):
            raise ValueError("PhaseLockingValue: low_frequency and high_frequency go together (or neither: no filtering)")
        super().__init__(window, hop, low_frequency=low_frequency, high_frequency=high_frequency,
                         sampling_rate=sampling_rate)

    def _block_params(self, params: dict) -> dict:
        """The band-pass as the block takes it: `filter_params=(low, high, rate)`, validated here. Without both edges
        (a live change one edge at a time passes through that state) nothing is filtered."""
        low, high, rate = (params.get(name) for name in ("low_frequency", "high_frequency", "sampling_rate"))
        if low is None or high is None:
            return {}
        if rate is None:
            raise ValueError("PhaseLockingValue: filtering needs sampling_rate (Hz)")
        return {"filter_params": validate_and_normalize_filter_params((low, high, rate))}

    def _minimum_window(self, **overrides) -> int:
        params = {**self._params, **overrides}
        filtering = params.get("low_frequency") is not None and params.get("high_frequency") is not None
        return 28 if filtering else 1  # filtfilt pads 3 * filter length (27) samples

    def _inputs(self) -> Inputs:
        return Inputs(_train("first_signal", "one value per call"), _train("second_signal", "one value per call"))

    def _to_result(self, raw: float, timestamp: Optional[float]) -> Result:
        return self._result(phase_locking_value=raw, timestamp=timestamp)


__all__ = ['PhaseLockingValue']
