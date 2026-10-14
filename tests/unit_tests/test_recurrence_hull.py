"""Output contract of RecurrencePlot, CrossRecurrencePlot and ConvexHull (ports of EyesWeb blocks).

The numerical behaviour is tested in C++ alongside the core; these tests check schemas, statuses, shapes, dtypes,
defaults and that the parameters reach the core. Skipped without the compiled core (see
test_blocks.py for how it is found).
"""
import math
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives.synchronization import CrossRecurrencePlot, RecurrencePlot  # noqa: E402
from pyeyesweb.data_models.results import Result, Schema, Status  # noqa: E402
from pyeyesweb.low_level import ConvexHull  # noqa: E402


def test_recurrence_plot_contract_and_values():
    block = RecurrencePlot(window=4)
    assert isinstance(block.outputs, Schema) and block.outputs["plot"].shape == (None, None)
    result = block._process_window(np.array([[0.0, 0.5, 1.0, 3.0]]))
    assert isinstance(result, Result) and result.status is Status.OK and result.valid == {"plot": True}
    assert result.plot.shape == (4, 4) and np.issubdtype(result.plot.dtype, np.floating)
    np.testing.assert_array_equal(result.plot, np.eye(4))  # |0 - 0.5| == epsilon is not a recurrence


def test_recurrence_plot_multichannel_order():
    states = np.array([[0.0, 1.0, 3.0], [0.0, 1.0, 0.0]])  # (channels, samples)
    euclidean = RecurrencePlot(window=3, order=2, epsilon=1.5)._process_window(states).plot
    l1 = RecurrencePlot(window=3, order=1, epsilon=1.5)._process_window(states).plot
    assert euclidean[0, 1] == 1 and l1[0, 1] == 0  # Euclidean 1.41 vs L1 2
    infinity = RecurrencePlot(window=3, order=math.inf, epsilon=2.1)._process_window(states).plot
    assert infinity[1, 2] == 1


def test_recurrence_plot_multiple_epsilons():
    block = RecurrencePlot(window=3, use_multiple_epsilons=True, multiple_epsilons=[1.5, 0.0, 1.0])
    np.testing.assert_array_equal(block._process_window(np.array([[0.0, 1.0, 2.0]])).plot,
                                  [[1, 1, 0], [0, 0, 0], [0, 0, 1]])
    with pytest.raises(ValueError):
        block._process_window(np.arange(4.0)[None])  # 3 epsilons for 4 samples
    with pytest.raises(ValueError):
        RecurrencePlot(window=3, epsilon=-1)


def test_cross_recurrence_plot_shapes():
    block = CrossRecurrencePlot(window=2)
    assert block.outputs["plot"].shape == (None, None)
    first_series, second_series = np.array([[0.0, 10.0]]), np.array([[0.0, 10.0, 0.0]])  # (channels, samples); lengths may differ
    result = block._process_window(first_series, second_series)
    assert result.status is Status.OK and result.plot.shape == (2, 3)
    np.testing.assert_array_equal(result.plot, [[1, 0, 1], [0, 1, 0]])
    assert CrossRecurrencePlot(window=2)._process_window(second_series, first_series).plot.shape == (3, 2)
    with pytest.raises(ValueError):
        block._process_window(np.zeros((2, 3)), np.zeros((1, 3)))


def test_convex_hull_contract_and_convention():
    block = ConvexHull()
    assert block.outputs["hull"].shape == (None, 2)
    result = block.process([(10, 0), (5, 5), (0, 10), (10, 10), (0, 0)])
    assert result.status is Status.OK and result.valid == {"hull": True}
    np.testing.assert_array_equal(result.hull, [[0, 0], [0, 10], [10, 10], [10, 0]])
    np.testing.assert_array_equal(block.process([(2, 2), (0, 0), (1, 1)]).hull, [[0, 0], [2, 2]])


def test_convex_hull_real_coordinates_are_exact():
    pts = [(0.0015, 0.0), (1.23456, 0.0), (0.5, 0.99999)]
    exact = ConvexHull(integer_coordinates=False)
    np.testing.assert_array_equal(exact.process(pts).hull, [[0.0015, 0.0], [0.5, 0.99999], [1.23456, 0.0]])
    with pytest.raises(ValueError):
        ConvexHull().process([(0.5, 0.0)])  # integer coordinates


def test_convex_hull_empty_contour_is_invalid_input():
    result = ConvexHull().process([])
    assert result.status is Status.INVALID_INPUT and result.reason
    assert result.valid == {"hull": False} and result.hull.shape == (0, 2)
