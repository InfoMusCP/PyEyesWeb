"""Call contract of the geometry / path features: declared inputs, process / run / reset, seconds, labelled
and array input, lists of points as arrays. Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import math
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from pyeyesweb.data_models import InputKind  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    BodyPartsFromCurvature, ConvexHull, ContourCurvature, Directness, FilterContour, Kinematics, TrajectoryNonPlanarity
)
from pyeyesweb.mid_level import PositionDependingPotentials, RegionDependingPotentials
from pyeyesweb.physical_signals import HitCellDetector  # noqa: E402

RNG = np.random.default_rng(0)
FRAME_COUNT = 12
LABELS = ["a", "b", "c", "d"]
SKELETON = RNG.standard_normal((FRAME_COUNT, 4, 3))
ANGLES = np.linspace(0, 2 * math.pi, 8, endpoint=False)
CIRCLE = np.stack([np.cos(ANGLES), np.sin(ANGLES)], axis=1)
CONTOURS = np.round(10 * (CIRCLE + 0.1 * RNG.standard_normal((FRAME_COUNT, 8, 2))))  # integer-valued, as the default hull wants
CURVATURES = RNG.choice([-1.0, 1.0], size=(FRAME_COUNT, 8))
UNIT_POINTS = RNG.uniform(0, 0.99, size=(FRAME_COUNT, 3, 2))
CELLS = RNG.integers(0, 3, size=(FRAME_COUNT, 4, 2)).astype(float)
POINT_2D = RNG.standard_normal((40, 2)).cumsum(axis=0)
TRAJECTORIES = RNG.standard_normal((FRAME_COUNT, 5, 3))

FACTORIES = {
    "FilterContour": (lambda: FilterContour(), CONTOURS),
    "HitCellDetector": (lambda: HitCellDetector(cells_along_x=4, cells_along_y=4, x_max=1.0, y_max=1.0), UNIT_POINTS),
    "ContourCurvature": (lambda: ContourCurvature(), CONTOURS),
    "ConvexHull": (lambda: ConvexHull(), CONTOURS),
    "BodyPartsFromCurvature": (lambda: BodyPartsFromCurvature(minimum_distance=1), CURVATURES, CONTOURS),
    "Kinematics": (lambda: Kinematics(dims=2), POINT_2D),
    "Kinematics several outputs": (lambda: Kinematics(dims=2, output_type=["velocity", "direction", "curvature"]), POINT_2D),
    "Directness": (lambda: Directness(), TRAJECTORIES),
    "TrajectoryNonPlanarity": (lambda: TrajectoryNonPlanarity(), TRAJECTORIES),
    "PositionDependingPotentials": (lambda: PositionDependingPotentials(cells_along_x=3, cells_along_y=3), CELLS),
    "RegionDependingPotentials": (lambda: RegionDependingPotentials(cells_along_x=3, cells_along_y=3,
                                                                    number_of_regions=3), CELLS),
}


@pytest.mark.parametrize("name", list(FACTORIES))
def test_contract(name):
    factory, *data = FACTORIES[name]
    check_feature_contract(factory, *data)


def test_declared_inputs():
    assert FilterContour().inputs["contour"].kind is InputKind.POINTS
    assert BodyPartsFromCurvature().inputs.names == ("curvature", "contour")
    assert Kinematics(dims=2).inputs["point"].kind is InputKind.SAMPLE
    assert Directness().inputs["points"].shape == (None, None)
    regions = RegionDependingPotentials(input_kind="hit_regions")
    assert regions.inputs.names == ("regions",) and regions.inputs[0].kind is InputKind.SAMPLE


def test_time_is_seconds_and_nan_when_absent():
    kin = Kinematics(dims=1)
    assert math.isnan(kin.process([0.0]).timestamp)
    assert kin.process([0.0], timestamp=1.5).timestamp == 1.5
    assert HitCellDetector().process(UNIT_POINTS[0], timestamp=0.25).timestamp == 0.25
    assert Directness().process(TRAJECTORIES[0], timestamp=2.0).timestamp == 2.0
    with pytest.raises(TypeError):
        kin.process([0.0], 1.0)  # t is keyword-only


def test_run_matches_streamed_kinematics_with_timestamps():
    ts = np.arange(len(POINT_2D)) * 0.02
    block = Kinematics(dims=2)
    recorded = block.run(POINT_2D, timestamps=ts)
    block.reset()
    streamed = [block.process(point, timestamp=timestamp).velocity for point, timestamp in zip(POINT_2D, ts)]
    assert np.allclose(recorded["velocity"], streamed) and np.allclose(recorded.timestamps, ts)


def test_kinematics_series_mode():
    block = Kinematics(dims=2, input_mode="time_series")
    result = block.process(POINT_2D[:30].T, timestamp=0.5)
    assert result.ok and result.timestamp == 0.5
