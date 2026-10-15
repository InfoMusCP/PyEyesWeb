from typing import Any, Literal, Optional
import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature, check_range, require_rate
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.base.signatures import input_mode_factory
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.low_level.kinematics import _InferredDimsBlock


class _SpeedProfileMetric(MinimumWindow, WindowedFeature, CoreFeature):
    """What the four metrics of a speed profile share: one value per call, a buffered window of at least 10 samples,
    one scalar output, and ``sampling_rate`` (required: the window has no time axis of its own)."""

    MIN_WINDOW = 10
    _rate_required = True

    def __init__(self, window: int, hop: int, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _inputs(self) -> Inputs:
        return Inputs(Input("speed", InputKind.SAMPLE, (1,), unit="units/s", doc="speed of the movement"))

    def _process_window(self, series, *, timestamp=None):
        profile = np.asarray(series, dtype=float)
        if reason := non_finite(profile, allow_empty=True):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        if profile.size < self.MIN_WINDOW:
            return self._no_output(Status.WARMING_UP, f"fewer than {self.MIN_WINDOW} samples", timestamp)
        name = self._OUTPUTS.names[0]
        value = self._block.process(np.ascontiguousarray(profile.ravel()))
        finite = np.isfinite(value)
        return self._result(status=Status.OK if finite else Status.INVALID_INPUT,
                           reason="" if finite else f"{name} is NaN: the profile cannot support it",
                           timestamp=timestamp, **{name: value})


@describe(Layer.LOW_LEVEL)
class SpectralArcLength(_SpeedProfileMetric):
    r"""Spectral arc length (SPARC) of a speed profile: smoothness from the shape of its amplitude spectrum.

    A smooth movement has a speed profile with a single bell-shaped peak, whose amplitude spectrum is concentrated at
    low frequencies; a movement made of several corrections, or with tremor, has a spectrum with extra peaks and a
    longer tail. SPARC measures the length of the normalised amplitude spectrum :math:`\hat{V}(f)` of the speed over the
    band :math:`[0, f_c]`, with the frequency also normalised by the cut-off :math:`f_c`,

    .. math::

        \mathrm{SPARC} = -\int_{0}^{f_c} \sqrt{\left(\frac{1}{f_c}\right)^{2}
        + \left(\frac{d\hat{V}(f)}{df}\right)^{2}} \, df, \qquad \hat{V}(f) = \frac{V(f)}{\max_f V(f)},

    where :math:`V(f)` is the magnitude of the Fourier transform of the (zero-padded) speed of the window. The cut-off
    is adaptive: the highest frequency at which :math:`\hat{V}` is still above ``amplitude_threshold``, limited to
    ``[minimum_cutoff_frequency, maximum_cutoff_frequency]``. The measure is dimensionless and independent of the
    amplitude and duration of the movement; it is negative, and closer to 0 means smoother.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    sampling_rate : float
        Sampling rate of the speed in Hz. Required: the window carries no time axis of its own. *(live)*
    amplitude_threshold : float, optional
        Fraction of the spectrum maximum, in [0, 1], above which a frequency counts for the cut-off (dimensionless).
        Defaults to ``0.05``. *(live)*
    minimum_cutoff_frequency : float, optional
        Lower limit of the cut-off frequency, in Hz (positive). Defaults to ``2.0``. *(live)*
    maximum_cutoff_frequency : float, optional
        Upper limit of the cut-off frequency, in Hz (not below the minimum). Defaults to ``20.0``. *(live)*

    Notes
    -----
    **Inputs.** One speed value per call, ``process(speed, *, timestamp=None)``, in any unit of length per second; the
    speed is used as given (no filtering). ``run(speeds, *, timestamps=None)`` takes a whole 1-D recording. Compute the
    speed beforehand, for example with ``Kinematics(output_type="velocity")``. ``timestamp`` only labels the result: it
    does not enter the computation and is not checked.

    **Outputs.** ``spectral_arc_length`` (dimensionless, negative; closer to 0 is smoother) of the last complete
    window.

    **Statuses.** ``WARMING_UP`` while fewer than 10 samples are available (``"k of N samples"``), ``NO_OUTPUT``
    between two windows when ``hop > 1``, ``INVALID_INPUT`` when the profile cannot support the measure (a constant
    or null speed, for example) or a sample is NaN or infinite.

    The value depends on the zero-padding and cut-off choices: compare windows of the same length and parameters.
    Speed derived from positions is noisy: filter or smooth it first.

    References
    ----------
    :cite:`balasubramanian2015smoothness`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import SpectralArcLength
    >>> t = np.arange(100) / 100.0
    >>> bell = np.sin(np.pi * t) ** 2  # one smooth bell-shaped speed peak
    >>> feature = SpectralArcLength(window=100, sampling_rate=100.0)
    >>> round(float(feature.run(bell).spectral_arc_length[-1]), 2)
    -1.43
    """

    _OUTPUTS = Schema(Output("spectral_arc_length", doc="Spectral arc length (SPARC); closer to 0 is smoother."))
    _core_class = core.motion.SpectralArcLength

    def __init__(self, window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None,
                 amplitude_threshold: float = 0.05, minimum_cutoff_frequency: float = 2.0,
                 maximum_cutoff_frequency: float = 20.0):
        super().__init__(window, hop, sampling_rate=sampling_rate, amplitude_threshold=amplitude_threshold,
                         minimum_cutoff_frequency=minimum_cutoff_frequency,
                         maximum_cutoff_frequency=maximum_cutoff_frequency)


@describe(Layer.LOW_LEVEL)
class LogDimensionlessJerk(_SpeedProfileMetric):
    r"""Log dimensionless jerk of a speed or acceleration profile: smoothness from the jerk of the movement.

    The jerk, the rate of change of the acceleration, is large for a jerky movement and small for a smooth one. The
    log dimensionless jerk (LDLJ) normalises its squared integral by the duration and the peak amplitude of the
    movement, so that movements of different size and speed can be compared, and takes the negative logarithm. For a
    speed profile :math:`v(t)` over a window of duration :math:`T`,

    .. math::

        \mathrm{LDLJ} = -\ln\left( \frac{T^{3}}{v_{\max}^{2}} \int_{0}^{T}
        \left( \frac{d^{2}v}{dt^{2}} \right)^{2} dt \right),

    with the derivatives taken by finite differences. In ``"acceleration"`` mode the input is the acceleration
    magnitude and the jerk is its first difference, normalised by the duration and the peak of the acceleration. The
    measure is dimensionless and negative; closer to 0 means smoother, and a flat signal gives 0.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    sampling_rate : float
        Sampling rate of the signal in Hz. Required: the window carries no time axis of its own. *(live)*
    input_mode : {"velocity", "acceleration"}, optional
        What the input holds: the speed (default) or the acceleration magnitude.
        ``LogDimensionlessJerk.from_velocity(...)`` and ``LogDimensionlessJerk.from_acceleration(...)`` build one or
        the other. *(live)*

    Notes
    -----
    **Inputs.** One value per call, ``process(value, *, timestamp=None)``: the speed (length/s) or the acceleration
    magnitude (length/s^2), used as given (no filtering); ``run(values, *, timestamps=None)`` takes a whole 1-D
    recording. Compute it beforehand, for example with ``Kinematics``. ``timestamp`` only labels the result: it does
    not enter the computation and is not checked.

    **Outputs.** ``log_dimensionless_jerk`` (dimensionless, negative; closer to 0 is smoother) of the last complete
    window.

    **Statuses.** ``WARMING_UP`` while fewer than 10 samples are available (``"k of N samples"``), ``NO_OUTPUT``
    between two windows when ``hop > 1``, ``INVALID_INPUT`` when the profile cannot support the measure or a sample is
    NaN or infinite.

    Differentiating a noisy signal amplifies the noise: filter or smooth the speed first.

    References
    ----------
    :cite:`balasubramanian2015smoothness`, :cite:`melendez2021imu`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import LogDimensionlessJerk
    >>> t = np.arange(100) / 100.0
    >>> bell = np.sin(np.pi * t) ** 2  # one smooth bell-shaped speed peak
    >>> feature = LogDimensionlessJerk(window=100, sampling_rate=100.0)
    >>> round(float(feature.run(bell).log_dimensionless_jerk[-1]), 1)
    -5.3
    """

    _OUTPUTS = Schema(Output("log_dimensionless_jerk", doc="Log dimensionless jerk; closer to 0 is smoother."))
    _core_class = core.motion.LogDimensionlessJerk

    def __init__(self, window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None,
                 input_mode: Literal["velocity", "acceleration"] = "velocity"):
        super().__init__(window, hop, sampling_rate=sampling_rate, input_mode=input_mode)

    @input_mode_factory("velocity")
    def from_velocity(cls) -> "LogDimensionlessJerk":
        """Log dimensionless jerk of a speed profile: one speed value (length/s) per call, buffered over ``window``
        samples; the jerk is the second difference of the speed. Takes the parameters of ``LogDimensionlessJerk`` except
        ``input_mode``."""

    @input_mode_factory("acceleration")
    def from_acceleration(cls) -> "LogDimensionlessJerk":
        """Log dimensionless jerk of an acceleration profile: one acceleration magnitude (length/s^2) per call, buffered
        over ``window`` samples; the jerk is the first difference of the acceleration. Takes the parameters of
        ``LogDimensionlessJerk`` except ``input_mode``."""

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), unit="units/s or units/s^2",
                            doc="speed or acceleration magnitude of the movement, as `input_mode` says"))


