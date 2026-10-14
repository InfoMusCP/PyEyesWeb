"""Discovery metadata: where each feature sits in the conceptual model, and `catalog()` to list them.

The conceptual model (Camurri et al.) has four layers plus the analysis primitives that span them:

| Layer | Timescale | Content |
|---|---|---|
| `PHYSICAL_SIGNALS` | frame, continuous | physical signals and virtual sensors: skeletons, images, space, body models |
| `LOW_LEVEL` | up to ~0.5 s | kinematics, energy, shape, symmetry, smoothness |
| `MID_LEVEL` | 0.5-3 s | amodal gesture features: segments, impulsivity, space occupation |
| `HIGH_LEVEL` | 3 s and above | qualities communicated (social and interaction level) |
| `ANALYSIS_PRIMITIVE` | any | metrics applicable to any movement feature at any layer |

Placement rule: a feature goes to the layer of what it needs as input and gives as output, not to the layer of its
EyesWeb block.

- Physical signals: produces a signal from raw frames or a model and gives a signal again (simulating a body, extracting
  centroids or parts from an image, locating points in a grid); stream plumbing that feeds the features belongs here too.
- Low-level: measures one frame, or a short window the feature buffers itself, of a signal (kinematics, energy, symmetry,
  smoothness), including the shape and the filtering of a contour and a path given as a list of points (directness,
  non-planarity).
- Mid-level: needs a whole gesture: the segmentation of gestures, impulsivity, suddenness, space occupied over time.
- High-level: needs several people.
- Analysis primitive: takes any scalar, vector or event signal and knows nothing of bodies, skeletons or geometry.

Every feature class carries `LAYER`, `TIMESCALE` and `EYESWEB_BLOCK` (the EyesWeb block it comes from, `None` when
it has none), set with `@describe`. `catalog()` lists them, and
`catalog_table()` renders the "Implemented" tables of the documentation.
"""

import enum
import importlib
from dataclasses import dataclass
from typing import List, Optional, Type

__all__ = ["Layer", "Timescale", "FeatureInfo", "describe", "catalog", "catalog_table"]


class Layer(enum.Enum):
    PHYSICAL_SIGNALS = "physical_signals"
    LOW_LEVEL = "low_level"
    MID_LEVEL = "mid_level"
    HIGH_LEVEL = "high_level"
    ANALYSIS_PRIMITIVE = "analysis_primitives"

    @property
    def package(self) -> str:
        return f"pyeyesweb.{self.value}"

    @property
    def title(self) -> str:
        return {"physical_signals": "Layer 1: physical signals", "low_level": "Layer 2: low-level features",
                "mid_level": "Layer 3: mid-level features", "high_level": "Layer 4: qualities communication",
                "analysis_primitives": "Analysis primitives"}[self.value]


class Timescale(enum.Enum):
    FRAME = "frame"
    SHORT = "up to ~0.5 s"
    MEDIUM = "0.5-3 s"
    LONG = "3 s and above"
    ANY = "any"


_DEFAULT_TIMESCALE = {
    Layer.PHYSICAL_SIGNALS: Timescale.FRAME,
    Layer.LOW_LEVEL: Timescale.SHORT,
    Layer.MID_LEVEL: Timescale.MEDIUM,
    Layer.HIGH_LEVEL: Timescale.LONG,
    Layer.ANALYSIS_PRIMITIVE: Timescale.ANY,
}


def describe(layer: Layer, *, timescale: Optional[Timescale] = None, eyesweb: Optional[str] = None):
    """Class decorator: attach `LAYER`, `TIMESCALE` and `EYESWEB_BLOCK` (the EyesWeb block the feature comes from, if any)."""

    def apply(cls: Type) -> Type:
        cls.LAYER = layer
        cls.TIMESCALE = timescale or _DEFAULT_TIMESCALE[layer]
        cls.EYESWEB_BLOCK = eyesweb
        return cls

    return apply


@dataclass(frozen=True)
class FeatureInfo:
    name: str
    layer: Layer
    timescale: Timescale
    eyesweb_block: Optional[str]
    module: str
    summary: str
    cls: Type


def _summary(cls: Type) -> str:
    lines = [line.strip() for line in (cls.__doc__ or "").strip().splitlines()]
    return lines[0] if lines else ""


def catalog(layer: Optional[Layer] = None) -> List[FeatureInfo]:
    """Every described feature of the conceptual tree, in layer order. Needs the compiled EyesWeb core, which the
    layer packages import. Filter by `layer`."""
    entries: List[FeatureInfo] = []
    for lay in [layer] if layer else list(Layer):
        package = importlib.import_module(lay.package)
        for name in package.__all__:
            obj = getattr(package, name)
            if isinstance(obj, type) and obj.__name__ == name and getattr(obj, "LAYER", None) is lay:
                entries.append(FeatureInfo(name, lay, obj.TIMESCALE, obj.EYESWEB_BLOCK, obj.__module__,
                                           _summary(obj), obj))
    return entries


def catalog_table(layer: Layer) -> str:
    """Markdown table of the features of one layer (documentation's "Implemented" tables are generated from it)."""
    rows = ["| Feature | Timescale | EyesWeb block |", "|---|---|---|"]
    for info in catalog(layer):
        rows.append(f"| `{info.name}` | {info.timescale.value} | {info.eyesweb_block or ''} |")
    return "\n".join(rows)
