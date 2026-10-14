"""Image features (EyesWeb BaseImaging): the centroids and the parts of a silhouette, the videogram.

An image is one 8-bit array per call: `(H, W)` for a grayscale image or a silhouette mask, `(H, W, C)` for colour
(`run` takes `(T, H, W[, C])` or a list of images). A `bool` array is a 0 / 1 mask; any other numeric array must hold whole
numbers in 0-255. A silhouette is a mask in which every non-zero pixel is foreground; the blob the EyesWeb blocks
take (the mask cropped to its bounding box, with its origin and the frame size) is built from it, so coordinates
come back in the frame of the mask. An empty image is `INVALID_INPUT`. Outputs that are images have a shape known
only from the first frame (`None` sizes in the schema) and hold the pixel values as integers.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature, XY
from pyeyesweb.base.inputs import as_image, image_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_imaging = core.imaging

_CENTROIDS = tuple(_imaging.CentroidsCalc.labels)
_BODY_PARTS = ("right_leg", "left_leg", "trunk", "right_arm", "left_arm", "head")


class _ImageFeature(FrameFeature):
    """A block taking one image per call: an empty image is `INVALID_INPUT`, any other goes to `_from_image`."""

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        image = as_image(frame)
        if image.size == 0:
            return self.no_output(Status.INVALID_INPUT, "empty image", timestamp)
        return self._from_image(image, timestamp)

    def _from_image(self, image: np.ndarray, timestamp: Optional[float]) -> Result:
        raise NotImplementedError


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="centroids_calc (Centroids Calc)")
class SilhouetteCentroids(_ImageFeature):
    """Hierarchical centroids of a human silhouette (EyesWeb Centroids Calc): centre of gravity, head, shoulders,
    elbows, forearms, hands, knees and feet.

    `process(silhouette, *, timestamp=None)`, `silhouette` a `(H, W)` mask (non-zero = body). The silhouette is split
    recursively into rectangles around its centre of gravity and the centre of gravity of each is taken; "left" and
    "right" are the image's (left = smaller x). A centroid that cannot be found (empty region, missing parent) is NaN.

    Parameters
    ----------
    silhouette : {"full", "upper", "lower", "left", "right"}, optional
        The part of the body the mask shows (default `"full"`): the centroids of the missing half (and the head
        of a left or right half) are not computed. Changing it restarts the filters.
    cog, head, left_shoulder, left_elbow, left_forearm, left_hand, right_shoulder, right_elbow, right_forearm, \