@describe(Layer.LOW_LEVEL)
class Harmonicity(_SpeedProfileMetric):
    r"""Harmonicity of a speed profile: 1 for a single bell-shaped speed peak, lower for an irregular speed.

    A smooth, ballistic movement has one peak of speed; a repeated movement alternates peaks and valleys. The
    harmonicity compares the number of peaks of the speed in the window with the number of sign changes of its
    gradient (the turning points of the speed): it is 1 when peaks and valleys alternate regularly, as in a single
    bell-shaped profile or in a regular oscillation, and lower when the speed has turning points that do not belong to
    that pattern (a maximum at the border of the window is not counted as a peak, for example). The measure is
    dimensionless and lies in [0, 1].

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    sampling_rate : float
        Sampling rate of the speed in Hz. Required: the window carries no time axis of its own. *(live)*

    Notes
    -----
    **Inputs.** One speed value per call, ``process(speed, *, timestamp=None)``, in any unit of length per second;
    ``run(speeds, *, timestamps=None)`` takes a whole 1-D recording. The speed is used as given (no filtering).
    ``timestamp`` only labels the result: it does not enter the computation and is not checked.

    **Outputs.** ``harmonicity`` (dimensionless, in [0, 1]; 1 is the most harmonic) of the last complete window.

    **Statuses.** ``WARMING_UP`` while fewer than 10 samples are available (``"k of N samples"``), ``NO_OUTPUT``
    between two windows when ``hop > 1``, ``INVALID_INPUT`` when a sample is NaN or infinite.

    Known limitation: on the synthetic profiles tried (bell, oscillation, noise) the index is 1, so it separates
    conditions poorly; check it on your data before relying on it.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import Harmonicity
    >>> t = np.arange(100) / 100.0
    >>> bell = np.sin(np.pi * t) ** 2  # one smooth bell-shaped speed peak
    >>> feature = Harmonicity(window=100, sampling_rate=100.0)
    >>> round(float(feature.run(bell).harmonicity[-1]), 2)
    1.0
    """

    _OUTPUTS = Schema(Output("harmonicity", doc="Harmonicity index of the speed profile, in [0, 1]."))
    _core_class = core.motion.Harmonicity

    def __init__(self, window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None):
        super().__init__(window, hop, sampling_rate=sampling_rate)


