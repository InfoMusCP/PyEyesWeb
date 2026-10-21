"""Float comparison against FROZEN reference data (produced by an earlier implementation, on another compiler / libm).

Frozen outputs come from Windows/MSVC; the same code built with GCC on Linux (libm, FMA contraction, vectorised sums)
differs in the last digits: 1-4 ulp, i.e. a relative 2e-16 to 1e-15. `assert_same_floats` accepts that and nothing more:
NaN and infinity positions and the shape must match exactly, finite values must agree to `rtol=1e-12` (about 4500 ulp,
far above platform noise, far below any real behaviour change) plus `atol=1e-14` for values that are zero up to rounding.

Do NOT use it between two runs of the same build (process versus run, loop versus recorder): that is bit-exact by contract.
Integers, statuses, reasons, counts, booleans and timestamps stay exact too.
"""
import numpy as np

RTOL = 1e-12
ATOL = 1e-14


def assert_same_floats(actual, expected, rtol=RTOL, atol=ATOL, err_msg=""):
    """Equal shape, equal NaN / infinity positions, finite values within `rtol` / `atol` (message shows the max relative difference)."""
    actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    assert actual.shape == expected.shape, f"{err_msg} shape {actual.shape} vs {expected.shape}"
    np.testing.assert_allclose(actual, expected, rtol=rtol, atol=atol, equal_nan=True, err_msg=err_msg)


def same_floats(actual, expected, rtol=RTOL, atol=ATOL):
    """Boolean form of `assert_same_floats`, for `assert same_floats(...)` and helpers that return a verdict."""
    actual, expected = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if actual.shape != expected.shape or not np.array_equal(np.isnan(actual), np.isnan(expected)):
        return False
    both = ~np.isnan(actual)
    return bool(np.allclose(actual[both], expected[both], rtol=rtol, atol=atol))


def bits_to_floats(bits):
    """The floats of int64 bit patterns (for comparing values stored as bits)."""
    return np.asarray(bits, dtype=np.int64).view(np.float64)
