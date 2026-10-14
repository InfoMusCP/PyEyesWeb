"""Reference copy of the removed Python `VelocityKineticEnergy` (weighted energy of given velocities), kept for parity tests of the
C++ KineticEnergy velocity mode."""

from typing import Union, List, Optional
import numpy as np

from legacy_base import StaticFeature
from pyeyesweb.data_models.results import Output, Schema, Status


class VelocityKineticEnergyReference(StaticFeature):
    r"""Compute weighted kinetic energy from joint velocities.

    Kinetic energy is defined here as:

    $$ E_k = \frac{1}{2} \cdot \sum_{i=1}^{N} w_i \cdot \|v_i\|^2 $$

    where $w_i$ is the weight (mass) of joint $i$ and $v_i$ is its velocity vector.

    !!! note
        Expects `frame_data` to represent velocities (e.g., from [extract_velocity_from_position](../utils/math_utils.md#extract_velocity_from_position)), not raw positions.

    Read more in the [User Guide](../../user_guide/theoretical_framework/low_level/kinetic_energy.md).

    Parameters
    ----------
    weights : float or array_like, optional
        Mass weights for each joint. Can be a single scalar applied to all
        joints or an array of shape `(N_signals,)`. Defaults to `1.0`.
    labels : list of str, optional
        Text labels for each signal; they name the entries of the per-joint outputs. With labels the per-joint
        outputs have a fixed length, without they have a data-dependent one.

    Returns
    -------
    Result
        `total_energy` (scalar), `component_energy` (per axis x, y, z, w; summed over joints),
        `joint_energy` (per joint) and `joint_component_energy` (per joint and axis).
        `Status.INVALID_INPUT` for an empty frame.
    """

    def __init__(
            self,
            weights: Union[float, List[float], np.ndarray] = 1.0,
            labels: List[str] = None
    ):
        super().__init__()
        self.labels = labels
        self.weights = weights

    @property
    def weights(self) -> Union[float, np.ndarray]:
        return self._weights

    @weights.setter
    def weights(self, value: Union[float, List[float], np.ndarray]):
        self._weights = self._parse_weights(value)

    @property
    def labels(self) -> Optional[List[str]]:
        return self._labels

    @labels.setter
    def labels(self, value: Optional[List[str]]):
        self._labels = value
        self._outputs_changed()

    def _schema(self) -> Schema:
        labels = [str(label) for label in self._labels] if self._labels else None
        label_count = len(labels) if labels else None
        comps = ("x", "y", "z", "w")
        return Schema(
            Output("total_energy", doc="Kinetic energy summed over all joints and axes."),
            Output("component_energy", (None,), components=comps, doc="Kinetic energy per axis, summed over joints."),
            Output("joint_energy", (label_count,), labels=labels, doc="Kinetic energy of each joint."),
            Output("joint_component_energy", (label_count, None), labels=labels, components=comps,
                   doc="Kinetic energy of each joint along each axis."),
        )

    def _parse_weights(self, weight_input: Union[float, List[float], np.ndarray]) -> Union[float, np.ndarray]:
        if np.isscalar(weight_input):
            mass_scalar = float(weight_input)
            if mass_scalar < 0:
                raise ValueError("Mass cannot be negative.")
            return mass_scalar

        mass_array = np.asarray(weight_input, dtype=float)
        if np.any(mass_array < 0):
            raise ValueError("Mass values cannot be negative.")

        return mass_array[:, np.newaxis]

    def compute(self, frame_data: np.ndarray):
        r"""Compute kinetic energy for a single frame of velocities.

        Parameters
        ----------
        frame_data : numpy.ndarray of shape (N_signals, N_dims)
            Snapshot of joint velocities.

        Returns
        -------
        Result
            Outputs `total_energy`, `component_energy`, `joint_energy`, `joint_component_energy`.
        """
        velocities = np.asarray(frame_data, dtype=float)

        if velocities.ndim == 1:
            velocities = velocities.reshape(1, -1)

        num_joints = velocities.shape[0]
        if velocities.size == 0:
            return self._no_output(Status.INVALID_INPUT, "empty frame")

        # 1. Validation Fail-Safes
        # Mismatches are programming errors and raise.
        if self.labels and len(self.labels) != num_joints:
            raise ValueError(f"Number of labels ({len(self.labels)}) must match number of joints ({num_joints}).")
        if isinstance(self.weights, np.ndarray) and self.weights.shape[0] != num_joints:
            raise ValueError(
                f"Weight array length ({self.weights.shape[0]}) must match number of joints ({num_joints}).")

        # 2. Optimized Computation
        kinetic_energy_components = 0.5 * self.weights * (velocities ** 2)
        kinetic_energy_per_joint = kinetic_energy_components.sum(axis=1)

        return self._result(
            total_energy=float(kinetic_energy_per_joint.sum()),
            component_energy=kinetic_energy_components.sum(axis=0),
            joint_energy=kinetic_energy_per_joint,
            joint_component_energy=kinetic_energy_components,
        )
