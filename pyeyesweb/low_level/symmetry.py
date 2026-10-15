"""Symmetry of a skeleton frame: ``Symmetry`` (a left/right ratio index or a mirror-reflection score) and
``TriangleSymmetry``.
"""

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
    r"""Left/right symmetry of a skeleton frame, as a ratio index or a mirror-reflection score.

    Measures how symmetric a posture is across the sagittal plane, with the x axis as the lateral axis, for couples of
    joints that mirror each other (left and right hand, left and right foot, ...). One class offers two formulas, chosen
    at construction by ``method``.

    **method="ratio"** (default; the EyesWeb SymmetryIndex-3D). Coordinates are taken relative to the reference joint,
    optionally normalised, and compared couple by couple and axis by axis. With :math:`L` and :math:`R` the left and
    right joints of a couple relative to the reference, on each axis :math:`k \in \{x, y, z\}`

    .. math::

        s_k = \begin{cases}
            \min(\lvert L_k \rvert, \lvert R_k \rvert) / \max(\lvert L_k \rvert, \lvert R_k \rvert)
                & \text{if the sign condition holds} \\
            0 & \text{otherwise}
        \end{cases}

    where the sign condition requires the two joints to lie on opposite sides of the reference along x and on the same
    side along y and z. The values :math:`s_k` are aggregated (``aggregation``) over all couples and axes into one index
    (``output_dims="global"``), or over the couples for each axis into a vector of three values
    (``output_dims="components"``). With ``normalize_skeleton`` each joint is first divided by its distance to the
    reference, so that only its direction counts. With ``index_type="symmetry_asymmetry"`` the sign condition is dropped
    and :math:`s_k` is the ratio of magnitudes alone.

    **method="reflection"** (mirror symmetry). The coordinates are taken relative to a centre :math:`C`, the right joint
    of each pair is reflected across the first axis, :math:`R'' = (-R_x, R_y, R_z)`, and the score of the pair is based
    on its distance to the left joint:

    .. math::

        s = \max\!\left(0,\; 1 - \frac{\lVert L - R'' \rVert}{\lVert L \rVert + \lVert R \rVert}\right),

    with :math:`L, R` relative to :math:`C`; it is 1 for a perfect mirror image and decreases towards 0.

    Input: one frame per call, an ``(N, 3)`` array in the order of ``labels`` (for ``"reflection"``, ``(N, D)``) or, for
    ``"ratio"``, a dictionary ``label -> (x, y, z)`` that carries its own labels; ``process(frame, *, timestamp=None)``.
    The feature keeps no state. Use ``"ratio"`` for the EyesWeb index of a labelled skeleton with named couples and one
    summary value, and ``"reflection"`` for one score per pair of a mirror about a body centre. A parameter of the other
    method raises ``TypeError`` or ``ValueError``.

    Parameters
    ----------
    labels : sequence of str, optional
        Joint names, in the order of the rows of an array frame. Given by ``skeleton`` when that is passed; needed for
        array input.
    skeleton : str or Skeleton, optional
        A device preset or a user-defined ``Skeleton`` that provides ``labels``, ``pairs`` and, when it defines one, the
        reference joint, unless they are passed explicitly.
    method : {"ratio", "reflection"}, optional
        The formula; fixed at construction. Defaults to ``"ratio"``.
    pairs : sequence of (str, str)
        The ``(left, right)`` joint names of each symmetric couple. Required (from ``skeleton`` or explicit). *(live)*
    reference_point : str, optional
        ``"ratio"``: the joint taken as the origin of the coordinates when ``reference_type="label"``, ``"neck"`` by
        default; a ``skeleton`` that defines no reference joint requires it (``ValueError`` at construction otherwise).
        ``"reflection"``: the joint about which the right joint is reflected; ``None``, the default for this method, is
        the barycenter (mean position) of the frame. *(live)*
    index_type : {"symmetry", "symmetry_asymmetry"}, optional
        ``"ratio"`` only. ``"symmetry"`` applies the sign condition; ``"symmetry_asymmetry"`` uses the magnitude ratio
        alone. Defaults to ``"symmetry"``. *(live)*
    output_dims : {"global", "components"}, optional
        ``"ratio"`` only. ``"global"``: one value; ``"components"``: one value per axis. Defaults to ``"global"``.
        *(live)*
    aggregation : {"mean", "min", "max", "weighted_mean"}, optional
        ``"ratio"`` only. How the values :math:`s_k` are combined; the weight of ``"weighted_mean"`` is the larger of
        the two magnitudes of a value. Defaults to ``"mean"``. *(live)*
    normalize_skeleton : bool, optional
        ``"ratio"`` only. Divide each joint of a couple by its distance to the reference. Defaults to ``True``. *(live)*
    reference_type : {"label", "barycenter", "point"}, optional
        ``"ratio"`` only. ``"label"`` translates the frame so that ``reference_point`` is the origin; with
        ``"barycenter"`` or ``"point"`` no translation is applied and the coordinates are taken as they are, so they
        must already be relative to the centre of symmetry. Defaults to ``"label"``. *(live)*

    Notes
    -----
    **Outputs.** ``"ratio"``: ``symmetry``, in [0, 1] (1 is symmetric), a scalar for ``"global"`` and a ``(3,)`` vector
    (x, y, z) for ``"components"``. ``"reflection"``: ``pair_symmetry``, ``(number of pairs,)`` in [0, 1] (1 is a
    perfect mirror image), labelled ``<left>_<right>``.

    **Statuses.** ``INVALID_INPUT`` for NaN or infinite coordinates; for ``"ratio"`` also for a dictionary frame that
    lacks a joint of a couple (``"missing joints: ..."``), when no complete couple is present, and when the index is not
    finite (both joints of a couple have a zero coordinate on an axis, a 0/0 ratio); for ``"reflection"`` when the frame
    has too few joints for the pairs.

    Corrected in the core: with ``method="ratio"`` the normalisation distance of a joint is measured from the reference
    joint (the origin of the translated frame), not from its coordinates before the translation.

    References
    ----------
    :cite:`glowinski2011minimal`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import Symmetry
    >>> labels, pairs = ["neck", "left_hand", "right_hand"], [("left_hand", "right_hand")]
    >>> frame = np.array([[0.0, 0.0, 0.0], [-0.5, -0.3, 0.1], [0.8, -0.1, 0.2]])
    >>> ratio = Symmetry(labels, pairs=pairs, reference_point="neck")
    >>> print(f"{ratio.process(frame).symmetry:.2f}")
    0.61
    >>> mirror = Symmetry(labels, pairs=pairs, method="reflection", reference_point="neck")
    >>> print(np.round(mirror.process(frame).pair_symmetry, 2))
    [0.74]
    """
    _SWITCH = ("method", "ratio")
    _variants = {}

    @property
    def method(self) -> Literal["ratio", "reflection"]:
        return self._variant


