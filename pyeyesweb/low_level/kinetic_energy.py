from dataclasses import dataclass
from typing import Union, List, Dict, Any, Optional
import numpy as np

from pyeyesweb.data_models.base import StaticFeature
from pyeyesweb.data_models.results import FeatureResult


@dataclass(slots=True)
class KineticEnergyResult(FeatureResult):
    """Output contract for Kinetic Energy evaluation."""
    total_energy: float = 0.0
    component_energy: Optional[List[float]] = None
    joints: Optional[Dict[str, Any]] = None

    def to_flat_dict(self, prefix: str = "") -> Dict[str, float]:
        """Overrides base method to dynamically unroll lists and dicts into scalars."""

        # FIX: Explicitly call the parent class method instead of using super()
        # This prevents the Python 3.10 slots=True bug.
        flat = FeatureResult.to_flat_dict(self, prefix)

        # Helper to format keys cleanly
        def make_key(base: str, sub: str) -> str:
            return f"{prefix}_{base}_{sub}" if prefix else f"{base}_{sub}"

        # 2. Unroll the component energies (e.g., -> energy_x, energy_y)
        comps = flat.pop(f"{prefix}_component_energy" if prefix else "component_energy", None)
        if comps is not None:
            axes = ['x', 'y', 'z', 'w']
            for i, val in enumerate(comps):
                axis = axes[i] if i < len(axes) else str(i)
                flat[make_key("energy", axis)] = float(val)

        # 3. Unroll the joint dictionary (e.g., -> joint_0_total, joint_0_x)
        joints_dict = flat.pop(f"{prefix}_joints" if prefix else "joints", None)
        if joints_dict is not None:
            for j_key, j_data in joints_dict.items():
                j_prefix = f"joint_{j_key}"
                flat[make_key(j_prefix, "total")] = float(j_data["total"])

                for i, val in enumerate(j_data["components"]):
                    axis = axes[i] if i < len(axes) else str(i)
                    flat[make_key(j_prefix, axis)] = float(val)

        return flat


class KineticEnergy(StaticFeature):
    """Computes kinetic energy from velocity vectors.

    Expects frame_data to represent velocities, not raw positions.
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

    def _parse_weights(self, weight_input: Union[float, List[float], np.ndarray]) -> Union[float, np.ndarray]:
        """Validates mass inputs and formats them for optimal broadcasting."""
        if np.isscalar(weight_input):
            mass_scalar = float(weight_input)
            if mass_scalar < 0:
                raise ValueError("Mass cannot be negative.")
            return mass_scalar

        mass_array = np.asarray(weight_input, dtype=float)
        if np.any(mass_array < 0):
            raise ValueError("Mass values cannot be negative.")

        return mass_array[:, np.newaxis]

    def compute(self, frame_data: np.ndarray) -> KineticEnergyResult:
        velocities = np.asarray(frame_data, dtype=float)

        if velocities.ndim == 1:
            velocities = velocities.reshape(1, -1)

        num_joints = velocities.shape[0]

        # 1. Validation Fail-Safes
        # Note: If these trigger, the base StaticFeature.__call__ catches the ValueError
        # and safely returns a FeatureResult(is_valid=False).
        if self.labels and len(self.labels) != num_joints:
            raise ValueError(f"Number of labels ({len(self.labels)}) must match number of joints ({num_joints}).")
        if isinstance(self.weights, np.ndarray) and self.weights.shape[0] != num_joints:
            raise ValueError(
                f"Weight array length ({self.weights.shape[0]}) must match number of joints ({num_joints}).")

        # 2. Optimized Computation
        kinetic_energy_components = 0.5 * self.weights * (velocities ** 2)
        kinetic_energy_per_joint = kinetic_energy_components.sum(axis=1)

        # 3. Aggregation and Dictionary Building
        joint_energy_dict = {}
        for i in range(num_joints):
            key = self.labels[i] if self.labels else str(i)
            joint_energy_dict[key] = {
                "total": float(kinetic_energy_per_joint[i]),
                "components": kinetic_energy_components[i].tolist()
            }

        return KineticEnergyResult(
            total_energy=float(kinetic_energy_per_joint.sum()),
            component_energy=kinetic_energy_components.sum(axis=0).tolist(),
            joints=joint_energy_dict
        )