right_hand, left_knee, left_foot, right_knee, right_foot : bool, optional
        Which centroids to output (default all). A centroid is computed when it or one that depends on it is
        requested (head <- shoulders, hand <- forearm <- elbow <- shoulder, foot <- knee).
    filter_centroids : bool, optional
        Smooth every centroid over time, `filtered += alpha * (new - filtered)` (default `False`). As in EyesWeb the
        filter works on the position inside the silhouette's bounding box, not on the movement of the box.
    alpha : float, optional
        Filter coefficient in [0, 1] (default 0.75): 1 does not filter, 0 keeps the first value.
    add_intermediate_centroids : bool, optional
        Also output the centroids that were computed only because another one needs them (default `False`).

    Returns
    -------
    Result
        `centroids`: `(14, 2)` pixel coordinates `(x, y)` in the frame, one row per label (`cog`, `head`,
        `left_shoulder`, ...); `normalized`: the same divided by the frame width and height. `INVALID_INPUT` for a
        mask without foreground.
    """
    _core_class = _imaging.CentroidsCalc
    INPUTS = Inputs(image_input("silhouette", "mask of the body: every non-zero pixel is foreground"))
    OUTPUTS = Schema(
        Output("centroids", (len(_CENTROIDS), 2), labels=_CENTROIDS, components=XY, unit="px",
               doc="centroid coordinates in the frame; NaN where absent"),
        Output("normalized", (len(_CENTROIDS), 2), labels=_CENTROIDS, components=XY,
               doc="the centroids divided by the frame width and height"))

    def _from_image(self, mask: np.ndarray, timestamp: Optional[float]) -> Result:
        found, raw = self._block.process(mask)
        if not found:
            return self.no_output(Status.INVALID_INPUT, "no foreground pixels in the silhouette", timestamp)
        return self.result(timestamp=timestamp, centroids=raw[:, :2], normalized=raw[:, 2:])


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="BlobSubRegions")
class SilhouetteBodyParts(_ImageFeature):
    """Head, trunk, arms and legs of a human silhouette (EyesWeb BlobSubRegions), from its projection histograms.

    `process(silhouette, *, timestamp=None)`, `silhouette` a `(H, W)` mask (non-zero = body). The columns holding
    the arms are found by accumulating the area from each side, the legs by the horizontal extent of the lower rows,
    the neck by the first row, going up from the barycentre, where the body narrows, and each arm by the rows where
    it holds many pixels. "Right" and "left" are the image's: the right arm and leg are on the smaller x.

    Parameters
    ----------
    arm_percentage : float, optional
        Fraction of the silhouette area that is not arm (default 0.8).
    legs_search : float, optional
        Fraction of the distance between the barycentre and the feet where the search for the legs starts (0.5).
    legs_offset : float, optional
        Minimal distance between the barycentre and the top of the legs, as a fraction of the same distance (0.2).
    arms_min_threshold, arms_max_threshold : float, optional
        An arm ends at the first row with fewer foreground pixels than `arms_min_threshold` times its width, and
        starts at the first row with more than `arms_max_threshold` times (defaults 0.2 and 0.5).
    extract_head, extract_trunk, extract_left_arm, extract_right_arm, extract_left_leg, extract_right_leg : bool, optional
        Which parts to output (default all).

    Returns
    -------
    Result
        `regions`: `(6, 4)` ints `(x, y, width, height)` of each part in the frame, rows in the order
        right_leg, left_leg, trunk, right_arm, left_arm, head, zeros for a part that was not found; `found`: which
        parts were; `masks`: dict part -> `(height, width)` 0 / 255 mask of the parts found. A part is dropped when it
        is empty or touches the first column or row of the frame, as in EyesWeb. `INVALID_INPUT` for a mask without
        foreground.
    """
    _core_class = _imaging.BlobSubRegions
    INPUTS = Inputs(image_input("silhouette", "mask of the body: every non-zero pixel is foreground"))
    OUTPUTS = Schema(
        Output("regions", (len(_BODY_PARTS), 4), kind=int, labels=_BODY_PARTS, components=("x", "y", "width", "height"),
               unit="px", doc="bounding box of each part in the frame; zeros where not found"),
        Output("found", len(_BODY_PARTS), kind=bool, labels=_BODY_PARTS, doc="the part was found"),
        Output("masks", (None, None), kind=int, labelled=True, doc="0 / 255 mask of each part found"))

    def _from_image(self, mask: np.ndarray, timestamp: Optional[float]) -> Result:
        if not mask.any():
            return self.no_output(Status.INVALID_INPUT, "no foreground pixels in the silhouette", timestamp)
        regions = np.zeros((len(_BODY_PARTS), 4), dtype=int)
        found = np.zeros(len(_BODY_PARTS), dtype=bool)
        masks = {}
        for label, left, top, part_mask in self._block.process(mask):
            slot = _BODY_PARTS.index(label)
            regions[slot] = (left, top, part_mask.shape[1], part_mask.shape[0])
            found[slot] = True
            masks[label] = part_mask
        return self.result(timestamp=timestamp, regions=regions, found=found, masks=masks)


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="video_gram (VideoGram)")
class Videogram(_ImageFeature):
    """Videogram or motiongram (EyesWeb VideoGram): each frame collapsed to one line, the lines stacked over time.

    `process(frame, *, timestamp=None)`, `frame` a `(H, W)` or `(H, W, C)` image with 1, 3 or 4 channels. The frame is
    summed along one axis (per channel) and the line is scaled by its maximum to 0-255. With a motion image (a frame
    difference) it is a motiongram (Jensenius, 2006). The first frame fixes the size; a frame of another size
    restarts the videogram (the result says so in `reason`).

    Parameters
    ----------
    length : int, optional
        Number of lines of the videogram, >= 1 (default 500).
    mode : {"horizontal", "vertical"}, optional
        `"horizontal"`: each frame becomes a column (the sum of each row) of an image `length` wide and `H` high;
        `"vertical"`: a row (the sum of each column) of an image `W` wide and `length` high. Changing it restarts.
    direction : {"left_to_right", "right_to_left"}, optional
        Where the newest line is written; the position wraps around so the oldest line is overwritten.
    end_of_image_mode : {"loop", "scroll"}, optional
        `"loop"`: the image as it is; `"scroll"`: once it has been filled, rotated so that the oldest line comes first.

    Returns
    -------
    Result
        `videogram`: `(H, length, C)` (horizontal) or `(length, W, C)` (vertical) image; `C = 1` for a grayscale input.
    """
    _core_class = _imaging.VideoGram
    INPUTS = Inputs(image_input("frame", "grayscale or colour frame", channels=None))
    OUTPUTS = Schema(Output("videogram", (None, None, None), kind=int, doc="the videogram image, channels last"))

    def __init__(self, **params: Any):
        super().__init__(**params)
        self._frame_shape = None

    def _from_image(self, image: np.ndarray, timestamp: Optional[float]) -> Result:
        if image.ndim == 3 and image.shape[2] not in (1, 3, 4):
            raise ValueError(f"{type(self).__name__}: input 'frame' expects an image with 1, 3 or 4 channels, got shape {image.shape}")
        restarted = self._frame_shape not in (None, image.shape)
        if restarted:
            self._block.reset()
        self._frame_shape = image.shape
        return self.result(timestamp=timestamp, videogram=self._to_image(self._block.process(image)),
                           reason="frame size changed: videogram restarted" if restarted else "")

    @staticmethod
    def _to_image(raw: np.ndarray) -> np.ndarray:
        return raw.reshape(raw.shape[0], raw.shape[1], -1)

    def reset(self) -> None:
        self._frame_shape = None
        super().reset()


__all__ = ["SilhouetteCentroids", "SilhouetteBodyParts", "Videogram"]
