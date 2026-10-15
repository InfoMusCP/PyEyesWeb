# Layers and the catalog

PyEyesWeb organises its features after the multi-layer conceptual model of expressive gesture of Camurri and colleagues
(see {doc}`../theory/framework`). The model describes movement at increasing levels of abstraction, from the signals a
sensor gives to the qualities an observer perceives, and attaches to each level a time span over which a quantity is
meaningful. The library has one package for each level, and a fifth package for measures that do not belong to any one level.
Every feature belongs to exactly one package.

## The five groups

| Group | Package | Timescale | Features | Content |
|---|---|---|---|---|
| Layer 1: physical signals | `pyeyesweb.physical_signals` | frame | {{ n_physical_signals }} | Signals and virtual sensors: simulating a body, centroids and body parts from an image, locating points in a grid. |
| Layer 2: low-level features | `pyeyesweb.low_level` | up to about 0.5 s | {{ n_low_level }} | Measures of one frame, or of a short window: kinematics, energy, contraction, symmetry, balance, smoothness, contour shape, the directness of a path. |
| Layer 3: mid-level features | `pyeyesweb.mid_level` | 0.5 to 3 s | {{ n_mid_level }} | Features of a gesture: segmentation, impulsivity, suddenness, space occupied over time. |
| Layer 4: qualities communicated | `pyeyesweb.high_level` | 3 s and above | {{ n_high_level }} | Social and interaction-level qualities, which need several people. |
| Analysis primitives | `pyeyesweb.analysis_primitives` | any | {{ n_analysis_primitives }} | Metrics for any scalar, vector or event signal, such as entropy, periodicity and synchronization. |

The **timescale** is the span of movement a value summarises: a frame, up to about half a second (a movement fragment),
half a second to three seconds (a gesture), or longer (a phrase or an interaction). It is a property of the layer, not a
promise about every parameter choice: a window of a low-level feature can be made longer than half a second, but the
quantity it measures is still one of a movement fragment. Analysis primitives have no timescale of their own, because
they take whatever signal they are given.

The groups are used as follows.

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy
>>> from pyeyesweb.mid_level import GestureSegmenter
>>> from pyeyesweb.analysis_primitives import SampleEntropy
```

Importing a package loads the compiled core (see {doc}`../getting_started/install`).

## Where a feature goes

A feature goes to the layer of what it needs as input and of what it gives as output, not to the layer of the EyesWeb block
it was ported from.

- **Physical signals** take raw frames or a model and give a signal again: they simulate a body, extract centroids or parts
  from an image, or locate points in a grid. Stream plumbing that feeds the features belongs here too.
- **Low-level** features measure one frame, or a short window that the feature buffers itself, of a signal. This includes the
  shape and filtering of a contour, and a path given as a list of points (its directness and its non-planarity).
- **Mid-level** features need a whole gesture: the segmentation of gestures, impulsivity, suddenness, the space occupied over
  time.
- **High-level** features need several people.
- An **analysis primitive** takes any scalar, vector or event signal and knows nothing of bodies, skeletons or geometry.

So `FilterContour`, `Directness` and `TrajectoryNonPlanarity` are low-level features, and the synchronization measures
between signals are analysis primitives although they are mostly applied to movement.

## Browsing the catalog

{py:func}`pyeyesweb.catalog.catalog` returns one {py:class}`~pyeyesweb.catalog.FeatureInfo` per feature, in layer order:
the class, its layer and timescale, a one-sentence summary, the module, and the EyesWeb block it comes from when it has one.
Pass a {py:class}`~pyeyesweb.catalog.Layer` to list one group.

```{doctest}
>>> from collections import Counter
>>> from pyeyesweb import Layer, catalog
>>> features = catalog()
>>> Counter(info.layer.value for info in features)
Counter({'low_level': 22, 'analysis_primitives': 19, 'physical_signals': 11, 'mid_level': 7, 'high_level': 1})
>>> [info.name for info in catalog(Layer.MID_LEVEL)]
['GestureSegmenter', 'MotionDuration', 'Suddenness', 'SuddennessImpulsivity', 'ContractionImpulsivity', 'PositionDependingPotentials', 'RegionDependingPotentials']
>>> info = next(info for info in features if info.name == "KineticEnergy")
>>> info.layer.title, info.timescale.value
('Layer 2: low-level features', 'up to ~0.5 s')
>>> info.summary
'Weighted kinetic energy of a set of labelled 3D points, such as the joints of a skeleton.'
>>> info.eyesweb_block
'KineticEnergyIndex (KineticEnergy)'
```

The same metadata is on the class itself, so a feature can be asked where it belongs without the catalog:

```{doctest}
>>> KineticEnergy.LAYER.name, KineticEnergy.TIMESCALE.value
('LOW_LEVEL', 'up to ~0.5 s')
>>> KineticEnergy.EYESWEB_BLOCK
'KineticEnergyIndex (KineticEnergy)'
```

`eyesweb_block` is `None` for the features that PyEyesWeb adds to the set of EyesWeb blocks:

```{doctest}
>>> [info.name for info in features if info.eyesweb_block is None]
['BoundingBoxFilledArea', 'SpectralArcLength', 'LogDimensionlessJerk', 'Harmonicity', 'SubmovementCount', 'CurvatureDispersion', 'Equilibrium', 'DirectionChange', 'Suddenness', 'SuddennessImpulsivity', 'EnsembleDominance', 'MultiScaleEntropy', 'PhaseLockingValue']
```

{py:func}`pyeyesweb.catalog.catalog_table` renders the features of one layer as a Markdown table. On this site, the
{doc}`../api/overview` lists every group with its features, and each feature has its own page with its parameters, inputs,
outputs and references.

## Using the catalog programmatically

Because every feature declares its inputs and outputs before it sees data (see {doc}`inputs` and {doc}`results`), the catalog
can drive generic code, for example to list the features that work on a window:

```{doctest}
>>> from pyeyesweb.data_models import WindowedFeature
>>> sorted(info.name for info in catalog(Layer.LOW_LEVEL) if issubclass(info.cls, WindowedFeature))
['CurvatureVelocityCorrelation', 'DirectionChange', 'Harmonicity', 'LogDimensionlessJerk', 'SpectralArcLength', 'SubmovementCount']
```
