"""Discovery metadata: where each feature sits in the conceptual model, and ``catalog()`` to list them.

The conceptual model (Camurri et al.) has four layers plus the analysis primitives that span them:

====================== ================= ===========================================================================
Layer                  Timescale         Content
====================== ================= ===========================================================================
``PHYSICAL_SIGNALS``   frame, continuous physical signals and virtual sensors: skeletons, images, space, body models
``LOW_LEVEL``          up to ~0.5 s      kinematics, energy, shape, symmetry, smoothness
``MID_LEVEL``          0.5-3 s           amodal gesture features: segments, impulsivity, space occupation
``HIGH_LEVEL``         3 s and above     qualities communicated (social and interaction level)
``ANALYSIS_PRIMITIVE`` any               metrics applicable to any movement feature at any layer
====================== ================= ===========================================================================

Placement rule: a feature goes to the layer of what it needs as input and gives as output, not to the layer of its
EyesWeb block.

- Physical signals: produces a signal from raw frames or a model and gives a signal again (simulating a body,
  extracting centroids or parts from an image, locating points in a grid); stream plumbing that feeds the features
  belongs here too.
- Low-level: measures one frame, or a short window the feature buffers itself, of a signal (kinematics, energy,
  symmetry, smoothness), including the shape and the filtering of a contour and a path given as a list of points
  (directness, non-planarity).
- Mid-level: needs a whole gesture: the segmentation of gestures, impulsivity, suddenness, space occupied over time.
- High-level: needs several people.
- Analysis primitive: takes any scalar, vector or event signal and knows nothing of bodies, skeletons or geometry.

Every feature class carries ``LAYER``, ``TIMESCALE`` and ``EYESWEB_BLOCK`` (the EyesWeb block it comes from, ``None``
when it has none). ``catalog()`` lists them, and ``catalog_table()`` renders the "Implemented" tables of the
documentation. The layer packages need the compiled EyesWeb core; the types of this module do not.
"""

import enum
import importlib
from dataclasses import dataclass
from typing import List, Optional, Type

__all__ = ["Layer", "Timescale", "FeatureInfo", "describe", "catalog", "catalog_table"]


class Layer(enum.Enum):
    """A layer of the conceptual model, or the analysis primitives that span them.

    Attributes
    ----------
    PHYSICAL_SIGNALS : ``"physical_signals"``
        Layer 1: physical signals and virtual sensors.
    LOW_LEVEL : ``"low_level"``
        Layer 2: low-level features.
    MID_LEVEL : ``"mid_level"``
        Layer 3: mid-level features.
    HIGH_LEVEL : ``"high_level"``
        Layer 4: qualities communicated.
    ANALYSIS_PRIMITIVE : ``"analysis_primitives"``
        Metrics applicable to any movement feature at any layer.

    Examples
    --------
    >>> from pyeyesweb import Layer
    >>> Layer.LOW_LEVEL.package, Layer.LOW_LEVEL.title
    ('pyeyesweb.low_level', 'Layer 2: low-level features')
    >>> Layer("analysis_primitives") is Layer.ANALYSIS_PRIMITIVE
    True
    """

    PHYSICAL_SIGNALS = "physical_signals"
    LOW_LEVEL = "low_level"
    MID_LEVEL = "mid_level"
    HIGH_LEVEL = "high_level"
    ANALYSIS_PRIMITIVE = "analysis_primitives"

    @property
    def package(self) -> str:
        """Dotted name of the package holding the features of the layer."""
        return f"pyeyesweb.{self.value}"

    @property
    def title(self) -> str:
        """Heading of the layer in the documentation."""
        return {"physical_signals": "Layer 1: physical signals", "low_level": "Layer 2: low-level features",
                "mid_level": "Layer 3: mid-level features", "high_level": "Layer 4: qualities communicated",
                "analysis_primitives": "Analysis primitives"}[self.value]


class Timescale(enum.Enum):
    """The time span a feature needs in order to produce a value.

    Attributes
    ----------
    FRAME : ``"frame"``
        One frame (the default of the physical signals).
    SHORT : ``"up to ~0.5 s"``
        Up to about half a second (the default of the low-level features).
    MEDIUM : ``"0.5-3 s"``
        Half a second to three seconds (the default of the mid-level features).
    LONG : ``"3 s and above"``
        Three seconds and more (the default of the high-level features).
    ANY : ``"any"``
        No intrinsic timescale (the default of the analysis primitives).

    The ``value`` of a member is the text shown in the catalog tables.

    Examples
    --------
    >>> from pyeyesweb import Timescale
    >>> [timescale.value for timescale in Timescale]
    ['frame', 'up to ~0.5 s', '0.5-3 s', '3 s and above', 'any']
    """

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
    """Class decorator: attach ``LAYER``, ``TIMESCALE`` and ``EYESWEB_BLOCK`` to a feature class.

    Parameters
    ----------
    layer : Layer
        The layer of the feature (see the placement rule in the module documentation).
    timescale : Timescale, optional
        Defaults to the timescale of the layer.
    eyesweb : str, optional
        The EyesWeb block the feature comes from, if any.
    """

    def apply(cls: Type) -> Type:
        cls.LAYER = layer
        cls.TIMESCALE = timescale or _DEFAULT_TIMESCALE[layer]
        cls.EYESWEB_BLOCK = eyesweb
        return cls

    return apply


@dataclass(frozen=True)
class FeatureInfo:
    """The catalog entry of one feature.

    Attributes
    ----------
    name : str
        Class name.
    layer : Layer
        Layer of the conceptual model.
    timescale : Timescale
        Time span the feature needs.
    eyesweb_block : str or None
        The EyesWeb block the feature comes from; ``None`` for the lab features that have none.
    module : str
        Module that defines the class.
    summary : str
        The one-line summary: the first line of the class docstring.
    cls : type
        The feature class.

    Examples
    --------
    >>> from pyeyesweb import Layer, catalog
    >>> info = catalog(Layer.LOW_LEVEL)[0]
    >>> info.layer, info.name == info.cls.__name__, bool(info.summary)
    (<Layer.LOW_LEVEL: 'low_level'>, True, True)
    """

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
    """Every described feature of the conceptual tree, in layer order.

    Needs the compiled EyesWeb core, which the layer packages import.

    Parameters
    ----------
    layer : Layer, optional
        List only the features of this layer.

    Returns
    -------
    list of FeatureInfo
        One entry per feature class.

    Examples
    --------
    >>> from pyeyesweb import Layer, catalog
    >>> features = catalog()
    >>> len(features) > 40, len(catalog(Layer.LOW_LEVEL)) < len(features)
    (True, True)
    >>> info = next(info for info in features if info.name == "KineticEnergy")
    >>> info.layer.name, info.timescale.value
    ('LOW_LEVEL', 'up to ~0.5 s')
    """
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
    """Markdown table of the features of one layer.

    The "Implemented" tables of the documentation are generated from it. Needs the compiled EyesWeb core.

    Parameters
    ----------
    layer : Layer
        The layer to list.

    Returns
    -------
    str
        A table with the columns ``Feature``, ``Timescale`` and ``EyesWeb block``.

    Examples
    --------
    >>> from pyeyesweb import Layer, catalog_table
    >>> catalog_table(Layer.LOW_LEVEL).splitlines()[0]
    '| Feature | Timescale | EyesWeb block |'
    """
    rows = ["| Feature | Timescale | EyesWeb block |", "|---|---|---|"]
    for info in catalog(layer):
        rows.append(f"| `{info.name}` | {info.timescale.value} | {info.eyesweb_block or ''} |")
    return "\n".join(rows)