@describe(Layer.LOW_LEVEL)
class SubmovementCount(_SpeedProfileMetric):
    r"""Number of sub-movements of a speed profile: its prominent speed peaks, at least 100 ms apart.

    A simple reaching movement has one peak of speed; corrections and hesitations add further peaks, called
    sub-movements. The feature counts the peaks of the speed in the window whose prominence is at least
    ``prominence_factor`` times the maximum of the window and that are separated by at least 100 ms. The count is
    dimensionless; fewer sub-movements means a smoother movement.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    sampling_rate : float
        Sampling rate of the speed in Hz, which turns the 100 ms separation into samples. Required: the window
        carries no time axis of its own. *(live)*
    prominence_factor : float, optional
        Minimum prominence of a peak, as a fraction of the speed maximum of the window (not negative,
        dimensionless). Defaults to ``0.1``. *(live)*

    Notes
    -----
    **Inputs.** One speed value per call, ``process(speed, *, timestamp=None)``, in any unit of length per second;
    ``run(speeds, *, timestamps=None)`` takes a whole 1-D recording. The speed is used as given (no filtering).
    ``timestamp`` only labels the result: it does not enter the computation and is not checked.

    **Outputs.** ``submovement_count`` (integer, 0 or more) of the last complete window; 0 for a speed below 1e-6.

    **Statuses.** ``WARMING_UP`` while fewer than 10 samples are available (``"k of N samples"``), ``NO_OUTPUT``
    between two windows when ``hop > 1``, ``INVALID_INPUT`` when a sample is NaN or infinite.

    Noise creates spurious peaks: filter or smooth the speed first, or raise ``prominence_factor``.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import SubmovementCount
    >>> t = np.linspace(0.0, 1.0, 200)
    >>> speed = sum(np.exp(-(((t - c) / 0.04) ** 2)) for c in (0.25, 0.75))  # two separate bell-shaped peaks
    >>> feature = SubmovementCount(window=200, sampling_rate=200.0)
    >>> int(feature.run(speed).submovement_count[-1])
    2
    """

    _OUTPUTS = Schema(Output("submovement_count", kind=int, doc="Number of detected sub-movements."))
    _core_class = core.motion.SubmovementCount

    def __init__(self, window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None,
                 prominence_factor: float = 0.1):
        super().__init__(window, hop, sampling_rate=sampling_rate, prominence_factor=prominence_factor)


