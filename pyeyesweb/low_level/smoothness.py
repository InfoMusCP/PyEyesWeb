from typing import Any, Literal, Optional
import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature, check_range
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.base.signatures import input_mode_factory
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.low_level.kinematics import _InferredDimsBlock


class _SpeedProfileMetric(MinimumWindow, WindowedFeature, CoreFeature):
    """What the four metrics of a speed profile share: one value per call, a buffered window of at least 10 samples
    (the minimum of the original), one scalar output. The maths is in the compiled core."""

    MIN_WINDOW = 10

    def __init__(self, window: int, hop: int, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    def _inputs(self) -> Inputs:
        return Inputs(Input("speed", InputKind.SAMPLE, (1,), unit="units/s", doc="speed of the movement"))

    def _process_window(self, series, *, timestamp=None):
        profile = np.asarray(series, dtype=float)
        if reason := non_finite(profile, allow_empty=True):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        if profile.size < self.MIN_WINDOW:
            return self.no_output(Status.WARMING_UP, f"fewer than {self.MIN_WINDOW} samples", timestamp)
        name = self.OUTPUTS.names[0]
        value = self._block.process(np.ascontiguousarray(profile.ravel()))
        finite = np.isfinite(value)
        return self.result(status=Status.OK if finite else Status.INVALID_INPUT,
                           reason="" if finite else f"{name} is NaN: the profile cannot support it",
                           timestamp=timestamp, **{name: value})


@describe(Layer.LOW_LEVEL)
class SpectralArcLength(_SpeedProfileMetric):
    """Spectral arc length (SPARC) of a speed profile: how smooth a movement is, from the arc length of the amplitude
    spectrum of its speed (maths in the compiled core).

    Input: one speed value per call (units/s). The feature buffers `window` samples and computes every `hop` samples
    (`WARMING_UP` while fewer than 10 samples are available, `NO_OUTPUT` between hops). Compute the speed beforehand,
    for example with `Kinematics(output_type="velocity")`; the signal is used as given (no filtering). `run(speeds)`
    processes a whole recording.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Defaults to `60`.
    hop : int, optional
        New samples between two windows. Defaults to `1`.
    sampling_rate : float, optional
        Sampling rate of the speed in Hz. Defaults to `50.0`.
    amplitude_threshold : float, optional
        Fraction of the spectrum maximum, in [0, 1], above which a frequency counts for the cut-off. Defaults to `0.05`.
    minimum_cutoff_frequency : float, optional
        Lower limit of the cut-off frequency in Hz (positive). Defaults to `2.0`.
    maximum_cutoff_frequency : float, optional
        Upper limit of the cut-off frequency in Hz (not below the minimum). Defaults to `20.0`.

    Returns
    -------
    Result
        `spectral_arc_length` (dimensionless, negative; closer to 0 is smoother). `Status.INVALID_INPUT` when the profile
        cannot support it (a constant speed, for example), `Status.WARMING_UP` below 10 samples.
    """

    OUTPUTS = Schema(Output("spectral_arc_length", doc="Spectral arc length (SPARC); closer to 0 is smoother."))
    _core_class = core.motion.SpectralArcLength

    def __init__(self, window: int = 60, hop: int = 1, sampling_rate: float = 50.0, amplitude_threshold: float = 0.05,
                 minimum_cutoff_frequency: float = 2.0, maximum_cutoff_frequency: float = 20.0):
        super().__init__(window, hop, sampling_rate=sampling_rate, amplitude_threshold=amplitude_threshold,
                         minimum_cutoff_frequency=minimum_cutoff_frequency,
                         maximum_cutoff_frequency=maximum_cutoff_frequency)


@describe(Layer.LOW_LEVEL)
class LogDimensionlessJerk(_SpeedProfileMetric):
    """Log dimensionless jerk of a speed or acceleration profile: how smooth a movement is, from its jerk normalised by
    the amplitude and duration of the movement (maths in the compiled core).

    Input: one value per call, the speed (units/s) or the acceleration magnitude (units/s^2), as `input_mode` says
    (`LogDimensionlessJerk.from_velocity(...)` and `.from_acceleration(...)` build one or the other). The
    feature buffers `window` samples and computes every `hop` samples (`WARMING_UP` while fewer than 10 samples are
    available, `NO_OUTPUT` between hops). Compute the speed or acceleration beforehand, for example with
    `Kinematics`; the signal is used as given (no filtering). `run(values)` processes a whole recording.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Defaults to `60`.
    hop : int, optional
        New samples between two windows. Defaults to `1`.
    sampling_rate : float, optional
        Sampling rate of the signal in Hz. Defaults to `50.0`.
    input_mode : {"velocity", "acceleration"}, optional
        What the input holds: the speed, or the acceleration magnitude (the jerk is then its first difference).
        Defaults to `"velocity"`.

    Returns
    -------
    Result
        `log_dimensionless_jerk` (dimensionless, negative; closer to 0 is smoother; 0 for a flat signal).
        `Status.INVALID_INPUT` when the profile cannot support it, `Status.WARMING_UP` below 10 samples.
    """

    OUTPUTS = Schema(Output("log_dimensionless_jerk", doc="Log dimensionless jerk; closer to 0 is smoother."))
    _core_class = core.motion.LogDimensionlessJerk

    def __init__(self, window: int = 60, hop: int = 1, sampling_rate: float = 50.0,
                 input_mode: Literal["velocity", "acceleration"] = "velocity"):
        super().__init__(window, hop, sampling_rate=sampling_rate, input_mode=input_mode)

    @input_mode_factory("velocity")
    def from_velocity(cls) -> "LogDimensionlessJerk":
        """Log dimensionless jerk of a speed profile: one speed value (units/s) per call, buffered over `window` samples;
        the jerk is the second difference of the speed. Takes the parameters of `LogDimensionlessJerk` except `input_mode`."""

    @input_mode_factory("acceleration")
    def from_acceleration(cls) -> "LogDimensionlessJerk":
        """Log dimensionless jerk of an acceleration profile: one acceleration magnitude (units/s^2) per call, buffered over
        `window` samples; the jerk is the first difference of the acceleration. Takes the parameters of
        `LogDimensionlessJerk` except `input_mode`."""

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), unit="units/s or units/s^2",
                            doc="speed or acceleration magnitude of the movement, as `input_mode` says"))


