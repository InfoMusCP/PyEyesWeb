"""Symmetry of a skeleton frame: `Symmetry` (two methods: left/right ratio or mirror reflection) and the triangle index."""

from typing import Any, Literal, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import XYZ, CoreFeature, FrameFeature, VariantFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.data_models.skeleton import Skeleton
from pyeyesweb.base.inputs import labelled_set, points_input
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.skeletons import get_skeleton, with_skeleton


def _from_skeleton(skeleton: Skeleton) -> dict:
    """The pairs and the reference joint a skeleton gives to either method."""
    return {"pairs": list(skeleton.pairs), **({} if skeleton.reference is None else {"reference_point": skeleton.reference})}


@describe(Layer.LOW_LEVEL, eyesweb="SymmetryIndex-3D (SymmetrySkeleton3D)")
class Symmetry(VariantFeature, FrameFeature):
    """Left/right symmetry of a skeleton frame; `method` chooses the formula (`"ratio"` or `"reflection"`).

    `"ratio"` (default, the EyesWeb SymmetryIndex-3D block): per axis, the ratio of the left and right magnitudes of
    the couples, valid when a sign condition holds, aggregated (`aggregation`: Mean, Min, Max, WeightedMean) into one
    index, globally or per axis. With `skeleton=` and the default `reference_type="label"` the skeleton must define its
    reference joint or `reference_point` must be given (`ValueError` otherwise). Parameters: `labels` (joint names of array input; a dict carries its own),
    `pairs` (the left and right joint of each couple, by name) and `reference_point`, both taken from `skeleton` when
    given, and the block parameters (normalisation, `aggregation`, `index_type`, `output_dims`, `reference_type`, ...).
    Input: one frame, an `(N, 3)` array in the order of `labels` or a dict `label -> (x, y, z)`.
    Output `symmetry` in [0, 1] (1 = symmetric): a scalar when `output_dims` is GLOBAL (default), a `(3,)` vector
    (x, y, z) when it is COMPONENTS. `INVALID_INPUT` ("missing joints: ...") for a dict frame that
    lacks a joint of a couple.

    `"reflection"` (mirror symmetry): the right joint of each pair is reflected across the first axis about a centre
    and its 3-D distance to the left joint gives a score per pair. Parameters: `labels`, `pairs` and `reference_point`
    (the joint to reflect about; `None`, the default of this method, is the barycentre), as in the other method.
    Input: one `(N, D)` frame of joint positions, in the order of `labels`. Output `pair_symmetry`, one score per pair
    in [0, 1] (1 = perfectly symmetric), labelled `<left>_<right>`.

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

        Input: one frame per call, an `(N, D)` array of joint positions in the order of `labels`;
    stateless. `process(frame, timestamp=None)`; `timestamp` is the timestamp in seconds (`NaN` when not given).

    Parameters
    ----------
    labels : sequence of str, optional
        Joint names, in the order of the rows of the frame (the joints of `skeleton` when that is given).
    skeleton : str or Skeleton, optional
        A device preset or your own `Skeleton`: gives `labels`, `pairs` and `reference_point` unless passed.
    pairs : list of (str, str)
        The `(left, right)` joint names of each symmetric pair.
    reference_point : str, optional
        The joint taken as the centre of symmetry. If not provided, it is the barycenter.

    Returns
    -------
    Result
        Output `pair_symmetry`, a vector with one entry per configured pair, labelled `<left>_<right>`
        (flat names `pair_symmetry_<left>_<right>`). `Status.INVALID_INPUT` if the frame has too few joints.
    """

    _core_class = core.motion.GeometricSymmetry
    _core_names = {"pairs": "joint_pairs", "reference_point": "center_of_symmetry"}  # `_block_params` turns names into rows

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, *,
                 pairs: Optional[Sequence[Tuple[str, str]]] = None, reference_point: Optional[str] = None,
                 method: str = "reflection"):
        given = {name: value for name, value in (("pairs", pairs), ("reference_point", reference_point)) if value is not None}
        labels, params = with_skeleton(skeleton, labels, given, _from_skeleton)
        self._labels = None if labels is None else tuple(labels)  # `_block_params` turns the names into rows
        super().__init__(**params)

    def _block_params(self, params: dict) -> dict:
        """The pairs and the reference joint as the block takes them: rows of the frame."""
        pairs, reference = params.get("pairs"), params.get("reference_point")
        if not pairs or self._labels is None:
            raise ValueError("Symmetry(method='reflection'): needs pairs of joint names and the joint names of the frame; "
                             "pass skeleton= (e.g. 'kinect_v2') or labels= and pairs=")
        row = {label: index for index, label in enumerate(self._labels)}
        names = {name for pair in pairs for name in pair} | ({reference} if reference is not None else set())
        if unknown := sorted(names - set(row)):
            raise ValueError(f"Symmetry: names that are not among the labels: {unknown}")
        return {"joint_pairs": [(row[left], row[right]) for left, right in pairs],
                "center_of_symmetry": -1 if reference is None else row[reference]}

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions", dims=None))

    def _schema(self) -> Schema:
        labels = [f"{self._labels[left]}_{self._labels[right]}" for left, right in self._block.pairs]
        return Schema(Output("pair_symmetry", (len(labels),), labels=labels,
                             doc="Symmetry score per pair in [0, 1]; 1 is perfectly symmetric."))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        try:
            scores = self._block.process(np.asarray(frame, dtype=float))
        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(scores, timestamp)

    def _to_result(self, raw: np.ndarray, timestamp: Optional[float]) -> Result:
        return self._result(pair_symmetry=raw.tolist(), timestamp=timestamp)


