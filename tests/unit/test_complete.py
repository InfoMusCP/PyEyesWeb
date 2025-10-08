"""Unit tests for feature testers and test helpers."""
import pytest
import numpy as np

from tests.test_helpers import FeatureTester, Colors, CLIFormatter, FeatureThresholds
from tests.conftest import assert_valid_result


# ============================================================================
# TEST HELPERS
# ============================================================================

class TestColors:
    """Test Colors class."""

    def test_colors_defined(self):
        """Test that all color codes are defined."""
        assert hasattr(Colors, 'HEADER')
        assert hasattr(Colors, 'OKBLUE')
        assert hasattr(Colors, 'OKCYAN')
        assert hasattr(Colors, 'OKGREEN')
        assert hasattr(Colors, 'WARNING')
        assert hasattr(Colors, 'FAIL')
        assert hasattr(Colors, 'ENDC')
        assert hasattr(Colors, 'BOLD')
        assert hasattr(Colors, 'UNDERLINE')

    def test_colors_are_strings(self):
        """Test that all color codes are strings."""
        assert isinstance(Colors.HEADER, str)
        assert isinstance(Colors.OKGREEN, str)
        assert isinstance(Colors.FAIL, str)


class TestCLIFormatter:
    """Test CLIFormatter class."""

    def test_init_verbose(self):
        """Test formatter initialization with verbose mode."""
        formatter = CLIFormatter(verbose=True)
        assert formatter.verbose is True

    def test_init_quiet(self):
        """Test formatter initialization with quiet mode."""
        formatter = CLIFormatter(verbose=False)
        assert formatter.verbose is False

    def test_print_methods_exist(self):
        """Test that all print methods exist."""
        formatter = CLIFormatter()
        assert hasattr(formatter, 'print_header')
        assert hasattr(formatter, 'print_info')
        assert hasattr(formatter, 'print_section')
        assert hasattr(formatter, 'print_success')
        assert hasattr(formatter, 'print_warning')
        assert hasattr(formatter, 'print_error')
        assert hasattr(formatter, 'print_timing')


class TestFeatureThresholds:
    """Test FeatureThresholds class."""

    def test_thresholds_initialized(self):
        """Test that all threshold categories are initialized."""
        thresholds = FeatureThresholds()
        assert hasattr(thresholds, 'sync')
        assert hasattr(thresholds, 'smoothness')
        assert hasattr(thresholds, 'equilibrium')
        assert hasattr(thresholds, 'symmetry')
        assert hasattr(thresholds, 'contraction_expansion')

    def test_sync_thresholds(self):
        """Test synchronization thresholds."""
        thresholds = FeatureThresholds()
        assert thresholds.sync.HIGH == 0.8
        assert thresholds.sync.MODERATE == 0.5

    def test_smoothness_thresholds(self):
        """Test smoothness thresholds."""
        thresholds = FeatureThresholds()
        assert thresholds.smoothness.VERY_SMOOTH == -1.6
        assert thresholds.smoothness.MODERATELY_SMOOTH == -3.0

    def test_equilibrium_thresholds(self):
        """Test equilibrium thresholds."""
        thresholds = FeatureThresholds()
        assert thresholds.equilibrium.HIGH_STABILITY == 0.9
        assert thresholds.equilibrium.MODERATE_STABILITY == 0.7

    def test_symmetry_thresholds(self):
        """Test symmetry thresholds."""
        thresholds = FeatureThresholds()
        assert thresholds.symmetry.HIGH_SYMMETRY == 0.95
        assert thresholds.symmetry.MODERATE_SYMMETRY == 0.8


class TestFeatureTesterBase:
    """Test FeatureTester base class."""

    def test_init(self):
        """Test base tester initialization."""
        tester = FeatureTester(verbose=True)
        assert tester.verbose is True
        assert hasattr(tester, 'formatter')
        assert hasattr(tester, 'generator')
        assert hasattr(tester, 'thresholds')

    def test_signal_generation(self):
        """Test single signal generation."""
        tester = FeatureTester(verbose=False)
        t, signal, metadata = tester.generate_single_signal('sine', length=100, freq=1.0)

        assert len(t) == 100
        assert len(signal) == 100
        assert isinstance(metadata, dict)

    def test_signal_pair_generation_same_type(self):
        """Test signal pair generation with same type."""
        tester = FeatureTester(verbose=False)
        signal1, signal2, metadata = tester.generate_signal_pair(
            'sine', length=100, freq=1.0
        )

        assert len(signal1) == 100
        assert len(signal2) == 100
        assert metadata['signal1_type'] == 'sine'
        assert metadata['signal2_type'] == 'sine'
        assert metadata['comparison_mode'] == 'modified_signal'

    def test_signal_pair_generation_different_types(self):
        """Test signal pair generation with different types."""
        tester = FeatureTester(verbose=False)
        signal1, signal2, metadata = tester.generate_signal_pair(
            'sine', signal2_type='square', length=100, freq=1.0
        )

        assert len(signal1) == 100
        assert len(signal2) == 100
        assert metadata['signal1_type'] == 'sine'
        assert metadata['signal2_type'] == 'square'
        assert metadata['comparison_mode'] == 'different_signals'

    def test_test_method_not_implemented(self):
        """Test that base class test method raises NotImplementedError."""
        tester = FeatureTester(verbose=False)
        with pytest.raises(NotImplementedError):
            tester.test('sine')