@describe(Layer.LOW_LEVEL)
class Harmonicity(_SpeedProfileMetric):
    """Harmonicity of a speed profile: 1 for a single bell-shaped speed peak per movement, lower the more the speed
    oscillates (maths in the compiled core).

    Input: one speed value per call (units/s). The feature buffers `window` samples and computes every `hop` samples
    (`WARMING_UP` while fewer than 10 samples are available, `NO_OUTPUT` between hops). Compute the speed beforehand,
    for example with `Kinematics(output_type="velocity")`; the signal is used as given (no filtering). `run(speeds)`
    processes a whole recording.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Defaults to `60`.
    hop : int, optional
        New samples between two windows. Defaults to `1`.
    sampling_rate : float, optional
        Sampling rate of the speed in Hz. Defaults to `50.0`.

    Returns
    -------
    Result
        `harmonicity` (dimensionless, in [0, 1]; 1 is the most harmonic). `Status.WARMING_UP` below 10 samples.
    """

    OUTPUTS = Schema(Output("harmonicity", doc="Harmonicity index of the speed profile, in [0, 1]."))
    _core_class = core.motion.Harmonicity

    def __init__(self, window: int = 60, hop: int = 1, sampling_rate: float = 50.0):
        super().__init__(window, hop, sampling_rate=sampling_rate)


@describe(Layer.LOW_LEVEL)
class SubmovementCount(_SpeedProfileMetric):
    """Number of sub-movements of a speed profile: the prominent peaks of the speed, at least 100 ms apart (maths in the
    compiled core).

    Input: one speed value per call (units/s). The feature buffers `window` samples and computes every `hop` samples
    (`WARMING_UP` while fewer than 10 samples are available, `NO_OUTPUT` between hops). Compute the speed beforehand,
    for example with `Kinematics(output_type="velocity")`; the signal is used as given (no filtering). `run(speeds)`
    processes a whole recording.

    Parameters
    ----------
    window : int, optional
        Samples per window (at least 10). Defaults to `60`.
    hop : int, optional
        New samples between two windows. Defaults to `1`.
    sampling_rate : float, optional
        Sampling rate of the speed in Hz. Defaults to `50.0`.
    prominence_factor : float, optional
        Minimum prominence of a peak, as a fraction of the speed maximum (not negative). Defaults to `0.1`.

    Returns
    -------
    Result
        `submovement_count` (integer; fewer is smoother; 0 for a speed below 1e-6). `Status.WARMING_UP` below 10 samples.
    """

    OUTPUTS = Schema(Output("submovement_count", kind=int, doc="Number of detected sub-movements."))
    _core_class = core.motion.SubmovementCount

    def __init__(self, window: int = 60, hop: int = 1, sampling_rate: float = 50.0, prominence_factor: float = 0.1):
        super().__init__(window, hop, sampling_rate=sampling_rate, prominence_factor=prominence_factor)


