"""Work package J-b: a reset is not a parameter change (B2), errors of the core name the public parameters (B3), the
recorder keeps the reason of every row (B5), `run` takes a sequence of dict frames (B17)."""

import re

import numpy as np
import pytest

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from test_contract_all_features import NAMES, factory_and_recordings  # noqa: E402
from test_live_validation_all_features import ACCEPTS_NEGATIVE, CASES  # noqa: E402

from pyeyesweb.data_models import Output, Recorder, Schema  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    Kinematics, KineticEnergy, MotionNoiseDetector, PointsDensity, SpectralArcLength, Symmetry
)

# core messages that name no parameter at all (the check says what is wrong in words)
UNNAMED = {"EventSynchronizationMECS.number_of_inputs", "SpikeSynchronization.number_of_inputs"}
CAMEL = re.compile(r"\b[a-z]+[A-Z]\w*")


def _loop(feature, recordings):
    return [feature.process(*(recording[index] for recording in recordings)) for index in range(len(recordings[0]))]


# -- B2
@pytest.mark.parametrize("name", NAMES)
def test_the_first_call_after_a_reset_never_reports_a_parameter_change(name):
    factory, recordings = factory_and_recordings(name)
    feature = factory()
    for index in range(min(len(recordings[0]), 6)):
        feature.process(*(recording[index] for recording in recordings))
    feature.reset()
    for index in range(3):
        result = feature.process(*(recording[index] for recording in recordings))
        assert "parameters changed" not in result.reason


def test_kinematics_reset_then_process_has_no_reason_and_a_structural_change_still_has():
    feature = Kinematics(sampling_rate=100.0)
    for index in range(10):
        feature.process((float(index), 0.0), timestamp=0.01 * index)
    feature.reset()
    assert feature.process((0.0, 0.0), timestamp=0.0).reason == ""
    for index in range(10):
        feature.process((float(index), 0.0), timestamp=0.01 * index)
    feature.filter_window_length = 9
    assert feature.process((0.0, 0.0), timestamp=0.2).reason.startswith("parameters changed: state reset")


# -- B3
def test_a_setter_error_names_the_public_parameter():
    feature = SpectralArcLength(sampling_rate=100.0)
    with pytest.raises(ValueError, match="amplitude_threshold must be in"):
        feature.amplitude_threshold = -1.0
    with pytest.raises(ValueError, match="amplitude_threshold"):
        SpectralArcLength(sampling_rate=100.0, amplitude_threshold=-1.0)


@pytest.mark.parametrize("name, parameter", [case.values[:2] for case in CASES if case.values[1] not in ACCEPTS_NEGATIVE],
                         ids=[case.id for case in CASES if case.values[1] not in ACCEPTS_NEGATIVE])
def test_core_errors_name_public_parameters(name, parameter):
    if f"{name}.{parameter}" in UNNAMED:
        pytest.skip("the core message names no parameter")
    factory, recordings = factory_and_recordings(name)
    feature = factory()
    feature.process(*(recording[0] for recording in recordings))
    with pytest.raises(ValueError) as caught:
        setattr(feature, parameter, -1)
    message = str(caught.value)
    assert not CAMEL.search(message), message
    assert parameter in message or "must" in message or "positive" in message


# -- B5
def test_recorder_reasons_in_every_path():
    feature = Kinematics()
    data = np.array([[0.0, 0], [1, 0], [np.nan, 0], [3, 0]])
    rec = feature.run(data, timestamps=[0.0, 0.01, 0.02, 0.03])
    loop = Kinematics()
    expected = [loop.process(row, timestamp=0.01 * index).reason for index, row in enumerate(data)]
    assert rec.reasons == expected and any(expected)
    assert [rec[index].reason for index in range(4)] == expected
    frame = rec.to_frame()
    assert list(frame.columns)[:3] == ["status", "reason", "timestamp"]
    assert frame["reason"].tolist() == expected
    assert "reason" not in rec.to_frame(meta=False).columns


def test_recorder_append_extend_run_and_from_arrays_store_reasons():
    schema = Schema(Output("x"))
    make = schema.result_type("R")
    from pyeyesweb.data_models import Status
    rec = Recorder(schema)
    rec.append(make(schema, {"x": 1.0}, Status.OK, "a"))
    rec.extend([make(schema, {"x": 2.0}, Status.OK, "b")])
    rec.run(lambda value: make(schema, {"x": value}, Status.OK, str(value)), [3.0])
    assert rec.reasons == ["a", "b", "3.0"] and len(rec.reasons) == len(rec)
    arrays = Recorder.from_arrays(schema, {"x": [1.0, 2.0]}, reasons=["p", ""])
    assert arrays.reasons == ["p", ""] and arrays[0].reason == "p" and arrays.to_frame()["reason"].tolist() == ["p", ""]
    assert Recorder.from_arrays(schema, {"x": [1.0]}).reasons == [""]
    with pytest.raises(ValueError):
        Recorder.from_arrays(schema, {"x": [1.0]}, reasons=["a", "b"])


@pytest.mark.parametrize("name", NAMES)
def test_run_reasons_equal_the_reasons_of_the_process_loop(name):
    factory, recordings = factory_and_recordings(name)
    feature = factory()
    expected = [result.reason for result in _loop(feature, recordings)]
    feature = factory()
    assert feature.run(*recordings).reasons == expected


# -- B17
LABELS = ["a", "b", "c", "d"]


def _dicts(array):
    return [dict(zip(LABELS, frame)) for frame in array]


@pytest.mark.parametrize("make", [
    lambda: KineticEnergy(labels=LABELS, weights={label: 1.0 for label in LABELS}, sampling_rate=50.0),
    lambda: MotionNoiseDetector(labels=LABELS, sampling_rate=50.0),
    lambda: Symmetry(labels=LABELS, pairs=[("a", "b")]),
    lambda: PointsDensity(labels=LABELS),
], ids=["KineticEnergy", "MotionNoiseDetector", "Symmetry", "PointsDensity"])
def test_run_takes_a_sequence_of_dict_frames_like_a_loop_of_process(make):
    frames = np.random.default_rng(3).standard_normal((12, 4, 3))
    by_dict = make().run(_dicts(frames))
    by_array = make().run(frames)
    looped = make()
    for index, frame in enumerate(_dicts(frames)):
        result = looped.process(frame)
        assert by_dict.reasons[index] == result.reason
        for output in by_dict.schema.fixed_outputs:
            np.testing.assert_allclose(by_dict.column(output.name)[index], getattr(result, output.name), equal_nan=True)
    for output in by_dict.schema.fixed_outputs:
        np.testing.assert_allclose(by_dict.column(output.name), by_array.column(output.name), equal_nan=True)


def test_run_with_dict_frames_on_a_feature_that_takes_none_is_a_clear_error():
    with pytest.raises(ValueError, match="array in label order"):
        Kinematics().run([{"a": 1.0}, {"a": 2.0}])
