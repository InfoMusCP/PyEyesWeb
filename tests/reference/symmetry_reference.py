from typing import Optional, List, Tuple
import numpy as np

from pyeyesweb.catalog import Layer, describe
from legacy_base import StaticFeature
from pyeyesweb.data_models.results import Output, Schema, Status
from pyeyesweb.utils.validators import validate_pairs


@describe(Layer.LOW_LEVEL)
class GeometricSymmetryReference(StaticFeature):
    """Computes the instantaneous spatial symmetry error for a skeletal frame.

    !!! info
        The symmetry error is calculated as the Euclidean distance between a joint and the reflection of its corresponding paired joint.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/geometric_symmetry.md).

    Parameters
    ----------
    joint_pairs : list of tuple
        A list of `(left_idx, right_idx)` representing the symmetric pair indices.
    center_of_symmetry : int, optional
        The index of the joint to scale as the center of symmetry. If not provided, it defaults to `-1` (barycenter).

    Returns
    -------
    Result
        Output `pair_error`, a vector with one entry per configured pair, labelled `<left>_<right>`
        (flat names `pair_error_<left>_<right>`). `Status.INVALID_INPUT` if the frame has too few joints.
    """

    EPSILON = 1e-10

    def __init__(self, joint_pairs: List[Tuple[int, int]], center_of_symmetry: Optional[int] = None):
        super().__init__()
        self._center_idx = center_of_symmetry if center_of_symmetry is not None else -1
        self._signal_pairs = sorted(set(validate_pairs(joint_pairs)))

        if not self._signal_pairs:
            raise ValueError("At least one signal pair must be provided.")

        self._max_required_idx = max(max(pair) for pair in self._signal_pairs)
        if self._center_idx != -1:
            self._max_required_idx = max(self._max_required_idx, self._center_idx)

    def _schema(self) -> Schema:
        labels = [f"{left}_{right}" for left, right in self._signal_pairs]
        return Schema(Output("pair_error", (len(labels),), labels=labels,
                             doc="Symmetry score per pair in [0, 1]; 1 is perfectly symmetric."))

    def compute(self, frame_data: np.ndarray, **kwargs):
        """Compute the symmetry error frame-by-frame.

        Expects `frame_data` as a 2D tensor: `(N_signals, N_dims)`.

        Parameters
        ----------
        frame_data : numpy.ndarray
            Snapshot of joint positions.
        **kwargs : dict
            Additional arguments.

        Returns
        -------
        Result
            Output `pair_error` (one entry per pair).
        """
        rows, columns = frame_data.shape

        # 1. Validation Fail-Safe
        if rows <= self._max_required_idx:
            return self.no_output(Status.INVALID_INPUT, f"frame has {rows} joints, need index {self._max_required_idx}")

        # 2. Determine the Center of Symmetry (CoS)
        if self._center_idx != -1:
            cos = frame_data[self._center_idx, :]
        else:
            cos = np.mean(frame_data, axis=0)

        # 3. Center the data
        centered_data = frame_data - cos

        # 4. Compute Symmetry Error Frame-by-Frame
        pair_errors = []
        for left_idx, right_idx in self._signal_pairs:
            left_joint = centered_data[left_idx, :]   # Shape: (3,)
            right_joint = centered_data[right_idx, :] # Shape: (3,)

            # Reflect the right joint across the X-axis
            reflected_right = right_joint.copy()
            reflected_right[0] = -reflected_right[0]

            # Calculate instantaneous Euclidean distance
            error = np.linalg.norm(left_joint - reflected_right)

            # Scale-invariant normalization via Triangle Inequality:
            # max possible distance between L and R' is ||L|| + ||R'|| = ||L|| + ||R||
            norm_l = np.linalg.norm(left_joint)
            norm_r = np.linalg.norm(right_joint)
            normalized_error = error / (norm_l + norm_r + self.EPSILON)

            pair_errors.append(float(max(0.0, 1.0 - normalized_error)))

        return self.result(pair_error=pair_errors)


__all__ = ["GeometricSymmetryReference"]