@describe(Layer.LOW_LEVEL)
class CurvatureDispersion(_InferredDimsBlock):
    """Curvature-based smoothness index of a movement: how well the path's curvature and the distance covered agree
    over the last `window` calls (maths in the compiled core; this was the `smoothness` output of `Kinematics`).

    Input: the velocity vector and the acceleration vector of the movement at this call, `dims` components each
    (units/s and units/s^2). Compute them beforehand with two `Kinematics(output_dims="components")`, one with
    `output_type="velocity"` and one with `"acceleration"`, with the same filter parameters and time rule, and feed
    both to every call. The feature keeps the curvature and the arc length of the last `window` calls and gives one
    value per call from the first one on; those rings fill over `window` calls (their zeros weigh in until then).
    `reset()` clears them. Time step: `timestamp` if given, else `sampling_rate`, else per sample (see `Kinematics`).

    Parameters
    ----------
    window : int, optional
        Calls the curvature and arc-length rings hold (at least 2). Defaults to `50`.
    movement_threshold : float, optional
        Speed below which the movement counts as still and the index is 1, in m/s (`units`). Defaults to `0.005`.
    dims : int, optional
        Number of components, 1, 2 or 3. Defaults to the size of the first frame. In 1D the curvature is 0, so the
        index is NaN (`INVALID_INPUT`) above the threshold.
    sampling_rate : float, optional
        Sampling rate in Hz, used when no timestamp is given. Defaults to `None` (per sample).
    units : {"m", "mm"}, optional
        Unit of the data: scales `movement_threshold`. Defaults to `"m"`.

    Returns
    -------
    Result
        `curvature_dispersion` (dimensionless; 1 when the movement is below the threshold). `Status.INVALID_INPUT`
        when it is not finite.
    """

    OUTPUTS = Schema(Output("curvature_dispersion",
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
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        return self._to_result(self._block.process(*vectors, dt), timestamp)


@describe(Layer.LOW_LEVEL, eyesweb="smoothnessindex (Smoothness)")
class CurvatureVelocityCorrelation(MinimumWindow, WindowedFeature, CoreFeature):
    """EyesWeb Smoothness (smoothnessindex): correlation between curvature and velocity of a 1-3 channel series.

    Input: one sample per call, `channels` values (1: y; 2: x, y; 3: x, y, z). The feature buffers `window` samples
    and computes every `hop` samples (`WARMING_UP` while the first window fills, `NO_OUTPUT` between hops).
    `_process_window(series)` is the EyesWeb Execute on one complete `(channels, window)` series. The block keeps
    its filter histories between windows (the previous window feeds the start of the next one): consecutive windows
    overlap by `window - hop` samples, EyesWeb's `overlapped_samples`; `hop` defaults to `window` (no overlap).
    With `input_kind` STATIC (default) every window has the shape of the first one; with DYNAMIC a window of any
    length can be passed to `_process_window`; a window of another length or channel count rebuilds the filters with an
    empty history, so it reports `WARMING_UP` (its first curvature samples are 0 / 0) and the windows after it are valid again. `run(samples, timestamps=None)` processes a whole `(T, channels)` recording.

    Parameters
    ----------
    window : int
        Samples per window.
    hop : int, optional
        New samples between two windows. Defaults to `window`.
    sampling_rate : float, optional
        Sampling rate of the series in Hz. Defaults to `25`.
    **params
        The parameters of the EyesWeb block (`filter_polyorder`, `filter_window_length`, `input_kind`, ...).

    Outputs `smoothness`, the per-sample `curvature` and `velocity` series of the window (data-dependent size) and
    their sample standard deviations `curvature_std`, `velocity_std`. `timestamp` is the timestamp in seconds of the newest
    sample (`NaN` when not given). Always `OK`.
    """
    _core_class = core.motion.SmoothnessIndex
    _DEFAULT_FILTER_WINDOW_LENGTH = 9
    _warmed_shape = None  # shape of the last window processed, None while the filters have no history

    def __init__(self, window: int, hop: Optional[int] = None, sampling_rate: float = 25.0, **params: Any):
        super().__init__(window=window, hop=window if hop is None else hop, **params)
        self._check_window()
        self.sampling_rate = float(sampling_rate)

    @property
    def sampling_rate(self) -> float:
        """Sampling rate of the series in Hz; a change gives the filters an empty history."""
        return self._sampling_rate

    @sampling_rate.setter
    def sampling_rate(self, value: float) -> None:
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
        return Schema(Output("smoothness"), Output("curvature", (None,), doc="curvature per sample"),
                      Output("velocity", (None,), doc="velocity per sample"),
                      Output("curvature_std"), Output("velocity_std"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        series = np.asarray(series, dtype=float)
        if reason := non_finite(series, allow_empty=True):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        try:
            smoothness, curvature, velocity, curvature_std, velocity_std = self._block.process(
                series, self.sampling_rate, self.window - self.hop)
        except ValueError as exc:
            return self.no_output(Status.INVALID_INPUT, str(exc), timestamp)
        warming_up, self._warmed_shape = series.shape != self._warmed_shape, series.shape  # a new shape: empty history
        status, reason = Status.OK, ""
        if np.isnan(smoothness) or np.isnan(curvature_std):
            status, reason = (Status.WARMING_UP, "the filters need a previous window") if warming_up else (
                Status.INVALID_INPUT, "the data does not support smoothness (NaN)")
        return self.result(status=status, reason=reason, smoothness=smoothness,
                           curvature=np.asarray(curvature, dtype=float), velocity=np.asarray(velocity, dtype=float),
                           curvature_std=curvature_std, velocity_std=velocity_std, timestamp=timestamp)


__all__ = ["SpectralArcLength", "LogDimensionlessJerk", "Harmonicity", "SubmovementCount", "CurvatureDispersion",
           "CurvatureVelocityCorrelation"]
