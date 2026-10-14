"""Symmetry of a skeleton frame: `Symmetry` (two methods: left/right ratio or mirror reflection) and the triangle index."""

from typing import Any, List, Literal, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, CoreFeature, FrameFeature, VariantFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.base.inputs import labelled_set, non_finite, points_input
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.skeletons import with_skeleton
from pyeyesweb.utils.validators import validate_pairs


@describe(Layer.LOW_LEVEL, eyesweb="SymmetryIndex-3D (SymmetrySkeleton3D)")
class Symmetry(VariantFeature, FrameFeature):
    """Left/right symmetry of a skeleton frame; `method` chooses the formula (`"ratio"` or `"reflection"`).

    `"ratio"` (default, the EyesWeb SymmetryIndex-3D block): per axis, the ratio of the left and right magnitudes of
    the couples, valid when a sign condition holds, aggregated (`algorithm`: Mean, Min, Max, WeightedMean) into one
    index, globally or per axis. Parameters: `labels` (joint names of array input; a dict carries its own),
    and the block parameters (`couples` by label, `reference`, normalisation, `algorithm`, `index_type`,
    `output_type`, `reference_type`, ...).
    Input: one frame, an `(N, 3)` array in the order of `labels` or a dict `label -> (x, y, z)`.
    Output `symmetry` in [0, 1] (1 = symmetric): a scalar when `output_type` is GLOBAL (default), a `(3,)` vector
    (x, y, z) when it is COMPONENTS. `INVALID_INPUT` ("no couple of the skeleton is present in the frame", the output
    keeps the 0 of the block) when the frame holds no complete couple.

    `"reflection"` (mirror symmetry): the right joint of each pair is reflected across the first axis about a centre
    and its 3-D distance to the left joint gives a score per pair. Parameters: `joint_pairs` (required list of
    `(left_idx, right_idx)` row indices) and `center_of_symmetry` (joint index; default the barycentre).
    Input: one `(N, D)` frame of joint positions. Output `pair_symmetry`, one score per pair in [0, 1]
    (1 = perfectly symmetric), labelled `<left>_<right>`; `INVALID_INPUT` if the frame has too few joints.

    Use `"ratio"` for the EyesWeb index of a labelled skeleton with named couples and one summary value; use
    `"reflection"` for per-pair scores of a mirror about a body centre. A parameter of the other method raises
    `TypeError` or `ValueError`. Stateless; `process(frame, timestamp=None)`; `timestamp` in seconds (`NaN` when not given).
    """
    _SWITCH = ("method", "ratio")
    _variants = {}

    @property
    def method(self) -> Literal["ratio", "reflection"]:
        return self._variant


class _ReflectionSymmetry(Symmetry, variant="reflection"):
    """Computes the instantaneous spatial symmetry error for a skeletal frame (maths in the compiled core).

    !!! info
        The symmetry error is calculated as the Euclidean distance between a joint and the reflection of its corresponding paired joint.

        Input: one frame per call, an `(N, D)` array of joint positions (the pairs are indices into its rows);
    stateless. `process(frame, timestamp=None)`; `timestamp` is the timestamp in seconds (`NaN` when not given).

    Parameters
    ----------
    joint_pairs : list of tuple
        A list of `(left_idx, right_idx)` representing the symmetric pair indices.
    center_of_symmetry : int, optional
        The index of the joint to scale as the center of symmetry. If not provided, it defaults to `-1` (barycenter).

    Returns
    -------
    Result
        Output `pair_symmetry`, a vector with one entry per configured pair, labelled `<left>_<right>`
        (flat names `pair_symmetry_<left>_<right>`). `Status.INVALID_INPUT` if the frame has too few joints.
    """

    INPUTS = Inputs(points_input("skeleton", None, "joint positions", dims=None))

    _core_class = core.motion.GeometricSymmetry

    def __init__(self, *, joint_pairs: List[Tuple[int, int]], center_of_symmetry: Optional[int] = None,
                 method: str = "reflection"):
        super().__init__(joint_pairs=validate_pairs(joint_pairs),
                         center_of_symmetry=center_of_symmetry if center_of_symmetry is not None else -1)

    def _schema(self) -> Schema:
        labels = [f"{left}_{right}" for left, right in self._block.pairs]
        return Schema(Output("pair_symmetry", (len(labels),), labels=labels,
                             doc="Symmetry score per pair in [0, 1]; 1 is perfectly symmetric."))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        frame = np.asarray(frame, dtype=float)
        if reason := non_finite(frame, allow_empty=True):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        try:
            scores = self._block.process(frame)
        except ValueError as exc:
            return self.no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(scores, timestamp)

    def _to_result(self, raw: np.ndarray, timestamp: Optional[float]) -> Result:
        return self.result(pair_symmetry=raw.tolist(), timestamp=timestamp)


