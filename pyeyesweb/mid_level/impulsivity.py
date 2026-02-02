import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
from ..low_level.direction_change import DirectionChange
from .suddenness import Suddenness

class Impulsivity:
    """
    Impulsivity evaluation based on the product of Direction Change and Suddenness.

    This class computes an impulsivity index for a given trajectory segment
    by combining the suddenness of the movement with the change in direction.
    
    Impulsivity = Direction Change * Suddenness

    Best results with marker based technology at 100fps have been obtained using 
    a suddenness widow length of 80 frames and epsilon direction change 0.5.

    Parameters
    ----------
    direction_change_epsilon : float, optional
        Tolerance factor for DirectionChange (default: 0.5).

    Examples
    --------
    >>> import numpy as np
    >>> imp = Impulsivity()
    >>> points = np.random.rand(20, 3)
    >>> from pyeyesweb.data_models.sliding_window import SlidingWindow
    >>> window = SlidingWindow(points)
    >>> result = imp(window)

    
    References
    ----------
    1. Radoslaw Niewiadomski, Maurizio Mancini, Gualtiero Volpe, and Antonio Camurri. 2015. 
       Automated Detection of Impulsive Movements in HCI. In Proceedings of the 11th Biannual Conference of the Italian SIGCHI Chapter (CHItaly '15). 
       Association for Computing Machinery, New York, NY, USA, 166–169. https://doi.org/10.1145/2808435.2808466
    
    """

    def __init__(self, direction_change_epsilon: float = 0.5):
        self.direction_change = DirectionChange(epsilon=direction_change_epsilon)
        self.suddenness = Suddenness()

    def __call__(self, positions: SlidingWindow) -> float:
        """
        Compute the impulsivity value for the given trajectory segment.

        Parameters
        ----------
        positions : SlidingWindow
            Input array of shape (N, 3) or (N, 2) representing coordinates
            (x, y, z) or (x, y) over time.

        Returns
        -------
        float
            Calculated impulsivity index. Returns 0.0 if segments are too short.
        """
        # Direction Change returns a dict with "value" key
        dc_result = self.direction_change(positions)

        # Suddenness returns a dict with "value" key
        suddenness_result = self.suddenness(positions)

        return {"value": dc_result.get("value", 0.0) * suddenness_result.get("value", 0.0)}
