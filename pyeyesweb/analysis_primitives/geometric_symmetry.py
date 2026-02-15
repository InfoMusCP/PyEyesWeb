"""Bilateral symmetry analysis module.

This module provides tools for quantifying the symmetry and synchronization
between bilateral body parts (e.g., left and right limbs) using multiple 
metrics including Bilateral Symmetry Index (BSI), Canonical Correlation 
Analysis (CCA), and Phase Synchronization.

Bilateral symmetry metrics are important indicators in:
1. Gait analysis and rehabilitation
2. Athletic performance assessment
3. Motor coordination studies
4. Neurological assessment
"""

import numpy as np
import warnings
from sklearn.cross_decomposition import CCA

from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.utils.validators import validate_pairs


class BilateralSymmetry:
    """Analyze bilateral symmetry between joint pairs in motion capture data.

    This class computes multiple symmetry metrics by comparing data from 
    bilateral joint pairs (e.g., left and right shoulders). It supports 
    Bilateral Symmetry Index (BSI), Phase Synchronization, and Canonical 
    Correlation Analysis (CCA).

    The implementation incorporates methods adapted from biomechanics 
    research on movement symmetry and data fusion.


    Parameters
    ----------
    window_size : int, optional
        Number of frames for sliding window analysis (default: 100).
    signal_pairs : list of tuple, optional
        List of tuples defining bilateral signal pairs (left_idx, right_idx).
        If None, standard MoCap signal pairs are used.
    filter_params : tuple, optional
        Optional tuple of (lowcut_hz, highcut_hz, sampling_rate_hz)
        for band-pass filtering. If None, no filtering is applied.

    Attributes
    ----------
    window_size : int
        Size of the analysis window.
    signal_pairs : list of tuple
        Indices of signal pairs being analyzed.
    filter_params : tuple or None
        Parameters for signal filtering.

    Examples
    --------
    >>> from pyeyesweb.analysis_primitives.bilateral_symmetry import BilateralSymmetry
    >>> import numpy as np
    >>> 
    >>> # Initialize with default signal pairs
    >>> analyzer = BilateralSymmetry(signal_pairs=[(0, 1), (2, 3)])
    >>> 
    >>> # Create dummy mocap frame (n_signals, 3)
    >>> frame = np.random.rand(20, 3)
    >>> 
    >>> # Analyze frame
    >>> result = analyzer(frame)
    >>> print(f"Overall Symmetry: {result['overall_symmetry']:.3f}")

    Notes
    -----
    1. BSI: Based on mirroring right-side data across the sagittal plane.
    2. CCA: Measures the maximum correlation between linear combinations of bilateral features.
    3. Phase Sync: Uses Hilbert transform to measure synchronization of vertical movement.

    References
    ----------
    1. "Movement Symmetry Assessment by Bilateral Motion Data Fusion" (2018)
       https://pubmed.ncbi.nlm.nih.gov/29993408/
    2. "Symmetry Analysis of Manual Wheelchair Propulsion Using Motion Capture Techniques" (2022)
       https://www.mdpi.com/2073-8994/14/6/1164/htm
    """
    
    def __init__(self, signal_pairs:list[tuple], center_of_symmetry:int|None=None):
        
        self._signal_pairs = set(validate_pairs(signal_pairs))
        if not len(self._signal_pairs):
            raise ValueError("At least one signal pair must be provided.")
        
        self._center_idx = center_of_symmetry if center_of_symmetry is not None else -1
        self._num_signals = max(max(pair) for pair in self._signal_pairs) + 1
        self.cca = CCA(n_components=1, max_iter=5000)  # CCA with single component for simplicity


            
    def _compute_bilateral_symmetry_index(self, left_data, right_data):
        """Compute Bilateral Symmetry Index based on research methodology.
        
        Inspired by wheelchair propulsion research paper method:
        Compares mirrored bilateral movements and calculates relative differences.
        
        Parameters
        ----------
        left_data : ndarray
            (n_frames, 3) array of left joint positions.
        right_data : ndarray
            (n_frames, 3) array of right joint positions.
            
        Returns
        -------
        float
            Symmetry index (0-1, where 1 is perfect symmetry).
        """
        # TODO: discuss
        # Mirror right side data across sagittal plane (flip x-coordinate)
        right_mirrored = right_data.copy()
        right_mirrored[:, 0] *= -1  # Flip x-axis for bilateral comparison
        
        # Calculate relative differences (from wheelchair research)
        diff = np.abs(left_data - right_mirrored)
        sum_val = np.abs(left_data) + np.abs(right_mirrored)
        
        # Avoid division by zero
        sum_val = np.where(sum_val == 0, 1e-8, sum_val)
        
        # Relative asymmetry percentage
        relative_asymmetry = np.mean(diff / sum_val) * 100
        
        # Convert to symmetry index (100% asymmetry = 0 symmetry)
        symmetry_index = max(0, 1 - (relative_asymmetry / 100))
        
        return symmetry_index
    

    def _compute_cca_correlation(self, left_data, right_data):
        """Compute canonical correlation between bilateral data.
        
        Based on "Movement Symmetry Assessment by Bilateral Motion Data Fusion" paper
        methodology using Canonical Correlation Analysis.
        
        Parameters
        ----------
        left_data : ndarray
            (n_frames, 3) left joint data.
        right_data : ndarray
            (n_frames, 3) right joint data.
            
        Returns
        -------
        float
            Canonical correlation (0-1).
        """
        if left_data.shape[0] < 5:  # Need minimum samples for CCA
            return np.nan  # Not enough data for CCA
            
        # Flatten spatial coordinates for CCA analysis
        left_features = left_data.reshape(left_data.shape[0], -1)
        right_features = right_data.reshape(right_data.shape[0], -1)
        
        # Apply CCA with single component
        left_c, right_c = self.cca.fit_transform(left_features, right_features)
        
        # Compute canonical correlation
        correlation = np.corrcoef(left_c.flatten(), right_c.flatten())[0, 1]

        # Handle NaN cases
        if np.isnan(correlation):
            return np.nan  # Correlation computation failed
            
        return abs(correlation)  # Take absolute value

    
    def __call__(self, sliding_windows:SlidingWindow) -> dict:
        """Compute bilateral symmetry metrics for motion capture frame.

        This method provides a standardized API interface by delegating to analyze_frame.

        Parameters
        ----------
        sliding_windows : SlidingWindow
            (n_frames, n_signals, 2/3) array of signal positions for multiple frames.

        Returns
        -------
        dict
            Symmetry metrics containing:
            - 'overall_symmetry': Overall bilateral symmetry score (0-1).
            - 'phase_sync': Phase synchronization value.
            - 'cca_correlation': Canonical correlation coefficient.
            - 'joint_symmetries': Per-joint-pair symmetry metrics.
        """
        if sliding_windows.get_num_dimensions() != 3:
            raise ValueError("Input data must be a 3D array (n_frames, n_signals, 3).")
        
        if sliding_windows.get_num_signals() < self._num_signals:
            raise ValueError("Sliding window does not have enough signals for the specified joint pairs.")
        
        history_length = len(sliding_windows)

        if history_length < 10:  # Need minimum history for analysis
            return {
                (left, right): {
                    'bilateral_symmetry_index': 0.0,
                    'cca_correlation': 0.0
                } for left, right in self.joint_pairs
            }

        # ThreadSafeHistoryBuffer provides thread-safe get_array method
        history_array = sliding_windows.to_array()[0]  # (n_frames, n_joints, 2/3)
        
        joint_symmetries = {}
    
        # Analyze each bilateral joint pair
        for left_idx, right_idx in self.joint_pairs:
            left_joint_data = history_array[:, left_idx, :].reshape(-1, 3)  # Ensure shape (n_frames, 3)
            right_joint_data = history_array[:, right_idx, :].reshape(-1, 3)  # Ensure same shape for comparison
            
            # Compute multiple symmetry metrics
            bsi = self._compute_bilateral_symmetry_index(left_joint_data, right_joint_data)

            
            cca_corr = self._compute_cca_correlation(left_joint_data, right_joint_data)
            
            joint_symmetries[(left_idx, right_idx)] = {
                'bilateral_symmetry_index': bsi,
                'cca_correlation': cca_corr
            }
            
        return joint_symmetries
    
    
    
    
