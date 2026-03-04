import pytest
import numpy as np
from pyeyesweb.data_models.sliding_window import SlidingWindow


def test_initialization_and_properties():
    """Test valid initialization and property access."""
    window = SlidingWindow(max_length=10, n_signals=3, n_dims=2)

    assert window.max_length == 10
    assert window.n_signals == 3
    assert window.n_dims == 2
    assert len(window) == 0
    assert window.is_full is False


def test_invalid_initialization():
    """Test that invalid initializations raise errors."""
    with pytest.raises(ValueError):
        SlidingWindow(max_length=-5)
    with pytest.raises(ValueError):
        SlidingWindow(max_length=10, n_signals=0)


def test_flexible_append():
    """Test that append handles scalars, flat lists, and arrays."""
    # Test 1: Single scalar (1 node, 1 dim)
    win_scalar = SlidingWindow(max_length=5, n_signals=1, n_dims=1)
    win_scalar.append(42.0)
    assert len(win_scalar) == 1

    # Test 2: Flat list for multiple dimensions (1 node, 3 dims)
    win_flat = SlidingWindow(max_length=5, n_signals=1, n_dims=3)
    win_flat.append([1.0, 2.0, 3.0])
    assert len(win_flat) == 1

    # Test 3: Structured numpy array (2 nodes, 2 dims)
    win_arr = SlidingWindow(max_length=5, n_signals=2, n_dims=2)
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    win_arr.append(arr)
    assert len(win_arr) == 1


def test_invalid_append_shape():
    """Test that appending the wrong amount of data raises a ValueError."""
    window = SlidingWindow(max_length=5, n_signals=2, n_dims=3)  # Expects 6 values

    with pytest.raises(ValueError, match="Cannot reshape input"):
        window.append([1.0, 2.0, 3.0])  # Only provided 3 values


def test_circular_buffer_logic():
    """Test that the window accurately drops old data when full."""
    window = SlidingWindow(max_length=3, n_signals=1, n_dims=1)

    # Append 5 items to a window of size 3
    for i in range(5):
        window.append(i, timestamp=float(i))

    assert window.is_full is True
    assert len(window) == 3

    tensor, timestamps = window.to_tensor()

    # The oldest items (0, 1) should be gone.
    # Expected order: 2, 3, 4
    expected_data = np.array([[[2.0]], [[3.0]], [[4.0]]])
    expected_times = np.array([2.0, 3.0, 4.0])

    np.testing.assert_array_equal(tensor, expected_data)
    np.testing.assert_array_equal(timestamps, expected_times)


def test_to_tensor_and_to_flat_array():
    """Test that the export views format data correctly."""
    window = SlidingWindow(max_length=5, n_signals=2, n_dims=2)

    # Append two frames
    window.append([1, 2, 3, 4])  # Frame 1
    window.append([5, 6, 7, 8])  # Frame 2

    tensor, _ = window.to_tensor()
    flat, _ = window.to_flat_array()

    # Tensor should be (T=2, N=2, D=2)
    assert tensor.shape == (2, 2, 2)
    np.testing.assert_array_equal(tensor[0], [[1, 2], [3, 4]])

    # Flat should be (T=2, N*D=4)
    assert flat.shape == (2, 4)
    np.testing.assert_array_equal(flat[0], [1, 2, 3, 4])


def test_dynamic_resize_shrink():
    """Test shrinking the window retains the most recent data."""
    window = SlidingWindow(max_length=5, n_signals=1, n_dims=1)
    for i in range(5):
        window.append(i)  # [0, 1, 2, 3, 4]

    window.max_length = 3
    assert window.max_length == 3
    assert len(window) == 3
    assert window.is_full is True

    tensor, _ = window.to_tensor()
    # Should keep the newest 3 elements
    np.testing.assert_array_equal(tensor, [[[2.]], [[3.]], [[4.]]])


def test_dynamic_resize_expand():
    """Test expanding the window retains all current data."""
    window = SlidingWindow(max_length=2, n_signals=1, n_dims=1)
    window.append(0)
    window.append(1)

    window.max_length = 5
    assert window.max_length == 5
    assert len(window) == 2
    assert window.is_full is False

    tensor, _ = window.to_tensor()
    np.testing.assert_array_equal(tensor, [[[0.]], [[1.]]])


def test_reset():
    """Test that reset clears the buffer and restores NaNs."""
    window = SlidingWindow(max_length=5, n_signals=1, n_dims=1)
    window.append(10.0)
    window.append(20.0)

    assert len(window) == 2
    window.reset()

    assert len(window) == 0
    assert window.is_full is False

    # Check internal buffer is filled with NaNs again
    assert np.isnan(window._buffer).all()
    assert np.isnan(window._timestamp).all()