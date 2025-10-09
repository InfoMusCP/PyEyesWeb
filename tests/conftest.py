"""Pytest configuration and shared fixtures for tests."""
import pytest
from tests.feature_test_cli import (
    SynchronizationTester,
    SmoothnessTester,
    BilateralSymmetryTester,
    EquilibriumTester,
    ContractionExpansionTester
)


# ============================================================================
# FIXTURES FOR FEATURE TESTERS
# ============================================================================

def create_tester_fixture(tester_class):
    """Factory function to create tester fixtures."""
    @pytest.fixture
    def tester():
        return tester_class(verbose=False)
    return tester


# Create fixtures using the factory function
sync_tester = create_tester_fixture(SynchronizationTester)
smoothness_tester = create_tester_fixture(SmoothnessTester)
symmetry_tester = create_tester_fixture(BilateralSymmetryTester)
equilibrium_tester = create_tester_fixture(EquilibriumTester)
contraction_tester = create_tester_fixture(ContractionExpansionTester)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_valid_result(result, expected_keys):
    """
    Assert that a test result is valid and contains expected keys.

    Args:
        result: The result dictionary to validate
        expected_keys: List of keys that should be present
    """
    assert result is not None, "Result should not be None"
    for key in expected_keys:
        assert key in result, f"Result should contain key '{key}'"
