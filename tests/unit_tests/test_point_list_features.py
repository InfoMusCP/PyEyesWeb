"""Directness and TrajectoryNonPlanarity take a list of points, an `(n, D)` array with row 0 = newest (contract checks; the
numerics are tested in C++ and frozen in `test_trajectory_parity.py`). Needs the compiled core (EYESWEB_CORE_PATH)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import Directness, TrajectoryNonPlanarity  # noqa: E402


def line(length=4, dims=3):
    points = np.zeros((length, dims))
    points[:, 0] = np.arange(length)[::-1]  # newest first
    return points


def test_directness_contract():
    directness = Directness()
    assert directness.outputs.names == ("directness_index",)
    assert directness.process(line()).directness_index == pytest.approx(1)
    assert directness.process(line(1)).status is Status.WARMING_UP
    assert directness.process(np.zeros((0, 3))).status is Status.WARMING_UP
    assert directness.process(np.ones((2, 3))).status is Status.INVALID_INPUT
    assert directness.process(line(dims=2)).directness_index == pytest.approx(1)
    assert directness.process(np.zeros((4, 4))).status is Status.INVALID_INPUT


def test_average_curvature_contract():
    curvature = TrajectoryNonPlanarity(radius=2.0)
    assert curvature.outputs.names == ("curvature_radius",)
    assert curvature.process(line()).curvature_radius == pytest.approx(0, abs=1e-6)
    assert curvature.process(np.zeros((0, 3))).status is Status.INVALID_INPUT
    assert curvature.process(line(dims=2)).status is Status.INVALID_INPUT
    with pytest.raises(TypeError):
        TrajectoryNonPlanarity(output_type="curvature_value")
    apart = np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]])  # 1 m apart, radius 0.1 m: no neighbour
    lonely = TrajectoryNonPlanarity().process(apart)
    assert lonely.status is Status.INVALID_INPUT and "nothing to fit" in lonely.reason
    assert TrajectoryNonPlanarity(radius=1.0).process(apart).status is Status.OK
    assert TrajectoryNonPlanarity(radius=0.0005, units="mm").process(apart * 1000).status is Status.INVALID_INPUT


def test_directness_takes_no_parameters_and_is_in_the_catalog():
    from inspect import signature
    from pyeyesweb import catalog

    entries = {entry.name: entry for entry in catalog()}
    assert not signature(entries["Directness"].cls).parameters
    assert entries["Directness"].eyesweb_block == "GetTrajectoryFeatures (TrajectoryBasicFeatures)"
    with pytest.raises(TypeError):
        Directness(feature="length")
