"""Live parameter changes of the motion features that port an EyesWeb block (see `test_live_parameters.py` for the rules).

A block that keeps no state has LIVE rows only (the new value is what a feature built with it gives); a block whose
original reads a parameter in Init() has a STRUCTURAL row; INVALID rows only where the core validates the value.
"""

import numpy as np
import pytest

from live_param_suite import check_invalid, check_live, check_structural, ids

from pyeyesweb._core import core
from pyeyesweb.analysis_primitives.complexity import CoarseGraining
from pyeyesweb.analysis_primitives.periodicity import Periodicity
from pyeyesweb.analysis_primitives.rarity import Rarity
from pyeyesweb.low_level.contraction import PointsDensity
from pyeyesweb.low_level.shape import BodyPartsFromCurvature, ConvexHull
from pyeyesweb.low_level.symmetry import Symmetry
from pyeyesweb.mid_level.impulsivity import ContractionImpulsivity
from pyeyesweb.low_level.motion_noise import MotionNoiseDetector
from pyeyesweb.mid_level.segmentation import GestureSegmenter, MotionDuration
from pyeyesweb.low_level.shape import FilterContour

_motion = core.motion
_rng = np.random.default_rng(11)
_FRAMES = 100

_ANGLES = 2 * np.pi * np.arange(24) / 24
_CIRCLE = np.column_stack([np.cos(_ANGLES), np.sin(_ANGLES)])
CONTOURS = [_CIRCLE * (1 + 0.1 * _rng.normal(size=(24, 1))) for _ in range(_FRAMES)]
HULLS = [_rng.integers(0, 6, size=(12, 2)).astype(float) for _ in range(_FRAMES)]

_CURVE_ANGLES = 2 * np.pi * np.arange(40) / 40
_CURVE_CIRCLE = np.column_stack([np.cos(_CURVE_ANGLES), np.sin(_CURVE_ANGLES)])
# 3 zero crossings pairs, 6-7 points apart, drifting by 0.05 rad per frame
CURVATURES = [(np.sin(3 * (_CURVE_ANGLES + 0.05 * frame)), _CURVE_CIRCLE) for frame in range(_FRAMES)]

