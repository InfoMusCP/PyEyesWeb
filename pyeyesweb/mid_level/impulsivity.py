"""Impulsivity analysis for body movement patterns."""

from dataclasses import dataclass
import numpy as np

from pyeyesweb.data_models.base import DynamicFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.mid_level.suddenness import Suddenness


@dataclass(slots=True)
class ImpulsivityResult(FeatureResult):
    """Output contract for Impulsivity evaluation.
    
    Attributes
    ----------
    impulsivity_index : float
        The computed impulsivity index.
    direction_change_val : float
        The computed direction change value.
    is_sudden : bool
        Whether the movement is sudden.
    """
    impulsivity_index: float = 0.0
    direction_change_val: float = 0.0
    is_sudden: bool = False


class Impulsivity(DynamicFeature):
    """Impulsivity evaluation based on the product of Direction Change and Suddenness.

    Read more in the [User Guide](../../user_guide/theoretical_framework/mid_level/impulsivity.md).

    Parameters
    ----------
    direction_change_epsilon : float, optional
        Epsilon threshold for Direction Change. Defaults to `0.5`.
    suddenness_algo : str, optional
        Algorithm to use for Suddenness. Defaults to `"new"`.
    """

    def __init__(self, direction_change_epsilon: float = 0.5, suddenness_algo: str = "new"):
        super().__init__()
        # Initialize sub-features
        self._direction_change = DirectionChange(metrics=["cosine"])
        self._suddenness = Suddenness()
        
        self.direction_change_epsilon = direction_change_epsilon
        self.suddenness_algo = suddenness_algo

    @property
    def direction_change_epsilon(self) -> float:
        return self._direction_change.epsilon

    @direction_change_epsilon.setter
    def direction_change_epsilon(self, value: float):
        self._direction_change.epsilon = value

    @property
    def suddenness_algo(self) -> str:
        return self._suddenness.algo

    @suddenness_algo.setter
    def suddenness_algo(self, value: str):
        self._suddenness.algo = value

    def compute(self, window_data: np.ndarray, **kwargs) -> ImpulsivityResult:
        """The Pure Math API for computing impulsivity.
        
        Parameters
        ----------
        window_data : numpy.ndarray
            A 3D tensor representing motion data over time of shape `(Time, N_signals, N_dims)`.
        **kwargs : dict
            Additional arguments.
            
        Returns
        -------
        ImpulsivityResult
            The computed impulsivity metrics.
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