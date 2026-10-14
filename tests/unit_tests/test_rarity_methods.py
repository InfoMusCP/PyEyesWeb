"""Rarity: one public feature, two methods (INFORMATION = EyesWeb block, MODE_DISTANCE = windowed histogram).
Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

import pyeyesweb  # noqa: E402
from contract_suite import check_feature_contract  # noqa: E402
from pyeyesweb.analysis_primitives import Rarity, rarity as rarity_module  # noqa: E402
from pyeyesweb.analysis_primitives.rarity import _InformationRarity, _ModeDistanceRarity  # noqa: E402
from rarity_reference import HistogramRarityReference  # noqa: E402

RNG = np.random.default_rng(1)
SINE = np.sin(np.arange(120) / 5.0) + 0.1 * RNG.standard_normal(120)
PAIR = RNG.standard_normal((60, 2))


def test_contract_information():
    check_feature_contract(lambda: Rarity(method="information"), PAIR)


def test_contract_mode_distance():
    check_feature_contract(lambda: Rarity(method="mode_distance", window=20, hop=5), SINE)


def test_default_method_is_information():
    feature = Rarity()
    assert feature.method == "information"
    assert isinstance(feature, _InformationRarity)


def test_unknown_method_and_foreign_parameters_raise():
    with pytest.raises(ValueError):
        Rarity(method="nope")
    with pytest.raises((TypeError, ValueError)):
        Rarity(method="information", window=10)
    with pytest.raises((TypeError, ValueError)):
        Rarity(method="mode_distance", window=10, number_of_inputs=3)
    with pytest.raises((TypeError, ValueError)):
        Rarity(method="mode_distance", window=10, data_memory=10)


def test_inputs_and_schemas_differ_per_method():
    information = Rarity(method="information", number_of_inputs=3)
    mode = Rarity(method="mode_distance", window=4)
    assert information.inputs["signals"].shape == (3,)
    assert mode.inputs["signal"].shape == (1,)
    assert information.outputs["rarity"].shape == (3,)
    assert mode.outputs["rarity"].shape != information.outputs["rarity"].shape


def test_information_equals_private_implementation():
    wrapped = Rarity(method="information")
    direct = _InformationRarity()
    for sample in PAIR:
        assert np.array_equal(wrapped.process(sample).rarity, direct.process(sample).rarity, equal_nan=True)


def test_mode_distance_equals_private_implementation_and_reference():
    wrapped = Rarity(method="mode_distance", window=20, alpha=1.0)
    direct = _ModeDistanceRarity(window=20, alpha=1.0)
    reference = HistogramRarityReference(alpha=1.0)
    for index, sample in enumerate(SINE):
        wrapped_result, direct_result = wrapped.process(sample), direct.process(sample)
        assert wrapped_result.status is direct_result.status
        if wrapped_result.ok:
            assert wrapped_result.rarity == direct_result.rarity
            assert wrapped_result.rarity == reference.compute(SINE[index - 19:index + 1]).rarity


def test_one_public_rarity_in_the_catalog():
    assert [entry.name for entry in pyeyesweb.catalog()].count("Rarity") == 1
    assert not hasattr(rarity_module, "HistogramRarity")
    assert "_InformationRarity" not in rarity_module.__all__ and "_ModeDistanceRarity" not in rarity_module.__all__


def test_information_rarity_is_warming_up_until_the_memory_is_full_and_the_numbers_do_not_change():
    from pyeyesweb.data_models import Status
    feature = Rarity(number_of_inputs=2, data_memory=5)
    results = [feature.process(sample) for sample in np.abs(PAIR[:8]) % 1.0]
    assert [result.status for result in results] == [Status.WARMING_UP] * 4 + [Status.OK] * 4
    assert "of 5" in results[0].reason and "1 of" in results[0].reason
    core_block = pyeyesweb._core.core.motion.RarityIndex(number_of_inputs=2, data_memory=5)
    for sample, result in zip(np.abs(PAIR[:8]) % 1.0, results):
        assert np.array_equal(result.rarity, core_block.process(list(sample)))
    feature.reset()
    assert feature.process([0.1, 0.2]).status is Status.WARMING_UP
    contrast = Rarity(number_of_inputs=2, type="contrast", data_memory=5)
    assert contrast.process([0.1, 0.2]).status is Status.OK  # contrast uses no memory


def test_information_rarity_warm_up_restarts_with_a_structural_change_not_with_a_live_one():
    from pyeyesweb.data_models import Status
    feature = Rarity(number_of_inputs=2, data_memory=4)
    for _ in range(6):
        feature.process([0.1, 0.5])
    assert feature.process([0.1, 0.5]).status is Status.OK
    feature.type = "contrast"  # live
    feature.type = "rarity"
    assert feature.process([0.1, 0.5]).status is Status.OK
    feature.data_memory = 6  # structural: the memory is emptied
    assert feature.process([0.1, 0.5]).status is Status.WARMING_UP


def test_information_rarity_value_outside_the_bins_is_invalid_input_without_numbers():
    from pyeyesweb.data_models import Status
    feature = Rarity(number_of_inputs=2, data_memory=2, bins=[0.5, 0.5])
    feature.process([0.2, 0.2])
    inside = feature.process([0.9, 0.9])
    assert inside.status is Status.OK
    outside = feature.process([0.9, 1.5])
    assert outside.status is Status.INVALID_INPUT and outside.reason == "value outside the bins"
    assert np.isnan(outside.rarity).all() and not any(outside.valid.values())  # the diagnostic is the reason
    assert feature.process([np.nan, 0.2]).status is Status.INVALID_INPUT


def test_information_rarity_rejects_the_degenerate_combinations_at_construction():
    with pytest.raises(ValueError):
        Rarity(number_of_inputs=1, type="contrast")
    with pytest.raises(ValueError):
        Rarity(number_of_inputs=2, data_memory=1)
    feature = Rarity(number_of_inputs=1, data_memory=3)
    with pytest.raises(ValueError):
        feature.type = "contrast"
    assert feature.process([0.1]).status.name == "WARMING_UP"  # unchanged: still the rarity block
