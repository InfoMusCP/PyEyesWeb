"""Declared inputs are enforced: a wrongly shaped sample raises `ValueError` instead of being silently misread."""

import numpy as np
import pytest

from pyeyesweb.analysis_primitives import CorrelationsMatrix, EventSynchronization
from pyeyesweb.data_models import Input, InputKind, Status
from pyeyesweb.low_level import (BodyPartsFromCurvature, ConvexHull, ContourCurvature, FilterContour, KineticEnergy,
                                 PointsDensity)
from pyeyesweb.low_level import MotionNoiseDetector
from pyeyesweb.mid_level import (GestureSegmenter, PositionDependingPotentials,
                                 Suddenness, SuddennessImpulsivity)
from pyeyesweb.physical_signals import HitCellDetector

LABELS = ["a", "b", "c"]
WEIGHTS = {label: 1.0 for label in LABELS}
RNG = np.random.default_rng(0)
CONTOUR = RNG.normal(size=(40, 2))
SKELETON = RNG.normal(size=(3, 3))


def _suddenness():
    return Suddenness(window=8, dims=2)


def _impulsivity():
    return SuddennessImpulsivity(window=8, dims=2)


# (feature factory, wrong sample(s) per input, name of the offending input)
WRONG = [
    (lambda: FilterContour(), [RNG.normal(size=(40, 3))], "contour"),
    (lambda: FilterContour(), [RNG.normal(size=(40, 1))], "contour"),
    (lambda: FilterContour(), [RNG.normal(size=80)], "contour"),
    (lambda: ContourCurvature(), [RNG.normal(size=(40, 3))], "contour"),
    (lambda: ContourCurvature(), [RNG.normal(size=(40, 1))], "contour"),
    (lambda: ContourCurvature(), [RNG.normal(size=80)], "contour"),
    (lambda: ConvexHull(), [RNG.normal(size=(40, 3))], "contour"),
    (lambda: ConvexHull(), [RNG.normal(size=80)], "contour"),
    (lambda: HitCellDetector(), [RNG.normal(size=(5, 3))], "points"),
    (lambda: PositionDependingPotentials(), [np.ones((4, 3))], "cells"),
    (lambda: MotionNoiseDetector(labels=LABELS), [SKELETON[:2]], "skeleton"),
    (lambda: GestureSegmenter(filter_window_length=5), [np.zeros(2)], "intensity"),
    (lambda: KineticEnergy(labels=LABELS, weights=WEIGHTS), [SKELETON[:2]], "skeleton"),
    (lambda: KineticEnergy(labels=LABELS, weights=WEIGHTS), [SKELETON[:, :2]], "skeleton"),
    (_suddenness, [RNG.normal(size=(2, 3))], "position"),
    (_impulsivity, [RNG.normal(size=(2, 3))], "position"),
    (lambda: EventSynchronization(window=8), [np.array([1.0, 0.0]), 0.0], "first_signal"),
    (lambda: CorrelationsMatrix(window=8, number_of_inputs=3), [np.ones(4)], "signals"),
]


@pytest.mark.parametrize("make, wrong, name", WRONG)
def test_a_wrongly_shaped_sample_raises_naming_feature_and_input(make, wrong, name):
    feature = make()
    args = list(wrong)
    if len(feature.inputs) > len(args):
        args += [np.zeros(1)] * (len(feature.inputs) - len(args))
    with pytest.raises(ValueError) as error:
        feature.process(*args)
    assert type(feature).__name__ in str(error.value) and f"'{name}'" in str(error.value)


def test_curvature_and_contour_of_different_lengths_raise():
    feature = BodyPartsFromCurvature()
    with pytest.raises(ValueError, match="BodyPartsFromCurvature"):
        feature.process(np.zeros(30), CONTOUR)
    assert feature.process(np.zeros(len(CONTOUR)), CONTOUR).status is Status.OK


def test_multi_input_features_check_each_input():
    feature = BodyPartsFromCurvature()
    with pytest.raises(ValueError, match="'contour'"):
        feature.process(np.zeros(40), RNG.normal(size=(40, 3)))
    with pytest.raises(ValueError, match="'curvature'"):
        feature.process(np.zeros((40, 2)), CONTOUR)
    sync = EventSynchronization(window=8)
    with pytest.raises(ValueError, match="'second_signal'"):
        sync.process(1.0, np.array([1.0, 2.0]))


def test_frames_are_checked_before_the_buffer_flattens_them():
    # a (3, 2) frame of signals would flatten to 6 channels, and a (3,) point is another dimension: both are shape errors
    feature = _suddenness()
    for _ in range(3):
        feature.process(RNG.normal(size=2))
    for wrong in (RNG.normal(size=(3, 2)), RNG.normal(size=3)):
        with pytest.raises(ValueError, match="Suddenness"):
            feature.process(wrong)


