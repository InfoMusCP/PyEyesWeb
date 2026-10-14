"""Call contract of the analysis primitives (all but synchronization): declared inputs, process / run / reset,
seconds, windows and `_process_window`. Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from pyeyesweb.analysis_primitives import (  # noqa: E402
    BinaryPulsesRegularity, CoarseGraining, MultiScaleEntropy, Rarity, SampleEntropy,
    ScalarPeakDetector
)
from pyeyesweb.data_models import InputKind, Status  # noqa: E402
from pyeyesweb.high_level import EnsembleDominance  # noqa: E402

RNG = np.random.default_rng(0)
SINE = np.sin(np.arange(120) / 5.0) + 0.1 * RNG.standard_normal(120)
FRAMES = RNG.standard_normal((30, 2, 2))
PAIR = RNG.standard_normal((150, 2))
PULSES = (RNG.random(80) < 0.3).astype(float)
PULSES[::4] = 1.0

FACTORIES = {
    "SampleEntropy": (lambda: SampleEntropy(window=40, hop=10, embedding_dimension=2, tolerance=0.5), SINE),
    "SampleEntropy (relative tolerance)": (lambda: SampleEntropy(window=40, hop=10, embedding_dimension=2), SINE),
    "CoarseGraining": (lambda: CoarseGraining(window=8, hop=4, factor=2), PAIR[:40]),
    "Rarity": (lambda: Rarity(method="information"), PAIR[:30]),
    "HistogramRarity": (lambda: Rarity(method="mode_distance", window=20, hop=5), SINE),
    "MultiScaleEntropy": (lambda: MultiScaleEntropy(window=100, hop=50, minimum_points=50, max_scale=2), PAIR),
    "EnsembleDominance": (lambda: EnsembleDominance(), np.abs(PAIR)),
    "ScalarPeakDetector": (lambda: ScalarPeakDetector(), SINE),
    "BinaryPulsesRegularity": (lambda: BinaryPulsesRegularity(window=12, hop=3, threshold=1), PULSES),
}


@pytest.mark.parametrize("name", FACTORIES)
def test_feature_contract(name):
    factory, recording = FACTORIES[name]
    check_feature_contract(factory, recording)


@pytest.mark.parametrize("name", [name for name in FACTORIES if name not in ("Rarity", "ScalarPeakDetector", "EnsembleDominance")])
def test_windowed_statuses_and_process_window_equal_the_stream(name):
    factory, recording = FACTORIES[name]
    feature = factory()
    streamed = [feature.process(sample) for sample in recording]
    window, hop = feature.window, feature.hop
    assert all(result.status is Status.WARMING_UP for result in streamed[:window - 1])
    ready = [index for index, result in enumerate(streamed) if result.status not in (Status.WARMING_UP, Status.NO_OUTPUT)]
    if name != "CoarseGraining":  # CoarseGraining itself skips some of the windows
        assert ready == list(range(window - 1, len(recording), hop))
    first_ready = ready[0]
    series = np.asarray(recording[first_ready - window + 1:first_ready + 1], dtype=float).reshape(window, -1).T
    direct = factory()._process_window(series)
    assert direct.status is streamed[first_ready].status
    for out in direct.schema.names:
        assert np.array_equal(direct[out], streamed[first_ready][out], equal_nan=True)


def test_declared_inputs():
    assert SampleEntropy(window=40).inputs["signal"].shape == (1,)
    assert Rarity(method="information", number_of_inputs=3).inputs["signals"].shape == (3,)
    for feature in (Rarity(method="mode_distance", window=4), ScalarPeakDetector(), CoarseGraining(window=4),
                    MultiScaleEntropy(window=3000), EnsembleDominance()):
        assert len(feature.inputs) == 1 and next(iter(feature.inputs)).kind is InputKind.SAMPLE


def test_time_is_in_seconds_and_nan_when_absent():
    for name in ("Rarity", "ScalarPeakDetector"):
        factory, recording = FACTORIES[name]
        feature = factory()
        assert np.isnan(feature.process(recording[0]).timestamp)
        assert feature.process(recording[1], timestamp=2.5).timestamp == 2.5
        assert np.allclose(factory().run(recording, timestamps=np.arange(len(recording)) * 0.5).timestamps,
                           np.arange(len(recording)) * 0.5)


def test_scalar_and_one_channel_samples_agree():
    for factory in (ScalarPeakDetector,):
        flat, column = factory().run(SINE), factory().run(SINE[:, None])
        for name in flat.schema.names:
            assert np.array_equal(flat[name], column[name])


def test_coarse_graining_no_output_semantics_are_kept():
    feature = CoarseGraining(window=4, hop=4, factor=2)
    block = [feature.process([float(index)]) for index in range(4)]
    assert [result.status for result in block[:3]] == [Status.WARMING_UP] * 3 and block[3].ok
    assert block[3].coarse_grained.shape == (1, 2)
    again = feature._process_window(np.arange(4.0)[None])  # a second activation: the block skips it
    assert again.status is Status.NO_OUTPUT and again.reason


def test_rarity_keeps_its_own_memory_until_reset():
    feature = Rarity(method="information")
    first = [feature.process(sample).rarity for sample in PAIR[:20]]
    feature.reset()
    assert np.array_equal(first, [feature.process(sample).rarity for sample in PAIR[:20]], equal_nan=True)


def test_multi_scale_entropy_window_and_invalid_input():
    feature = MultiScaleEntropy(window=100, minimum_points=100, max_scale=1)
    assert feature._process_window(PAIR[:60].T).status is Status.WARMING_UP
    assert feature._process_window(np.array([])).status is Status.INVALID_INPUT
    assert feature._process_window(np.full((1, 600), np.inf)).status is Status.INVALID_INPUT


def test_old_call_styles_are_gone():
    for feature in (Rarity(method="mode_distance", window=4), MultiScaleEntropy(window=3000), EnsembleDominance(), SampleEntropy(window=20)):
        assert not hasattr(feature, "compute")
        with pytest.raises(TypeError):
            feature(np.zeros((4, 1, 1)))
