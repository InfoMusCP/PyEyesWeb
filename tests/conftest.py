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

@pytest.fixture
def sync_tester():
    """Fixture for SynchronizationTester with verbose=False."""
    return SynchronizationTester(verbose=False)


@pytest.fixture
def smoothness_tester():
    """Fixture for SmoothnessTester with verbose=False."""
    return SmoothnessTester(verbose=False)


@pytest.fixture
def symmetry_tester():
    """Fixture for BilateralSymmetryTester with verbose=False."""
    return BilateralSymmetryTester(verbose=False)


@pytest.fixture
def equilibrium_tester():
    """Fixture for EquilibriumTester with verbose=False."""
    return EquilibriumTester(verbose=False)


@pytest.fixture
def contraction_tester():
    """Fixture for ContractionExpansionTester with verbose=False."""
    return ContractionExpansionTester(verbose=False)


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
