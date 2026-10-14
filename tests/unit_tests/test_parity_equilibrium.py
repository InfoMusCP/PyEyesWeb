"""Parity of the core-backed Equilibrium with the preserved NumPy reference
(tests/reference/equilibrium_reference.py). Needs the compiled core: set EYESWEB_CORE_PATH (tests are skipped
otherwise)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from equilibrium_reference import EquilibriumReference  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level.equilibrium import Equilibrium  # noqa: E402


def _points(frame, left_foot_idx=0, right_foot_idx=1, barycenter_idx=2, axes=(0, 1), **_):
    """The three floor-plane points the reference takes out of a frame by index and axes: the new input."""
    return [np.asarray(frame)[index][list(axes)] for index in (left_foot_idx, right_foot_idx, barycenter_idx)]


def _feature(margin_mm=100.0, y_weight=0.5, **_):
    return Equilibrium(margin=margin_mm, y_weight=y_weight)


def _compare(frame, tol=1e-9, **params):
    points = _points(frame, **params)
    new = _feature(**params).process(*points)
    ref = EquilibriumReference(**params).compute(frame)
    if ref.status == Status.OK and (not np.isfinite(points).all() or (points[0] == points[1]).all()):
        assert new.status == Status.INVALID_INPUT  # no support vector, or NaN coordinates
        return ref
    assert new.status == ref.status
    assert new.reason == ref.reason
    assert new.valid == ref.valid
    for name in ref.valid:
        np.testing.assert_allclose(new[name], ref[name], rtol=tol, atol=tol, equal_nan=True)
    return ref


PARAMS = [{}, {"margin_mm": 10.0}, {"margin_mm": 0.0}, {"y_weight": 2.0}, {"y_weight": 0.0},
          {"margin_mm": 0.0, "y_weight": 0.0}, {"axes": (0, 2)}, {"axes": (2, 1)},
          {"left_foot_idx": 3, "right_foot_idx": 4, "barycenter_idx": 0}, {"margin_mm": -5.0}]


@pytest.mark.parametrize("params", PARAMS)
def test_random_frames(params):
    rng = np.random.default_rng(13)
    for _ in range(200):
        _compare(rng.standard_normal((5, 3)) * 100, **params)


@pytest.mark.parametrize("params", PARAMS)
def test_barycenter_near_the_support_centre(params):
    rng = np.random.default_rng(14)
    for _ in range(100):
        frame = rng.standard_normal((5, 3)) * 100
        frame[2] = (frame[0] + frame[1]) / 2 + rng.standard_normal(3) * 20
        _compare(frame, **params)


@pytest.mark.parametrize("params", PARAMS)
def test_degenerate_frames(params):
    _compare(np.zeros((5, 3)), **params)
    frame = np.tile(np.array([1.0, 2.0, 3.0]), (5, 1))
    _compare(frame, **params)
    frame[2] += [0.0, 1e-12, 0.0]
    _compare(frame, **params)
    frame[2] += [3.0, 0.0, 0.0]
    _compare(frame, **params)
    aligned = np.zeros((5, 3))
    aligned[1] = [10.0, 0.0, 0.0]
    aligned[2] = [3.0, 0.0, 0.0]
    _compare(aligned, **params)
    aligned[2] = [3.0, 1e-11, 0.0]
    _compare(aligned, **params)


@pytest.mark.parametrize("params", PARAMS)
def test_nan_inf_and_integer_frames(params):
    rng = np.random.default_rng(15)
    frame = rng.standard_normal((5, 3)) * 100
    frame[1, 0] = np.nan
    _compare(frame, **params)
    frame = rng.standard_normal((5, 3)) * 100
    frame[2, 1] = np.inf
    _compare(frame, **params)
    _compare(rng.integers(-300, 300, size=(5, 3)).astype(float), **params)


def test_inside_the_ellipse_gives_a_value():
    frame = np.array([[-100.0, 0, 0], [100.0, 0, 0], [30.0, 10.0, 0]])
    assert _compare(frame)["value"] > 0


def test_setters_reach_the_core():
    eq = Equilibrium()
    eq.margin, eq.y_weight = 30.0, 1.5
    frame = np.random.default_rng(16).standard_normal((3, 3)) * 20
    ref = EquilibriumReference(margin_mm=30.0, y_weight=1.5, axes=(0, 2)).compute(frame)
    np.testing.assert_allclose(eq.process(*_points(frame, axes=(0, 2)))["value"], ref["value"], rtol=1e-9, atol=1e-9)


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
FROZEN_PARAMS = [{}, {"margin": 10.0}, {"margin": 0.0}, {"y_weight": 2.0}, {"y_weight": 0.0}, {"margin": 0.0, "y_weight": 0.0},
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
                np.testing.assert_array_equal(np.float64([result.value, result.angle]).view(np.int64),
                                              np.float64([reference[f"{key}|value"][frame_index],
                                                          reference[f"{key}|angle"][frame_index]]).view(np.int64))
                assert recorded["value"][frame_index].view(np.int64) == np.float64(result.value).view(np.int64)
