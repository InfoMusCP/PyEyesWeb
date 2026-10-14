"""Live parameter changes of the motion blocks that come from the lab's Python library (checks in `tests/live_param_suite.py`).

Every block here is stateless, so all parameters are LIVE and the state of the wrapper (windows, hop counters) is
never touched.
"""

import numpy as np
import pytest

from live_param_suite import CHANGE_AT, NOTE, check_invalid, check_live, feed, ids

from pyeyesweb.analysis_primitives.multi_scale_entropy import MultiScaleEntropy
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.low_level.contraction import BoundingBoxFilledArea
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.low_level.equilibrium import Equilibrium
from pyeyesweb.low_level.smoothness import Harmonicity, LogDimensionlessJerk, SpectralArcLength, SubmovementCount
from pyeyesweb.low_level.symmetry import Symmetry
from pyeyesweb.mid_level.impulsivity import SuddennessImpulsivity
from pyeyesweb.mid_level.suddenness import Suddenness

_rng = np.random.default_rng(11)

POINT = list(np.cumsum(_rng.normal(size=(120, 3)), axis=0))
SCALAR = [[value] for value in np.cumsum(_rng.normal(size=120))]
SPEED = [[value] for value in np.abs(_rng.normal(size=120)) * 50]
FLOOR_POINTS = [tuple(frame[:3, :2]) for frame in [_rng.normal(size=(5, 3)) * 100 for _ in range(120)]]
CLOUDS = [_rng.normal(size=(8, 3)) for _ in range(120)]
FRAMES = [_rng.normal(size=(5, 3)) * 100 for _ in range(120)]


def reflection(**params):
    return Symmetry(method="reflection", joint_pairs=[(0, 1), (2, 3)], **params)


LIVE = [
    (lambda: BoundingBoxFilledArea(), "epsilon", 3.0, CLOUDS),
    (lambda: DirectionChange(window=10), "epsilon", 0.9, POINT),
    (lambda: Equilibrium(), "margin", 300.0, FLOOR_POINTS),
    (lambda: Rarity(window=20, method="mode_distance"), "alpha", 2.0, SCALAR),
    (lambda: SuddennessImpulsivity(window=12), "direction_change_epsilon", 0.9, POINT),
    (lambda: MultiScaleEntropy(window=40, embedding_dimension=1, max_scale=2, minimum_points=10), "tolerance", 0.3, SCALAR),
    (lambda: SpectralArcLength(window=30), "sampling_rate", 100.0, SPEED),
    (lambda: SpectralArcLength(window=30), "amplitude_threshold", 0.2, SPEED),
    (lambda: SpectralArcLength(window=30), "minimum_cutoff_frequency", 1.0, SPEED),
    (lambda: SpectralArcLength(window=30), "maximum_cutoff_frequency", 10.0, SPEED),
    (lambda: LogDimensionlessJerk(window=30), "sampling_rate", 100.0, SPEED),
    (lambda: LogDimensionlessJerk(window=30), "input_mode", "acceleration", SPEED),
    (lambda: Harmonicity(window=30), "sampling_rate", 100.0, SPEED),
    (lambda: SubmovementCount(window=30), "sampling_rate", 100.0, SPEED),
    (lambda: SubmovementCount(window=30), "prominence_factor", 0.3, SPEED),
    (lambda: reflection(), "center_of_symmetry", 2, FRAMES),
]
INVALID = [
    (lambda: MultiScaleEntropy(window=40, embedding_dimension=1, max_scale=2, minimum_points=10), "embedding_dimension", 0, SCALAR),
    (lambda: SpectralArcLength(window=30), "sampling_rate", 0.0, SPEED),
    (lambda: SpectralArcLength(window=30), "amplitude_threshold", 1.5, SPEED),
    (lambda: SpectralArcLength(window=30), "minimum_cutoff_frequency", 0.0, SPEED),
    (lambda: SpectralArcLength(window=30), "maximum_cutoff_frequency", 1.0, SPEED),
    (lambda: LogDimensionlessJerk(window=30), "sampling_rate", -1.0, SPEED),
    (lambda: LogDimensionlessJerk(window=30), "input_mode", "jerk", SPEED),
    (lambda: Harmonicity(window=30), "sampling_rate", 0.0, SPEED),
    (lambda: SubmovementCount(window=30), "sampling_rate", 0.0, SPEED),
    (lambda: SubmovementCount(window=30), "prominence_factor", -0.1, SPEED),
    (lambda: reflection(), "center_of_symmetry", -2, FRAMES),
]


def _param(rows):
    return pytest.mark.parametrize("factory, attr, value, recording", rows, ids=ids(rows))


@_param(LIVE)
def test_live_change_keeps_the_state(factory, attr, value, recording):
    check_live(factory, attr, value, recording)


@_param(INVALID)
def test_invalid_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)


def test_suddenness_algorithm_change_keeps_the_window():
    # the two algorithms differ in which windows they can fit, so the status sequence of check_live does not apply
    changed, fresh = Suddenness(window=12), Suddenness(window=12)
    fresh.algorithm = "quantile"
    feed(changed, POINT[:CHANGE_AT])
    changed.algorithm = "quantile"
    actual = feed(changed, POINT[CHANGE_AT:])
    assert all(NOTE not in result.reason for result in actual)
    assert actual == feed(fresh, POINT)[CHANGE_AT:]
