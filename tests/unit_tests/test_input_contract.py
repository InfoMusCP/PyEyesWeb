"""The input / call contract (`Feature`): declared inputs, `process`, `run`, `reset`, windowing, time."""

import math

import numpy as np
import pytest

from contract_suite import check_feature_contract
from pyeyesweb.data_models import InputKind, Recorder, Status, WindowedFeature

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives import Periodicity  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    Harmonicity, KineticEnergy, LogDimensionlessJerk, SpectralArcLength, SubmovementCount)

LABELS = ["a", "b", "c"]
RNG = np.random.default_rng(0)
SKELETON = RNG.normal(size=(40, 3, 3))
SPEED = np.abs(RNG.normal(size=120)) + 1.0
SIGNAL = np.sin(2 * np.pi * np.arange(160) / 10)[:, None] + 0.05 * RNG.normal(size=(160, 1))


def _ke():
    return KineticEnergy(labels=LABELS, weights=dict.fromkeys(LABELS, 1.0),
                         input_mode="velocity")


# name -> (factory, recording)
FEATURES = {
    "KineticEnergy": (_ke, SKELETON),
    "SpectralArcLength": (lambda: SpectralArcLength(window=30, hop=7, sampling_rate=50.0), SPEED),
    "LogDimensionlessJerk": (lambda: LogDimensionlessJerk(window=30, hop=7, sampling_rate=50.0), SPEED),
    "LogDimensionlessJerk acceleration": (
        lambda: LogDimensionlessJerk(window=30, hop=7, sampling_rate=50.0, input_mode="acceleration"), SPEED),
    "Harmonicity": (lambda: Harmonicity(window=30, hop=7, sampling_rate=50.0), SPEED),
    "SubmovementCount": (lambda: SubmovementCount(window=30, hop=7, sampling_rate=50.0), SPEED),
    "Periodicity": (lambda: Periodicity(window=64, hop=16), SIGNAL),
}


@pytest.mark.parametrize("name", list(FEATURES))
def test_feature_contract_suite(name):
    factory, data = FEATURES[name]
    check_feature_contract(factory, data)


def test_windowed_features_report_warming_up_then_no_output_between_hops():
    feature = SpectralArcLength(window=30, hop=7)
    assert isinstance(feature, WindowedFeature)
    statuses = [feature.process(value).status for value in SPEED[:50]]
    assert statuses[:29] == [Status.WARMING_UP] * 29
    assert statuses[29] is Status.OK
    assert statuses[30:36] == [Status.NO_OUTPUT] * 6 and statuses[36] is Status.OK


def test_process_window_is_the_static_analysis_of_one_segment():
    feature = SpectralArcLength(window=30, hop=1, sampling_rate=50.0)
    streamed = [feature.process(value) for value in SPEED[:30]][-1]
    assert streamed.ok and streamed.spectral_arc_length == feature._process_window(SPEED[:30]).spectral_arc_length
    per = Periodicity(window=64)
    assert per._process_window(SIGNAL[:64].T).periods[0, 0] == 10


def test_window_and_hop_are_validated():
    with pytest.raises(ValueError):
        SpectralArcLength(window=10, hop=11)
    with pytest.raises(ValueError):
        SpectralArcLength(window=0)


def test_skeleton_inputs_declare_their_labels():
    (skeleton,) = _ke().inputs
    assert skeleton.kind is InputKind.POINTS and skeleton.labels == tuple(LABELS) and skeleton.shape == (3, 3)
    assert isinstance(_ke().run(SKELETON), Recorder)


class _PairWindow(WindowedFeature):
    """A two-input windowed feature, to test the plumbing of several inputs."""

    from pyeyesweb.data_models import Input, Inputs, Output, Schema
    OUTPUTS = Schema(Output("dot"))

    def _inputs(self):
        return self.Inputs(self.Input("x", InputKind.SAMPLE, (1,)), self.Input("y", InputKind.SAMPLE, (2,)))

    def _process_window(self, first, second, *, timestamp=None):
        assert first.shape == (1, self.window) and second.shape == (2, self.window)
        return self.result(dot=float(np.sum(first[0] * second[0] + second[1])), timestamp=math.nan if timestamp is None else timestamp)


def test_several_inputs_are_split_per_input_and_run_takes_one_array_each():
    feature = _PairWindow(window=4, hop=2)
    first_series, second_series = RNG.normal(size=(10, 1)), RNG.normal(size=(10, 2))
    rec = feature.run(first_series, second_series)
    expected = [float(np.sum(first_series[index - 3:index + 1, 0] * second_series[index - 3:index + 1, 0] + second_series[index - 3:index + 1, 1])) for index in (3, 5, 7, 9)]
    assert np.allclose(rec["dot"][rec.ok], expected)
    with pytest.raises(ValueError, match="2 input"):
        feature.run(first_series)
    with pytest.raises(ValueError, match="same number"):
        feature.run(first_series, second_series[:-1])


# a windowed feature fixes the size of a frame with its first frame after reset(); declared-shape features fail in
# the central check, the ones with a free shape (`(None,)`) in the buffer
@pytest.mark.parametrize("factory, frame, other", [
    (lambda: Periodicity(window=10), [1.0, 2.0], [1.0, 2.0, 3.0]),              # free shape: the buffer
    (lambda: Periodicity(window=10), [1.0, 2.0], [1.0]),
])
def test_a_frame_of_another_size_raises_and_reset_allows_a_new_size(factory, frame, other):
    feature = factory()
    for _ in range(3):
        feature.process(frame)
    with pytest.raises(ValueError, match=type(feature).__name__):
        feature.process(other)
    feature.reset()
    assert feature.process(other).status == Status.WARMING_UP


def test_the_size_error_of_the_buffer_names_the_sizes_and_the_remedy():
    feature = Periodicity(window=10)
    feature.process([1.0, 2.0])
    with pytest.raises(ValueError, match=r"expected 2 values per frame, got 3.*must not change.*reset\(\)"):
        feature.process([1.0, 2.0, 3.0])


def test_run_with_ragged_frames_raises():
    with pytest.raises(ValueError):
        Periodicity(window=10).run([[1.0, 2.0]] * 5 + [[1.0, 2.0, 3.0]] * 5)
    with pytest.raises(ValueError):
        Periodicity(window=10).run([np.ones(2), np.ones(2), np.ones(3)])


def test_a_frame_of_another_size_raises_for_a_declared_shape():
    feature = SpectralArcLength(window=10)
    feature.process(1.0)
    with pytest.raises(ValueError, match="SpectralArcLength"):
        feature.process([1.0, 2.0])


def test_run_with_ragged_data_raises_early_for_a_fixed_shape():
    with pytest.raises(ValueError):
        SpectralArcLength(window=10).run([np.ones(1)] * 3 + [np.ones(2)])