@describe(Layer.LOW_LEVEL)
class CurvatureDispersion(_InferredDimsBlock):
    r"""Curvature-based smoothness index of a movement, from its velocity and acceleration vectors.

    The index relates the curvature of the path to the distance covered over the last ``window`` calls: it compares how
    much the path bends with how far the point travelled, and it is 1 while the movement is slower than
    ``movement_threshold`` (a still point has no smoothness to measure). It is computed from the velocity
    :math:`\mathbf{v}` and the acceleration :math:`\mathbf{a}` of the point, from which the feature derives the
    curvature :math:`\kappa` of the path and the arc length :math:`\lVert\mathbf{v}\rVert\,dt` covered at each call; it
    keeps both over a ring of ``window`` calls and returns one dimensionless value per call, from the first call on.
    The two rings fill over ``window`` calls and their empty entries (zeros) weigh in until then.

    Parameters
    ----------
    dims : int, optional
        Number of components of the vectors: 1, 2 or 3. ``None`` (default) takes it from the first frame. In 1D the
        curvature is 0, so the index is NaN (``INVALID_INPUT``) above the threshold. *(structural)*
    window : int, optional
        Calls held by the curvature and arc-length rings (at least 2). Defaults to ``50``. *(structural)*
    movement_threshold : float, optional
        Speed below which the movement counts as still and the index is 1, in m/s (scaled by ``units``). Defaults to
        ``0.005``. *(live)*
    sampling_rate : float, optional
        Sampling rate in Hz, used when no timestamp is given. Defaults to ``None`` (one second per call, and the
        ``reason`` says so). *(live)*
    units : {"m", "mm"}, optional
        Unit of the data: scales ``movement_threshold`` (the vectors and the output are never scaled). Defaults to
        ``"m"``. *(live)*

    Notes
    -----
    **Inputs.** ``process(velocity, acceleration, *, timestamp=None)``: the velocity vector (length/s) and the
    acceleration vector (length/s^2) of the movement at this call, ``dims`` components each. Compute them beforehand
    with two ``Kinematics(output_dims="components")``, one with ``output_type="velocity"`` and one with
    ``output_type="acceleration"``, with the same filter parameters and time rule, and feed both to every call.
    ``reset()`` clears the rings. ``timestamp`` is in seconds.

    **Outputs.** ``curvature_dispersion`` (dimensionless; 1 when the movement is below the threshold).

    **Statuses.** ``OK`` from the first call; ``INVALID_INPUT`` when an input is NaN or infinite, the timestamp does
    not increase, or the index is not finite (for example a perfectly straight path, whose curvature is 0).

    Corrected in the core: the arc length added the speed alone above the movement threshold but the speed times the
    time step below it; every call now adds the speed times the time step. This index was the ``smoothness`` output
    of ``Kinematics``.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import CurvatureDispersion, Kinematics
    >>> t = np.arange(200) / 100.0
    >>> path = np.c_[np.cos(2 * np.pi * t), np.sin(2 * np.pi * t)]  # a circle of radius 1 m
    >>> speed = Kinematics(output_type="velocity", output_dims="components", sampling_rate=100.0)
    >>> acceleration = Kinematics(output_type="acceleration", output_dims="components", sampling_rate=100.0)
    >>> feature = CurvatureDispersion(window=50, sampling_rate=100.0)
    >>> for point in path:
    ...     result = feature.process(speed.process(point).velocity, acceleration.process(point).acceleration)
    >>> round(float(result.curvature_dispersion), 2)
    0.06
    """

    _OUTPUTS = Schema(Output("curvature_dispersion",
                            doc="Curvature-based smoothness index; 1 when the movement is below the threshold."))
    _core_class = core.trajectory.CurvatureDispersion
    _timed = True
    _unit_params = {"movement_threshold": 1}  # a speed threshold: length per time

    def _inputs(self) -> Inputs:
        return Inputs(Input("velocity", InputKind.SAMPLE, (self._dims,), unit="units/s", doc="velocity vector"),
                      Input("acceleration", InputKind.SAMPLE, (self._dims,), unit="units/s^2",
                            doc="acceleration vector"))

    def _frame_dims(self, frame: Any) -> Optional[int]:
        shape = np.shape(frame)
        return shape[0] if len(shape) == 1 and shape[0] >= 1 else None

    def process(self, velocity: Any, acceleration: Any, *, timestamp: Optional[float] = None) -> Result:
        self._infer_dims(velocity)
        self.inputs.check((velocity, acceleration), type(self).__name__)  # the declared shapes now know `dims`
        dt = self._time_step(timestamp)
        vectors = [np.ascontiguousarray(vector, dtype=float) for vector in (velocity, acceleration)]
        if reason := non_finite(vectors):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(*vectors, dt), timestamp)


