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
    curvature = TrajectoryNonPlanarity()
    assert curvature.outputs.names == ("curvature_radius",)
    assert curvature.process(line()).curvature_radius == pytest.approx(0, abs=1e-6)
    assert curvature.process(np.zeros((0, 3))).status is Status.INVALID_INPUT
    assert curvature.process(line(dims=2)).status is Status.INVALID_INPUT
    assert TrajectoryNonPlanarity(output_type="curvature_value").outputs.names == ("curvature",)


def test_directness_takes_no_parameters_and_is_in_the_catalog():
    from inspect import signature
    from pyeyesweb import catalog

    entries = {entry.name: entry for entry in catalog()}
    assert not signature(entries["Directness"].cls).parameters
    assert entries["Directness"].eyesweb_block == "GetTrajectoryFeatures (TrajectoryBasicFeatures)"
    with pytest.raises(TypeError):
        Directness(feature="length")
