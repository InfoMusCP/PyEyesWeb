#!/usr/bin/env python3
"""
PyEyesWeb Feature Testing Framework
A unified CLI tool for testing all PyEyesWeb features with various signal types.

Author: PyEyesWeb Testing Framework
Usage: python test_feature.py <feature> [options]

Examples:
    python test_feature.py synchronization --signal sine --freq 10
    python test_feature.py smoothness --signal random --length 1000
    python test_feature.py bilateral-symmetry --signal chirp --freq-start 1 --freq-end 50
    python test_feature.py equilibrium --signal gaussian --std 1.5
    python test_feature.py contraction-expansion --signal square --freq 5
"""

import argparse
import sys
import numpy as np
from typing import Dict, Tuple, List, Any, Optional
import time
from datetime import datetime
import json
from pathlib import Path
import os

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the signal generator from utils
from pyeyesweb.utils.signal_generators import SignalGenerator, generate_signal

# Color codes for beautiful CLI output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ============================================================================
# FEATURE TESTERS (Using centralized signal generator)
# ============================================================================

class FeatureTester:
    """Base class for feature testing."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def print_header(self, title: str):
        """Print a formatted header."""
        if self.verbose:
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{title}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

    def print_info(self, label: str, value: Any):
        """Print formatted information."""
        if self.verbose:
            print(f"{Colors.OKCYAN}{label:20s}{Colors.ENDC}: {value}")

    def print_success(self, message: str):
        """Print success message."""
        if self.verbose:
            print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

    def print_warning(self, message: str):
        """Print warning message."""
        if self.verbose:
            print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def print_error(self, message: str):
        """Print error message."""
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

class SynchronizationTester(FeatureTester):
    """Test synchronization features."""

    def test(self, signal_type: str, **kwargs):
        from pyeyesweb.analysis_primitives.synchronization import Synchronization

        self.print_header("SYNCHRONIZATION FEATURE TEST")

        # Generate test signals
        length = kwargs.get('length', 1000)
        generator = SignalGenerator()
        t1, signal1, metadata1 = generator.generate(signal_type, **kwargs)

        # Check if user specified a different second signal
        signal2_type = kwargs.get('signal2', None)

        if signal2_type:
            # Generate different signal type for comparison
            t2, signal2, metadata2 = generator.generate(signal2_type, **kwargs)
            self.print_info("Signal 1 Type", signal_type)
            self.print_info("Signal 2 Type", signal2_type)
        else:
            # Create a second signal of same type with phase shift for testing
            phase_shift = kwargs.get('phase_shift', np.pi/4)
            kwargs_copy = kwargs.copy()
            kwargs_copy['phase'] = kwargs.get('phase', 0) + phase_shift
            t2, signal2, metadata2 = generator.generate(signal_type, **kwargs_copy)
            self.print_info("Signal Type", f"{signal_type} (both)")
            self.print_info("Phase Shift", f"{phase_shift:.3f} radians")

        self.print_info("Signal Length", length)

        # Test synchronization
        try:
            from pyeyesweb.data_models.sliding_window import SlidingWindow

            sync = Synchronization(output_phase=True)

            # Create a sliding window with both signals
            window = SlidingWindow(max_length=length, n_columns=2)

            # Fill the window with both signals
            for i in range(length):
                window.append([signal1[i], signal2[i]])

            # Calculate PLV
            print(f"\n{Colors.BOLD}Phase Locking Value (PLV) Analysis:{Colors.ENDC}")
            result = sync.compute_synchronization(window)
            plv = result['plv']
            phase_status = result['phase_status']

            self.print_info("PLV", f"{plv:.4f}")
            self.print_info("Phase Status", phase_status)

            if plv > 0.8:
                self.print_success(f"High synchronization detected (PLV={plv:.4f})")
            elif plv > 0.5:
                self.print_warning(f"Moderate synchronization (PLV={plv:.4f})")
            else:
                self.print_warning(f"Low synchronization (PLV={plv:.4f})")

            # Test with sliding window analysis
            window_size = min(100, length // 10)
            sync_windowed = Synchronization(sensitivity=window_size, output_phase=True)

            print(f"\n{Colors.BOLD}Windowed Analysis (window={window_size}):{Colors.ENDC}")

            # Process some windows
            n_windows = min(10, length // window_size)
            plv_values = []

            for i in range(n_windows):
                start = i * window_size
                end = start + window_size

                # Create a window for this segment
                segment_window = SlidingWindow(max_length=window_size, n_columns=2)
                for j in range(start, end):
                    if j < length:
                        segment_window.append([signal1[j], signal2[j]])

                if segment_window.is_full():
                    result = sync_windowed.compute_synchronization(segment_window)
                    plv_values.append(result['plv'])

            if plv_values:
                self.print_info("Mean PLV (windowed)", f"{np.mean(plv_values):.4f}")
                self.print_info("Std PLV (windowed)", f"{np.std(plv_values):.4f}")
            else:
                self.print_warning("No windows processed")

            self.print_success("Synchronization test completed successfully")

            # Return results
            return {
                'plv': plv,
                'phase_status': phase_status,
                'windowed_plv_mean': np.mean(plv_values) if plv_values else None,
                'windowed_plv_std': np.std(plv_values) if plv_values else None,
                'n_windows': len(plv_values)
            }

        except Exception as e:
            self.print_error(f"Error in synchronization test: {str(e)}")
            return None

class SmoothnessTester(FeatureTester):
    """Test smoothness features."""

    def test(self, signal_type: str, **kwargs):
        from pyeyesweb.low_level.smoothness import Smoothness
        from pyeyesweb.data_models.sliding_window import SlidingWindow

        self.print_header("SMOOTHNESS FEATURE TEST")

        # Generate test signal(s)
        length = kwargs.get('length', 1000)
        generator = SignalGenerator()

        # Check if user wants to compare two different signals
        signal2_type = kwargs.get('signal2', None)

        if signal2_type:
            # Compare smoothness of two different signals
            t1, signal1, metadata1 = generator.generate(signal_type, **kwargs)
            t2, signal2, metadata2 = generator.generate(signal2_type, **kwargs)
            self.print_info("Comparing Signals", f"{signal_type} vs {signal2_type}")
            signals_to_test = [(signal_type, signal1), (signal2_type, signal2)]
        else:
            # Single signal test
            t, signal, metadata = generator.generate(signal_type, **kwargs)
            self.print_info("Signal Type", signal_type)
            signals_to_test = [(signal_type, signal)]

        self.print_info("Signal Length", length)

        try:
            smoothness = Smoothness(rate_hz=kwargs.get('sampling_rate', 100.0))
            all_results = {}

            for sig_type, sig_data in signals_to_test:
                # Create a sliding window with the signal
                window = SlidingWindow(max_length=length, n_columns=1)
                for i in range(length):
                    window.append([sig_data[i]])  # Wrap in list for proper format

                print(f"\n{Colors.BOLD}Smoothness Analysis for {sig_type}:{Colors.ENDC}")

                # Calculate smoothness metrics
                result = smoothness(window)
                sparc = result['sparc']
                jerk_rms = result['jerk_rms']

                self.print_info("SPARC", f"{sparc:.6f}")
                self.print_info("Jerk RMS", f"{jerk_rms:.6f}")

                # Interpret results (SPARC is negative; closer to 0 = less smooth)
                if sparc > -1.6:
                    self.print_success("Very smooth signal detected (healthy-like movement)")
                elif sparc > -3.0:
                    self.print_warning("Moderately smooth signal")
                else:
                    self.print_warning("Rough/pathological signal detected")

                all_results[sig_type] = {'sparc': sparc, 'jerk_rms': jerk_rms}

            # If comparing two signals, show comparison
            if signal2_type:
                print(f"\n{Colors.BOLD}Comparison Summary:{Colors.ENDC}")
                sparc_diff = all_results[signal_type]['sparc'] - all_results[signal2_type]['sparc']
                jerk_diff = all_results[signal_type]['jerk_rms'] - all_results[signal2_type]['jerk_rms']

                if sparc_diff > 0:
                    self.print_info("Smoother Signal", f"{signal_type} (SPARC diff: {sparc_diff:.4f})")
                else:
                    self.print_info("Smoother Signal", f"{signal2_type} (SPARC diff: {-sparc_diff:.4f})")

            self.print_success("Smoothness test completed successfully")

            return {
                'sparc': sparc,
                'jerk_rms': jerk_rms
            }

        except Exception as e:
            self.print_error(f"Error in smoothness test: {str(e)}")
            return None

class BilateralSymmetryTester(FeatureTester):
    """Test bilateral symmetry features."""

    def test(self, signal_type: str, **kwargs):
        from pyeyesweb.analysis_primitives.bilateral_symmetry import BilateralSymmetryAnalyzer

        self.print_header("BILATERAL SYMMETRY FEATURE TEST")

        # Generate test signals for left and right
        length = kwargs.get('length', 1000)
        generator = SignalGenerator()

        # Check if user wants different signals for left/right
        signal2_type = kwargs.get('signal2', None)

        if signal2_type:
            # Use different signals for left and right
            t_left, left_signal, metadata_left = generator.generate(signal_type, **kwargs)
            t_right, right_signal, metadata_right = generator.generate(signal2_type, **kwargs)
            self.print_info("Left Signal", signal_type)
            self.print_info("Right Signal", signal2_type)
        else:
            # Use same signal type with asymmetry
            t, left_signal, metadata = generator.generate(signal_type, **kwargs)
            # Create right signal with optional asymmetry
            asymmetry = kwargs.get('asymmetry', 0.1)
            right_signal = left_signal * (1 + asymmetry) + np.random.normal(0, 0.01, length)
            self.print_info("Signal Type", f"{signal_type} (both)")
            self.print_info("Induced Asymmetry", f"{asymmetry*100:.1f}%")

        self.print_info("Signal Length", length)

        try:
            # Define joint pairs (simulating left-right pairs like wrists, ankles)
            joint_pairs = [(0, 1)]  # One pair for simplicity
            analyzer = BilateralSymmetryAnalyzer(window_size=min(100, length), joint_pairs=joint_pairs)

            print(f"\n{Colors.BOLD}Bilateral Symmetry Analysis:{Colors.ENDC}")

            # Create mocap frames from signals
            # Simulate 2 joints (left and right) with 3D positions
            for i in range(length):
                mocap_frame = np.array([
                    [left_signal[i], 0, left_signal[i]],   # Left joint (x, y, z)
                    [right_signal[i], 0, right_signal[i]]   # Right joint (x, y, z)
                ])
                # Feed frame to analyzer
                analyzer(mocap_frame)

            # Get the final analysis
            results = analyzer.analyze_frame(mocap_frame)  # Use last frame to trigger analysis

            self.print_info("Overall Symmetry", f"{results['overall_symmetry']:.4f}")
            self.print_info("Phase Synchronization", f"{results['phase_sync']:.4f}")
            self.print_info("CCA Correlation", f"{results['cca_correlation']:.4f}")

            # Check individual joint pair if available
            if results['joint_symmetries']:
                joint_name = list(results['joint_symmetries'].keys())[0]
                joint_data = results['joint_symmetries'][joint_name]
                print(f"\n{Colors.BOLD}Joint Pair Analysis:{Colors.ENDC}")
                self.print_info("Bilateral Symmetry Index", f"{joint_data['bilateral_symmetry_index']:.4f}")
                self.print_info("Phase Sync", f"{joint_data['phase_synchronization']:.4f}")
                self.print_info("CCA Corr", f"{joint_data['cca_correlation']:.4f}")

            # Interpret results
            if results['overall_symmetry'] > 0.95:
                self.print_success("High bilateral symmetry detected")
            elif results['overall_symmetry'] > 0.8:
                self.print_warning("Moderate bilateral symmetry")
            else:
                self.print_warning("Low bilateral symmetry")

            self.print_success("Bilateral symmetry test completed successfully")

            return results

        except Exception as e:
            self.print_error(f"Error in bilateral symmetry test: {str(e)}")
            return None

class EquilibriumTester(FeatureTester):
    """Test equilibrium features."""

    def test(self, signal_type: str, **kwargs):
        from pyeyesweb.low_level.equilibrium import Equilibrium

        self.print_header("EQUILIBRIUM FEATURE TEST")

        # Generate test signal(s)
        length = kwargs.get('length', 1000)
        generator = SignalGenerator()

        # Check if user wants to compare equilibrium with two different signals
        signal2_type = kwargs.get('signal2', None)

        if signal2_type:
            # Compare equilibrium between two different signal types
            t1, signal1, metadata1 = generator.generate(signal_type, **kwargs)
            t2, signal2, metadata2 = generator.generate(signal2_type, **kwargs)

            # Add drift for testing equilibrium
            drift = kwargs.get('drift', 0.001)
            signal1 += drift * t1
            signal2 += drift * t2

            self.print_info("Signal 1", signal_type)
            self.print_info("Signal 2", signal2_type)
            self.print_info("Mode", "Comparing two signals")
            signals_to_test = [(signal_type, signal1, t1), (signal2_type, signal2, t2)]
        else:
            # Single signal test
            t, signal, metadata = generator.generate(signal_type, **kwargs)

            # Add drift for testing equilibrium
            drift = kwargs.get('drift', 0.001)
            signal += drift * t

            self.print_info("Signal Type", signal_type)
            signals_to_test = [(signal_type, signal, t)]

        self.print_info("Signal Length", length)
        self.print_info("Added Drift", f"{drift:.4f}")

        try:
            eq = Equilibrium(margin_mm=100, y_weight=0.5)
            all_results = {}

            # Simulate foot positions (fixed) and barycenter movement from signal
            left_foot = np.array([0, 0, 0])  # Left foot at origin
            right_foot = np.array([400, 0, 0])  # Right foot 400mm away

            for sig_type, sig_data, time_arr in signals_to_test:
                print(f"\n{Colors.BOLD}Equilibrium Analysis for {sig_type}:{Colors.ENDC}")

                # Test equilibrium at various points in the signal
                equilibrium_values = []
                for i in range(0, length, max(1, length // 20)):  # Sample 20 points
                    # Use signal to move barycenter (center of mass)
                    # x: lateral sway, y: forward/backward sway
                    barycenter = np.array([
                        200 + sig_data[i] * 50,  # Center between feet + lateral movement
                        sig_data[i] * 100,  # Forward/backward movement
                        0
                    ])
                    result = eq(left_foot, right_foot, barycenter)
                    equilibrium_values.append(result['value'])

                mean_equilibrium = np.mean(equilibrium_values)
                std_equilibrium = np.std(equilibrium_values)
                min_equilibrium = np.min(equilibrium_values)
                max_equilibrium = np.max(equilibrium_values)

                self.print_info("Mean Equilibrium", f"{mean_equilibrium:.4f}")
                self.print_info("Std Equilibrium", f"{std_equilibrium:.4f}")
                self.print_info("Min Equilibrium", f"{min_equilibrium:.4f}")
                self.print_info("Max Equilibrium", f"{max_equilibrium:.4f}")

                # Interpret results (equilibrium value: 1 = perfect balance, 0 = outside ellipse)
                if mean_equilibrium > 0.9:
                    self.print_success("High stability/equilibrium detected")
                elif mean_equilibrium > 0.7:
                    self.print_warning("Moderate stability")
                else:
                    self.print_warning("Low stability/equilibrium")

                all_results[sig_type] = {
                    'mean': mean_equilibrium,
                    'std': std_equilibrium,
                    'min': min_equilibrium,
                    'max': max_equilibrium
                }

            # If comparing two signals, show comparison
            if signal2_type:
                print(f"\n{Colors.BOLD}Comparison Summary:{Colors.ENDC}")
                mean_diff = all_results[signal_type]['mean'] - all_results[signal2_type]['mean']
                if mean_diff > 0:
                    self.print_info("More Stable Signal", f"{signal_type} (mean diff: {mean_diff:.4f})")
                else:
                    self.print_info("More Stable Signal", f"{signal2_type} (mean diff: {-mean_diff:.4f})")

            self.print_success("Equilibrium test completed successfully")

            return {
                'mean_equilibrium': mean_equilibrium,
                'std_equilibrium': std_equilibrium,
                'min_equilibrium': min_equilibrium,
                'max_equilibrium': max_equilibrium
            }

        except Exception as e:
            self.print_error(f"Error in equilibrium test: {str(e)}")
            return None

class ContractionExpansionTester(FeatureTester):
    """Test contraction-expansion features."""

    def test(self, signal_type: str, **kwargs):
        from pyeyesweb.low_level.contraction_expansion import ContractionExpansion

        self.print_header("CONTRACTION-EXPANSION FEATURE TEST")

        # Generate test signal(s)
        length = kwargs.get('length', 1000)
        generator = SignalGenerator()

        # Check if user wants to compare two signals
        signal2_type = kwargs.get('signal2', None)

        if signal2_type:
            # Compare contraction-expansion between two signals
            t1, signal1, metadata1 = generator.generate(signal_type, **kwargs)
            t2, signal2, metadata2 = generator.generate(signal2_type, **kwargs)

            # Apply envelope modulation for testing
            envelope1 = 1 + 0.5 * np.sin(2 * np.pi * 0.1 * t1)
            envelope2 = 1 + 0.5 * np.sin(2 * np.pi * 0.1 * t2)
            signal1 = signal1 * envelope1
            signal2 = signal2 * envelope2

            self.print_info("Signal 1", signal_type)
            self.print_info("Signal 2", signal2_type)
            signals_to_test = [(signal_type, signal1, t1), (signal2_type, signal2, t2)]
        else:
            # Single signal test
            t, signal, metadata = generator.generate(signal_type, **kwargs)

            # Apply envelope modulation for testing
            envelope = 1 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
            signal = signal * envelope

            self.print_info("Signal Type", signal_type)
            signals_to_test = [(signal_type, signal, t)]

        self.print_info("Signal Length", length)
        self.print_info("Envelope Applied", "Yes (sinusoidal)")

        try:
            ce = ContractionExpansion(mode="2D", baseline_frame=0)
            all_results = {}

            for sig_type, sig_data, time_arr in signals_to_test:
                print(f"\n{Colors.BOLD}Contraction-Expansion Analysis for {sig_type}:{Colors.ENDC}")

                # Create time series of 4 points forming a square that expands/contracts based on signal
                frames = []
                for i in range(length):
                    # Use signal to modulate square size
                    size = 1.0 + sig_data[i] * 0.5  # Base size + modulation
                    points = np.array([
                        [0, 0],           # Bottom-left
                        [size, 0],        # Bottom-right
                        [size, size],     # Top-right
                        [0, size]         # Top-left
                    ])
                    frames.append(points)
                frames = np.array(frames)

                # Analyze the time series
                result = ce(frames)

                metrics = result['metrics']
                states = result['states']
                # The baseline is the first metric (baseline_frame=0)
                baseline_metric = metrics[0] if len(metrics) > 0 else 1.0

                # Count states (-1=contraction, 0=neutral, 1=expansion)
                n_contractions = np.sum(states == -1)
                n_expansions = np.sum(states == 1)
                n_stable = np.sum(states == 0)

                self.print_info("Baseline Area", f"{baseline_metric:.4f}")
                self.print_info("Mean Area", f"{np.mean(metrics):.4f}")
                self.print_info("Std Area", f"{np.std(metrics):.4f}")
                self.print_info("Min Area", f"{np.min(metrics):.4f}")
                self.print_info("Max Area", f"{np.max(metrics):.4f}")

                print(f"\n{Colors.BOLD}State Analysis:{Colors.ENDC}")
                self.print_info("Contraction Frames", f"{n_contractions} ({100*n_contractions/length:.1f}%)")
                self.print_info("Expansion Frames", f"{n_expansions} ({100*n_expansions/length:.1f}%)")
                self.print_info("Stable Frames", f"{n_stable} ({100*n_stable/length:.1f}%)")

                # Interpret results
                if n_contractions > n_expansions * 1.2:
                    self.print_warning("Signal shows more contraction than expansion")
                elif n_expansions > n_contractions * 1.2:
                    self.print_warning("Signal shows more expansion than contraction")
                else:
                    self.print_success("Signal shows balanced contraction-expansion")

                all_results[sig_type] = {
                    'baseline_metric': baseline_metric,
                    'mean_area': np.mean(metrics),
                    'std_area': np.std(metrics),
                    'n_contractions': n_contractions,
                    'n_expansions': n_expansions,
                    'n_stable': n_stable
                }

            # If comparing two signals, show comparison
            if signal2_type:
                print(f"\n{Colors.BOLD}Comparison Summary:{Colors.ENDC}")
                mean_diff = all_results[signal_type]['mean_area'] - all_results[signal2_type]['mean_area']
                if mean_diff > 0:
                    self.print_info("Larger Area Signal", f"{signal_type} (mean diff: {mean_diff:.4f})")
                else:
                    self.print_info("Larger Area Signal", f"{signal2_type} (mean diff: {-mean_diff:.4f})")

            self.print_success("Contraction-Expansion test completed successfully")

            return {
                'baseline_metric': baseline_metric,
                'mean_area': np.mean(metrics),
                'std_area': np.std(metrics),
                'n_contractions': n_contractions,
                'n_expansions': n_expansions,
                'n_stable': n_stable
            }

        except Exception as e:
            self.print_error(f"Error in contraction-expansion test: {str(e)}")
            return None

# ============================================================================
# MAIN CLI INTERFACE
# ============================================================================

def create_parser():
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="PyEyesWeb Feature Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/feature_test_cli.py list-features
  python tests/feature_test_cli.py list-signals
  python tests/feature_test_cli.py synchronization --signal sine --freq 10
  python tests/feature_test_cli.py smoothness --signal random --length 1000
  python tests/feature_test_cli.py bilateral-symmetry --signal chirp --freq-start 1 --freq-end 50
  python tests/feature_test_cli.py equilibrium --signal gaussian --std 1.5 --drift 0.01
  python tests/feature_test_cli.py contraction-expansion --signal square --freq 5
  python tests/feature_test_cli.py smoothness --signal sine --save-results test.json  # Saves as output/YYYYMMDD_HHMMSS_test.json
  python tests/feature_test_cli.py --help  # Show all options
        """
    )

    # Feature selection (positional argument)
    parser.add_argument(
        'feature',
        type=str,
        choices=['synchronization', 'smoothness', 'bilateral-symmetry',
                'equilibrium', 'contraction-expansion', 'list-signals', 'list-features'],
        help='Feature to test or action to perform'
    )

    # Signal configuration
    parser.add_argument(
        '--signal', '-s',
        type=str,
        default='sine',
        help='Type of signal to generate (default: sine)'
    )

    parser.add_argument(
        '--signal2', '-s2',
        type=str,
        default=None,
        help='Second signal type for comparison (optional). If not specified, uses --signal with modifications'
    )

    parser.add_argument(
        '--length', '-l',
        type=int,
        default=1000,
        help='Length of the signal (default: 1000)'
    )

    # Common signal parameters
    parser.add_argument(
        '--freq',
        type=float,
        default=1.0,
        help='Frequency for periodic signals (default: 1.0)'
    )

    parser.add_argument(
        '--amplitude', '-a',
        type=float,
        default=1.0,
        help='Amplitude of the signal (default: 1.0)'
    )

    parser.add_argument(
        '--phase',
        type=float,
        default=0.0,
        help='Phase offset for periodic signals (default: 0.0)'
    )

    parser.add_argument(
        '--sampling-rate',
        type=float,
        default=100.0,
        help='Sampling rate (default: 100.0)'
    )

    # Noise and modulation
    parser.add_argument(
        '--noise-level',
        type=float,
        default=0.1,
        help='Noise level for noisy signals (default: 0.1)'
    )

    parser.add_argument(
        '--std',
        type=float,
        default=1.0,
        help='Standard deviation for Gaussian signals (default: 1.0)'
    )

    # Chirp signal parameters
    parser.add_argument(
        '--freq-start',
        type=float,
        default=1.0,
        help='Start frequency for chirp signal (default: 1.0)'
    )

    parser.add_argument(
        '--freq-end',
        type=float,
        default=10.0,
        help='End frequency for chirp signal (default: 10.0)'
    )

    # Feature-specific parameters
    parser.add_argument(
        '--phase-shift',
        type=float,
        default=np.pi/4,
        help='Phase shift for second signal in synchronization (default: π/4)'
    )

    parser.add_argument(
        '--asymmetry',
        type=float,
        default=0.1,
        help='Asymmetry factor for bilateral symmetry (default: 0.1)'
    )

    parser.add_argument(
        '--drift',
        type=float,
        default=0.001,
        help='Drift factor for equilibrium testing (default: 0.001)'
    )

    # Output options
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output (only show results)'
    )

    parser.add_argument(
        '--save-results',
        type=str,
        help='Save results to JSON file'
    )

    parser.add_argument(
        '--seed',
        type=int,
        help='Random seed for reproducibility'
    )

    return parser

