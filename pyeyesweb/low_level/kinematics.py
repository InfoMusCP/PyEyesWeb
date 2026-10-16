"""Kinematics of a moving point: velocity, acceleration, jerk, curvature and direction.

``Kinematics`` returns a ``Result`` with one output per requested ``output_type`` (``velocity`` by default), named after
it: a scalar for ``output_dims="tangential"``, a ``(dims,)`` vector with the components x, y, z for ``"components"``;
a ``direction`` output is always a vector. ``timestamp`` is the timestamp in seconds.
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
    r"""Velocity, acceleration, jerk, curvature or direction of a moving point, from a Savitzky-Golay fit.

    ``Kinematics`` describes how a point (a joint, a marker, the centre of mass) moves along its path; with one
    component it describes a scalar signal. The position samples are smoothed and differentiated in one step by a
    Savitzky-Golay filter: the newest ``filter_window_length`` samples are fitted by a polynomial of order
    ``filter_polyorder`` and the estimate is the fit, or one of its derivatives, evaluated at the centre of that window.
    With :math:`\mathbf{x}(t)` the smoothed position, the derivatives are taken with respect to time in seconds,

    .. math::

        \mathbf{v} = \frac{d\mathbf{x}}{dt}, \qquad \mathbf{a} = \frac{d^2\mathbf{x}}{dt^2}, \qquad
        \mathbf{j} = \frac{d^3\mathbf{x}}{dt^3},

    and the curvature is that of the path (:math:`1/r` for a circle of radius :math:`r`); the direction is the unit
    vector of the velocity. Because the estimate is centred in the window it lags the newest sample by
    ``(filter_window_length - 1) / 2`` samples (70 ms at 100 Hz with the default window of 15). The step :math:`dt` of
    a call is the difference to the previous ``timestamp`` if given, else ``1 / sampling_rate``, else one second per
    sample.

    ``output_type`` may be a list; the result then holds one output per type, in that order, all computed in the same
    pass and each identical to a ``Kinematics`` built for that type alone. The curvature-based smoothness index of
    a movement is a separate feature, ``CurvatureDispersion``, fed with the velocity and acceleration vectors of this
    one (``output_dims="components"``).

    Parameters
    ----------
    dims : int, optional
        Number of components of a point: 1, 2 or 3. ``None`` (default) takes it from the first frame; a later frame
        of another size raises. *(structural)*
    input_mode : {"point", "time_series"}, optional
        ``"point"`` (default): one position per call, the feature keeps its own window. ``"time_series"``: a series
        of positions buffered by the caller per call. ``Kinematics.from_point(...)`` and
        ``Kinematics.from_series(...)`` build one or the other. *(structural)*
    output_dims : {"tangential", "components"}, optional
        ``"tangential"`` (default): each output is a scalar, the magnitude of the vector (the speed, for the
        velocity). ``"components"``: a ``(dims,)`` vector with the components x, y, z. A ``"direction"`` output is
        always a vector. *(structural)*
    output_type : str or sequence of str, optional
        What to compute: ``"smoothed"`` (the filtered position), ``"velocity"`` (default), ``"acceleration"``,
        ``"jerk"``, ``"curvature"`` or ``"direction"``, or a list of them. *(structural)*
    filter_window_length : int, optional
        Samples of the Savitzky-Golay window; odd, greater than 3 and than ``filter_polyorder``. Defaults to ``15``.
        *(structural)*
    filter_polyorder : int, optional
        Order of the fitted polynomial. Defaults to ``3``. *(structural)*
    movement_threshold : float, optional
        Speed below which the point counts as still and the curvature is reported as 0, in m/s (scaled by
        ``units``). Defaults to ``0.005``. *(live)*
    sampling_rate : float, optional
        Sampling rate in Hz, used when no timestamp is given. Defaults to ``None`` (one second per sample, and the
        ``reason`` says so). *(live)*
    units : {"m", "mm"}, optional
        Unit of the position data. It scales ``movement_threshold`` and names the output units (``m/s``,
        ``mm/s``, ...); the data and the outputs are never scaled. Defaults to ``"m"``. *(live)*

    Notes
    -----
    **Inputs.** In ``"point"`` mode ``process(point, *, timestamp=None)`` takes one ``(D,)`` position per call and
    ``run(points, *, timestamps=None)`` a ``(T, D)`` recording. In ``"time_series"`` mode ``process(series)`` takes a
    ``(D, N)`` matrix, newest sample last, with ``N >= filter_window_length`` and the same ``N`` at every call; it
    describes the newest sample. ``timestamp`` is in seconds.

    **Outputs.** One output per requested type, named after it: ``smoothed`` (unit of the data), ``velocity`` (unit/s),
    ``acceleration`` (unit/s^2), ``jerk`` (unit/s^3), ``curvature`` (1/unit; 0 below ``movement_threshold``),
    ``direction`` (dimensionless unit vector). A scalar for ``output_dims="tangential"``, a ``(dims,)`` vector for
    ``"components"`` (``direction`` always a vector).

    **Statuses.** ``OK`` from the first sample on (the window is filled from the first call); ``INVALID_INPUT`` when
    the input or a result is not finite, or the timestamp does not increase. The first estimates, before the window
    holds ``filter_window_length`` real samples, are those of a partly filled window.

    Corrected in the core: acceleration and jerk are the true second and third derivatives (they were the polynomial
    coefficients, half and a sixth of them); the 2D tangential curvature was too large by a factor
    :math:`\sqrt{2}`; the component curvature used a wrong normalisation. The estimate is the fit to the newest
    ``filter_window_length`` samples read at their centre; EyesWeb leaves the newest sample out of the fit, so its
    estimate lags one sample more.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import Kinematics
    >>> t = np.arange(100) / 100.0
    >>> path = np.c_[0.5 * t, np.zeros_like(t)]  # 0.5 m/s along x, sampled at 100 Hz
    >>> feature = Kinematics(sampling_rate=100.0, output_type="velocity")
    >>> round(float(feature.run(path).velocity[-1]), 3)
    0.5
    """
    _core_class = _trajectory.Kinematics
    _timed = True
    _unit_params = {"movement_threshold": 1}  # a speed threshold: length per time

    @input_mode_factory("point")
    def from_point(cls) -> "Kinematics":
        """Kinematics of a point streamed one sample per call.

        ``process(point)`` takes a ``(D,)`` position (or signal value), ``run`` a ``(T, D)`` recording. Stateful: the
        feature keeps its sliding Savitzky-Golay window. Takes the parameters of ``Kinematics`` except ``input_mode``.
        """

    @input_mode_factory("time_series")
    def from_series(cls) -> "Kinematics":
        """Kinematics of a series buffered by the caller.

        ``process(series)`` takes a ``(D, N)`` matrix (``N`` at least ``filter_window_length``, the same ``N`` at every
        call, newest sample last) and describes its newest sample. Takes the parameters of ``Kinematics`` except
        ``input_mode``.
        """

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
