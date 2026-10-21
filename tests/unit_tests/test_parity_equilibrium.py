"""Equilibrium: input contract and frozen outputs of the frame-based feature. Needs the compiled core:
set EYESWEB_CORE_PATH (tests are skipped otherwise)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from floats import assert_same_floats  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level.equilibrium import Equilibrium  # noqa: E402


def test_inside_the_ellipse_gives_a_value():
    result = Equilibrium(units="mm").process((-100.0, 0.0), (100.0, 0.0), (30.0, 10.0))
    assert result.status == Status.OK and result["equilibrium"] > 0


def test_the_removed_parameters_are_gone():
    for name in ("axes", "left_foot_idx", "right_foot_idx", "barycenter_idx", "margin_mm"):
        with pytest.raises(TypeError):
            Equilibrium(**{name: 1})


def test_a_point_is_two_floor_coordinates():
    eq = Equilibrium()
    with pytest.raises(ValueError):
        eq.process((0, 0, 0), (1, 0), (0, 0))
    assert eq.process((0, 0), (1, 0), (np.nan, 0)).status == Status.INVALID_INPUT
    assert eq.process((), (1, 0), (0, 0)).status == Status.INVALID_INPUT
    assert eq.process((0, 0), (0, 0), (0, 0)).status == Status.INVALID_INPUT  # the feet coincide
    assert eq.inputs.names == ("left_foot", "right_foot", "barycenter")


# ------------------------------------------------------------------- frozen outputs of the frame-based feature
REFERENCE = os.path.join(os.path.dirname(__file__), "..", "data", "equilibrium_reference.npz")
FROZEN_PARAMS = [{"margin": 100.0}, {"margin": 10.0}, {"margin": 0.0}, {"margin": 100.0, "y_weight": 2.0},
                 {"margin": 100.0, "y_weight": 0.0}, {"margin": 0.0, "y_weight": 0.0},
                 {"margin": -5.0}, {"margin": 0.4, "units": "mm"}, {"margin": 100.0, "units": "mm", "y_weight": 0.3},
                 {"margin": 100.0}, {"margin": 100.0, "y_weight": 1.5}]


def _frozen_cases():
    """name -> (frames (T, 5, 3), left, right, barycenter row index, floor axes)."""
    rng = np.random.default_rng(13)
    random = rng.standard_normal((200, 5, 3)) * 100
    near = random.copy()
    near[:, 2] = (random[:, 0] + random[:, 1]) / 2 + rng.standard_normal((200, 3)) * 20
    bad = random.copy()
    bad[10, 0, 0], bad[20, 2, 1], bad[30, 4, 2] = np.nan, np.inf, np.nan  # the last one is in a joint no point uses
    coincide = random.copy()
    coincide[5, 1] = coincide[5, 0]
    coincide[6, 1, :2] = coincide[6, 0, :2]
    centred = random.copy()
    centred[:, 2] = (random[:, 0] + random[:, 1]) / 2
    return {"random": (random, 0, 1, 2, (0, 1)), "other_indices": (random, 3, 4, 0, (0, 2)), "near_centre": (near, 0, 1, 2, (0, 1)),
            "non_finite": (bad, 0, 1, 2, (0, 1)), "coincide": (coincide, 0, 1, 2, (0, 1)),
            "zeros": (np.zeros((6, 5, 3)), 0, 1, 2, (0, 1)), "centred": (centred, 0, 1, 2, (0, 1))}


def test_the_three_point_form_reproduces_the_frozen_outputs_of_the_frame_form():
    """Same numbers, bit for bit (NaN equal), for the points the old index / axes selection took out of each frame.
    One difference by design: the old feature rejected a NaN anywhere in the frame, the new one only in its points."""
    reference = np.load(REFERENCE)
    for name, (frames, left, right, bary, axes) in _frozen_cases().items():
        selected = [frames[:, index][:, list(axes)] for index in (left, right, bary)]
        for index, params in enumerate(FROZEN_PARAMS):
            key = f"{name}|{index}"
            recorded = Equilibrium(**params).run(*selected)
            feature = Equilibrium(**params)
            for frame_index, points in enumerate(zip(*selected)):
                result = feature.process(*points)
                if name == "non_finite" and frame_index == 30:
                    assert result.status == Status.OK
                    continue
                assert result.status.name == reference[f"{key}|status"][frame_index]
                assert result.reason == reference[f"{key}|reason"][frame_index]
                if result.status is Status.INVALID_INPUT:  # the old feature kept the numbers next to INVALID_INPUT; now they are empty
                    assert np.isnan([result.equilibrium, result.angle]).all() and np.isnan(recorded["equilibrium"][frame_index])
                    continue
                assert_same_floats([result.equilibrium, result.angle],
                                   [reference[f"{key}|equilibrium"][frame_index], reference[f"{key}|angle"][frame_index]])
                assert recorded["equilibrium"][frame_index].view(np.int64) == np.float64(result.equilibrium).view(np.int64)
