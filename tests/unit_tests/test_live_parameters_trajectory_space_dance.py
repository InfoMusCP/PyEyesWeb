"""Live parameter changes of the kinematics, space and dance blocks (checks in `tests/live_param_suite.py`).

* Kinematics: the filter, the output type (one or a list), the dimension and the input mode are STRUCTURAL; the movement threshold
  is LIVE.
* TrajectoryNonPlanarity and HitCellDetector keep no state and take any parameter on the next call: LIVE only.
* Potentials: the kernel parameters and the factors are LIVE (the potential is kept; InPercentage rescales it); the grid,
  the potential type, the region count / input kind and the initial values are STRUCTURAL.
* Dance: the thresholds and the repetitions are LIVE; the buffer length of ScalarPeakDetector is STRUCTURAL.

A parameter that is stored in the state is changed where that state is still empty (the recordings are flat before the
change), so that "built with the new value" is comparable.
"""

import numpy as np
import pytest

from live_param_suite import NOTE, check_invalid, check_live, check_structural, feed, ids

from pyeyesweb.analysis_primitives.signal_events import ScalarPeakDetector
from pyeyesweb.low_level.kinematics import Kinematics
from pyeyesweb.low_level import TrajectoryNonPlanarity
from pyeyesweb.mid_level.space_occupation import PositionDependingPotentials, RegionDependingPotentials
from pyeyesweb.physical_signals.space import HitCellDetector

_rng = np.random.default_rng(11)
SAMPLE_COUNT = 120

PATH3 = np.cumsum(_rng.normal(size=(SAMPLE_COUNT + 6, 3)), axis=0)
TRAJECTORIES = [PATH3[start:start + 6][::-1] for start in range(SAMPLE_COUNT)]  # row 0 = newest point
POINTS3 = list(PATH3[:SAMPLE_COUNT])
HITS = [_rng.uniform(0, 1, size=(2, 2)) for _ in range(SAMPLE_COUNT)]  # (x, y) points of the unit square
CELLS = [np.array([[_rng.integers(0, 4), _rng.integers(0, 4)]]) for _ in range(SAMPLE_COUNT)]
REGION_CELLS = [np.array([[0, _rng.integers(0, 4)]]) for _ in range(SAMPLE_COUNT)]
PEAK_SIGNAL = [0.0] * 60 + list(np.sin(np.linspace(0, 8 * np.pi, SAMPLE_COUNT - 60)))

CURVATURE = "curvature"
_GRID = dict(cells_along_x=4, cells_along_y=4)


def kinematics(**params):
    return Kinematics(dims=3, **{"output_type": CURVATURE, **params}, filter_window_length=7)


LIVE = [
    (lambda: kinematics(), "movement_threshold", 0.5, POINTS3),
    (lambda: kinematics(output_type=["velocity", CURVATURE]), "movement_threshold", 0.5, POINTS3),
    (lambda: TrajectoryNonPlanarity(), "radius", 50.0, TRAJECTORIES),
    (lambda: HitCellDetector(cells_x=4, cells_y=4), "x_max", 2.0, HITS),
    (lambda: PositionDependingPotentials(potential_type="gaussian", **_GRID),
     "std_dev_x", 2.0, CELLS),
    (lambda: RegionDependingPotentials(**_GRID), "output_region_values", True, CELLS),
    (lambda: ScalarPeakDetector(buffer_length=5, threshold=0.01), "threshold", 0.5, PEAK_SIGNAL),
]
STRUCTURAL = [
    (lambda: kinematics(), "filter_polyorder", 4, POINTS3),
    (lambda: kinematics(), "output_type", ["velocity", "acceleration"], POINTS3),
    (lambda: kinematics(output_type=["velocity", "acceleration"]), "output_type", "jerk", POINTS3),
    (lambda: PositionDependingPotentials(**_GRID), "potential_type", "gaussian", CELLS),
    (lambda: RegionDependingPotentials(**_GRID), "potential_type", "occupation_rates_linear",
     REGION_CELLS),
    (lambda: ScalarPeakDetector(buffer_length=5), "buffer_length", 7, PEAK_SIGNAL),
]
INVALID = [
    (lambda: kinematics(), "filter_window_length", 3, POINTS3),
    (lambda: kinematics(), "output_type", ["velocity", "velocity"], POINTS3),
    (lambda: kinematics(), "output_type", ["velocity", "nonsense"], POINTS3),
    (lambda: TrajectoryNonPlanarity(radius=100.0), "radius", -1.0, TRAJECTORIES),
    (lambda: HitCellDetector(cells_x=4, cells_y=4), "cells_x", 0, HITS),
    (lambda: PositionDependingPotentials(**_GRID), "cells_along_x", 0, CELLS),
    (lambda: RegionDependingPotentials(num_of_regions=10, **_GRID), "num_of_regions", 0, CELLS),
    (lambda: ScalarPeakDetector(buffer_length=5), "buffer_length", 0, PEAK_SIGNAL),
]


def _param(rows):
    return pytest.mark.parametrize("factory, attr, value, recording", rows, ids=ids(rows))


@_param(LIVE)
def test_live_change_keeps_the_state(factory, attr, value, recording):
    check_live(factory, attr, value, recording)


@_param(STRUCTURAL)
def test_structural_change_restarts_and_says_so_once(factory, attr, value, recording):
    check_structural(factory, attr, value, recording)


@_param(INVALID)
def test_invalid_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)


def test_potential_in_percentage_rescales_the_occupation_rates_and_keeps_them():
    rates = "occupation_rates"
    feature = PositionDependingPotentials(potential_type=rates, in_percentage=True, **_GRID)
    control = PositionDependingPotentials(potential_type=rates, in_percentage=False, **_GRID)
    feed(feature, CELLS[:20])
    feed(control, CELLS[:20])
    feature.in_percentage = False
    after = feed(feature, CELLS[20:40])
    assert all(NOTE not in outcome.reason for outcome in after)
    for result, expected in zip(after, feed(control, CELLS[20:40])):
        assert result.potential == pytest.approx(expected.potential, abs=1e-9)  # the scaled state, not a restart


def test_region_mask_change_keeps_the_region_values():
    feature = RegionDependingPotentials(output_region_values=True, mask=np.zeros((4, 4), dtype=int), **_GRID)
    feed(feature, CELLS[:20])
    before = feature.process(CELLS[20]).region_values.copy()
    feature.mask = np.arange(16).reshape(4, 4) % 10
    after = feature.process(CELLS[21])
    assert NOTE not in after.reason and after.region_values[0] != 0 and (after.region_values != before).any()
