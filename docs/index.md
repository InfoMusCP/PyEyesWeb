# PyEyesWeb

PyEyesWeb is a research toolkit for the analysis of expressive movement, built on the EyesWeb Expressive Gesture Analysis library.

```
pip install pyeyesweb
```

The catalog holds {{ n_features }} features, organised in five layers, from physical signals to high-level descriptors (compiled core {{ core_version }}).

<!-- TODO(WP5): replace this paragraph by the executed 10-line example. -->

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} Physical signals
:link: user_guide/physical_signals
:link-type: doc

{{ n_physical_signals }} features. <!-- TODO(WP6): timescale line -->
:::

:::{grid-item-card} Low-level features
:link: user_guide/low_level
:link-type: doc

{{ n_low_level }} features.
:::

:::{grid-item-card} Mid-level features
:link: user_guide/mid_level
:link-type: doc

{{ n_mid_level }} features.
:::

:::{grid-item-card} High-level features
:link: user_guide/high_level
:link-type: doc

{{ n_high_level }} feature.
:::

:::{grid-item-card} Analysis primitives
:link: user_guide/analysis_primitives
:link-type: doc

{{ n_analysis_primitives }} features.
:::
::::

::::{grid} 1 2 4 4
:gutter: 3

:::{grid-item-card} Getting started
:link: getting_started/install
:link-type: doc
:::

:::{grid-item-card} Concepts
:link: concepts/layers
:link-type: doc
:::

:::{grid-item-card} Tutorials
:link: tutorials/index
:link-type: doc

Executed tutorials, from the first feature to a real-time loop, each downloadable as a notebook.
:::

:::{grid-item-card} API reference
:link: api/overview
:link-type: doc
:::
::::

## Funding and citation

Developed with the partial support of the [EU ICT STARTS Resilence project](https://resilence.eu/).
TODO(WP8): citation block (CITATION.cff).

```{toctree}
:hidden:
:caption: Getting started
:maxdepth: 1

getting_started/install
getting_started/quickstart
```

```{toctree}
:hidden:
:caption: Concepts
:maxdepth: 1

concepts/layers
concepts/inputs
concepts/results
concepts/time_units_parameters
```

```{toctree}
:hidden:
:caption: Theory
:maxdepth: 1

theory/framework
theory/notation
theory/kinematics_energy
theory/smoothness
theory/shape_symmetry_balance
theory/impulsivity_suddenness
theory/gesture_segmentation
theory/entropy_rarity_periodicity
theory/synchronization
theory/dominance
theory/humanoid_models
theory/imaging
```

```{toctree}
:hidden:
:caption: User guide
:maxdepth: 1

user_guide/physical_signals
user_guide/low_level
user_guide/mid_level
user_guide/high_level
user_guide/analysis_primitives
```

```{toctree}
:hidden:
:caption: API reference
:maxdepth: 1

api/overview
api/data_models
api/skeletons
api/datasets
api/catalog
```

```{toctree}
:hidden:
:caption: Tutorials and how-tos
:maxdepth: 1

tutorials/index
howto/load_data
howto/map_skeleton
howto/realtime_live_parameters
howto/batch_to_pandas
howto/images
```

```{toctree}
:hidden:
:caption: Developer guide
:maxdepth: 1

developer/architecture
developer/conventions
developer/porting_status
developer/adding_a_feature
developer/building_the_docs
```

```{toctree}
:hidden:
:caption: Project
:maxdepth: 1

changelog
migration
references
```
