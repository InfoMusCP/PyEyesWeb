# Architecture and contract

This page describes how PyEyesWeb is built and the contract every feature obeys. It is written for people who change the library
or add a feature; users of the library need only {doc}`../concepts/results` and {doc}`../concepts/inputs`. The page repeats nothing
that the generated reference holds ({doc}`../api/data_models`); it explains how the parts fit together. Rules marked as decided
were chosen by the maintainers and are not changed without asking.

## Two pieces

PyEyesWeb is a Python layer over a compiled port of the EyesWeb Expressive Gesture Analysis library.

| Piece | Job |
|---|---|
| the compiled core, the package `eyesweb_core` | The algorithms: ports of EyesWeb blocks and the features of the laboratory that have no EyesWeb original. It exposes each block as a class with a Python binding. It contains no call contract and no validation of what users give. |
| the Python package `pyeyesweb` (this repository) | The public interface: one call contract, validation, discovery (`catalog()`), results. Pure Python. |

The source of the core is not part of this repository. `pyeyesweb` contains Python only and depends on the compiled package. The
core is independent of Python, so that it can be used from other hosts as well; the logic therefore belongs in the core, the
validation and the call contract in the Python layer.

### The core as a separate package

`pyeyesweb._core` is the only module that imports the compiled package. It does three things when `pyeyesweb` loads a feature
package.

1. If the environment variable `EYESWEB_CORE_PATH` is set, that folder is put first on `sys.path`: this is how a development build
   of the core is used. The import fails if the module found is not the one in that folder, for example because another copy was
   already loaded.