@describe(Layer.LOW_LEVEL, eyesweb="smoothnessindex (Smoothness)")
class CurvatureVelocityCorrelation(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Correlation between curvature and velocity of a 1 to 3 channel trajectory, a smoothness index.

    A smooth movement slows down where its path bends: curvature and speed are negatively related. The feature
    measures that coupling inside a window of the trajectory. The samples of the window are
    smoothed and differentiated by a Savitzky-Golay filter, which gives the velocity :math:`v_k` and the curvature
    :math:`\kappa_k` at every sample :math:`k`; the ``smoothness`` output is then, by default, their Pearson
    correlation coefficient over the window,

    .. math::

        S = \frac{\sum_k (\kappa_k - \bar{\kappa})(v_k - \bar{v})}
        {\sqrt{\sum_k (\kappa_k - \bar{\kappa})^2 \, \sum_k (v_k - \bar{v})^2}} \in [-1, 1],

    which is strongly negative for a smooth movement (high curvature, low speed). With ``correlation_type="simplified"``
    the index is a simplified form of the original block, bounded above by ``upper_limit``. The outputs also hold the
    per-sample ``curvature`` and ``velocity`` series of the window and their standard deviations.

    The filters keep their history between windows (the previous window feeds the start of the next one), so
    consecutive windows overlap by ``window - hop`` samples; ``hop=window`` means no overlap.

    Parameters
    ----------
    window : int
        Samples per window, at least ``filter_window_length + 1`` (10 with the default filter). Changing it, or
        ``hop`` or ``sampling_rate``, on a running feature restarts the filters with an empty history.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    sampling_rate : float
        Sampling rate of the series in Hz. Required: the window carries no time axis of its own.
    velocity_threshold : float, optional
        Velocity threshold of the original block, in the unit of the velocity output. Defaults to ``0.001``.
        *(live)*
    standard_deviation_threshold : float, optional
        Threshold of the original block on the standard deviations of the curvature and the velocity, in their
        output units. Defaults to ``0.0001``. *(live)*
    upper_limit : float, optional
        Upper bound of the index (dimensionless); the ``"simplified"`` index is capped at it. Defaults to ``100.0``.
        *(live)*
    filter_polyorder : int, optional
        Order of the Savitzky-Golay polynomial (at least 3). Defaults to ``3``. *(structural)*
    filter_window_length : int, optional
        Samples of the Savitzky-Golay window (odd, greater than ``filter_polyorder``). Defaults to ``9``.
        *(structural)*
    correlation_type : {"pearson", "simplified"}, optional
        ``"pearson"`` (default): the Pearson correlation coefficient. ``"simplified"``: the simplified index of the
        original block, at most ``upper_limit``. *(live)*
    differentiate : bool, optional
        Whether the derivatives of the filter are taken with respect to time in seconds. With the default
        ``False`` they are taken per sample: at 100 Hz the velocity is 100 times smaller than with ``True``, while the
        curvature and the correlation do not change. *(structural)*
    input_kind : {"static", "dynamic"}, optional
        ``"static"`` (default): every window has the shape of the first one. ``"dynamic"``: the series may change
        length from window to window; a window of another length or channel count rebuilds the filters with an empty
        history. *(structural)*

    Notes
    -----
    **Inputs.** One sample per call, ``process(sample, *, timestamp=None)``, with the channels of the trajectory: 1
    value (y), 2 (x, y) or 3 (x, y, z). The feature buffers ``window`` samples and computes every ``hop`` samples.
    ``run(samples, *, timestamps=None)`` takes a whole ``(T, channels)`` recording. ``timestamp`` only labels the
    result: it does not enter the computation and is not checked.

    **Outputs.** ``smoothness`` (dimensionless; in [-1, 1] for ``"pearson"``); ``curvature``: the per-sample curvature
    of the window (``window`` values, 1/length); ``velocity``: the per-sample velocity of the window (``window``
    values, length per sample unless ``differentiate``, length/s); ``curvature_std`` and ``velocity_std``: their
    sample standard deviations of the window.

    **Statuses.** ``WARMING_UP`` while the first window fills (``"k of N samples"``) and for the first window after
    it, because the filters need a previous window (``smoothness`` is then NaN); ``NO_OUTPUT`` between two windows
    when ``hop > 1``; ``INVALID_INPUT`` when the data does not support the index (a null movement, for example) or a
    sample is NaN or infinite.

    Corrected in the core: the curvature used half of the second derivative of the Savitzky-Golay fit. With
    ``input_kind="dynamic"``, the window after a change of length or channel count is ``WARMING_UP`` (it was reported
    as ``INVALID_INPUT``) and the windows after it are valid again.

    References
    ----------
    :cite:`mazzarino2009impulsivity`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import CurvatureVelocityCorrelation
    >>> t = np.arange(300) / 100.0
    >>> ellipse = np.c_[2 * np.cos(np.pi * t), np.sin(np.pi * t)]
    >>> feature = CurvatureVelocityCorrelation(window=100, hop=100, sampling_rate=100.0)
    >>> round(float(feature.run(ellipse).smoothness[-1]), 2)
    -0.94
    """
    _core_class = core.motion.SmoothnessIndex
    _DEFAULT_FILTER_WINDOW_LENGTH = 9
    _warmed_shape = None  # shape of the last window processed, None while the filters have no history

    def __init__(self, window: int, hop: int = 1, *, sampling_rate: Optional[float] = None, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()
        self.sampling_rate = sampling_rate

    @property
    def sampling_rate(self) -> float:
        """Sampling rate of the series in Hz; a change gives the filters an empty history."""
        return self._sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
        require_rate(type(self).__name__, value)
        check_range("sampling_rate", value)
        value = float(value)
        if value != self.__dict__.get("_sampling_rate", value):
            self._restart_filters()  # the filters take the rate of the series at their first call
        self._sampling_rate = value

    def _restart_filters(self) -> None:
        if self._built is not None:
            self._built.reset()
            self._state_lost()

    def _window_changed(self) -> None:
        self._restart_filters()  # the filters are built for the length and overlap of the series

    def _state_lost(self) -> None:
        super()._state_lost()
        self._warmed_shape = None

    @property
    def filter_window_length(self) -> int:
        return int(self._param("filter_window_length", self._DEFAULT_FILTER_WINDOW_LENGTH))

    @filter_window_length.setter
    def filter_window_length(self, value: int) -> None:
        self._check_window(filter_window_length=value)
        self._set_param("filter_window_length", value)

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("filter_window_length", self.filter_window_length)) + 1

    def reset(self) -> None:
        super().reset()
        self._warmed_shape = None

    def _inputs(self) -> Inputs:
        return Inputs(Input("series", InputKind.SAMPLE, (None,), doc="y, (x, y) or (x, y, z) of the signal"))

    def _schema(self) -> Schema:
        return Schema(Output("smoothness"), Output("curvature", (None,), unit="1/<length>", doc="curvature per sample"),
                      Output("velocity", (None,), unit="<length>/s", doc="velocity per sample"),
                      Output("curvature_std", unit="1/<length>"), Output("velocity_std", unit="<length>/s"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        series = np.asarray(series, dtype=float)
        if reason := non_finite(series, allow_empty=True):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        try:
            smoothness, curvature, velocity, curvature_std, velocity_std = self._block.process(
                series, self.sampling_rate, self.window - self.hop)
        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)
        warming_up, self._warmed_shape = series.shape != self._warmed_shape, series.shape  # a new shape: empty history
        status, reason = Status.OK, ""
        if np.isnan(smoothness) or np.isnan(curvature_std):
            status, reason = (Status.WARMING_UP, "the filters need a previous window") if warming_up else (
                Status.INVALID_INPUT, "the data does not support smoothness (NaN)")
        return self._result(status=status, reason=reason, smoothness=smoothness,
                           curvature=np.asarray(curvature, dtype=float), velocity=np.asarray(velocity, dtype=float),
                           curvature_std=curvature_std, velocity_std=velocity_std, timestamp=timestamp)


__all__ = ["SpectralArcLength", "LogDimensionlessJerk", "Harmonicity", "SubmovementCount", "CurvatureDispersion",
           "CurvatureVelocityCorrelation"]