SQUARE_WAVE = [float((frame // 7) % 2) for frame in range(_FRAMES + 20)]
SAMPLES_2 = [list(_rng.uniform(0, 1, size=2)) for _ in range(_FRAMES)]
PERIODIC = [[float(value)] for value in np.tile([3.0, -1.0, 0.0, 2.0, -4.0], _FRAMES // 5 + 4)[:_FRAMES + 20]]
IMPULSES = [(0.2 * (frame % 9 in (2, 3, 4)) + 0.05, float(_rng.uniform())) for frame in range(_FRAMES + 20)]
POINT_CLOUDS = [_rng.normal(size=(6, 3)) for _ in range(_FRAMES)]

# (no coordinate is zero on both shoulders: that is 0/0 = NaN in the block, an INVALID_INPUT result)
SKELETONS = [{"torso": (0.0, 0.0, 0.0), "left_shoulder": (-1 - 0.1 * (frame % 9), 0.5, 0.25),
              "right_shoulder": (1.0, 0.4, 0.25), "hand": (0.5 * frame, 1.0, 2.0)} for frame in range(_FRAMES)]

# Still until sample 60, then moving at random: the thresholds do not enter the state, the gesture starts afterwards.
_HAND = np.concatenate([np.zeros(61), np.cumsum(_rng.normal(size=_FRAMES))])
TIMED_HAND = [({"hand": (float(x_position), 0.0, 0.0)}, frame / 25) for frame, x_position in enumerate(_HAND[:_FRAMES + 20])]


class TimedMotionNoiseDetector(MotionNoiseDetector):
    """`process` takes `(frame, t)` positionally, as the suite feeds one item per call."""

    def process(self, frame, timestamp):
        return super().process(frame, timestamp=timestamp)

    process._input_checked = True  # the check of the number of inputs is the parent's, on the call it receives


def detector(**params):
    return TimedMotionNoiseDetector(labels=["hand"], **{"noise_threshold": 0.5, **params})


def segmenter(**params):
    return GestureSegmenter(**{"filter_window_length": 5, "firing_threshold": 0.1, **params})


# the energy of the hand above (weight 2) and a noise flag that comes and goes: what the segmenter receives
INTENSITY = [(float(2.0 * 0.5 * np.diff(_HAND, prepend=0.0)[frame] ** 2), float(frame % 17 < 5)) for frame in range(_FRAMES + 20)]


def symmetry(**params):
    return Symmetry(reference_point="torso",
                    pairs=[("left_shoulder", "right_shoulder")], normalize_skeleton=False, **params)


LIVE = [
    (lambda: BodyPartsFromCurvature(), "minimum_distance", 3, CURVATURES),
    (lambda: ConvexHull(integer_coordinates=True), "integer_coordinates", False, HULLS),
    (lambda: FilterContour(window=5, gaussian_sigma=2.0), "gaussian_sigma", 1.0, CONTOURS),
    (lambda: segmenter(), "firing_threshold", 5.0, INTENSITY),
    (lambda: detector(), "noise_threshold", 1e-9, TIMED_HAND),
    (lambda: ContractionImpulsivity(sampling_rate=25.0), "sampling_rate", 50.0, IMPULSES),
    (lambda: ContractionImpulsivity(), "peak_threshold", 0.5, IMPULSES),
    (lambda: ContractionImpulsivity(), "motion_threshold", 0.1, IMPULSES),
    (lambda: MotionDuration(sampling_rate=25.0), "sampling_rate",
     50.0, SQUARE_WAVE),
    (lambda: Periodicity(window=40, hop=10, threshold=0.2), "threshold", 0.6, PERIODIC),
    (lambda: Rarity(number_of_inputs=2, window=20), "measure", "contrast", SAMPLES_2),
    (lambda: symmetry(aggregation="mean"), "aggregation", "min",
     SKELETONS),
    (lambda: PointsDensity(distance_type="mean"), "distance_type",
     "max", POINT_CLOUDS),
]
STRUCTURAL = [
    (lambda: segmenter(), "filter_window_length", 7, INTENSITY),
    (lambda: detector(), "labels", ["hand", "torso"], TIMED_HAND),
    (lambda: Rarity(number_of_inputs=2, window=20), "window", 10, SAMPLES_2),
    (lambda: CoarseGraining(window=20, hop=5, factor=2), "factor", 4, PERIODIC),
]
INVALID = [
    (lambda: FilterContour(window=5, gaussian_sigma=2.0), "window", 0, CONTOURS),
    (lambda: segmenter(), "filter_window_length", 3, INTENSITY),
    (lambda: ContractionImpulsivity(peak_threshold=0.02), "peak_threshold", 2.0, IMPULSES),
    (lambda: ContractionImpulsivity(motion_threshold=0.01), "motion_threshold", -0.1, IMPULSES),
    (lambda: Rarity(number_of_inputs=2, window=20), "window", 0, SAMPLES_2),
    (lambda: symmetry(), "pairs", [("left_shoulder", "right_shoulder"), ("left_shoulder", "right_shoulder")],
     SKELETONS),
    (lambda: CoarseGraining(window=20, hop=5, factor=2), "factor", 0, PERIODIC),
]


def _param(rows):
    return pytest.mark.parametrize("factory, attr, value, recording", rows, ids=ids(rows))


@_param(LIVE)
def test_live_change_keeps_the_state(factory, attr, value, recording):
    check_live(factory, attr, value, recording)


@_param(STRUCTURAL)
def test_structural_change_restarts_and_says_so_once(factory, attr, value, recording):
    check_structural(factory, attr, value, recording)


@_param(INVALID)
def test_invalid_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)
