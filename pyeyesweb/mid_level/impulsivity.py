"""Impulsivity analysis for body movement patterns."""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.mid_level.suddenness import Suddenness


@dataclass(slots=True)
class ImpulsivityResult(FeatureResult):
    """Output contract for Impulsivity evaluation."""
    impulsivity_index: float = 0.0
    direction_change_val: float = 0.0
    is_sudden: bool = False


class Impulsivity(DynamicFeature):
    """
    Impulsivity evaluation based on the product of Direction Change and Suddenness.
    """

    def __init__(self, direction_change_epsilon: float = 0.5, suddenness_algo: str = "new"):
        super().__init__()
        # Initialize sub-features
        self._direction_change = DirectionChange(metrics=["cosine"], epsilon=direction_change_epsilon)
        self._suddenness = Suddenness(algo=suddenness_algo)

    def compute(self, window_data: np.ndarray, **kwargs) -> ImpulsivityResult:
        """
        The Pure Math API.
        Expects window_data of shape (Time, N_signals, N_dims).
        """
        # 1. Compute sub-features by calling their public compute methods
        dc_result = self._direction_change.compute(window_data)
        sud_result = self._suddenness.compute(window_data)

        # 2. Check validity
        if not dc_result.is_valid or not sud_result.is_valid:
            return ImpulsivityResult(is_valid=False)

        # 3. Extract metrics
        dc_val = getattr(dc_result, 'cosine', 0.0) 
        is_sudden = sud_result.is_sudden

        # Impulsivity = Direction Change * Suddenness
        # Since Suddenness is boolean/binary here, impulsivity is 0 if not sudden.
        impulsivity = dc_val * float(is_sudden)

        return ImpulsivityResult(
            impulsivity_index=float(impulsivity),
            direction_change_val=float(dc_val),
            is_sudden=bool(is_sudden)
        )