class _ReflectionSymmetry(Symmetry, variant="reflection"):
    """The ``method="reflection"`` formula of ``Symmetry``; see that class for the parameters and the outputs.
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
    """The ``method="ratio"`` formula of ``Symmetry``; see that class for the parameters and the outputs.
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
    """Symmetry of a head-and-shoulders triangle about its apex, from 0 to 1.

    Measures the lateral lean of an upper body as the symmetry of the triangle formed by the head (apex, ``upper``) and
    the two shoulders (``left`` and ``right``) about the vertical line through the apex. The coordinates are taken
    relative to the apex, the base is split at that line, and the two halves of the triangle, mirrored on top of each
    other, are compared: the index is 1 when they coincide and decreases as their areas differ, down to 0. It is a
    posture measure, the tilt of the apex over the base, not a test of whether the triangle is isosceles. When both base
    vertices lie on the same side of the apex the index is 0.

    Three inputs, the vertices of the triangle as ``(x, y)`` samples with y growing downwards (image coordinates):
    ``process(upper, left, right, *, timestamp=None)``; ``run`` takes the three recordings in the same order. The apex
    is the first argument and is anatomical (head over the shoulders), not detected. The feature has no parameters and
    keeps no state.

    Notes
    -----
    **Outputs.** ``symmetry``: dimensionless, in [0, 1], 1 for a symmetric triangle and 0 for total asymmetry. It is one
    minus the asymmetry that the original block outputs.

    **Statuses.** ``INVALID_INPUT`` for an empty vertex, for NaN or infinite coordinates and for collinear vertices.

    Examples
    --------
    >>> from pyeyesweb.low_level import TriangleSymmetry
    >>> feature = TriangleSymmetry()
    >>> print(f"{feature.process((0, 0), (-1, 1), (1, 1)).symmetry:.2f}")
    1.00
    >>> print(f"{feature.process((0, 0), (-1, 1), (3, 1)).symmetry:.2f}")
    0.33
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