2. It imports `eyesweb_core`. If there is none, `ImportError` tells the user to install the package or to set `EYESWEB_CORE_PATH`.
3. It checks the version. `REQUIRED_CORE` is a `(major, minor)` pair, now `(2, 0)`; the package and the core are released together,
   and a core of another major or minor version, or a module with no `__version__`, raises `ImportError` ("Rebuild or reinstall the
   core").

```{doctest}
>>> from pyeyesweb import _core
>>> _core.REQUIRED_CORE
(2, 0)
>>> _core.core.__version__.split(".")[:2]
['2', '0']
```

`import pyeyesweb`, `pyeyesweb.data_models`, `Layer` and `Timescale` need no core. `catalog()` and the layer packages
(`low_level`, ...) do, because they import the features. Without the core the test suite collects only the tests of the pure Python
data model.

```{admonition} Packaging status
:class: note

The decision is that the core is published as a binary wheel `eyesweb-core` on PyPI and that `pyeyesweb` depends on it, so that
`pip install pyeyesweb` brings both. The packaging has not been done yet; until it is, a development install needs a build of the
core and `EYESWEB_CORE_PATH`, as described in {doc}`building_the_docs`.
```

## Packages

The packages follow the conceptual model of movement qualities ({doc}`../concepts/layers`).

| Package | Layer | Content |
|---|---|---|
| `pyeyesweb.physical_signals` | 1 | physical signals and virtual sensors: body models, space, images, stream plumbing |
| `pyeyesweb.low_level` | 2 | kinematics, energy, shape, symmetry, smoothness (up to about 0.5 s) |
| `pyeyesweb.mid_level` | 3 | gestures, impulsivity, suddenness (0.5 to 3 s) |
| `pyeyesweb.high_level` | 4 | features of several people (3 s and above) |
| `pyeyesweb.analysis_primitives` | any | metrics for any signal: entropy, rarity, periodicity, `synchronization` |
| `pyeyesweb.data_models` | | the contract: `Feature`, `WindowedFeature`, `Input`, `Inputs`, `InputKind`, `Output`, `Schema`, `Result`, `Status`, `Recorder`, `Skeleton` |
| `pyeyesweb.catalog` | | `describe`, `Layer`, `Timescale`, `FeatureInfo`, `catalog()` |
| `pyeyesweb.skeletons` | | presets of capture devices, `get_skeleton`, `with_skeleton` |
| `pyeyesweb.datasets` | | the example recordings of the tutorials; needs no core |
| `pyeyesweb.base` | | machinery that features are built from; internal |
| `pyeyesweb._core` | | the import of the compiled core |

`pyeyesweb.base` and `pyeyesweb.utils` are internal: they are not listed by `dir(pyeyesweb)` and are not documented. Only the
names in the `__all__` of a package are public.

## The contract

A feature is an object with state, and these are its entry points.

```text
feature = Feature(**parameters)
result  = feature.process(*sample, timestamp=None)               # one sample or frame per input; returns a Result
record  = feature.run(*recording, timestamps=None, reset=True)   # a whole recording, time on axis 0; returns a Recorder
feature.reset()                                                  # forget the state
feature.inputs                                                   # what one call takes: kind, shape, labels
feature.outputs                                                  # the Schema of the result, known before any data
feature.latest                                                   # the last result with status OK, or None
feature.parameters                                               # the constructor parameters, read-only
```

The classes that carry the contract are in {py:mod}`pyeyesweb.data_models`.

{py:class}`~pyeyesweb.data_models.Feature`
: The abstract base class. It defines `run` (a loop over `process`, so the two give identical numbers), `latest`, `parameters` and
  the declared `inputs` and `outputs`.

{py:class}`~pyeyesweb.data_models.WindowedFeature`
: A feature that buffers its own window. It takes `window` and `hop`, reports `WARMING_UP` and then `NO_OUTPUT` between hops, and
  implements a private hook (a method whose name starts with an underscore) for one complete `(channels, window)` series. The
  hook is never public API. Changing `window` or `hop` keeps the newest samples.

{py:class}`~pyeyesweb.data_models.Input`, {py:class}`~pyeyesweb.data_models.Inputs`, {py:class}`~pyeyesweb.data_models.InputKind`
: What one call receives: a name, a kind (`SAMPLE`, `POINTS`, `MATRIX`, `IMAGE`), a shape with `None` for a free size, optional
  labels and a unit. `Inputs` is the single source of truth for shape checks.

{py:class}`~pyeyesweb.data_models.Output`, {py:class}`~pyeyesweb.data_models.Schema`
: What a call returns: names, shapes, element kinds, component names, a unit and a one-line description. A schema that depends on
  parameters is built by `_schema()`, and `_outputs_changed()` is called from a setter that changes it.

{py:class}`~pyeyesweb.data_models.Result`, {py:class}`~pyeyesweb.data_models.Status`
: One immutable result per call: `status`, `reason`, `timestamp` (seconds, NaN when unknown), `valid` (per output) and one
  attribute per output. A missing value is NaN, 0 or `False`, never `None`. The statuses are `OK`, `WARMING_UP`, `NO_OUTPUT` and
  `INVALID_INPUT`. Each schema makes its own result class, `<Feature>Result`.

{py:class}`~pyeyesweb.data_models.Recorder`
: The columns of a recording: one row per sample, a NumPy column per output, `status`, `timestamps`, `to_frame()`, `to_numpy()`.

### Error policy (decided)

- A wrong **shape or kind** of input raises `ValueError`, from the central check of `Inputs`, naming the feature and the input.
- Bad **data** (NaN, infinity, an empty frame, a missing joint, a timestamp that goes back, degenerate geometry) returns a result
  with status `INVALID_INPUT` and a `reason`. It never raises and never returns a plausible number: every output is empty and `valid` is
  `False` for all of them.
- Too few samples gives `WARMING_UP`, never an exception.
- Invalid **parameters** raise at construction and at setters, and the feature is left as it was.
- The same condition always has the same `reason`: use the shared helpers.

### The central wrappers

A feature does not write its own checks. `Feature.__init_subclass__` wraps the `process` of every subclass, and the wrappers do the
common work once.

- **The check of the call against `inputs`.** A wrong shape raises. Then the central rules of data apply before the feature sees the
  call: NaN or infinity in a numeric input, a missing joint of a dict frame when the feature reads named joints, and a timestamp
  that is not finite return `INVALID_INPUT`. The sample is not buffered and no state advances, so the next valid call behaves as if
  the rejected one had not happened. An input declares `allow_non_finite=True` when NaN is data and the feature checks it itself.
  Timed features also reject a timestamp that does not increase.
- **`latest`.** After a call, a result with status `OK` is remembered; `reset()` forgets it.
- **Empty outputs.** The result of an `INVALID_INPUT` call is built with every output empty, whatever the feature passed.
- **Parameter validation.** Rates, window sizes, widths and counts must be positive, thresholds and weights not negative, in the
  constructor and in every setter, from lists kept in one place; a parameter that takes any sign by design is listed with the reason
  in the tests.

```{doctest}
>>> from pyeyesweb.data_models import Feature, Input, InputKind, Inputs, Output, Schema
>>> class Speed(Feature):
...     _INPUTS = Inputs(Input("position", InputKind.SAMPLE, shape=(2,), unit="m"))
...     _OUTPUTS = Schema(Output("speed", unit="m/s"))
...     def __init__(self, sampling_rate=100.0):
...         self.sampling_rate, self._previous = sampling_rate, None
...     def process(self, position, *, timestamp=None):
...         position, previous, self._previous = np.asarray(position, float), self._previous, np.asarray(position, float)
...         if previous is None:
...             return self._no_output(timestamp=timestamp)
...         return self._result(speed=float(np.linalg.norm(position - previous)) * self.sampling_rate, timestamp=timestamp)
...     def reset(self):
...         self._previous = None
>>> feature = Speed()
>>> feature.latest is None
True
>>> feature.process((0.0, 0.0)).status.name
'NO_OUTPUT'
>>> feature.process((0.03, 0.04)).speed
5.0
>>> feature.process((float("nan"), 0.0)).reason
'NaN or infinite values'
>>> feature.latest.speed
5.0
>>> feature.process((1.0, 2.0, 3.0))
Traceback (most recent call last):
  ...
ValueError: Speed: input 'position' expects sample of shape (2,), got shape (3,)
```

The class above wrote no check. The NaN call was rejected, the shape error was raised and `latest` was kept by the wrappers, which
also stay the same in every catalog feature.

## How a core-backed feature wraps the core

Most catalog features are backed by one block of the compiled core and derive from `CoreFeature` (in `pyeyesweb.base`), which
supplies the construction, the parameters and the result of the block. Frame-wise features without a window derive from
`FrameFeature`, and features with several algorithms from `VariantFeature`: one subclass per variant, chosen by a selector such as
`method=` at construction. A subclass names its block and the rest of what it needs as class attributes.

| Attribute | Meaning |
|---|---|
| `_core_class` | the block of the core that the feature wraps |
| `_core_names` | public parameter name to the name in the block, where the block abbreviates; everything public uses the public name |
| `_unit_params` | `{name: power}`: the parameters that are lengths (power 1) or areas and energies (power 2); the feature then takes `units="m"` or `"mm"` and scales the parameters, never the data or the outputs |
| `_timed` | the feature has a time step: the wrapper turns `timestamp`, `sampling_rate` or the per-sample rule into the step in seconds and hands it to the core, which never sees timestamps |
| `_rate_required` | a window feature that has no time axis and needs `sampling_rate` or raises at construction |
| `_parts` | `parts=` choices, to the on/off switches of the block |
| `_hidden_params` | block parameters the wrapper replaces by a parameter of its own |
| `_OUTPUTS`, `_schema()` | the schema of the result |
| `_inputs()`, `_INPUTS` | the declared inputs |

The signature of a core-backed class is explicit: every parameter appears with its default and annotation in
`inspect.signature`, and there is no `**params` in a public signature. It is not written by hand. The compiled core exposes each
block with a Python binding whose signature text carries the names, types and defaults of its parameters; the Python layer reads
that text once, when the class is defined, and merges it with the parameters of the class's own `__init__`. A choice that the block
takes as an enumeration becomes `Literal["a", "b"]` with a string default. The bindings must therefore name every parameter
descriptively and give it a default. A misspelled keyword raises a `TypeError` that names the feature and suggests the right
spelling.

```{doctest}
>>> import inspect
>>> from pyeyesweb.low_level import Equilibrium
>>> [cls.__name__ for cls in Equilibrium.__mro__[:5]]
['Equilibrium', 'CoreFeature', 'Feature', 'OutputsMixin', 'ABC']
>>> str(inspect.signature(Equilibrium))
"(*, margin: float = 0.1, y_weight: float = 0.5, units: Literal['m', 'mm'] = 'm')"
>>> Equilibrium.LAYER, Equilibrium.TIMESCALE, Equilibrium.EYESWEB_BLOCK
(<Layer.LOW_LEVEL: 'low_level'>, <Timescale.SHORT: 'up to ~0.5 s'>, None)
>>> Equilibrium(marjin=0.2)
Traceback (most recent call last):
  ...
TypeError: Equilibrium() got unexpected keyword argument(s) 'marjin' (did you mean 'margin'?); valid parameters: margin, y_weight, units
```

### Choices, switches and units

These rules are decided and are enforced centrally, so a feature does not repeat them ({doc}`conventions`).

- A parameter that picks an algorithm or a mode is a lower-case string, typed `Literal[...]`, case-insensitive, with `-` or a space
  counting as `_`; a wrong value raises `ValueError` listing the options. The core's enumerations are never exported into the public
  namespace. A group of on/off switches that select outputs is one `parts=` sequence.
- An on/off switch is a real `bool`.
- A feature whose input differs for the same quantity gets one constructor per mode (`from_position`, `from_velocity`), made by one
  helper from the signature of the constructor.
- All time is in seconds. Lengths and thresholds are in metres, and `units` lets data in millimetres be used by scaling the
  parameters. The exception, decided, is the humanoid features, which convert at the boundary around an internal millimetre model.
- A parameter that must change while the feature runs is **live** (applied in place) or **structural** (the state restarts and
  the next `reason` says "parameters changed: state reset"). The classification is decided from the original block and where
  uncertain a parameter is structural ({doc}`../howto/realtime_live_parameters`).

## Discovery: `catalog()`

Every feature class carries `@describe(Layer.X, eyesweb="<EyesWeb block>")`, which attaches `LAYER`, `TIMESCALE` (the default of
the layer unless given) and `EYESWEB_BLOCK` (omitted for features of the laboratory). {py:func}`pyeyesweb.catalog` lists the
described classes, in layer order, with the first line of the class docstring as the summary. A class that is not described and
exported in its layer package's `__all__` does not exist for users. The generated pages of the API reference are written from this
list ({doc}`building_the_docs`).

## Where to go next

- The naming, unit and docstring rules: {doc}`conventions`.
- Adding a feature, step by step: {doc}`adding_a_feature`.
- What the port reproduces and what it corrects: {doc}`porting_status`.
