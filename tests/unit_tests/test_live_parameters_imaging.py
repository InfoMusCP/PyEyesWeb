"""Live parameter changes of the imaging blocks and BinaryPulsesRegularity (checks in `tests/live_param_suite.py`).

* SilhouetteBodyParts: stateless, every parameter is LIVE.
* SilhouetteCentroids: the centroid `parts`, the filter switch, alpha and "add intermediate centroids" are LIVE (the filters
  are kept); the silhouette type is STRUCTURAL (EyesWeb reads it in Init()).
* Videogram: direction and end of image mode are read by Execute(): LIVE; length and mode size the image: STRUCTURAL.
* BinaryPulsesRegularity: the threshold is LIVE; `window` is changed through `configure` (see the windowed tests).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from imaging_inputs import silhouette  # noqa: E402
from live_param_suite import NOTE, check_invalid, check_live, check_structural, feed, ids  # noqa: E402

from pyeyesweb.analysis_primitives import BinaryPulsesRegularity  # noqa: E402
from pyeyesweb.physical_signals import SilhouetteBodyParts, SilhouetteCentroids, Videogram  # noqa: E402

_rng = np.random.default_rng(13)
FRAME_COUNT = 120
NOISE = [(_rng.random((12, 16)) * 255).astype(np.uint8) for _ in range(FRAME_COUNT)]
BODIES = [silhouette(shift=int(shift)) for shift in np.round(8 * np.sin(np.arange(FRAME_COUNT) / 7.0))]
COLOUR = [(_rng.random((6, 8, 3)) * 255).astype(np.uint8) for _ in range(FRAME_COUNT)]
# flat before the change (nothing regular to remember), then pulses whose intervals differ by one sample
PULSES = [0.0] * 60 + ([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0] * 5)[:FRAME_COUNT - 60]

LIVE = [
    (lambda: SilhouetteBodyParts(), "arm_percentage", 0.6, BODIES),
    (lambda: SilhouetteBodyParts(), "parts", ["trunk", "left_arm", "right_arm", "left_leg", "right_leg"], BODIES),
    (lambda: SilhouetteCentroids(), "parts", ["center_of_gravity", "left_hand"], BODIES),
    (lambda: SilhouetteCentroids(filter_centroids=True, alpha=0.5), "parts", ["head", "left_hand"], BODIES),
    (lambda: SilhouetteCentroids(), "add_intermediate_centroids", True, BODIES),
    (lambda: BinaryPulsesRegularity(window=10, hop=2), "threshold", 1, PULSES),
]
STRUCTURAL = [
    (lambda: SilhouetteCentroids(filter_centroids=True), "silhouette", "upper", BODIES),
    (lambda: Videogram(window=20), "window", 30, NOISE),
    (lambda: Videogram(window=20), "mode", "vertical", COLOUR),
]
INVALID = [
    (lambda: SilhouetteBodyParts(arm_percentage=0.8), "arm_percentage", float("nan"), BODIES),
    (lambda: SilhouetteCentroids(alpha=0.75), "alpha", 2.0, BODIES),
    (lambda: SilhouetteCentroids(silhouette="full"), "silhouette", "torso", BODIES),
    (lambda: SilhouetteCentroids(), "parts", ["head", "nose"], BODIES),
    (lambda: SilhouetteBodyParts(), "parts", ["Head", "tail"], BODIES),
    (lambda: Videogram(window=20), "window", 0, NOISE),
    (lambda: Videogram(direction="left_to_right"), "direction", "up", NOISE),
    (lambda: BinaryPulsesRegularity(window=10, threshold=0), "threshold", -1, PULSES),
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
def test_an_invalid_value_raises_and_changes_nothing(factory, attr, value, recording):
    check_invalid(factory, attr, value, recording)


def test_the_videogram_direction_is_live_and_keeps_the_lines():
    changed, control = Videogram(window=30), Videogram(window=30)
    feed(changed, NOISE[:10])
    feed(control, NOISE[:10])
    changed.direction = "right_to_left"
    after = changed.process(NOISE[10])
    assert NOTE not in after.reason
    before = control.process(NOISE[10])
    assert np.array_equal(after.videogram[:, :9], before.videogram[:, :9])  # the nine lines written first are kept
    assert changed._block.write_position == 9  # moved back from 10: the new line replaced the tenth


def test_the_videogram_end_of_image_mode_is_live():
    feature = Videogram(window=5)
    feed(feature, NOISE[:8])
    feature.end_of_image_mode = "scroll"
    result = feature.process(NOISE[8])
    assert NOTE not in result.reason and result.videogram.shape == (12, 5, 1)


def test_the_centroid_alpha_is_live_and_the_filters_survive():
    feature = SilhouetteCentroids(filter_centroids=True, alpha=1.0)
    still = feed(feature, [BODIES[0]] * 5)[-1]
    feature.alpha = 0.0  # the filtered position inside the bounding box is frozen: the filters were not reset
    headless = BODIES[0].copy()
    headless[:60] = 0  # a different silhouette whose box starts lower, at the same x
    result = feature.process(headless)
    assert NOTE not in result.reason
    assert np.array_equal(result.centroids[:, 0], still.centroids[:, 0], equal_nan=True)
    assert not np.array_equal(result.centroids[:, 1], still.centroids[:, 1])  # only the box origin moved