class _RatioSymmetry(LabelGuard, Symmetry, variant="ratio"):
    """EyesWeb SymmetryIndex-3D (SymmetrySkeleton3D).

    Input: one skeleton frame per call, an `(N, 3)` array in the order of `labels`, or a dict
    `label -> (x, y, z)`; stateless. `process(skeleton, timestamp=None)`; `timestamp` in seconds (`NaN` when not given).
    `labels` are the joint names of the arrays; they are needed for array input (a dict carries its own).

    Output `symmetry` in [0, 1] (1 = symmetric): a scalar when `output_dims` is GLOBAL (default), a `(3,)` vector
    with components x, y, z when it is COMPONENTS. `INVALID_INPUT` ("missing joints: ...") for a dict frame that lacks a
    joint of a couple.
    """
    _core_class = core.motion.SymmetryIndex3D
    _core_names = {"pairs": "couples", "aggregation": "algorithm", "output_dims": "output_type"}

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, *,
                 method: str = "ratio", **params: Any):
        labels, params = with_skeleton(skeleton, labels, params, _from_skeleton)
        super().__init__(**params)
        reference_type = core.motion.SymmetryIndex3DReferenceType
        if skeleton is not None and "reference_point" not in params and self._param("reference_type", reference_type.LABEL) == reference_type.LABEL:
            # the core translates by the reference only if the label is present: a default that is no joint would pass silently
            raise ValueError(f"Symmetry(method='ratio'): the skeleton {get_skeleton(skeleton).name!r} defines no reference joint; "
                             "pass reference_point= (a joint of the skeleton) or reference_type='barycenter'")
        self._set_labels(labels)

    def _label_names(self):
        return {name for couple in self._param("pairs", None) or () for name in couple}

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions", accepts=(dict,)))

    def _schema(self) -> Schema:
        output_dims = core.motion.SymmetryIndex3DOutputType
        if self._param("output_dims", output_dims.GLOBAL) == output_dims.GLOBAL:
            return Schema(Output("symmetry", doc="1 = symmetric"))
        return Schema(Output("symmetry", components=XYZ, doc="per-axis indices, 1 = symmetric"))

    def _process(self, skeleton: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(labelled_set(skeleton, self._labels, "Symmetry")), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        return self._finite_result(timestamp=timestamp, symmetry=np.asarray(raw, dtype=float) if isinstance(raw, tuple) else raw)

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
            return self._no_output(Status.INVALID_INPUT, "empty vertex or NaN / infinite coordinates", timestamp)
        return self._to_result((vertices, self._block.process(*(tuple(vertex.tolist()) for vertex in vertices))), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        vertices, symmetry = raw
        to_left, to_right = vertices[1] - vertices[0], vertices[2] - vertices[0]
        collinear = abs(to_left[0] * to_right[1] - to_left[1] * to_right[0]) <= (
            _COLLINEAR * np.linalg.norm(to_left) * np.linalg.norm(to_right))
        return self._result(status=Status.INVALID_INPUT if collinear else Status.OK,
                           reason="the vertices are collinear" if collinear else "",
                           symmetry=symmetry, timestamp=timestamp)


__all__ = ["Symmetry", "TriangleSymmetry"]
