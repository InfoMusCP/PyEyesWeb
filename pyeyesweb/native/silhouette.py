"""Silhouette features (EyesWeb catalog *BaseImaging*, native C++).

These work on a binary body mask, e.g. the Azure Kinect *body index map*
(see :func:`mask_from_body_index`), not on skeleton joints, so they are not
:class:`~pyeyesweb.data_models.base.BaseFeature`: call ``compute(mask)``
(or the feature itself) once per video frame.

* :class:`SilhouetteCentroids` - hierarchical centroids (COG, head,
  shoulders, elbows, hands, knees, feet) of the silhouette (EyesWeb
  *Centroids Calc*).
* :class:`BodySubRegions` - bounding boxes of head, trunk, arms and legs
  from projection histograms (EyesWeb *BlobSubRegions*).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_numeric

from ._backend import require

#: Value of background pixels in the Azure Kinect body index map.
AZURE_BODY_INDEX_BACKGROUND = 255

_SILHOUETTE_TYPES = ("full", "upper", "lower", "left", "right")


def mask_from_body_index(body_index_map: np.ndarray, body_index: Optional[int] = None) -> np.ndarray:
    """Binary mask (0 / 255, uint8) from an Azure Kinect body index map.

    Parameters
    ----------
    body_index_map : numpy.ndarray of shape (H, W), uint8
        255 = background, otherwise the index of the body in the frame.
    body_index : int, optional
        Keep only this body; ``None`` keeps every body.
    """
    bim = np.asarray(body_index_map)
    if bim.ndim != 2:
        raise ValueError(f"expected a (H, W) body index map, got shape {bim.shape}")
    sel = bim != AZURE_BODY_INDEX_BACKGROUND if body_index is None else bim == body_index
    return sel.view(np.uint8) * np.uint8(255)


def crop_to_blob(mask: np.ndarray) -> Optional[Tuple[np.ndarray, Tuple[int, int], Tuple[int, int]]]:
    """Crop a full-frame mask to its bounding box.

    Returns ``(cropped_mask, (x0, y0), (width, height))`` - the EyesWeb blob
    representation expected by ``eyw_core`` - or ``None`` if the mask is empty.
    """
    mask = np.asarray(mask)
    if mask.ndim == 3:
        mask = mask[:, :, 0]
    if mask.ndim != 2:
        raise ValueError(f"expected a (H, W) mask, got shape {mask.shape}")
    rows = np.flatnonzero(mask.any(axis=1))
    if len(rows) == 0:
        return None
    y0, y1 = rows[0], rows[-1] + 1
    cols = np.flatnonzero(mask[y0:y1].any(axis=0))
    x0, x1 = cols[0], cols[-1] + 1
    crop = (mask[y0:y1, x0:x1] > 0).view(np.uint8) * np.uint8(255)
    return crop, (int(x0), int(y0)), (int(mask.shape[1]), int(mask.shape[0]))


class _ImageFeature:
    """Minimal base: ``feature(mask)`` is the same as ``feature.compute(mask)``."""

    def __call__(self, mask: np.ndarray) -> FeatureResult:
        return self.compute(mask)

    def compute(self, mask: np.ndarray) -> FeatureResult:  # pragma: no cover - abstract
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Centroids
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class SilhouetteCentroidsResult(FeatureResult):
    """Output contract of :class:`SilhouetteCentroids`.

    Attributes
    ----------
    centroids : dict
        ``{label: (x, y)}`` with EyesWeb labels (``"cog"``, ``"head"``,
        ``"left_shoulder"``, ... ``"right_foot"``).  Pixels of the input
        frame, or ``[0, 1]`` if ``normalized``.  *Left* / *right* refer to
        the image (left = smaller x), as in EyesWeb.
    """
    centroids: Dict[str, Tuple[float, float]] = field(default_factory=dict)


class SilhouetteCentroids(_ImageFeature):
    """Hierarchical centroids of a human silhouette (EyesWeb Centroids Calc).

    Parameters
    ----------
    silhouette_type : {"full", "upper", "lower", "left", "right"}
        Which part of the body the silhouette shows.
    normalized : bool
        Return coordinates divided by the frame size.
    filter_alpha : float, optional
        Exponential smoothing of every centroid over time
        (``filtered += alpha * (new - filtered)``); ``None`` disables it.
    """

    def __init__(self, silhouette_type: str = "full", normalized: bool = False,
                 filter_alpha: Optional[float] = None):
        if silhouette_type not in _SILHOUETTE_TYPES:
            raise ValueError(f"silhouette_type must be one of {_SILHOUETTE_TYPES}")
        eyw = require()
        st = getattr(eyw.imaging.SilhouetteType, silhouette_type.capitalize())
        self._impl = eyw.imaging.CentroidsCalc(st)
        self.normalized = bool(normalized)
        if filter_alpha is not None:
            self._impl.set_filter(True, validate_numeric(filter_alpha, "filter_alpha", min_val=0.0, max_val=1.0))

    def reset(self) -> None:
        """Reset the temporal filter."""
        self._impl.reset()

    def compute(self, mask: np.ndarray) -> SilhouetteCentroidsResult:
        blob = crop_to_blob(mask)
        if blob is None:
            return SilhouetteCentroidsResult(is_valid=False)
        crop, origin, size = blob
        c = self._impl.compute(crop, origin=origin, frame_size=size, normalized=self.normalized)
        if not c:
            return SilhouetteCentroidsResult(is_valid=False)
        return SilhouetteCentroidsResult(centroids={k: (float(v[0]), float(v[1])) for k, v in c.items()})


# ---------------------------------------------------------------------------
# Sub-regions
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BodySubRegionsResult(FeatureResult):
    """Output contract of :class:`BodySubRegions`.

    Attributes
    ----------
    regions : dict
        ``{part: (x, y, width, height)}`` in pixels of the input frame, for
        the parts found among head, trunk, left/right arm, left/right leg.
    """
    regions: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict)


class BodySubRegions(_ImageFeature):
    """Splits a silhouette into head, trunk, arms and legs (EyesWeb BlobSubRegions).

    Parameters
    ----------
    arm_percentage : float, optional
        Override of the EyesWeb parameter of the same name; any other
        ``eyw_core.imaging.BlobSubRegionsParams`` field can be passed as a
        keyword argument too.
    """

    def __init__(self, **params):
        eyw = require()
        p = eyw.imaging.BlobSubRegionsParams()
        for k, v in params.items():
            if not hasattr(p, k):
                raise ValueError(f"unknown BlobSubRegions parameter {k!r}")
            setattr(p, k, v)
        self._impl = eyw.imaging.BlobSubRegions(p)

    def compute(self, mask: np.ndarray) -> BodySubRegionsResult:
        blob = crop_to_blob(mask)
        if blob is None:
            return BodySubRegionsResult(is_valid=False)
        crop, origin, size = blob
        parts = self._impl.compute(crop, origin=origin, frame_size=size)
        return BodySubRegionsResult(regions={r["part"]: tuple(int(v) for v in r["rect"]) for r in parts})
