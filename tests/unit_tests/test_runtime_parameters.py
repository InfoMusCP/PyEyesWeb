"""Parameters change on a live feature (real time): runtime setters, window / hop, attribute forwarding, declarations."""

import numpy as np
import pytest

from pyeyesweb.analysis_primitives.periodicity import Periodicity
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.data_models import Recorder, Status
from pyeyesweb.low_level.direction_change import DirectionChange
from pyeyesweb.low_level.smoothness import SpectralArcLength
from pyeyesweb.mid_level.suddenness import Suddenness

SPEED = np.abs(np.sin(np.linspace(0, 12, 200))) + 0.1


def feed(feature, samples):
    return [feature.process([value]) for value in samples]


# -- task 1: runtime parameters
def test_core_parameter_without_property_reaches_the_block():
    feature = Periodicity(window=16)
    feature.threshold = 0.5
    assert feature.threshold == 0.5 and feature._params["threshold"] == 0.5
    assert feature._built is not None  # the block keeps running with the new value


def test_parameter_setters_reach_the_block():
    feature = SpectralArcLength(window=20, sampling_rate=50.0)
    block = feature._block
    feature.sampling_rate = 100.0
    assert feature.sampling_rate == 100.0 and feature._built is block  # live: the block is kept
    with pytest.raises(ValueError):
        feature.sampling_rate = 0.0
    assert feature.sampling_rate == 100.0


def test_unknown_public_name_raises():
    feature = SpectralArcLength(window=20, sampling_rate=50.0)
    with pytest.raises(AttributeError, match="SpectralArcLength has no parameter 'typo'"):
        feature.typo = 1
    with pytest.raises(AttributeError, match="no parameter 'use_filter'"):
        feature.use_filter = True


def test_removed_parameter():
    with pytest.raises(TypeError):
        SpectralArcLength(window=20, use_filter=True, sampling_rate=50.0)


def test_private_names_are_normal_attributes():
    feature = SpectralArcLength(window=20, sampling_rate=50.0)
    feature._scratch = 3
    assert feature._scratch == 3


def test_labels_write_after_construction_is_not_silent():
    with pytest.raises(AttributeError):
        DirectionChange(window=8).labels = ["a"]


def test_variant_feature_writes_refresh_its_caches():
    feature = Rarity(method="mode_distance", window=10)
    inputs = feature.inputs
    feature.alpha = 0.9
    assert feature.alpha == 0.9
    assert feature.inputs is not inputs
    feature.window = 12
    assert feature.window == 12
    with pytest.raises(AttributeError):
        feature.typo = 1
    with pytest.raises(AttributeError):
        feature.method = "information"


# -- task 2: window and hop
def test_window_and_hop_validate_and_keep_the_newest_samples():
    feature = SpectralArcLength(window=20, hop=5, sampling_rate=50.0)
    results = feed(feature, SPEED[:40])
    assert results[19].status != Status.WARMING_UP
    feature.window = 30
    assert feature.window == 30 and feature.hop == 5
    again = feed(feature, SPEED[:40])
    assert all(result.status == Status.WARMING_UP for result in again[:9])  # 20 samples are held: 10 more fill the window
    assert again[9].status != Status.WARMING_UP


def test_hop_validation():
    feature = SpectralArcLength(window=20, hop=5, sampling_rate=50.0)
    with pytest.raises(ValueError, match="hop <= window"):
        feature.hop = 21
    with pytest.raises(ValueError):
        feature.hop = 0
    assert feature.hop == 5


def test_window_smaller_than_hop_needs_configure():
    feature = SpectralArcLength(window=30, hop=20, sampling_rate=50.0)
    with pytest.raises(ValueError, match="window=12, hop=20"):
        feature.window = 12
    assert feature.window == 30
    feature.configure(window=12, hop=2)
    assert (feature.window, feature.hop) == (12, 2)
    with pytest.raises(ValueError):
        feature.window = 0


def test_window_change_equals_a_new_feature_fed_the_newest_samples():
    live = SpectralArcLength(window=20, hop=3, sampling_rate=50.0)
    feed(live, SPEED[:50])
    live.configure(window=30, hop=4)
    fresh = SpectralArcLength(window=30, hop=4, sampling_rate=50.0)
    for live_result, fresh_result in zip(feed(live, SPEED[50:150])[9:], feed(fresh, SPEED[30:150])[29:]):
        assert live_result == fresh_result


# -- task 4: declarations follow runtime changes
def test_real_time_scenario():
    feature = SpectralArcLength(window=20, hop=1, sampling_rate=50.0)
    recorder = Recorder(feature)
    for sample in SPEED[:30]:
        recorder.append(feature.process([sample]))
    feature.window = 25
    feature.maximum_cutoff_frequency = 10.0
    feature.sampling_rate = 100.0
    out = feed(feature, SPEED[:60])
    assert out[24].status != Status.WARMING_UP
    assert feature.maximum_cutoff_frequency == 10.0 and feature._built is not None
    new_recorder = Recorder(feature)
    new_recorder.append(out[-1])
    assert len(new_recorder) == 1


def test_inputs_follow_dims_of_mid_level_feature():
    feature = Suddenness(window=8, dims=3)
    assert feature.inputs is feature.inputs
    feature.dims = 2
    assert feature.inputs["position"].shape == (2,)


def test_core_parameter_refreshes_declarations():
    feature = DirectionChange(window=8)
    first = feature.outputs
    feature.epsilon = 0.2
    assert feature.outputs is not first and feature.outputs.names == first.names


def test_metrics_change_refreshes_outputs_and_inputs_cache():
    feature = DirectionChange(window=8, metrics=["cosine"])
    inputs = feature.inputs
    feature.metrics = ["cosine", "polygon"]
    assert feature.outputs.names == ("cosine", "polygon")
    assert feature.inputs is not inputs


# -- task 3: attribute forwarding
def test_typo_neither_builds_the_block_nor_recurses():
    feature = Periodicity(window=16)
    feature._invalidate_block()
    assert not hasattr(feature, "typo")
    assert feature._built is None


def test_underscore_names_are_not_forwarded():
    feature = Periodicity(window=16)
    assert not hasattr(feature, "_nothing")


def test_only_core_attributes_are_forwarded():
    feature = SpectralArcLength(window=20, sampling_rate=50.0)
    assert feature._process_window is not None
    assert hasattr(feature, "maximum_cutoff_frequency")


def test_buggy_property_surfaces_as_itself():
    class Buggy(Periodicity):
        @property
        def broken(self):
            return self.no_such_attribute_anywhere

    with pytest.raises(AttributeError, match="no_such_attribute_anywhere"):
        Buggy(window=16).broken


def test_typo_inside_build_block_surfaces():
    class Typo(Periodicity):
        def _build_block(self):
            return self._core_clas(**self._params)

    with pytest.raises(AttributeError, match="_core_clas"):
        Typo(window=16).process([1.0])


def test_forwarding_inside_build_block_does_not_recurse():
    class Probe(Periodicity):
        def _build_block(self):
            self.seen = getattr(self, "_process_window_missing", None)
            return super()._build_block()

    assert Probe(window=16)._block is not None


def test_inputs_is_protected():
    feature = Periodicity(window=16)
    assert feature.inputs.names == ("signal",)
