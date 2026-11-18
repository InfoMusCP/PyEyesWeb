"""Rarity(method="novelty"): how unusual the movement of the last moments is compared with the recent past.

The pattern of the last `pattern` samples is compared with the patterns of the last `memory` samples; the result is the
distance to the nearest ones relative to its median (about 1 = familiar). New in the library (design review 2026-11-17),
so the oracle is the behaviour described in the docstring, not another implementation.
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives import Rarity  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402

RATE = 60


def oscillation(seconds, frequency=1.0, amplitude=0.5, centre=0.5):
    t = np.arange(int(seconds * RATE)) / RATE
    return centre + amplitude * np.sin(2 * np.pi * frequency * t)


def make(**params):
    params.setdefault("memory", 300)
    params.setdefault("pattern", 30)
    params.setdefault("step", 2)
    return Rarity(method="novelty", **params)


def peak(recording, start, stop):
    return float(np.nanmax(np.asarray(recording.rarity)[int(start * RATE):int(stop * RATE)]))


def test_the_method_and_its_declared_inputs_and_outputs():
    feature = make()
    assert feature.method == "novelty"
    assert feature.inputs.names == ("signals",) and feature.inputs["signals"].shape == (1,)
    assert feature.outputs["rarity"].shape == ()
    assert make(number_of_inputs=3).inputs["signals"].shape == (3,)


def test_warming_up_for_the_documented_number_of_samples_then_ok():
    pattern = 10
    feature = Rarity(method="novelty", memory=90, pattern=pattern)
    record = feature.run(oscillation(5.0))
    warmup = (pattern - 1) + (2 * pattern + pattern // 2) - 1
    assert list(record.status[:warmup]) == [Status.WARMING_UP] * warmup
    assert record.status[warmup] == Status.OK and (record.status[warmup:] == Status.OK).all()


def test_a_steady_oscillation_is_familiar():
    record = make().run(oscillation(20.0))
    assert peak(record, 12, 20) < 1.5


def test_a_pause_a_new_amplitude_and_a_new_frequency_are_rare():
    steady = peak(make().run(oscillation(20.0)), 12, 13)
    paused = oscillation(20.0)
    paused[12 * RATE:12 * RATE + 30] = 0.5
    faster = oscillation(20.0)
    t = np.arange(len(faster)) / RATE
    faster[12 * RATE:] = 0.5 + 0.5 * np.sin(2 * np.pi * (12.0 + 2.0 * (t[12 * RATE:] - 12.0)))
    smaller = oscillation(20.0)
    t = np.arange(len(smaller)) / RATE
    smaller[10 * RATE:] = 0.8 + 0.2 * np.sin(2 * np.pi * t[10 * RATE:])
    assert peak(make().run(paused), 12, 13) > 3 * max(1.0, steady)
    assert peak(make().run(faster), 12, 13) > 3.0
    assert peak(make().run(smaller), 10, 11) > 3.0


def test_a_repeated_new_movement_becomes_familiar():
    signal = oscillation(30.0)
    t = np.arange(len(signal)) / RATE
    signal[10 * RATE:] = 0.8 + 0.2 * np.sin(2 * np.pi * t[10 * RATE:])
    record = make().run(signal)
    assert peak(record, 10, 11) > 3.0 and peak(record, 22, 30) < 1.5


def test_shape_ignores_where_the_movement_happens():
    t = np.arange(20 * RATE) / RATE
    centre = np.where(t >= 12.0, 5.0, 0.0)
    circle = np.column_stack([np.cos(2 * np.pi * t) + centre, np.sin(2 * np.pi * t) + centre])
    where = make(number_of_inputs=2).run(circle)
    shape = make(number_of_inputs=2, shape=True).run(circle)
    assert peak(where, 13, 15) > 3.0       # the level is part of the pattern: a new place is new
    assert peak(shape, 13, 15) < 2.0       # only the shape counts: the same circle elsewhere is familiar


def test_a_non_finite_sample_is_invalid_and_not_used():
    feature = make()
    record = feature.run(oscillation(8.0))
    assert feature.process(np.nan).status == Status.INVALID_INPUT
    assert feature.process(0.5).status == Status.OK and len(record) > 0


def test_reset_starts_the_warm_up_again():
    feature = make()
    feature.run(oscillation(8.0))
    feature.reset()
    assert feature.process(0.5).status == Status.WARMING_UP


def test_neighbours_is_live_and_the_pattern_is_structural():
    feature = make()
    feature.run(oscillation(8.0))
    feature.neighbours = 3
    assert feature.process(0.5).status == Status.OK            # the memory is kept
    feature.pattern = 20
    assert feature.process(0.5).status == Status.WARMING_UP    # the memory restarts


@pytest.mark.parametrize("params", [dict(pattern=1), dict(memory=80, pattern=30), dict(neighbours=0), dict(step=0),
                                    dict(number_of_inputs=0)])
def test_invalid_parameters_raise(params):
    with pytest.raises(ValueError):
        make(**params)


@pytest.mark.parametrize("params", [dict(bins=(0.5, 0.5)), dict(alpha=1.0), dict(window=20), dict(measure="contrast")])
def test_the_parameters_of_the_other_methods_raise(params):
    with pytest.raises(TypeError):
        Rarity(method="novelty", **params)


def test_one_sample_of_the_wrong_length_raises():
    with pytest.raises(ValueError):
        make(number_of_inputs=2).process([0.1, 0.2, 0.3])