def test_process_window_checks_the_channels_of_a_fixed_input():
    with pytest.raises(ValueError, match="CorrelationsMatrix"):
        CorrelationsMatrix(window=8, number_of_inputs=3)._process_window(np.ones((4, 8)))
    with pytest.raises(ValueError, match="Suddenness"):
        _suddenness()._process_window(np.ones((5, 8)))   # 5 channels are not 2 coordinates
    assert CorrelationsMatrix(window=8, number_of_inputs=3)._process_window(RNG.normal(size=(3, 8))).ok


def test_run_with_a_mis_shaped_recording_raises_before_looping():
    feature = ContourCurvature()
    with pytest.raises(ValueError, match="ContourCurvature"):
        feature.run(RNG.normal(size=(5, 40, 3)))
    ke = KineticEnergy(labels=LABELS, weights=WEIGHTS)
    with pytest.raises(ValueError, match="KineticEnergy"):
        ke.run(RNG.normal(size=(5, 2, 3)))
    # nothing was processed: a mis-shaped recording does not leave a half-fed state behind
    seen = []
    feature = ConvexHull()
    feature.process = lambda *args, **kwargs: seen.append(1)
    with pytest.raises(ValueError):
        feature.run(np.ones((5, 4, 3)))
    assert not seen


# ----------------------------------------------------------------------------------------- valid input still works

def test_valid_inputs_of_every_kind_are_accepted():
    assert ContourCurvature().process(CONTOUR).status is Status.OK
    assert ConvexHull().process(np.round(CONTOUR * 10)).status is Status.OK
    assert KineticEnergy(labels=LABELS, weights=WEIGHTS).process(SKELETON).status is Status.OK
    suddenness = _suddenness()
    results = [suddenness.process(RNG.normal(size=2)) for _ in range(8)]
    assert results[-1].status in (Status.OK, Status.NO_OUTPUT)
    # a scalar sample, a vector sample
    assert EventSynchronization(window=8).process(1.0, np.array([0.0])).status in (Status.OK, Status.WARMING_UP)
    assert CorrelationsMatrix(window=4, number_of_inputs=3).process(np.ones(3)).status is Status.WARMING_UP


@pytest.mark.parametrize("make", [ContourCurvature, ConvexHull, FilterContour, HitCellDetector,
                                  lambda: PointsDensity()])
def test_empty_frames_still_reach_the_feature(make):
    feature = make()
    for empty in (np.zeros((0, 2)), np.zeros(0), []):
        result = feature.process(empty)       # no ValueError: emptiness is data, not shape
        assert result.status in (Status.INVALID_INPUT, Status.NO_OUTPUT, Status.OK)
    assert ConvexHull().process(np.zeros((0, 2))).status is Status.INVALID_INPUT


def test_dict_inputs_are_still_accepted():
    skeleton = {label: tuple(point) for label, point in zip(LABELS, SKELETON)}
    assert KineticEnergy(weights=WEIGHTS).process(skeleton).status is Status.OK
    assert PointsDensity().process(skeleton).status is Status.OK
    assert MotionNoiseDetector(labels=LABELS).process(skeleton, timestamp=0.0).status is Status.OK


# ------------------------------------------------------------------------------------------------- the rules

@pytest.mark.parametrize("kind, shape, labels, good, bad", [
    (InputKind.SAMPLE, (3,), None, [np.ones(3)], [np.ones(2), np.ones((1, 3)), np.ones((3, 1)), 1.0]),
    (InputKind.SAMPLE, (1,), None, [1.0, np.ones(1), np.float64(2)], [np.ones(2), np.ones((1, 1))]),
    (InputKind.SAMPLE, (None,), None, [1.0, np.ones(7)], [np.ones((2, 2))]),
    (InputKind.POINTS, (None, 3), None, [np.ones((5, 3)), np.ones((1, 3))], [np.ones(3), np.ones((5, 2)),
                                                                              np.ones((2, 5, 3))]),
    (InputKind.POINTS, (None, 3), ("a", "b"), [np.ones((2, 3))], [np.ones((3, 3)), np.ones((1, 3))]),
    (InputKind.POINTS, (4, 2), None, [np.ones((4, 2))], [np.ones((3, 2)), np.ones((4, 3))]),
    (InputKind.MATRIX, (2, None), None, [np.ones((2, 5))], [np.ones((3, 5)), np.ones(5)]),
])
def test_rules_per_kind(kind, shape, labels, good, bad):
    declared = Input("x", kind, shape, labels)
    for value in good:
        declared.check(value, "Owner")
    for value in bad:
        with pytest.raises(ValueError, match="Owner: input 'x' expects"):
            declared.check(value, "Owner")
    declared.check(np.zeros((0, 3)), "Owner")      # empty: the feature reports it
    with pytest.raises(ValueError, match="numeric"):
        declared.check("abc", "Owner")


def test_accepts_passes_the_extra_types_through():
    declared = Input("x", InputKind.POINTS, (None, 3), accepts=(dict,))
    declared.check({"a": (1, 2, 3)}, "Owner")
    with pytest.raises(ValueError):
        Input("x", InputKind.POINTS, (None, 3)).check({"a": (1, 2, 3)}, "Owner")