# ============================================================================
# TEST FEATURE TESTERS
# ============================================================================

class TestSynchronizationTester:
    """Test SynchronizationTester."""

    def test_init(self, sync_tester):
        """Test tester initialization."""
        assert isinstance(sync_tester, FeatureTester)

    def test_basic_sync_test(self, sync_tester):
        """Test basic synchronization with sine wave."""
        result = sync_tester.test('sine', length=100, freq=1.0)
        assert_valid_result(result, ['plv', 'phase_status'])
        assert 0 <= result['plv'] <= 1

    def test_sync_with_different_signals(self, sync_tester):
        """Test synchronization with two different signal types."""
        result = sync_tester.test('sine', signal2='square', length=100, freq=1.0)
        assert_valid_result(result, ['plv'])

    def test_sync_high_correlation(self, sync_tester):
        """Test synchronization with identical signals (should be high PLV)."""
        result = sync_tester.test('sine', length=100, freq=1.0, phase_shift=0.0)
        assert_valid_result(result, ['plv'])
        assert result['plv'] > 0.9  # Should be very high

    def test_windowed_plv_computed(self, sync_tester):
        """Test that windowed PLV is computed."""
        result = sync_tester.test('sine', length=200, freq=1.0)
        assert_valid_result(result, ['windowed_plv_mean', 'n_windows'])
        assert result['n_windows'] > 0


class TestSmoothnessTester:
    """Test SmoothnessTester."""

    def test_init(self, smoothness_tester):
        """Test tester initialization."""
        assert isinstance(smoothness_tester, FeatureTester)

    def test_basic_smoothness_test(self, smoothness_tester):
        """Test basic smoothness with sine wave."""
        result = smoothness_tester.test('sine', length=100, freq=1.0)
        assert_valid_result(result, ['sparc', 'jerk_rms'])
        assert isinstance(result['sparc'], (float, np.floating))
        assert isinstance(result['jerk_rms'], (float, np.floating))

    def test_smoothness_with_different_signals(self, smoothness_tester):
        """Test smoothness comparison with two signal types."""
        result = smoothness_tester.test('sine', signal2='random', length=100)
        assert_valid_result(result, ['sparc'])

    def test_smooth_vs_noisy_signal(self, smoothness_tester):
        """Test that smooth signal has better SPARC than noisy signal."""
        sine_result = smoothness_tester.test('sine', length=200, freq=1.0)
        random_result = smoothness_tester.test('random', length=200)

        assert_valid_result(sine_result, ['sparc'])
        assert_valid_result(random_result, ['sparc'])
        # SPARC is negative; closer to 0 is smoother
        assert sine_result['sparc'] > random_result['sparc']


class TestBilateralSymmetryTester:
    """Test BilateralSymmetryTester."""

    def test_init(self, symmetry_tester):
        """Test tester initialization."""
        assert isinstance(symmetry_tester, FeatureTester)

    def test_basic_symmetry_test(self, symmetry_tester):
        """Test basic bilateral symmetry."""
        result = symmetry_tester.test('sine', length=200, freq=1.0, asymmetry=0.1)
        assert_valid_result(result, ['overall_symmetry', 'phase_sync', 'cca_correlation'])
        assert 0 <= result['overall_symmetry'] <= 1

    def test_symmetry_with_different_signals(self, symmetry_tester):
        """Test symmetry with different left/right signals."""
        result = symmetry_tester.test('sine', signal2='square', length=200)
        assert_valid_result(result, ['overall_symmetry'])

    def test_low_asymmetry_gives_high_symmetry(self, symmetry_tester):
        """Test that low asymmetry gives high symmetry."""
        result = symmetry_tester.test('sine', length=200, freq=1.0, asymmetry=0.01)
        assert_valid_result(result, ['overall_symmetry'])
        assert result['overall_symmetry'] > 0.5


