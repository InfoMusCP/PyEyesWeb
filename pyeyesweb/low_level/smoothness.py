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
    amplitude and duration of the movement; it is negative, and closer to 0 means smoother. The cut-off frequency of
    the arc is bounded below by ``minimum_cutoff_frequency`` (2 Hz by default), a bound that is not in the original
    definition: it keeps the value from depending on the spectrum below it, but for a movement longer than about 1.5 s,
    or a window with a low-frequency spectrum, the value grows more negative with the duration, so it is no longer
    independent of the duration.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
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
    :cite:`balasubramanian2015analysis`

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
    measure is dimensionless and negative; closer to 0 means smoother. A flat signal has no jerk to measure and gives
    ``INVALID_INPUT``. In ``"acceleration"`` mode the input is a magnitude, so the gravity that the LDLJ-A variant of the
    literature removes from the acceleration vector is not removed here: give an acceleration with gravity already taken
    off, or use the speed.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Changing it on a running feature keeps the newest samples. Defaults to
        ``60``. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
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
    between two windows when ``hop > 1``, ``INVALID_INPUT`` when the profile cannot support the measure (a flat or null
    signal: no jerk, or no peak to normalise by) or a sample is NaN or infinite.

    Differentiating a noisy signal amplifies the noise: filter or smooth the speed first.

    References
    ----------
    :cite:`balasubramanian2015analysis`, :cite:`melendez2021imu`

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
        """Log dimensionless jerk of a speed profile.

        One speed value (length/s) per call, buffered over ``window`` samples; the jerk is the second difference of the
        speed. Takes the parameters of ``LogDimensionlessJerk`` except ``input_mode``.
        """

    @input_mode_factory("acceleration")
    def from_acceleration(cls) -> "LogDimensionlessJerk":
        """Log dimensionless jerk of an acceleration profile.

        One acceleration magnitude (length/s^2) per call, buffered over ``window`` samples; the jerk is the first
        difference of the acceleration. Takes the parameters of ``LogDimensionlessJerk`` except ``input_mode``.
        """

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), unit="units/s or units/s^2",
                            doc="speed or acceleration magnitude of the movement, as `input_mode` says"))


@describe(Layer.LOW_LEVEL, released=False)
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
        ``60``. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
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
    >>> from pyeyesweb.low_level.smoothness import Harmonicity
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
        ``60``. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
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


