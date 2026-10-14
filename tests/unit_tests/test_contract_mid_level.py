"""The call contract (docs/user_guide/input_contract.md) on the mid-level features."""
import math
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from contract_suite import check_feature_contract  # noqa: E402

from pyeyesweb.data_models import InputKind, Status  # noqa: E402
from pyeyesweb.low_level import MotionNoiseDetector  # noqa: E402
from pyeyesweb.mid_level import (ContractionImpulsivity, GestureSegmenter, MotionDuration,  # noqa: E402
                                 Suddenness, SuddennessImpulsivity)

RNG = np.random.default_rng(0)
LABELS = ["head", "left_hand", "right_hand"]
SKELETON = np.cumsum(RNG.standard_normal((40, 3, 3)) * 0.05, axis=0)
SIGNAL = (np.sin(np.arange(60) / 4) > 0).astype(float)
ANGLE = np.abs(np.sin(np.arange(60) / 3))
DISTANCE = np.abs(np.cos(np.arange(60) / 5)) + 0.1
POSITIONS = np.cumsum(RNG.standard_normal((40, 2, 3)), axis=0)[:, 0, :]  # one point per frame: (T, dims)
VELOCITIES = RNG.standard_normal((40, 3, 3))


def test_gesture_segmenter():
    intensity = np.abs(np.sin(np.arange(60) / 4)) + (np.arange(60) > 30)
    noise = (np.arange(60) % 9 < 3).astype(float)
    check_feature_contract(lambda: GestureSegmenter(filter_window_length=5, firing_threshold=0.5), intensity, noise)
    segmenter = GestureSegmenter()
    assert segmenter.inputs.names == ("intensity", "noise")
    assert all(declared.kind is InputKind.SAMPLE for declared in segmenter.inputs)
    assert segmenter.outputs.names == ("smoothed_intensity", "is_gesturing", "is_gesture_start", "is_gesture_end")


def test_gesture_segmenter_noise_input_is_optional():
    intensity = np.abs(np.sin(np.arange(60) / 4)) + (np.arange(60) > 30)
    plain, silent = GestureSegmenter(filter_window_length=5).run(intensity), GestureSegmenter(filter_window_length=5).run(intensity, np.zeros(60))
    assert np.array_equal(plain.status, silent.status) and np.array_equal(plain["is_gesturing"], silent["is_gesturing"])
    streamed = GestureSegmenter(filter_window_length=5)
    assert [streamed.process(value).status for value in intensity] == list(plain.status)


def test_motion_noise_detector():
    check_feature_contract(lambda: MotionNoiseDetector(labels=LABELS), SKELETON)
    detector = MotionNoiseDetector(labels=LABELS)
    assert detector.inputs[0].kind is InputKind.POINTS and detector.inputs[0].labels == tuple(LABELS)
    assert detector.outputs.names == ("is_noisy",)


def test_motion_noise_detector_array_and_dict_agree_and_time_is_seconds():
    ts = np.arange(len(SKELETON)) * 0.04
    by_array = MotionNoiseDetector(labels=LABELS).run(SKELETON, timestamps=ts)
    dicts = MotionNoiseDetector(labels=LABELS)
    for index, frame in enumerate(SKELETON):
        result = dicts.process(dict(zip(LABELS, map(tuple, frame))), timestamp=ts[index])
        assert result.status == by_array.status[index] and result.timestamp == pytest.approx(ts[index])
        assert result.is_noisy == by_array["is_noisy"][index]


def test_motion_noise_detector_array_needs_labels():
    with pytest.raises(ValueError):
        MotionNoiseDetector()
    with pytest.raises(ValueError):
        MotionNoiseDetector(labels=LABELS).process(SKELETON[0][:2], timestamp=0.0)


def test_motion_duration():
    check_feature_contract(lambda: MotionDuration(), SIGNAL)
    recording = MotionDuration().run(SIGNAL)
    assert (recording.status == Status.OK).any() and (recording.status == Status.NO_OUTPUT).any()


def test_motion_duration_accepts_one_channel_columns():
    plain = MotionDuration().run(SIGNAL)
    column = MotionDuration().run(SIGNAL[:, None])
    assert np.array_equal(plain.status, column.status)


def test_contraction_impulsivity_takes_two_inputs():
    sqom, ci = np.abs(np.sin(np.arange(60) / 5)), np.abs(np.cos(np.arange(60) / 7))
    assert ContractionImpulsivity().inputs.names == ("quantity_of_motion", "contraction_index")
    check_feature_contract(ContractionImpulsivity, sqom, ci)


@pytest.mark.parametrize("make, data", [
    (lambda: Suddenness(window=20, hop=5, dims=3), POSITIONS),
    (lambda: SuddennessImpulsivity(window=20, hop=5, dims=3), POSITIONS),
])
def test_windowed_features(make, data):
    check_feature_contract(make, data)
    recording = make().run(data)
    n_windows = (len(data) - 20) // 5 + 1
    assert (recording.status == Status.OK).sum() == n_windows
    assert (recording.status[:19] == Status.WARMING_UP).all()
    # the streamed result of the last window is _process_window of that window
    feature = make()
    last = feature.run(data)
    streamed = [last[name][-1] for name in last.schema.names]
    direct = feature._process_window(data[-20:].T)
    assert [direct[name] for name in direct.schema.names] == streamed


def test_windowed_inputs_are_declared_from_the_constructor():
    assert Suddenness(window=10, dims=2).inputs[0].shape == (2,)
    assert Suddenness(window=10).inputs[0].kind is InputKind.SAMPLE
    assert Suddenness(window=10, dims=3).inputs[0].kind is InputKind.SAMPLE
    with pytest.raises(ValueError):
        Suddenness(window=10, dims=0)
    with pytest.raises(ValueError):
        Suddenness(window=10, dims=3)._process_window(np.zeros((4, 12)))


def test_process_window_stamps_the_time():
    assert Suddenness(window=10, dims=3)._process_window(POSITIONS[:10].T, timestamp=1.5).timestamp == 1.5
    assert math.isnan(Suddenness(window=10, dims=3)._process_window(POSITIONS[:10].T).timestamp)
