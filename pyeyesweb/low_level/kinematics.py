"""Kinematics of a moving point: velocity, acceleration, curvature, direction (EyesWeb TrajectoryAnalysis).

`Kinematics` returns a `Result` with one output per requested `output_type` (`velocity` by default), named after it:
a scalar for TANGENTIAL output, a `(dimension,)` vector with components x, y, z for COMPONENTS. A `direction` output is
always COMPONENTS (the schema mirrors that). `timestamp` is the timestamp in seconds. Point and time-series input always
give `OK`, except when a result is not finite.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import InferredDims, non_finite
from pyeyesweb.base.signatures import input_mode_factory

_trajectory = core.trajectory
_MODES = _trajectory.KinematicsInputMode

# Unit of each output type in the unit of the data (`units`); a direction is a unit vector.
_OUTPUT_UNITS = {"smoothed": "{}", "velocity": "{}/s", "acceleration": "{}/s^2", "jerk": "{}/s^3", "curvature": "1/{}", "direction": ""}


class _InferredDimsBlock(InferredDims, FrameFeature):
    """A block with one output whose `dims` (1, 2 or 3) is optional: taken from the first frame, the block built then."""
    _lazy_block = True

    def __init__(self, *, dims: Optional[int] = None, **params: Any):
        super().__init__(**params)
        self.dims = dims
        if dims is not None:  # an explicit dimension is validated now, as before
            self._block

    def _dimension(self) -> Optional[int]:
        return self._dims

    def _set_dims(self, value: Optional[int], inferred: bool) -> None:
        if self._built is not None:  # the filters are sized by the dimension: a new block, from scratch
            self._invalidate_block()
            self._state_lost()
        super()._set_dims(value, inferred)

    def _build_block(self, params: Optional[dict] = None) -> Any:
        return super()._build_block({**(self._params if params is None else params), "dims": self._dims})

    def _vector(self, name: str, unit: str = "") -> Output:
        """The `(dims,)` output `name`, of unknown length until the dimension is."""
        dimension = self._dims
        return Output(name, (dimension,), components=None if dimension is None else XYZ[:dimension], unit=unit)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        (name,) = self.outputs.names
        finite = bool(np.isfinite(raw).all())
        return self._result(status=Status.OK if finite else Status.INVALID_INPUT,
                           reason="" if finite else "the result is not finite", timestamp=timestamp, **{name: raw})


@describe(Layer.LOW_LEVEL, eyesweb="TrajectoryFeatures-1D/2D/3D (Kinematics1D/2D/3D)")
class Kinematics(_InferredDimsBlock):
    """EyesWeb TrajectoryFeatures-1D/2D/3D (Kinematics1D/2D/3D).

    Point input (`input_mode="point"`, default; `Kinematics.from_point(...)`): `process(point, *, timestamp=None)` takes one
    `(D,)` sample per call (`run` takes `(T, D)`); the block keeps its own window, so no buffer is added here. Time-series
    input (`input_mode="time_series"`; `Kinematics.from_series(...)`): `process(series, *, timestamp=None)` takes a `(D, N)`
    series, newest sample last. The factories take the constructor's parameters except `input_mode`. `timestamp` is a
    timestamp in seconds (`NaN` in the result when not given).

    `output_type` is one of `smoothed`, `velocity`, `acceleration`, `jerk`, `curvature`, `direction`, or a list of them
    (`output_type=["velocity", "acceleration"]`): the result has one output per type, in that order and named after it, all
    computed from the same Savitzky-Golay pass and each identical to a `Kinematics` built for that type alone. `output_dims`
    applies to every output: a scalar for TANGENTIAL (default), a `(dimension,)` vector (components x, y, z) for COMPONENTS,
    except `direction`, which is always a vector. Derivatives are per second^k with the time step. The curvature-based smoothness index is a separate feature, `CurvatureDispersion`, fed with the velocity
    and the acceleration of this one (`output_dims="components"`). The Savitzky-Golay filter has frame
    `filter_window_length` (odd, > 3 and > `filter_polyorder`) and order `filter_polyorder`; the estimate is the fit to the newest `filter_window_length` samples (the window holds that many) evaluated at their centre, so it lags the newest sample by (filter_window_length - 1) / 2 samples (EyesWeb skips the newest sample and lags one sample more).
    """
    _core_class = _trajectory.Kinematics
    _timed = True
    _unit_params = {"movement_threshold": 1}  # a speed threshold: length per time

    @input_mode_factory("point")
    def from_point(cls) -> "Kinematics":
        """Kinematics of a point streamed one sample per call: `process(point)` takes a `(D,)` position (or signal value),
        `run` a `(T, D)` recording. Stateful: the block keeps its sliding Savitzky-Golay window. Takes the parameters of
        `Kinematics` except `input_mode`."""

    @input_mode_factory("time_series")
    def from_series(cls) -> "Kinematics":
        """Kinematics of a series buffered by the caller: `process(series)` takes a `(D, N)` matrix (N at least
        `filter_window_length`, the same N every call, newest sample last) and describes its newest sample. The
        Takes the parameters of `Kinematics` except `input_mode`."""

    def _output_types(self) -> list:
        """The requested output types as enum members, in order."""
        types = self._param("output_type", _trajectory.KinematicsOutputType.VELOCITY)  # C++ default
        return list(types) if isinstance(types, list) else [types]

    def _schema(self) -> Schema:
        dims = _trajectory.KinematicsOutputDimension
        components = self._param("output_dims", dims.TANGENTIAL) == dims.COMPONENTS
        names = [(kind.name.lower(), kind) for kind in self._output_types()]
        return Schema(*(self._vector(name, self._unit(name)) if components or kind == _trajectory.KinematicsOutputType.DIRECTION
                        else Output(name, unit=self._unit(name)) for name, kind in names))  # a Direction output is always a vector

    def _unit(self, name: str) -> str:
        return _OUTPUT_UNITS[name].format(self._params["units"])

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        values = dict(zip(self.outputs.names, raw))
        bad = [name for name, value in values.items() if not np.isfinite(value).all()]
        reason = "the result is not finite" + (f": {', '.join(bad)}" if bad and len(values) > 1 else "")
        return self._result(status=Status.INVALID_INPUT if bad else Status.OK, reason=reason if bad else "",
                           timestamp=timestamp, **values)

    def _mode(self) -> Any:
        return self._param("input_mode", _MODES.POINT)

    def _inputs(self) -> Inputs:
        dimension = self._dims
        if self._mode() == _MODES.TIME_SERIES:
            return Inputs(Input("series", InputKind.MATRIX, (dimension, None),
                                doc="(D, N) series, newest sample last"))
        return Inputs(Input("point", InputKind.SAMPLE, (dimension,),
                            doc="position of the point (or value of the signal)"))

    def _frame_dims(self, frame: Any) -> Optional[int]:
        shape = np.shape(frame)
        return shape[0] if len(shape) == (1 if self._mode() == _MODES.POINT else 2) and shape[0] >= 1 else None

    def _process(self, data: Any, timestamp: Optional[float]) -> Result:
        """The feature of one sample or series, as `input_mode` says."""
        mode = self._mode()
        dt = self._time_step(timestamp)
        values = np.asarray(data, dtype=float)
        if reason := non_finite(values):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)
        push = self._block.push_point if mode == _MODES.POINT else self._block.process_series
        return self._to_result(push(values, dt), timestamp)


__all__ = ["Kinematics"]
