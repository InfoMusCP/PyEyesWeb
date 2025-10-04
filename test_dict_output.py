#!/usr/bin/env python3
"""Test script to verify all features return dictionaries."""

import numpy as np
from pyeyesweb.sync import Synchronization
from pyeyesweb.low_level.equilibrium import Equilibrium
from pyeyesweb.mid_level.smoothness import Smoothness
from pyeyesweb.data_models.sliding_window import SlidingWindow

def test_synchronization():
    """Test Synchronization class returns dictionary."""
    print("Testing Synchronization...")

    # Create synchronization analyzer
    sync = Synchronization(sensitivity=50, output_phase=True)

    # Create sliding window with two signals
    window = SlidingWindow(max_length=100, n_columns=2)

    # Generate sample data
    t = np.linspace(0, 2 * np.pi, 100)
    signal1 = np.sin(t)
    signal2 = np.sin(t + np.pi/4)  # Phase shifted signal

    # Fill window
    for i in range(100):
        window.append([signal1[i], signal2[i]])

    # Compute synchronization
    result = sync(window)

    # Check that result is a dictionary
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'plv' in result, "Missing 'plv' key in result"
    assert 'phase_status' in result, "Missing 'phase_status' key in result"

    print(f"  ✓ Synchronization returns dict with keys: {list(result.keys())}")
    print(f"    PLV: {result['plv']:.3f}")
    print(f"    Phase Status: {result['phase_status']}")

def test_equilibrium():
    """Test Equilibrium class returns dictionary."""
    print("\nTesting Equilibrium...")

    # Create equilibrium analyzer
    eq = Equilibrium(margin_mm=100, y_weight=0.5)

    # Define foot positions and barycenter
    left_foot = np.array([0, 0, 0])
    right_foot = np.array([400, 0, 0])
    barycenter = np.array([200, 50, 0])

    # Compute equilibrium
    result = eq(left_foot, right_foot, barycenter)

    # Check that result is a dictionary
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'value' in result, "Missing 'value' key in result"
    assert 'angle' in result, "Missing 'angle' key in result"

    print(f"  ✓ Equilibrium returns dict with keys: {list(result.keys())}")
    print(f"    Value: {result['value']:.3f}")
    print(f"    Angle: {result['angle']:.1f}°")

def test_smoothness():
    """Test Smoothness class returns dictionary."""
    print("\nTesting Smoothness...")

    # Create smoothness analyzer
    smooth = Smoothness(rate_hz=100.0, use_filter=True)

    # Create sliding window
    window = SlidingWindow(max_length=200, n_columns=1)

    # Generate sample movement data (smooth sinusoidal motion)
    t = np.linspace(0, 2, 200)
    movement = np.sin(2 * np.pi * t)

    # Fill window
    for value in movement:
        window.append([value])

    # Compute smoothness
    result = smooth(window)

    # Check that result is a dictionary
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    assert 'sparc' in result, "Missing 'sparc' key in result"
    assert 'jerk_rms' in result, "Missing 'jerk_rms' key in result"

    print(f"  ✓ Smoothness returns dict with keys: {list(result.keys())}")
    print(f"    SPARC: {result['sparc']:.3f}")
    print(f"    Jerk RMS: {result['jerk_rms']:.3f}")

def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Feature Dictionary Output Standardization")
    print("=" * 50)

    try:
        test_synchronization()
        test_equilibrium()
        test_smoothness()

        print("\n" + "=" * 50)
        print("✅ All tests passed! All features return dictionaries.")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())