import numpy as np

class GeometricSymmetry:
    """
    Computes the spatial symmetry error for a sequence of skeletal frames.
    
    The symmetry is calculated by reflecting joints across a central plane 
    passing through the 'center of symmetry' and measuring the deviation.
    """
    
    def __init__(self, joint_pairs:list[tuple], center_of_symmetry:int|None=None):
        """
        Args:
            joint_pairs (list of tuples): List of (left_joint_idx, right_joint_idx).
            center_of_symmetry (int, optional): Index of the joint representing the center 
                                       (e.g., pelvis). If None, the center of mass 
                                       per frame is used.
        """
        self._center_idx = center_of_symmetry if center_of_symmetry is not None else -1  # Use -1 to indicate center of mass if not specified
        self._signal_pairs = set(validate_pairs(joint_pairs))
        if not len(self._signal_pairs):
            raise ValueError("At least one signal pair must be provided.")
        
        self._num_signals = max(max(pair) for pair in self._signal_pairs) + 1

    def __call__(self, sliding_window:SlidingWindow) -> dict[tuple, float]:
        """
        Args:
            sliding_window (SlidingWindow): Sliding window containing the data.
            
        Returns:
            dict: Pairwise symmetry errors per frame for each signal pair.
        """
        data = sliding_window.to_array()[0]  # (t_frames, n_signals, 3)
        t, m, n = data.shape
        #print(f"Data shape: {data} (t_frames, n_signals, 3)")
        
        # 1. Determine the Center of Symmetry (CoS)
        if self._center_idx != -1:
            # Use a specific signal (e.g., Mid-Hip)
            cos = data[:, self._center_idx, :][:,np.newaxis,:]
        else:
            # Calculate Center of Mass (Mean of all signals)
            cos = np.mean(data, axis=1)[:, np.newaxis, :]
            
        # 2. Center the data
        # We shift the coordinate system so the center of symmetry is at (0,0,0)
        centered_data = data - cos
        
        # 3. Compute Symmetry Error
        # We compare signal_L with the reflected version of signal_R
        # Reflection across the sagittal plane (assuming X-axis is lateral)
        # reflected_R = [-x, y, z]
        pair_errors = {}
        for left_idx, right_idx in self._signal_pairs:
            left_joints = centered_data[:, left_idx, :].reshape(-1, 3)  # Ensure shape is (t_frames, 3)
            right_joints = centered_data[:, right_idx, :].reshape(-1, 3)  # Ensure shape is (t_frames, 3)
            
            # Reflect the right joint across the X-axis (index 0)
            reflected_right = right_joints.copy()
            reflected_right[:, 0] = -reflected_right[:, 0]
            
            # Calculate Euclidean distance between Left and Reflected Right
            # Error = sqrt( (xL - (-xR))^2 + (yL - yR)^2 + (zL - zR)^2 )
            pair_errors[(left_idx, right_idx)] = 1 - np.mean(np.linalg.norm(left_joints - reflected_right, axis=1))
            
        # Return the pairwise errors for each joint pair. The user can compute overall symmetry from these if desired.
        return pair_errors