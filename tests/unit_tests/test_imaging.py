"""Image features (EyesWeb BaseImaging): call contract, the `IMAGE` input, behaviour, and parity with the colleague's
independent port on frozen outputs (`tests/data/imaging_reference.npz`, inputs in `tests/_support/imaging_inputs.py`).
Needs the compiled core (EYESWEB_CORE_PATH), else skipped."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from imaging_inputs import PULSE_WINDOWS, VIDEO_COLOUR, VIDEO_GRAY, silhouette  # noqa: E402
from floats import assert_same_floats  # noqa: E402
from pyeyesweb import Layer, catalog  # noqa: E402
from pyeyesweb.analysis_primitives import BinaryPulsesRegularity  # noqa: E402
from pyeyesweb.data_models import Input, InputKind, Status  # noqa: E402
from pyeyesweb.physical_signals import SilhouetteBodyParts, SilhouetteCentroids, Videogram  # noqa: E402

REFERENCE = np.load(os.path.join(os.path.dirname(__file__), "..", "data", "imaging_reference.npz"))
BODY = silhouette()
LABELS = ["center_of_gravity", "head", "left_shoulder", "left_elbow", "left_forearm", "left_hand", "right_shoulder", "right_elbow",
          "right_forearm", "right_hand", "left_knee", "left_foot", "right_knee", "right_foot"]
PARTS = ["left_leg", "right_leg", "trunk", "left_arm", "right_arm", "head"]  # the image's sides (left = smaller x)
# the reference port names the parts by the subject's sides: its "right" parts are on the smaller x
PORT_NAMES = {"right_leg": "left_leg", "left_leg": "right_leg", "trunk": "trunk", "right_arm": "left_arm",
              "left_arm": "right_arm", "head": "head"}
MOVING_BODY = np.stack([silhouette(shift=2 * step) for step in range(8)])
RNG = np.random.default_rng(1)
GRAY_FRAMES = (RNG.random((10, 12, 16)) * 255).astype(np.uint8)
COLOUR_FRAMES = (RNG.random((10, 12, 16, 3)) * 255).astype(np.uint8)

FACTORIES = {
    "SilhouetteCentroids": (lambda: SilhouetteCentroids(filter_centroids=True, alpha=0.5), MOVING_BODY),
    "SilhouetteBodyParts": (lambda: SilhouetteBodyParts(), MOVING_BODY),
    "Videogram gray": (lambda: Videogram(window=4), GRAY_FRAMES),
    "Videogram colour": (lambda: Videogram(window=4, mode="vertical", end_of_image_mode="scroll"), COLOUR_FRAMES),
}


@pytest.mark.parametrize("name", FACTORIES)
def test_feature_contract(name):
    factory, recording = FACTORIES[name]
    check_feature_contract(factory, recording)


def test_the_features_are_catalogued_as_physical_signals():
    layers = {info.name: (info.layer, info.eyesweb_block) for info in catalog()}
    for name, block in (("SilhouetteCentroids", "centroids_calc (Centroids Calc)"),
                        ("SilhouetteBodyParts", "BlobSubRegions"), ("Videogram", "video_gram (VideoGram)")):
        assert layers[name] == (Layer.PHYSICAL_SIGNALS, block)
    assert layers["BinaryPulsesRegularity"] == (Layer.ANALYSIS_PRIMITIVE, "binary_pulses_regularity (BinaryPulsesRegularity)")


# ---------------------------------------------------------------------------------------------- the IMAGE input

def test_an_image_input_is_declared_and_described():
    declared = SilhouetteCentroids().inputs["silhouette"]
    assert declared.kind is InputKind.IMAGE and declared.shape == (None, None)
    assert "silhouette" in declared.describe()
    assert Videogram().inputs["frame"].shape == (None, None, None)


@pytest.mark.parametrize("image", [np.zeros((4, 5), np.uint8), np.zeros((4, 5, 1), np.uint8), np.ones((4, 5), bool),
                                   np.full((4, 5), 255.0), np.zeros((4, 5), np.int64), np.zeros((0, 0), np.uint8)])
def test_a_grayscale_input_takes_the_natural_forms(image):
    SilhouetteCentroids().inputs.check([image], "SilhouetteCentroids")


@pytest.mark.parametrize("image, what", [
    (np.zeros(5), "1-D"), (np.zeros((2, 3, 4, 5)), "4-D"), (np.zeros((4, 5, 3)), "colour for a grayscale input"),
    (np.full((4, 5), 256.0), "above 255"), (np.full((4, 5), -1.0), "negative"), (np.full((4, 5), 0.5), "not whole"),
    (np.full((4, 5), np.nan), "NaN"), (np.array([["a", "b"]]), "text"), (np.zeros((4, 5), np.int64) + 300, "int above 255")])
def test_a_wrong_image_raises_value_error(image, what):
    with pytest.raises(ValueError, match="SilhouetteCentroids"):
        SilhouetteCentroids().process(image)


def test_an_image_input_with_declared_sizes_and_channels():
    declared = Input("frame", InputKind.IMAGE, (4, 5, 3))
    declared.check(np.zeros((4, 5, 3), np.uint8))
    for wrong in (np.zeros((4, 5), np.uint8), np.zeros((4, 5, 4), np.uint8), np.zeros((5, 4, 3), np.uint8)):
        with pytest.raises(ValueError):
            declared.check(wrong)


def test_run_takes_a_stack_or_a_list_of_images_and_keeps_them_8_bit():
    feature = Videogram(window=3)
    stacked = feature.run(GRAY_FRAMES[:5])
    listed = Videogram(window=3).run([frame for frame in GRAY_FRAMES[:5]])
    assert np.array_equal(stacked["videogram"], listed["videogram"]) and len(stacked) == 5
    mixed = Videogram(window=3).run([GRAY_FRAMES[0], GRAY_FRAMES[1][:6]])  # a frame of another size restarts it
    assert mixed.column("videogram")[1].shape == (6, 3, 1)


def test_an_empty_image_is_invalid_input_and_a_wrong_channel_count_raises():
    for feature in (SilhouetteCentroids(), SilhouetteBodyParts(), Videogram()):
        result = feature.process(np.zeros((0, 0), np.uint8))
        assert result.status is Status.INVALID_INPUT and "empty" in result.reason
    with pytest.raises(ValueError, match="Videogram"):
        Videogram().process(np.zeros((5, 5, 2), np.uint8))
    with pytest.raises(ValueError, match="CentroidsCalc|SilhouetteCentroids"):
        SilhouetteCentroids().process(np.zeros((5, 5, 3), np.uint8))


# ----------------------------------------------------------------------------------------------- behaviour

def test_centroids_of_a_silhouette():
    feature = SilhouetteCentroids()
    result = feature.process(BODY)
    assert result.status is Status.OK and result.centroids.shape == (14, 2) and result.normalized.shape == (14, 2)
    assert feature.outputs["centroids"].axis_names[0] == tuple(LABELS)
    assert not np.isnan(result.centroids).any()
    assert np.allclose(result.normalized, result.centroids / [320, 240])
    assert result["centroids_center_of_gravity_x"] == result.centroids[0, 0]
    assert result.centroids[2, 0] < result.centroids[0, 0] < result.centroids[6, 0]  # shoulders around the COG


def test_centroids_only_the_requested_ones_unless_intermediate_are_added():
    only_hand = dict(parts=["left-hand"])
    result = SilhouetteCentroids(**only_hand).process(BODY)
    assert np.isfinite(result.centroids[:, 0]).tolist() == [name == "left_hand" for name in LABELS]
    chain = SilhouetteCentroids(add_intermediate_centroids=True, **only_hand).process(BODY)
    assert {name for name, value in zip(LABELS, chain.centroids[:, 0]) if np.isfinite(value)} == {
        "center_of_gravity", "left_shoulder", "left_elbow", "left_forearm", "left_hand"}


def test_centroids_of_half_silhouettes_and_empty_masks():
    upper = SilhouetteCentroids(silhouette="upper").process(BODY).centroids
    assert np.isfinite(upper[LABELS.index("head")]).all() and np.isnan(upper[LABELS.index("left_foot")]).all()
    left = SilhouetteCentroids(silhouette="left").process(BODY).centroids
    assert np.isnan(left[LABELS.index("head")]).all() and np.isnan(left[LABELS.index("right_hand")]).all()
    result = SilhouetteCentroids().process(np.zeros((20, 20), np.uint8))
    assert result.status is Status.INVALID_INPUT and "foreground" in result.reason and np.isnan(result.centroids).all()
    with pytest.raises(ValueError, match="silhouette"):
        SilhouetteCentroids(silhouette="torso")
    with pytest.raises(ValueError, match="parts.*'left_hand'"):
        SilhouetteCentroids(parts=["head", "nose"])
    with pytest.raises(ValueError):
        SilhouetteCentroids(alpha=1.5)


def test_centroid_coordinates_are_those_of_the_frame_not_of_the_crop():
    shifted = np.roll(BODY, (7, 11), axis=(0, 1))
    first, second = SilhouetteCentroids().process(BODY), SilhouetteCentroids().process(shifted)
    assert np.allclose(second.centroids - first.centroids, [11, 7], atol=1)  # truncation to int moves a point by < 1 pixel


def test_body_parts_of_a_silhouette():
    feature = SilhouetteBodyParts()
    result = feature.process(BODY)
    assert result.status is Status.OK and result.is_found.all() and result.regions.shape == (6, 4)
    assert list(result.masks) == PARTS
    for slot, name in enumerate(PARTS):
        x, y, width, height = result.regions[slot]
        assert result.masks[name].shape == (height, width) and set(np.unique(result.masks[name])) <= {0, 255}
        assert result.masks[name].any()
    assert result.regions[PARTS.index("head"), 1] < result.regions[PARTS.index("trunk"), 1]
    assert result.regions[PARTS.index("left_arm"), 0] < result.regions[PARTS.index("right_arm"), 0]  # left = smaller x


def test_body_parts_selection_and_missing_parts():
    result = SilhouetteBodyParts(parts=["Left leg"]).process(BODY)
    assert result.is_found.tolist() == [True, False, False, False, False, False] and list(result.masks) == ["left_leg"]
    assert not result.regions[1].any()
    empty = SilhouetteBodyParts().process(np.zeros((20, 20), np.uint8))
    assert empty.status is Status.INVALID_INPUT and "foreground" in empty.reason
    block = np.zeros((20, 20), np.uint8)
    block[5:15, 5:15] = 255  # a square has no arms to find
    assert SilhouetteBodyParts().process(block).status is Status.OK


def _oracle_videogram(frames, window, mode="horizontal", direction="left_to_right", end="loop"):
    """An independent numpy videogram (Jensenius 2006): each frame gives the mean of its rows (horizontal) or columns
    (vertical), per channel, truncated; lines are written left to right or right to left, wrapping; in scroll mode the
    image, once filled, is rotated so that the line at the write position comes first."""
    lines = [frame.reshape(frame.shape[:2] + (-1,)).astype(np.int64).sum(axis=1 if mode == "horizontal" else 0)
             // frame.shape[1 if mode == "horizontal" else 0] for frame in frames]
    buffer = np.zeros((window,) + lines[0].shape, np.uint8)
    position, filled, out = 0, False, []
    for line in lines:
        if direction == "right_to_left":
            position = (position - 1) % window
            buffer[position] = line
        else:
            buffer[position] = line
            position = (position + 1) % window
        filled = filled or position == 0
        image = np.roll(buffer, -position, axis=0) if end == "scroll" and filled and position != 0 else buffer.copy()
        out.append(image.transpose(1, 0, 2) if mode == "horizontal" else image)
    return out


def test_the_videogram_sums_every_channel_on_its_own():
    """The independent oracle: a numpy videogram, line = mean of the frame along an axis, per channel."""
    for frames, mode in ((COLOUR_FRAMES, "horizontal"), (COLOUR_FRAMES, "vertical"), (GRAY_FRAMES, "horizontal")):
        feature = Videogram(window=len(frames) + 2, mode=mode)
        recorded = feature.run(frames)
        lines = np.stack([frame.reshape(frame.shape[:2] + (-1,)).astype(np.int64).sum(axis=1 if mode == "horizontal" else 0)
                          // frame.shape[1 if mode == "horizontal" else 0] for frame in frames]).astype(np.uint8)
        last = recorded.column("videogram")[-1]
        expected = lines.transpose(1, 0, 2) if mode == "horizontal" else lines
        assert np.array_equal(last[:, :len(frames)] if mode == "horizontal" else last[:len(frames)], expected)


def test_the_videogram_loops_scrolls_and_changes_direction():
    frames = [np.full((2, 2), level, np.uint8) for level in (1, 2, 3)]
    marked = [np.array([[level, level], [100, 100]], np.uint8) for level in (10, 20, 30, 40, 50)]
    looped = Videogram(window=3).run(marked).column("videogram")[-1]
    scrolled = Videogram(window=3, end_of_image_mode="scroll").run(marked).column("videogram")[-1]
    assert looped[0, :, 0].tolist() == [40, 50, 30] and scrolled[0, :, 0].tolist() == [30, 40, 50]  # oldest line first
    assert looped[1, :, 0].tolist() == [100, 100, 100]  # the mean keeps the level of each row
    backwards = Videogram(window=3, direction="right_to_left").run(frames).column("videogram")[-1]
    assert backwards[:, :, 0].tolist() == [[3, 2, 1]] * 2  # right to left: columns 2, 1, 0
    assert Videogram(window=3).process(frames[0]).videogram.shape == (2, 3, 1)


def test_the_videogram_restarts_when_the_frame_size_changes():
    feature = Videogram(window=4)
    feature.process(GRAY_FRAMES[0])
    result = feature.process(GRAY_FRAMES[1][:6, :8])
    assert result.videogram.shape == (6, 4, 1) and "restarted" in result.reason
    assert feature.process(GRAY_FRAMES[2][:6, :8]).reason == ""
    feature.reset()
    assert feature.process(GRAY_FRAMES[0]).videogram.shape == (12, 4, 1)


# ------------------------------------------------------------------------------------- BinaryPulsesRegularity

def test_binary_pulses_regularity():
    feature = BinaryPulsesRegularity(window=10)
    train = [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1]
    results = [feature.process(value) for value in train]
    assert [result.status for result in results[:9]] == [Status.WARMING_UP] * 9
    assert results[9].is_regular and results[9].pulse_count == 4 and results[9].is_regularity_detected
    assert not results[10].is_regularity_detected and results[10].is_regular and results[10].pulse_count == 3
    assert list(feature.outputs.names) == ["is_regular", "pulse_count", "is_regularity_detected"]
    irregular = BinaryPulsesRegularity(window=11)
    for value in [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1]:
        result = irregular.process(value)
    assert not result.is_regular and BinaryPulsesRegularity(window=11, threshold=2).run(
        np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1], float))["is_regular"][-1]  # intervals 3, 4, 3: spread 1 < 2


def test_binary_pulses_regularity_validation():
    with pytest.raises(ValueError, match="window"):
        BinaryPulsesRegularity(window=2)
    with pytest.raises(ValueError):
        BinaryPulsesRegularity(window=5, threshold=0)  # max - min < 0 is never true
    feature = BinaryPulsesRegularity(window=3)
    assert feature.process(1).status is Status.WARMING_UP and feature.process(np.nan).status is Status.INVALID_INPUT
    assert feature.process(1).status is Status.WARMING_UP  # the NaN was not buffered
    assert feature.process(1).status is Status.OK
    with pytest.raises(ValueError, match="BinaryPulsesRegularity"):
        feature.process([1, 0])


# ------------------------------------------------------------- parity with the colleague's port (frozen outputs)

def test_centroids_equal_the_reference_port_with_the_filter():
    feature = SilhouetteCentroids(filter_centroids=True, alpha=0.5)
    for step in range(3):
        assert_same_floats(feature.process(silhouette(shift=3 * step)).centroids, REFERENCE["centroids_filtered"][step])


def test_body_parts_equal_the_reference_port():
    result = SilhouetteBodyParts().process(BODY)
    assert list(result.masks) == [PORT_NAMES[label] for label in REFERENCE["parts_labels"].tolist()]
    for index, name in enumerate(result.masks):
        slot = PARTS.index(name)
        assert result.regions[slot].tolist() == REFERENCE["parts_rects"][index].tolist()
        assert result.masks[name].shape == tuple(REFERENCE["parts_mask_shapes"][index])
        assert int(result.masks[name].sum()) == REFERENCE["parts_mask_sums"][index]


def test_the_videogram_equals_the_oracle_on_the_reference_videos():
    # The frozen port scaled every line to 255; the line is the mean now (algorithm review, D1), so the oracle is numpy.
    colour = Videogram(window=5, direction="right_to_left", end_of_image_mode="scroll").run(VIDEO_COLOUR).column("videogram")
    assert np.array_equal(np.stack(colour), np.stack(_oracle_videogram(VIDEO_COLOUR, 5, direction="right_to_left", end="scroll")))
    gray = Videogram(window=5, mode="vertical").run(VIDEO_GRAY).column("videogram")
    assert np.array_equal(np.stack(gray), np.stack(_oracle_videogram(VIDEO_GRAY, 5, mode="vertical")))


def _paper_regularity(windows, threshold):
    """Niewiadomski et al. 2019, sec. 3.2: regular when max(I) - min(I) < threshold, with at least 3 pulses; the trigger
    is the first regular window after one that was not."""
    out, before = [], False
    for window in windows:
        pulses = np.flatnonzero(np.asarray(window) != 0)
        intervals = np.diff(pulses)
        regular = len(pulses) >= 3 and int(intervals.max() - intervals.min()) < threshold
        out.append((regular, len(pulses), regular and not before))
        before = regular
    return out


@pytest.mark.parametrize("threshold", [1, 2, 3])
def test_pulse_regularity_follows_the_paper(threshold):
    # The windows of the frozen port; the rule changed on purpose (algorithm review, D1), so the oracle is the paper's.
    block = BinaryPulsesRegularity(window=3, threshold=threshold)._block  # the core block, one window per call
    assert [block.process(window) for window in PULSE_WINDOWS] == _paper_regularity(PULSE_WINDOWS, threshold)
    assert any(regular for regular, _, _ in _paper_regularity(PULSE_WINDOWS, threshold))


def test_parts_default_to_everything_and_are_listed_in_the_signature():
    import inspect
    assert SilhouetteCentroids().parts == tuple(LABELS) and SilhouetteBodyParts().parts == tuple(PARTS)
    assert inspect.signature(SilhouetteBodyParts).parameters["parts"].default == tuple(PARTS)
    feature = SilhouetteBodyParts()
    feature.parts = ["head"]
    assert feature.parts == ("head",) and list(feature.process(BODY).masks) == ["head"]


def test_a_body_part_touching_the_first_column_is_found():
    # The original dropped a region whose origin was 0 (final round D2): crop a body so that its left arm starts at x = 0.
    rows, columns = np.mgrid[:240, :320]
    body = (abs(columns - 160) <= 28) & (rows >= 60) & (rows <= 140)
    body |= (columns - 160) ** 2 / 18 ** 2 + (rows - 40) ** 2 / 22 ** 2 <= 1
    body |= (abs(rows - 75) <= 7) & (columns >= 80) & (columns <= 240)
    body |= (abs(columns - 147) <= 9) & (rows > 140) & (rows <= 225)
    body |= (abs(columns - 173) <= 9) & (rows > 140) & (rows <= 225)
    result = SilhouetteBodyParts().process(body[:, 80:].astype(np.uint8) * 255)
    assert result.is_found.all() and result.regions[PARTS.index("left_arm"), 0] == 0