class _RatioSymmetry(LabelGuard, Symmetry, variant="ratio"):
    """EyesWeb SymmetryIndex-3D (SymmetrySkeleton3D).

    Input: one skeleton frame per call, an `(N, 3)` array in the order of `labels`, or a dict
    `label -> (x, y, z)`; stateless. `process(skeleton, timestamp=None)`; `timestamp` in seconds (`NaN` when not given).
    `labels` are the joint names of the arrays; they are needed for array input (a dict carries its own).

    Output `symmetry` in [0, 1] (1 = symmetric): a scalar when `output_type` is GLOBAL (default), a `(3,)` vector
    with components x, y, z when it is COMPONENTS. `INVALID_INPUT` ("no couple of the skeleton is present in the frame",
    the output keeps the 0 of the block) when the frame holds no complete couple.
    """
    _core_class = core.motion.SymmetryIndex3D

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, *,
                 method: str = "ratio", **params: Any):
        labels, params = with_skeleton(skeleton, labels, params, lambda resolved: {
            "couples": list(resolved.pairs),
            **({} if resolved.reference is None else {"reference_point": resolved.reference})})
        super().__init__(**params)
        self._set_labels(labels)

    def _label_names(self):
        return {name for couple in self._param("couples", None) or () for name in couple}

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions", accepts=(dict,)))

    def _schema(self) -> Schema:
        output_type = core.motion.SymmetryIndex3DOutputType
        if self._param("output_type", output_type.GLOBAL) == output_type.GLOBAL:
            return Schema(Output("symmetry", doc="1 = symmetric"))
        return Schema(Output("symmetry", components=XYZ, doc="per-axis indices, 1 = symmetric"))

    def _process(self, skeleton: Any, timestamp: Optional[float]) -> Result:
        if (problem := self._label_problem(skeleton, timestamp)) is not None:
            return problem
        points = labelled_set(skeleton, self._labels, "Symmetry")
        if reason := non_finite(list(points.values())):
            return self.no_output(Status.INVALID_INPUT, reason, timestamp)
        present = any(left in points and right in points for left, right in self._param("couples", None) or ())
        return self._to_result(self._block.process(points), timestamp,
                               "" if present else "no couple of the skeleton is present in the frame")

    def _to_result(self, raw: Any, timestamp: Optional[float], reason: str = "") -> Result:
        return self.result(status=Status.INVALID_INPUT if reason else Status.OK, reason=reason, timestamp=timestamp,
                           symmetry=np.asarray(raw, dtype=float) if isinstance(raw, tuple) else raw)

for _variant in (_RatioSymmetry, _ReflectionSymmetry):
    _variant.__name__ = Symmetry.__name__


_COLLINEAR = 1e-9  # relative size of the triangle area below which the vertices count as collinear


@describe(Layer.LOW_LEVEL, eyesweb="trianglesymmetryindex (SymmetryTriangle3D)")
class TriangleSymmetry(CoreFeature):
    """EyesWeb SymmetryTriangle3D, as a symmetry index.

    Three inputs, the vertices of the triangle as `(x, y)` samples (y grows downwards): `process(upper, left, right,
    timestamp=None)` and `run(upper, left, right, timestamps=None)`; stateless. The apex (`upper`) is the FIRST argument and is
    anatomical (head over the shoulders), not detected: the coordinates are taken relative to the apex x, so it is a
    posture measure (tilt of the apex over the base), not the isosceles-ness of the triangle. `timestamp` in seconds
    (`NaN` when not given).

    Output `symmetry`: 1 for a symmetric triangle down to 0 for total asymmetry (the EyesWeb block outputs the
    asymmetry; this is `1 - asymmetry`). Always `OK`, `INVALID_INPUT` for collinear vertices.
    """
    _core_class = core.motion.TriangleSymmetryIndex

    def _inputs(self) -> Inputs:
        return Inputs(*(Input(name, InputKind.SAMPLE, (2,), doc=f"{name} vertex (x, y)")
                        for name in ("upper", "left", "right")))

    def _schema(self) -> Schema:
        return Schema(Output("symmetry", doc="1 = symmetric, 0 = totally asymmetric"))

    def process(self, upper: Any, left: Any, right: Any, *, timestamp: Optional[float] = None) -> Result:
        vertices = [np.asarray(vertex, dtype=float) for vertex in (upper, left, right)]
        if any(vertex.size != 2 for vertex in vertices) or not np.isfinite(vertices).all():
            return self.no_output(Status.INVALID_INPUT, "empty vertex or NaN / infinite coordinates", timestamp)
        return self._to_result((vertices, self._block.process(*(tuple(vertex.tolist()) for vertex in vertices))), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        vertices, symmetry = raw
        to_left, to_right = vertices[1] - vertices[0], vertices[2] - vertices[0]
        collinear = abs(to_left[0] * to_right[1] - to_left[1] * to_right[0]) <= (
            _COLLINEAR * np.linalg.norm(to_left) * np.linalg.norm(to_right))
        return self.result(status=Status.INVALID_INPUT if collinear else Status.OK,
                           reason="the vertices are collinear" if collinear else "",
                           symmetry=symmetry, timestamp=timestamp)


__all__ = ["Symmetry", "TriangleSymmetry"]
