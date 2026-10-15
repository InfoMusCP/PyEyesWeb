"""Image features (EyesWeb BaseImaging): the centroids and the parts of a silhouette, the videogram.

An image is one 8-bit array per call: ``(H, W)`` for a grayscale image or a silhouette mask, ``(H, W, C)`` for colour
(``run`` takes ``(T, H, W[, C])`` or a list of images). A ``bool`` array is a 0 / 1 mask; any other numeric array must
hold whole numbers in 0-255. A silhouette is a mask in which every non-zero pixel is foreground; the region the
EyesWeb blocks work on (the mask cropped to its bounding box, with its origin and the frame size) is built from it, so
coordinates come back in the frame of the mask. An empty image is ``INVALID_INPUT``. Outputs that are images have a
shape known only from the first frame (``None`` sizes in the schema) and hold the pixel values as integers.
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

_CENTROIDS = tuple("center_of_gravity" if label == "cog" else label for label in _imaging.CentroidsCalc.labels)
_BODY_PARTS = ("right_leg", "left_leg", "trunk", "right_arm", "left_arm", "head")


class _ImageFeature(FrameFeature):
    """A block taking one image per call: an empty image is `INVALID_INPUT`, any other goes to `_from_image`."""

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        image = as_image(frame)
        if image.size == 0:
            return self._no_output(Status.INVALID_INPUT, "empty image", timestamp)
        return self._from_image(image, timestamp)

    def _from_image(self, image: np.ndarray, timestamp: Optional[float]) -> Result:
        raise NotImplementedError


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="centroids_calc (Centroids Calc)")
class SilhouetteCentroids(_ImageFeature):
    r"""Hierarchical centroids of a human silhouette: centre of gravity, head, shoulders, limbs.

    The silhouette of a person, a binary mask, is described by the centres of gravity of its parts, a cheap body model that
    needs no skeleton. The centre of gravity of the whole mask,

    .. math::

        \mathbf{c} = \left(\frac{1}{N}\sum_k x_k,\ \frac{1}{N}\sum_k y_k\right),

    where the sum runs over the :math:`N` foreground pixels (the result is truncated to whole pixels), is the root. The
    silhouette is then split recursively into rectangles around the centre of gravity, and the centre of gravity of the
    foreground of each rectangle is taken, which yields the head and the shoulders, then the elbows, the forearms and the
    hands, and the knees and the feet, each computed from the one it depends on. "Left" and "right" are those of the
    image: left means the smaller x.

    ``process(silhouette, *, timestamp=None)`` takes one ``(H, W)`` mask (non-zero is body; see the module description for the
    image types); the frame is the frame of the mask, so the coordinates are in it. A centroid that cannot be found (empty
    region, missing parent) is NaN.

    Parameters
    ----------
    silhouette : {"full", "upper", "lower", "left", "right"}, default "full"
        The part of the body the mask shows *(structural)*: the centroids of the missing half (and the head of a left or
        right half) are not computed. Changing it restarts the filters.
    filter_centroids : bool, default False
        Smooth every centroid over time, ``filtered += alpha * (new - filtered)`` *(live)*. As in EyesWeb the filter
        works on the position inside the bounding box of the silhouette, not on the movement of the box.
    alpha : float, default 0.75
        Coefficient of the filter, in [0, 1], dimensionless *(live)*: 1 does not filter, 0 keeps the first value.
    add_intermediate_centroids : bool, default False
        Also output the centroids that were computed only because another one needs them *(live)*.
    parts : sequence of str, default all fourteen
        Which centroids to output *(live)*, among ``"center_of_gravity"``, ``"head"``, ``"left_shoulder"``,
        ``"left_elbow"``, ``"left_forearm"``, ``"left_hand"``, ``"right_shoulder"``, ``"right_elbow"``,
        ``"right_forearm"``, ``"right_hand"``, ``"left_knee"``, ``"left_foot"``, ``"right_knee"`` and ``"right_foot"``.
        A centroid is computed when it or one that depends on it is requested (head after the shoulders, hand after
        forearm after elbow after shoulder, foot after knee).

    Notes
    -----
    **Outputs.** ``centroids``: ``(14, 2)`` array of ``(x, y)`` in pixels of the frame, one row per label in the order above
    (whole-pixel values); the rows of the parts that were not requested are NaN. ``normalized``: the same coordinates divided
    by the width and the height of the frame, dimensionless, in [0, 1]. A mask without foreground is ``INVALID_INPUT``
    (``"no foreground pixels in the silhouette"``); an empty image too (``"empty image"``). The result is otherwise ``OK``
    (no warm-up).

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import SilhouetteCentroids
    >>> mask = np.zeros((20, 20), dtype=np.uint8)
    >>> mask[2:18, 8:12] = 255                                    # a vertical bar, 16 high and 4 wide
    >>> result = SilhouetteCentroids(parts=["center_of_gravity"]).process(mask)
    >>> result.centroids[0].tolist()                              # (x, y) of the centre of gravity, whole pixels
    [9.0, 9.0]
    """
    _core_class = _imaging.CentroidsCalc
    _core_names = {"center_of_gravity": "cog"}
    _parts = {label: label for label in _CENTROIDS}
    _INPUTS = Inputs(image_input("silhouette", "mask of the body: every non-zero pixel is foreground"))
    _OUTPUTS = Schema(
        Output("centroids", (len(_CENTROIDS), 2), labels=_CENTROIDS, components=XY, unit="px",
               doc="centroid coordinates in the frame; NaN where absent"),
        Output("normalized", (len(_CENTROIDS), 2), labels=_CENTROIDS, components=XY,
               doc="the centroids divided by the frame width and height"))

    def _from_image(self, mask: np.ndarray, timestamp: Optional[float]) -> Result:
        found, raw = self._block.process(mask)
        if not found:
            return self._no_output(Status.INVALID_INPUT, "no foreground pixels in the silhouette", timestamp)
        return self._result(timestamp=timestamp, centroids=raw[:, :2], normalized=raw[:, 2:])


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="BlobSubRegions")
class SilhouetteBodyParts(_ImageFeature):
    """Head, trunk, arms and legs of a human silhouette, from its projection histograms.

    The silhouette of a person, a binary mask, is divided into six body parts, each with its bounding box and mask, for the
    analysis of the movement of single parts (the arms, the head) from a plain image. The columns holding the arms are
    found by accumulating the area from each side (``arm_percentage``), the legs by the horizontal extent of the lower rows, the neck by the first row, going up from the
    barycentre, where the body narrows, and each arm by the rows where it holds many pixels. "Right" and "left" are the
    image's: the right arm and the right leg are on the smaller x.

    ``process(silhouette, *, timestamp=None)`` takes one ``(H, W)`` mask (non-zero is body; see the module description for the
    image types); the boxes are in the frame of the mask.

    Parameters
    ----------
    arm_percentage : float, default 0.8
        Fraction of the silhouette area that is not arm, in [0, 1], dimensionless *(live)*.
    legs_search : float, default 0.5
        Fraction of the distance between the barycentre and the feet where the search for the legs starts, dimensionless
        *(live)*.
    legs_offset : float, default 0.2
        Minimal distance between the barycentre and the top of the legs, as a fraction of the same distance, dimensionless
        *(live)*.
    arms_min_threshold : float, default 0.2
        An arm ends at the first row with fewer foreground pixels than this fraction of its width *(live)*.
    arms_max_threshold : float, default 0.5
        An arm starts at the first row with more foreground pixels than this fraction of its width *(live)*.
    parts : sequence of str, default all six
        Which parts to output *(live)*, among ``"right_leg"``, ``"left_leg"``, ``"trunk"``, ``"right_arm"``, ``"left_arm"``
        and ``"head"``.

    Notes
    -----
    **Outputs.** ``regions``: ``(6, 4)`` integer array of ``(x, y, width, height)`` in pixels of the frame, rows in the order
    right_leg, left_leg, trunk, right_arm, left_arm, head, zeros for a part that was not found. ``is_found``: ``(6,)``
    booleans, which parts were found. ``masks``: dict ``part -> (height, width)`` array of 0 and 255 holding the mask of
    each part found. A part is dropped when it is empty or touches the first column or the first row of the frame, as in
    EyesWeb. A mask without foreground is ``INVALID_INPUT`` (``"no foreground pixels in the silhouette"``); an empty image
    too (``"empty image"``). The result is otherwise ``OK`` (no warm-up).

    **Known limitation.** The tests of the original read pixels outside the mask or the region of interest (the neck test
    and the walk over the arm columns, in particular when ``arm_percentage`` is above 1); such pixels count as background.

    **Differences from EyesWeb.** Every output region carries the name of its body part.

    **Corrected in the core.** The barycentre is the centroid of the mask, truncated to whole pixels (the original took the
    normalised centroid of the blob times its width, which is only right for a blob as large as its frame).

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import SilhouetteBodyParts
    >>> rows, columns = np.mgrid[:240, :320]
    >>> body = (abs(columns - 160) <= 28) & (rows >= 60) & (rows <= 140)             # trunk
    >>> body |= ((columns - 160) ** 2 / 18 ** 2 + (rows - 40) ** 2 / 22 ** 2 <= 1)   # head
    >>> body |= (abs(rows - 75) <= 7) & (columns >= 80) & (columns <= 240)           # arms, a horizontal bar
    >>> body |= (abs(columns - 147) <= 9) & (rows > 140) & (rows <= 225)             # legs
    >>> body |= (abs(columns - 173) <= 9) & (rows > 140) & (rows <= 225)
    >>> result = SilhouetteBodyParts().process(body.astype(np.uint8) * 255)
    >>> result.is_found.tolist()
    [True, True, True, True, True, True]
    """
    _core_class = _imaging.BlobSubRegions
    _parts = {part: f"extract_{part}" for part in _BODY_PARTS}
    _INPUTS = Inputs(image_input("silhouette", "mask of the body: every non-zero pixel is foreground"))
    _OUTPUTS = Schema(
        Output("regions", (len(_BODY_PARTS), 4), kind=int, labels=_BODY_PARTS, components=("x", "y", "width", "height"),
               unit="px", doc="bounding box of each part in the frame; zeros where not found"),
        Output("is_found", len(_BODY_PARTS), kind=bool, labels=_BODY_PARTS, doc="the part was found"),
        Output("masks", (None, None), kind=int, labelled=True, doc="0 / 255 mask of each part found"))

    def _from_image(self, mask: np.ndarray, timestamp: Optional[float]) -> Result:
        if not mask.any():
            return self._no_output(Status.INVALID_INPUT, "no foreground pixels in the silhouette", timestamp)
        regions = np.zeros((len(_BODY_PARTS), 4), dtype=int)
        found = np.zeros(len(_BODY_PARTS), dtype=bool)
        masks = {}
        for label, left, top, part_mask in self._block.process(mask):
            slot = _BODY_PARTS.index(label)
            regions[slot] = (left, top, part_mask.shape[1], part_mask.shape[0])
            found[slot] = True
            masks[label] = part_mask
        return self._result(timestamp=timestamp, regions=regions, is_found=found, masks=masks)


@describe(Layer.PHYSICAL_SIGNALS, eyesweb="video_gram (VideoGram)")
class Videogram(_ImageFeature):
    r"""Videogram or motiongram: each frame collapsed to one line, the lines stacked over time.

    A video is summarised in one image that shows its evolution in time: every frame is reduced to a single line (a column
    or a row) and the lines of successive frames are placed side by side, so that a movement becomes a visible trace. With a
    motion image (a frame difference) it is a motiongram (Jensenius, 2006). For a grayscale frame :math:`I(h, w)` and the
    mode ``"horizontal"`` the line of a frame is the sum of each row, scaled by its maximum to 0-255,

    .. math::

        v(h) = 255\, \frac{\sum_w I(h, w)}{\max_h \sum_w I(h, w)},

    each channel of a colour frame being summed and scaled on its own; the mode ``"vertical"`` sums the columns instead.

    ``process(frame, *, timestamp=None)`` takes one ``(H, W)`` or ``(H, W, C)`` image with 1, 3 or 4 channels (see the module
    description for the image types). The first frame fixes the size; a frame of another size restarts the videogram (the
    result says so in ``reason``).

    Parameters
    ----------
    window : int, default 500
        Number of lines of the videogram, >= 1 *(structural)*; changing it restarts the image.
    mode : {"horizontal", "vertical"}, default "horizontal"
        ``"horizontal"``: each frame becomes a column (the sum of each row) of an image ``window`` wide and ``H`` high;
        ``"vertical"``: a row (the sum of each column) of an image ``W`` wide and ``window`` high *(structural)*. Changing
        it restarts the image.
    direction : {"left_to_right", "right_to_left"}, default "left_to_right"
        Where the newest line is written *(live)*; the position wraps around so that the oldest line is overwritten.
    end_of_image_mode : {"loop", "scroll"}, default "loop"
        ``"loop"``: the image as it is; ``"scroll"``: once it has been filled, the image is rotated so that the oldest line
        comes first *(live)*.

    Notes
    -----
    **Outputs.** ``videogram``: integer image in 0-255, channels last, of shape ``(H, window, C)`` (``"horizontal"``) or
    ``(window, W, C)`` (``"vertical"``); ``C = 1`` for a grayscale input. The lines not written yet are 0. A line of an
    entirely black frame is 0. The result is ``OK`` on every valid call. An empty image is ``INVALID_INPUT``. The output
    is an image: ``result.to_frame()`` and the recorder have no value columns for it.

    **Corrected in the core.** The channel sums are independent: in the original the accumulators of the channels aliased each
    other, so with one channel the next pixel was added to channel 0 (and a byte past the end of the row was read), and with
    three channels the first byte of the next pixel was.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.physical_signals import Videogram
    >>> videogram = Videogram(window=4)
    >>> frame = np.zeros((3, 2), dtype=np.uint8)
    >>> frame[1] = (10, 30)                                       # only the middle row holds signal
    >>> videogram.process(frame).videogram[:, 0, 0].tolist()      # the first line: its row sums, scaled to 255
    [0, 255, 0]
    >>> videogram.process(frame * 2).videogram.shape              # a second line is written next to it
    (3, 4, 1)
    """
    _core_class = _imaging.VideoGram
    _core_names = {"window": "length"}
    _INPUTS = Inputs(image_input("frame", "grayscale or colour frame", channels=None))
    _OUTPUTS = Schema(Output("videogram", (None, None, None), kind=int, doc="the videogram image, channels last"))

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
        return self._result(timestamp=timestamp, videogram=self._to_image(self._block.process(image)),
                           reason="frame size changed: videogram restarted" if restarted else "")

    @staticmethod
    def _to_image(raw: np.ndarray) -> np.ndarray:
        return raw.reshape(raw.shape[0], raw.shape[1], -1)

    def reset(self) -> None:
        self._frame_shape = None
        super().reset()


__all__ = ["SilhouetteCentroids", "SilhouetteBodyParts", "Videogram"]