@describe(Layer.LOW_LEVEL, eyesweb="smoothnessindex (Smoothness)")
class CurvatureVelocityCorrelation(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Correlation between curvature and velocity of a 1 to 3 channel trajectory, a smoothness index.

    A smooth movement slows down where its path bends: curvature and speed are negatively related, close to a power
    law (log speed falls linearly with log curvature). The feature measures that coupling inside a window of the
    trajectory, as Mazzarino et al. (2009) and Piana et al. (2016) define it. The samples of the window are smoothed and
    differentiated by a Savitzky-Golay filter, which gives the velocity :math:`v_k` and the curvature :math:`\kappa_k`
    at every sample :math:`k`. The index is computed on their logarithms; by default (``correlation_type="simplified"``,
    the papers' form for a short window) it is

    .. math::

        S = \frac{1}{\sigma_{\log\kappa}\,\sigma_{\log |v|}},

    capped at ``upper_limit``: large for a smooth movement, whose curvature and speed vary together within a narrow
    band, and close to 1 for a jerky one (about 10 against 1 on the smooth and jerky figure-eights of the example
    session). ``correlation_type="pearson"`` gives the correlation coefficient of the two logarithms instead, in
    [-1, 1]; on movement data it does not rank smooth above jerky (stops pair a near-zero speed with a large curvature,
    which also correlates strongly). Samples with zero curvature or speed have no logarithm and are left out of the
    window.

    The filters keep their history between windows (the previous window feeds the start of the next one), so
    consecutive windows overlap by ``window - hop`` samples; ``hop=window`` means no overlap.

    Parameters
    ----------
    window : int
        Samples per window, at least ``filter_window_length + 1`` (10 with the default filter). Changing it, or
        ``hop`` or ``sampling_rate``, on a running feature restarts the filters with an empty history. *(structural)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(structural)*
    sampling_rate : float
        Sampling rate of the series in Hz. Required: the window carries no time axis of its own. *(structural)*
    standard_deviation_threshold : float, optional
        Smallest variation that counts: when the standard deviation of the (linear) curvature or velocity of the window
        is below it, there is nothing to correlate (a straight path, a constant speed) and the result is
        ``INVALID_INPUT``. It acts on the quantities the filters give, so on the velocity per sample (not per second)
        unless ``differentiate`` is set; the ``velocity`` outputs are always per second. Defaults to ``0.0001``.
        *(live)*
    upper_limit : float, optional
        Upper bound of the index (dimensionless); the ``"simplified"`` index is capped at it. Defaults to ``100.0``.
        *(live)*
    filter_polyorder : int, optional
        Order of the Savitzky-Golay polynomial (at least 3). Defaults to ``3``. *(structural)*
    filter_window_length : int, optional
        Samples of the Savitzky-Golay window (odd, greater than ``filter_polyorder``). Defaults to ``9``.
        *(structural)*
    correlation_type : {"simplified", "pearson"}, optional
        ``"simplified"`` (default): :math:`1 / (\sigma_{\log\kappa}\,\sigma_{\log |v|})`, at most ``upper_limit``.
        ``"pearson"``: the correlation coefficient of the logarithms. *(live)*
    differentiate : bool, optional
        Whether the derivatives of the filter are taken with respect to time in seconds. With the default
        ``False`` they are taken per sample and the velocity outputs are multiplied by ``sampling_rate``, so they
        are per second in both modes. The curvature (of a 2 or 3 channel trajectory) and both indices do not depend on
        it (a scale factor does not change the spread of a logarithm); ``standard_deviation_threshold`` does, because
        it acts on the velocity before that conversion. *(structural)*
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
    values, length/s); ``log_curvature_std`` and ``log_speed_std``: the sample standard deviations of the logarithms
    of curvature and speed that enter the index (dimensionless).

    **Statuses.** ``WARMING_UP`` while the first window fills (``"k of N samples"``) and for the first window after
    it, because the filters need a previous window (no output); ``NO_OUTPUT`` between two windows when ``hop > 1``;
    ``INVALID_INPUT`` (no output) when there is nothing to correlate (curvature or velocity does not vary, or fewer
    than 3 samples have a non-zero curvature and speed) or a sample is NaN or infinite.

    **Changed from EyesWeb.** The block correlated the linear values of curvature and velocity; the index here is on
    their logarithms, as the papers define it, and ``"simplified"`` is the default. A window without variation gave
    ``upper_limit`` or a correlation of rounding noise; it is ``INVALID_INPUT``.

    Corrected in the core: the curvature used half of the second derivative of the Savitzky-Golay fit. With
    ``input_kind="dynamic"``, the window after a change of length or channel count is ``WARMING_UP`` (it was reported
    as ``INVALID_INPUT``) and the windows after it are valid again.

    References
    ----------
    :cite:`mazzarino2009need`, :cite:`piana2016adaptive`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import CurvatureVelocityCorrelation
    >>> t = np.arange(300) / 100.0
    >>> ellipse = np.c_[2 * np.cos(np.pi * t), np.sin(np.pi * t)]
    >>> feature = CurvatureVelocityCorrelation(window=100, hop=100, sampling_rate=100.0)
    >>> round(float(feature.run(ellipse).smoothness[-1]), 2)
    5.77
    >>> pearson = CurvatureVelocityCorrelation(window=100, hop=100, sampling_rate=100.0, correlation_type="pearson")
    >>> round(float(pearson.run(ellipse).smoothness[-1]), 2)  # an ellipse follows the power law exactly
    -1.0
    """
    _core_class = core.motion.SmoothnessIndex
    _hidden_params = frozenset({"velocity_threshold"})  # read nowhere by the block: left at its default
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
                      Output("log_curvature_std", doc="standard deviation of log curvature"),
                      Output("log_speed_std", doc="standard deviation of log speed"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        series = np.asarray(series, dtype=float)
        if reason := non_finite(series, allow_empty=True):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        try:
            smoothness, curvature, velocity, curvature_std, velocity_std = self._block.process(
                series, self.sampling_rate, self.window - self.hop)
        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)
        if not self._param("differentiate", False):  # the filters give a velocity per sample: the output is per second
            velocity = np.asarray(velocity) * self.sampling_rate  # (the spread of its logarithm does not change)
        warming_up, self._warmed_shape = series.shape != self._warmed_shape, series.shape  # a new shape: empty history
        if warming_up:
            return self._no_output(Status.WARMING_UP, "the filters need a previous window", timestamp)
        if np.isnan(smoothness):
            return self._no_output(Status.INVALID_INPUT, "nothing to correlate: curvature or velocity does not vary, or "
                                   "fewer than 3 samples have a non-zero curvature and speed", timestamp)
        if not (np.isfinite(curvature).all() and np.isfinite(velocity).all()):
            return self._no_output(Status.INVALID_INPUT, "curvature or velocity is not finite (values too large)",
                                   timestamp)
        return self._result(status=Status.OK, reason="", smoothness=smoothness,
                           curvature=np.asarray(curvature, dtype=float), velocity=np.asarray(velocity, dtype=float),
                           log_curvature_std=curvature_std, log_speed_std=velocity_std, timestamp=timestamp)


__all__ = ["SpectralArcLength", "LogDimensionlessJerk", "Harmonicity", "SubmovementCount",
           "CurvatureVelocityCorrelation"]
