"""The tolerance for frozen float references accepts the Linux (GCC) rounding differences and still catches real ones."""
import numpy as np
import pytest

from floats import assert_same_floats, bits_to_floats, same_floats

LINUX_PAIRS = [(0.09710244150706666, 0.09710244150706668), (0.9599591866521336, 0.9599591866521338),
               (0.38208887616574266, 0.38208887616574294)]


@pytest.mark.parametrize("actual, expected", LINUX_PAIRS)
def test_last_digit_differences_are_accepted(actual, expected):
    assert_same_floats(actual, expected)
    assert_same_floats([actual, np.nan], [expected, np.nan])


def test_int64_bit_patterns_one_to_four_ulp_apart_are_accepted():
    assert_same_floats(bits_to_floats([4600969470428024608]), bits_to_floats([4600969470428024612]))
    assert_same_floats(bits_to_floats([4600147734399107266]), bits_to_floats([4600147734399107264]))


def test_real_differences_nan_positions_and_shapes_are_rejected():
    assert not same_floats(1.0, 1.0 + 1e-9)
    assert not same_floats([1.0, np.nan], [1.0, 2.0])
    assert not same_floats([1.0], [1.0, 1.0])
    with pytest.raises(AssertionError, match="Max relative difference"):
        assert_same_floats(1.0, 1.001)
