#!/usr/bin/env python3
"""
Example usage of the contraction_expansion module.
"""

import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyeyesweb.low_level.contraction_expansion import analyze_movement


def demo_2d_analysis():
    """Demonstrate 2D contraction/expansion analysis."""
    print("=== 2D Analysis Demo ===")
    
    # Rectangle formation (clockwise order for proper area)
    rectangle = np.array([
        [-1, -1],  # bottom left
        [1, -1],   # bottom right  
        [1, 1],    # top right
        [-1, 1]    # top left
    ], dtype=np.float64)
    
    result = analyze_movement(rectangle, mode="2D")
    print(f"Rectangle area: {result['metric']:.4f}")
    
    # Contracted position
    contracted = rectangle * 0.5
    result = analyze_movement(contracted, mode="2D")
    print(f"Contracted area: {result['metric']:.4f}")
    
    # Expanded position
    expanded = rectangle * 1.5
    result = analyze_movement(expanded, mode="2D")
    print(f"Expanded area: {result['metric']:.4f}\n")


def demo_3d_analysis():
    """Demonstrate 3D contraction/expansion analysis."""
    print("=== 3D Analysis Demo ===")
    
    # Tetrahedron formation
    tetrahedron = np.array([
        [0, 0, 0],   # origin foot
        [1, 0, 0],   # x-axis foot
        [0, 1, 0],   # y-axis arm
        [0, 0, 1]    # z-axis arm
    ], dtype=np.float64)
    
    result = analyze_movement(tetrahedron, mode="3D")
    print(f"Tetrahedron volume: {result['metric']:.6f}\n")


def demo_timeseries():
    """Demonstrate timeseries analysis with breathing pattern."""
    print("=== Timeseries Demo ===")
    
    # Generate breathing pattern (50 frames)
    # Data format: (n_frames, 4_points, 2_coordinates)
    n_frames = 50
    base_positions = np.array([
        [-1, -1],  # bottom left (left foot)
        [1, -1],   # bottom right (right foot)
        [1, 1],    # top right (right arm)
        [-1, 1]    # top left (left arm)
    ], dtype=np.float64)
    
    timeseries = np.zeros((n_frames, 4, 2), dtype=np.float64)
    
    for i in range(n_frames):
        t = i * 4 * np.pi / n_frames
        scale = 1 + 0.3 * np.sin(t)  # Breathing pattern
        timeseries[i] = base_positions * scale
    
    results = analyze_movement(timeseries, mode="2D")
    
    print(f"Processed {len(results['metrics'])} frames")
    print(f"Area range: {results['metrics'].min():.4f} - {results['metrics'].max():.4f}")
    
    # Count expansion/contraction phases
    expansions = np.sum(results['states'] == 1)
    contractions = np.sum(results['states'] == -1)
    
    print(f"Expansions: {expansions}, Contractions: {contractions}")
    print("✓ Breathing pattern detected!\n")


if __name__ == "__main__":
    demo_2d_analysis()
    demo_3d_analysis()
    demo_timeseries()
    
    print("All demos completed successfully.")