def list_signals():
    """List all available signal types."""
    generator = SignalGenerator()
    available_signals = generator.available_signals
    signal_info = generator.signal_info
    categories = generator.get_signals_by_category()

    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Available Signal Types ({len(available_signals)} types){Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    # Define category display order
    category_order = [
        'Basic Waveforms', 'Noise Signals', 'Chirp Signals', 'Modulated',
        'Transient', 'Biological', 'Complex', 'Chaotic'
    ]

    for category in category_order:
        if category in categories:
            signals = sorted(categories[category])
            print(f"\n{Colors.BOLD}{category}:{Colors.ENDC}")
            for signal_type in signals:
                if signal_type in available_signals:
                    desc = signal_info.get(signal_type, {}).get('description', 'Custom signal')
                    print(f"  {Colors.OKCYAN}{signal_type:18s}{Colors.ENDC} - {desc}")

    print(f"\n{Colors.OKGREEN}Use any of these with --signal parameter{Colors.ENDC}")
    print(f"{Colors.OKGREEN}Example: python test_feature.py synchronization --signal ecg --heart-rate 80{Colors.ENDC}")

def list_features():
    """List all available features."""
    features = [
        ('synchronization', 'Test phase synchronization between signals'),
        ('smoothness', 'Analyze signal smoothness using various metrics'),
        ('bilateral-symmetry', 'Test bilateral symmetry between left/right signals'),
        ('equilibrium', 'Analyze equilibrium and stability of signals'),
        ('contraction-expansion', 'Test contraction-expansion dynamics'),
    ]

    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}Available Features{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

    for feature, description in features:
        print(f"  {Colors.OKCYAN}{feature:20s}{Colors.ENDC} - {description}")

    print(f"\n{Colors.OKGREEN}Use any of these as the first argument{Colors.ENDC}")

def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle list commands
    if args.feature == 'list-signals':
        list_signals()
        return

    if args.feature == 'list-features':
        list_features()
        return

    # Set random seed if provided
    if args.seed is not None:
        np.random.seed(args.seed)

    # Create feature tester
    verbose = not args.quiet

    # Map features to testers
    testers = {
        'synchronization': SynchronizationTester,
        'smoothness': SmoothnessTester,
        'bilateral-symmetry': BilateralSymmetryTester,
        'equilibrium': EquilibriumTester,
        'contraction-expansion': ContractionExpansionTester,
    }

    if args.feature not in testers:
        print(f"{Colors.FAIL}Unknown feature: {args.feature}{Colors.ENDC}")
        print("Run 'python test_feature.py list-features' to see available features")
        sys.exit(1)

    # Create tester instance
    tester = testers[args.feature](verbose=verbose)

    # Prepare kwargs from args
    kwargs = {
        'length': args.length,
        'freq': args.freq,
        'amplitude': args.amplitude,
        'phase': args.phase,
        'sampling_rate': args.sampling_rate,
        'noise_level': args.noise_level,
        'std': args.std,
        'freq_start': args.freq_start,
        'freq_end': args.freq_end,
        'phase_shift': args.phase_shift,
        'asymmetry': args.asymmetry,
        'drift': args.drift,
        'seed': args.seed,
        'signal2': args.signal2,  # Add the second signal type
    }

    # Run the test
    start_time = time.time()
    results = tester.test(args.signal, **kwargs)
    elapsed_time = time.time() - start_time

    if results:
        if verbose:
            print(f"\n{Colors.OKBLUE}Test completed in {elapsed_time:.3f} seconds{Colors.ENDC}")

        # Save results if requested
        if args.save_results:
            results['metadata'] = {
                'feature': args.feature,
                'signal_type': args.signal,
                'timestamp': datetime.now().isoformat(),
                'elapsed_time': elapsed_time,
                'parameters': kwargs
            }

            # Create output directory if it doesn't exist
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)

            # Generate timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(args.save_results)

            # Add timestamp to filename (timestamp first for proper sorting)
            if output_path.suffix == '.json':
                # Has .json extension - put timestamp at start
                filename_base = output_path.stem
                timestamped_filename = f"{timestamp}_{filename_base}.json"
            else:
                # No extension or different extension - add timestamp and .json
                timestamped_filename = f"{timestamp}_{args.save_results}.json"

            # Determine final output path
            if not output_path.is_absolute() and output_path.parent == Path('.'):
                # Just a filename provided - save in output/
                output_path = output_dir / timestamped_filename
            else:
                # Full path provided - use provided directory with timestamped filename
                output_path = output_path.parent / timestamped_filename

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            if verbose:
                print(f"{Colors.OKGREEN}Results saved to {output_path}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}Test failed!{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()