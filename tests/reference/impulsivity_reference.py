"""Impulsivity analysis for body movement patterns."""

import numpy as np

from pyeyesweb.catalog import Layer, describe
from legacy_base import DynamicFeature
from pyeyesweb.data_models.results import Output, Schema
from direction_change_reference import DirectionChangeReference as DirectionChange
from suddenness_reference import SuddennessReference as Suddenness


@describe(Layer.MID_LEVEL)
class SuddennessImpulsivityReference(DynamicFeature):
    """Impulsivity evaluation based on the product of Direction Change and Suddenness.

    Read more in the [User Guide](../../user_guide/theoretical_framework/mid_level/impulsivity.md).

    Parameters
    ----------
    direction_change_epsilon : float, optional
        Epsilon threshold for Direction Change. Defaults to `0.5`.
    suddenness_algo : str, optional
        Algorithm to use for Suddenness. Defaults to `"new"`.

    Returns
    -------
    Result
        `impulsivity_index` (float), `direction_change_val` (float), `is_sudden` (bool).
        A non-OK status of the DirectionChange or Suddenness sub-feature is propagated with its reason.
    """

    _OUTPUTS = Schema(
        Output("impulsivity_index", doc="Direction change times suddenness (0 when not sudden)."),
        Output("direction_change_val", doc="Cosine direction change of the window."),
        Output("is_sudden", kind=bool, doc="Whether the movement is sudden."),
    )

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

    def compute(self, window_data: np.ndarray, **kwargs):
        """The Pure Math API for computing impulsivity.
        
        Parameters
        ----------
        window_data : numpy.ndarray
            A 3D tensor representing motion data over time of shape `(Time, N_signals, N_dims)`.
        **kwargs : dict
            Additional arguments.
            
        Returns
        -------
        Result
            Outputs `impulsivity_index`, `direction_change_val`, `is_sudden`.
        """
        # 1. Compute sub-features by calling their public compute methods
        dc_result = self._direction_change.compute(window_data)
        sud_result = self._suddenness.compute(window_data)

        # 2. Check validity
        for name, sub in (("direction change", dc_result), ("suddenness", sud_result)):
            if not sub.ok:
                return self._no_output(sub.status, f"{name}: {sub.reason}")

        # 3. Extract metrics
        dc_val = dc_result.cosine
        is_sudden = sud_result.is_sudden

        # Impulsivity = Direction Change * Suddenness
        # Since Suddenness is boolean/binary here, impulsivity is 0 if not sudden.
        impulsivity = dc_val * float(is_sudden)

        return self._result(
            impulsivity_index=float(impulsivity),
            direction_change_val=float(dc_val),
            is_sudden=bool(is_sudden)
        )


__all__ = ["SuddennessImpulsivityReference"]
