import numpy as np

from pyeyesweb.data_models.sliding_window import SlidingWindow
#import os
#from pathlib import Path
#os.sys.path.append(Path(__file__).parent.parent.as_posix())
#print(os.sys.path)
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.mid_level.suddenness import Suddenness

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
        self.direction_change = DirectionChange(epsilon=direction_change_epsilon, method="cosine_similarity")
        self.suddenness = Suddenness()

    def __call__(self, positions: SlidingWindow, algo="new") -> dict:
        """
        Compute the impulsivity value for the given trajectory segment.

        Parameters
        ----------
        positions : SlidingWindow
            Input array of shape (N, 3) or (N, 2) representing coordinates
            (x, y, z) or (x, y) over time.

        Returns
        -------
        dict
            Calculated impulsivity index. Returns 0.0 if segments are too short.
        """
        # Direction Change returns a dict with "value" key
        dc_result = self.direction_change(positions)
        dc_result = dc_result.get("value", 0.0)

        # Suddenness returns a dict with "value" key
        suddenness_result = self.suddenness(positions, algo=algo)
        suddenness_result = suddenness_result.get("value", 0.0)
        
        return {"suddenness": suddenness_result, 
                "direction_change": dc_result, 
                "value": dc_result * suddenness_result}
        
        
class ImpulsivityNiewiadomski:
    
    class StblFit:
        _alphaTab = np.array([
            [2, 1.916, 1.808, 1.729, 1.664, 1.563, 1.484, 1.391, 1.279, 1.128, 1.029, 0.896, 0.818, 0.698, 0.593],
            [2, 1.924, 1.813, 1.73, 1.663, 1.56, 1.48, 1.386, 1.273, 1.121, 1.021, 0.892, 0.812, 0.695, 0.59],
            [2, 1.924, 1.829, 1.737, 1.663, 1.553, 1.471, 1.378, 1.266, 1.114, 1.014, 0.887, 0.806, 0.692, 0.588],
            [2, 1.924, 1.829, 1.745, 1.668, 1.548, 1.46, 1.364, 1.25, 1.101, 1.004, 0.883, 0.801, 0.689, 0.586],
            [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.448, 1.337, 1.21, 1.067, 0.974, 0.855, 0.78, 0.676, 0.579],
            [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.438, 1.318, 1.184, 1.027, 0.935, 0.823, 0.756, 0.656, 0.563],
            [2, 1.924, 1.829, 1.745, 1.676, 1.547, 1.438, 1.318, 1.15, 0.973, 0.874, 0.769, 0.691, 0.595, 0.513]
        ])

        _betaTab = np.array([
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [2.16, 1.592, 0.759, 0.482, 0.36, 0.253, 0.203, 0.165, 0.136, 0.109, 0.096, 0.082, 0.074, 0.064, 0.056],
            [1, 3.39, 1.8, 1.048, 0.76, 0.518, 0.41, 0.332, 0.271, 0.216, 0.19, 0.163, 0.147, 0.128, 0.112],
            [1, 1, 1, 1.694, 1.232, 0.823, 0.632, 0.499, 0.404, 0.323, 0.284, 0.243, 0.22, 0.191, 0.167],
            [1, 1, 1, 1, 2.229, 1.575, 1.244, 0.943, 0.689, 0.539, 0.472, 0.412, 0.377, 0.33, 0.285],
            [1, 1, 1, 1, 1, 1, 1.906, 1.56, 1.23, 0.827, 0.693, 0.601, 0.546, 0.478, 0.428],
            [1, 1, 1, 1, 1, 1, 1, 1, 2.195, 1.917, 1.759, 1.596, 1.482, 1.362, 1.274]
        ])

        _a = np.array([2.439, 2.5, 2.6, 2.7, 2.8, 3, 3.2, 3.5, 4, 5, 6, 8, 10, 15, 25])

        _b = np.array([0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0])
        
        def _interp2d(self,tab, nuAlpha,nuBeta):
            rows, cols = tab.shape
            a = self._a
            b = self._b

            row, col = -1, -1

            # Find the column index
            for i in range(1, cols):
                if a[i - 1] <= nuAlpha <= a[i]:
                    col = i - 1
                    break

            # Find the row index
            for i in range(1, rows):
                if b[i - 1] <= nuBeta <= b[i]:
                    row = i - 1
                    break

            if row != -1 and col != -1:
                relcol = abs(a[col] - nuAlpha) / abs(a[col] - a[col + 1])
                mean1 = tab[row, col] + (tab[row, col + 1] - tab[row, col]) * relcol
                mean2 = tab[row + 1, col] + (tab[row + 1, col + 1] - tab[row + 1, col]) * relcol

                relrow = abs(b[row] - nuBeta) / abs(b[row] - b[row + 1])
                result = mean1 + (mean2 - mean1) * relrow

                return result

            return -1


        def fit(self, data, p0=None):

            # Compute percentiles
            percentiles = [95, 75, 50, 25, 5]
            x_percentiles = np.percentile(np.sort(data), percentiles)
            
            # Compute nuAlpha as the ratio of the difference between the 95th and 5th percentiles to the difference between the 75th and 25th percentiles
            nuAlpha = (x_percentiles[0] - x_percentiles[4]) / (x_percentiles[1] - x_percentiles[3])   

            nuBeta = (x_percentiles[0] + x_percentiles[4] - 2 * x_percentiles[2]) / (x_percentiles[0] - x_percentiles[4])
            
            s = 1 if nuBeta >= 0. else -1
            
            alpha = self._interp2d(self._alphaTab, nuAlpha, abs(nuBeta))
            beta = s * self._interp2d(self._betaTab, nuAlpha, abs(nuBeta))
            beta = max(min(nuBeta, 1.0), -1.0)
            
            gamma = (x_percentiles[1] - x_percentiles[3]) / (x_percentiles[1] - x_percentiles[2])
            
            # delta = xpcts[1] - beta * gamma * tan(M_PI * alpha / 2)
            delta = x_percentiles[2] - beta * gamma * np.tan(np.pi * x_percentiles[2] / 2)
            
            return alpha, beta, gamma, delta

    
    def __init__(self):
        self._stbl_fit = self.StblFit()
        
        
    def _suddenness(self, hand_pos, l):
        """
        Suddenness algorithm to compute a result based on hand position and time window.
        
        Parameters:
        - hand_pos: np.ndarray of shape (N, 3), where each row is a 3D position of the hand
        - l: int, length of the time window
        
        Returns:
        - result: list of suddenness values for each window
        """
        result = []

        # Iterate over each window of length l in the hand positions
        for indx in range(l, len(hand_pos)):
            window = hand_pos[indx - l : indx + 1]

            # Calculate velocities
            vA = []
            for i in range(1, len(window)):
                v = window[i] - window[i - 1]  # Difference (velocity vector)
                magnitude = np.sqrt(np.sum(v ** 2))  # Compute magnitude of velocity
                vA.append(magnitude)

            # Fit to a stable distribution
            vA = np.array(vA)
            if len(vA) > 0:
                #print(vA)
                alpha, beta, gamma, delta = self._stbl_fit.fit(vA)

                # Suddenness calculation
                result.append(gamma * (1 - (alpha / 2)) * beta >= 0)
                
                
        result.extend([0] * l)
        return np.array(result)

    @staticmethod
    def _angle_between_lines(L0, L1):
        """Calculate the angle between two 3D lines (vectors)."""
        dot_product = np.dot(L0, L1)
        norms = np.linalg.norm(L0) * np.linalg.norm(L1)
        cos_theta = np.clip(dot_product / norms, -1.0, 1.0)
        return np.arccos(cos_theta)  # Return the angle in radians


    def _direction_change(self, hand_pos, delta_t, epsilon):
        """
        Parameters:
        - hand_pos: numpy array of shape (n, 3), where n is the number of time steps, and 3 represents the 3D coordinates (x, y, z)
        - delta_t: time window (integer)
        - epsilon: tolerance factor (float)
        
        Returns:
        - result: list of calculated direction change values
        """

        result = [0] * (2 * delta_t)

        for t in range(2 * delta_t, len(hand_pos)):
            
            # Extract points
            p0 = hand_pos[t]
            p1 = hand_pos[t - delta_t]
            p2 = hand_pos[t - 2 * delta_t]
            
            # Calculate direction vectors (lines)
            L0 = p0 - p1
            L1 = p1 - p2
            
            # Skip if either vector is too small (avoids divide by zero errors)
            if np.linalg.norm(L0) < 1e-6 or np.linalg.norm(L1) < 1e-6:
                result.append(0)
                continue
            
            # Calculate angle and normalized difference from 0.5
            angle = self._angle_between_lines(L0, L1) / np.pi
            a = 1 - angle
            if abs(a - 0.5) < epsilon:
                result.append(1 - abs(a - 0.5) / epsilon)
            else:
                result.append(0)

        return np.array(result)
    
    def __call__(self, trajectory, delta_t=80, eps=0.5):
        '''
        Parameters:
        - trajectory: np.ndarray of shape (N, 3), where each row is a 3D position of a marker
        - delta_t: int, length of the time window
        - eps: float, tolerance factor
        '''
        dir_ch = self._direction_change(trajectory, delta_t, eps)
        suddenness = self._suddenness(trajectory, delta_t)
        mask = suddenness > 0
        boundaries = np.diff(np.concatenate(([0], mask.astype(np.int32), [0])))
        starts = np.where(boundaries == 1)[0]
        ends = np.where(boundaries == -1)[0]

        for start, end in zip(starts, ends):
            if end - start < delta_t:
                suddenness[start:end] = 0
        
        return {"direction_change": dir_ch, 
                "suddenness": suddenness,
                "value": dir_ch * suddenness}