class TestEquilibriumTester:
    """Test EquilibriumTester."""

    def test_init(self, equilibrium_tester):
        """Test tester initialization."""
        assert isinstance(equilibrium_tester, FeatureTester)

    def test_basic_equilibrium_test(self, equilibrium_tester):
        """Test basic equilibrium analysis."""
        result = equilibrium_tester.test('sine', length=100, freq=1.0)
        assert_valid_result(result, ['mean', 'std', 'min', 'max'])
        assert 0 <= result['mean'] <= 1
        assert 0 <= result['min'] <= 1
        assert 0 <= result['max'] <= 1

    def test_equilibrium_with_different_signals(self, equilibrium_tester):
        """Test equilibrium comparison with two signals."""
        result = equilibrium_tester.test('sine', signal2='square', length=100)
        assert_valid_result(result, ['mean'])

    def test_equilibrium_with_drift(self, equilibrium_tester):
        """Test equilibrium with different drift values."""
        low_drift = equilibrium_tester.test('sine', length=100, drift=0.001)
        high_drift = equilibrium_tester.test('sine', length=100, drift=0.01)

        assert_valid_result(low_drift, ['mean'])
        assert_valid_result(high_drift, ['mean'])
        # More drift should generally lead to lower equilibrium
        assert low_drift['mean'] >= high_drift['mean'] - 0.2  # Allow some tolerance


class TestContractionExpansionTester:
    """Test ContractionExpansionTester."""

    def test_init(self, contraction_tester):
        """Test tester initialization."""
        assert isinstance(contraction_tester, FeatureTester)

    def test_basic_contraction_expansion_test(self, contraction_tester):
        """Test basic contraction-expansion analysis."""
        result = contraction_tester.test('sine', length=100, freq=1.0)
        expected_keys = ['baseline_metric', 'mean_area', 'std_area',
                        'n_contractions', 'n_expansions', 'n_stable']
        assert_valid_result(result, expected_keys)

    def test_contraction_expansion_with_different_signals(self, contraction_tester):
        """Test contraction-expansion comparison."""
        result = contraction_tester.test('sine', signal2='square', length=100)
        assert_valid_result(result, ['mean_area'])

    def test_state_counts_sum_to_length(self, contraction_tester):
        """Test that state counts sum to signal length."""
        length = 100
        result = contraction_tester.test('sine', length=length, freq=1.0)
        assert_valid_result(result, ['n_contractions', 'n_expansions', 'n_stable'])

        total_states = (result['n_contractions'] +
                       result['n_expansions'] +
                       result['n_stable'])
        assert total_states == length


# ============================================================================
# TEST SIGNAL TYPES
# ============================================================================

class TestVariousSignalTypes:
    """Test testers with various signal types."""

    @pytest.mark.parametrize("signal_type", [
        'sine', 'square', 'triangle', 'sawtooth', 'random', 'gaussian'
    ])
    def test_synchronization_with_various_signals(self, sync_tester, signal_type):
        """Test synchronization with various signal types."""
        result = sync_tester.test(signal_type, length=100)
        assert_valid_result(result, ['plv'])

    @pytest.mark.parametrize("signal_type", [
        'sine', 'square', 'random', 'gaussian'
    ])
    def test_smoothness_with_various_signals(self, smoothness_tester, signal_type):
        """Test smoothness with various signal types."""
        result = smoothness_tester.test(signal_type, length=100)
        assert_valid_result(result, ['sparc'])


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_all_testers_can_run(self, sync_tester, smoothness_tester, symmetry_tester,
                                 equilibrium_tester, contraction_tester):
        """Test that all testers can run without errors."""
        testers = [
            ('sync', sync_tester),
            ('smoothness', smoothness_tester),
            ('symmetry', symmetry_tester),
            ('equilibrium', equilibrium_tester),
            ('contraction', contraction_tester)
        ]

        for name, tester in testers:
            result = tester.test('sine', length=100, freq=1.0)
            assert result is not None, f"{name} tester failed"

    def test_quiet_mode(self, sync_tester):
        """Test that quiet mode suppresses output."""
        result = sync_tester.test('sine', length=100)
        assert_valid_result(result, ['plv'])

    def test_verbose_mode(self):
        """Test that verbose mode works."""
        from tests.feature_test_cli import SynchronizationTester
        tester = SynchronizationTester(verbose=True)
        result = tester.test('sine', length=100)
        assert_valid_result(result, ['plv'])

    def test_reproducibility_with_seed(self, sync_tester):
        """Test that results are reproducible with seed."""
        np.random.seed(42)
        result1 = sync_tester.test('random', length=100, seed=42)

        np.random.seed(42)
        result2 = sync_tester.test('random', length=100, seed=42)

        assert_valid_result(result1, ['plv'])
        assert_valid_result(result2, ['plv'])
        # Results should be similar (within numerical tolerance)
        assert abs(result1['plv'] - result2['plv']) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
