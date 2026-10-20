# PyEyesWeb

PyEyesWeb is a research toolkit for the analysis of expressive movement, built on the EyesWeb Expressive Gesture Analysis library.

```
pip install pyeyesweb
```

The catalog holds {{ n_features }} features, organised in four layers, from physical signals to high-level descriptors, and the analysis primitives (compiled core {{ core_version }}).

A feature processes one sample at a time (`process`) or a whole recording (`run`); both give the same numbers.

```{doctest}
>>> from pyeyesweb.low_level import SpectralArcLength
>>> rate = 100.0                                              # samples per second
>>> time = np.arange(300) / rate                              # seconds
>>> speed = 0.6 * np.exp(-0.5 * ((time - 1.5) / 0.4) ** 2)    # one smooth reach, m/s
>>> feature = SpectralArcLength(window=100, sampling_rate=rate)
>>> recording = feature.run(speed, timestamps=time)           # a whole recording gives a Recorder
>>> print(recording)
Recorder(SpectralArcLength, rows=300, columns=['spectral_arc_length'], status={'OK': 201, 'WARMING_UP': 99})
>>> print(recording[-1])                                      # a row is a Result
SpectralArcLengthResult(status=OK, spectral_arc_length=-1.63417)
>>> feature.reset()                                           # streaming: one sample per call
>>> print(feature.process(speed[0], timestamp=time[0]))
SpectralArcLengthResult(status=WARMING_UP, reason='1 of 100 samples', spectral_arc_length=nan)
```

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} Physical signals
:link: user_guide/physical_signals
:link-type: doc

{{ n_physical_signals }} features. Timescale: {{ ts_physical_signals }}.
:::

:::{grid-item-card} Low-level features
:link: user_guide/low_level
:link-type: doc

{{ n_low_level }} features. Timescale: {{ ts_low_level }}.
:::

:::{grid-item-card} Mid-level features
:link: user_guide/mid_level
:link-type: doc

{{ n_mid_level }} features. Timescale: {{ ts_mid_level }}.
:::

:::{grid-item-card} High-level features
:link: user_guide/high_level
:link-type: doc

{{ n_high_level }} feature. Timescale: {{ ts_high_level }}.
:::

:::{grid-item-card} Analysis primitives
:link: user_guide/analysis_primitives
:link-type: doc

{{ n_analysis_primitives }} features. Timescale: {{ ts_analysis_primitives }}.
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

If you use PyEyesWeb in your research, please cite (from `CITATION.cff` in the repository):

> S. R. Sabharwal, N. Corbellini, S. Ghisio, P. Coletta, G. Romano, A. A. Foysal, G. Volpe and A. Camurri.
> PyEyesWeb: An open source toolkit for multimodal movement feature extraction. In *MOCO '26: Proceedings of the 10th
> International Conference on Movement and Computing*, ACM, 2026. [doi:10.1145/3802842.3802904](https://doi.org/10.1145/3802842.3802904)

```bibtex
@inproceedings{sabharwal2026pyeyesweb,
  author    = {Sabharwal, Sanket Rajeev and Corbellini, Nicola and Ghisio, Simone and Coletta, Paolo and
               Romano, Gabriele and Foysal, Abdullah Al and Volpe, Gualtiero and Camurri, Antonio},
  title     = {PyEyesWeb: An open source toolkit for multimodal movement feature extraction},
  booktitle = {MOCO '26: Proceedings of the 10th International Conference on Movement and Computing},
  publisher = {ACM},
  year      = {2026},
  doi       = {10.1145/3802842.3802904}
}
```

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
