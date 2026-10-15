# PyEyesWeb: development specification

Conventions and rules for anyone (people or coding agents) who changes PyEyesWeb or the EyesWeb C++ core under it.
Read this first. When a rule here conflicts with what you see in older code, the rule wins and the old code is a bug
to fix, unless the maintainer says otherwise. Rules marked **Decided** were chosen by the maintainer; do not change
them without asking.

## 1. What this is

PyEyesWeb is a Python library for movement analysis. It has three tiers, each with one job:

| Tier | Where | Job |
|---|---|---|
| C++ core `ew_core` | `EyesWebCore/core` (repository EyesWebCore) | The algorithms: faithful ports of EyesWeb blocks plus the lab's own features. Pure C++17, no Python, no nanobind. |
| Bindings and module `eyesweb_core` | `EyesWebCore/bindings` (private repository EyesWebCore) | Marshalling only (dict, numpy, lists to C++ types and back). No logic. Built there into the compiled module and shipped as the binary wheel `eyesweb-core`. |
| Python package `pyeyesweb` | `PyEyesWeb/pyeyesweb` (this repository) | The public API: one uniform call contract, validation, discovery, results. Pure Python; depends on the compiled `eyesweb_core` package. |

The C++ (core, bindings, module build) is closed source and is not part of this repository: PyEyesWeb contains Python only.

Keep the core independent of Python. It must stay usable from native C++ (for example TouchDesigner operators) and
from the command line. Logic belongs in the core, validation and the call contract belong in the Python layer,
marshalling belongs in the bindings.

Related documents: `EyesWebCore/CONVENTIONS.md` (the C++ rules, read it before touching the core),
`EyesWebCore/PORTING_STATUS.md` (every ported block, deviations from the original, removed blocks).

## 2. Package layout (Python)

The package follows the conceptual model of movement qualities (layers):

| Package | Layer | Content |
|---|---|---|
| `pyeyesweb.physical_signals` | 1 | Physical signals and virtual sensors: body models, space, images (silhouettes, videograms), stream plumbing (`TimeWindowSynchronizer`). |
| `pyeyesweb.low_level` | 2 | Kinematics, energy, shape and filtering of contours, symmetry, smoothness (up to about 0.5 s). |
| `pyeyesweb.mid_level` | 3 | Segments, impulsivity, suddenness, space occupation (0.5 to 3 s). |
| `pyeyesweb.high_level` | 4 | Social and interaction-level features (3 s and above): `EnsembleDominance`. |
| `pyeyesweb.analysis_primitives` | any | Metrics applicable to any movement feature at any layer (entropy, rarity, periodicity, `synchronization/`). |
| `pyeyesweb.data_models` | | The contract: `Feature`, `WindowedFeature`, `Input(s)`, `Schema`, `Output`, `Result`, `Status`, `Recorder`, and `skeleton.py` (the `Skeleton` class). |
| `pyeyesweb.base` | | Machinery features are built from: `core_feature.py` (`CoreFeature`, `VariantFeature`, `FrameFeature`), `signatures.py`, `choices.py`, `inputs.py`, `minimum_window.py`, `labels.py` (`LabelGuard`). Internal. |
| `pyeyesweb.catalog` | | `@describe(Layer, ...)` metadata and `catalog()`. |
| `pyeyesweb.skeletons` | | The lab device presets (`KINECT_V2`, ...), `get_skeleton`, `with_skeleton`; re-exports `Skeleton` (defined in `data_models/skeleton.py`). |
| `pyeyesweb.datasets` | | The example recordings of the gallery: `load_qualisys_trial` (returns a `QualisysTrial`: positions in mm, labels, sampling rate, units), `fetch_data_file`, `cache_dir`, `available_trials`. Needs no core. Files are looked up in `PYEYESWEB_DATA`, then `examples/data` of a checkout, then downloaded with the optional `pooch` (`BASE_URL` is `None` until a host is chosen; SHA-256 sums in `_datasets_registry.py`, written by `tools/trim_example_data.py`). Data access only: plotting and derived signals live in `examples/helpers.py`. |
| `pyeyesweb._core` | | The only place that imports the compiled module (the `eyesweb_core` package, a binary wheel built from the private EyesWebCore repository; in development the build found through `EYESWEB_CORE_PATH`). |

Where a new feature goes: the layer whose timescale and meaning fit it; if it applies to any signal at any layer it is
an analysis primitive. Every feature class carries `@describe(Layer.X, eyesweb="<EyesWeb block>")` (omit `eyesweb`
for lab features), and is exported in its layer package `__init__` and `__all__`. `catalog()` is generated from that
metadata, so a feature that is not described and exported does not exist as far as users are concerned.

## 3. The call contract (every feature obeys it)

A feature is an object with state. These are the only public entry points:

```python
feature = Feature(**parameters)
result  = feature.process(*sample, timestamp=None)     # one sample or frame per input, returns a Result
record  = feature.run(*recording, timestamps=None, reset=True)  # whole recording, time on axis 0, returns a Recorder
feature.reset()                                        # forget the state
feature.inputs                                         # what one call takes: kind, shape, labels
feature.outputs                                        # the Schema of the result, known before any data
```

- `Result` is immutable. Fields: `status`, `reason`, `timestamp` (seconds, NaN when unknown), `valid` (per output),
  and one attribute per declared output (`result.kinetic_energy`, `result["centroid_x"]`). A missing value is NaN, 0 or
  False, never `None`.
- `Status` is one of `OK`, `WARMING_UP` (a window is filling), `NO_OUTPUT` (between hops) and `INVALID_INPUT`.
- `Schema`/`Output` declare names, shapes, kinds, units and docs. Schemas that depend on parameters are computed by
  `_schema()`; call `_outputs_changed()` from a setter that changes them.
- `run` is a loop over `process` and must give identical numbers. `Recorder` holds one row per sample (columns,
  `to_frame()`, `timestamps`).
- Windowed features derive from `WindowedFeature`: they own their buffer, take `window` and `hop`, report `WARMING_UP`
  then `NO_OUTPUT` between hops, and implement the private hook `_process_window(*series)` for one full
  `(channels, window)` series. `_process_window` is never public API.
- Features backed by a C++ block derive from `CoreFeature` (`_core_class = core.<area>.<Block>`); features with
  several algorithms or versions derive from `VariantFeature` (one subclass per variant, chosen by a selector
  argument such as `method=`).
- Frame-wise features without a window derive from `FrameFeature`.

### Input data

Inputs accept the natural forms: a dict `label -> (x, y, z)`, an `(N, 3)` array in the order of `labels=`, and an
`(n, D)` array for a list of points (row 0 = newest). The declared `Inputs` are the single source of
truth for shape checks.

An **image** is `InputKind.IMAGE`: one 8-bit array per call, `(H, W)` or `(H, W, C)` (`image_input` in `base/inputs.py`; `run` takes
`(T, H, W[, C])` or a list of images and keeps them 8-bit). A `bool` array is a 0 / 1 mask, any other numeric array must hold whole numbers
in 0-255; the central check raises `ValueError` for a wrong rank, size, channel count or value. A silhouette is a full-frame mask in which any
non-zero pixel is foreground (the feature cuts the blob the EyesWeb blocks pass around, so coordinates are those of the frame). An output that
is an image has `None` sizes in its `Output` shape (known from the first frame) and holds the pixels as integers; images are never part of
`to_array()`. An input property the block fixes at its first call (the frame size) restarts the block when it changes, and the result says so.

### Error policy (**Decided**)

- Wrong **shape or kind** of input: raise `ValueError` (central check in `Inputs`, with the feature and input name).
- Bad **data** (NaN, infinite, empty frame, a missing joint, a timestamp that goes back, degenerate geometry): return a
  `Result` with `INVALID_INPUT` and a `reason`. Never raise and never return a plausible-looking number: an
  `INVALID_INPUT` result holds the empty value (NaN, 0, False) in every output and `valid` is `False` for all of them;
  the diagnostic is the `reason`. The central rules are in "Contract changes of work package A" below.
- Not enough samples yet: `WARMING_UP`, never an exception.
- Invalid **parameters** raise at construction, never at the first `process`. A minimum window size is validated at
  construction (`MinimumWindow`).
- Use the shared helpers (`non_finite(...)` in `base/inputs.py` and friends) so that the same condition always has
  the same `reason` text.

### Contract changes of work package A (2026-10-14)

These are Python-layer rules, implemented once in the central call path (`Feature` wrapper, `Inputs`, `OutputsMixin`,
`CoreFeature`) and tested catalog-wide (`test_invariants_all_features.py`, `test_time_rule_all_features.py`,
`test_live_validation_all_features.py`).

- **Finite check.** Before the feature sees a call, `Input.problem` looks at every numeric input (`SAMPLE`, `POINTS`,
  `MATRIX`, scalars, the values of a dict frame; not images): NaN or infinity gives `INVALID_INPUT` "NaN or infinite
  values" (the text of `non_finite`). The sample is not buffered and no state advances, so the next valid call behaves
  as if the rejected one had not happened (a windowed feature does not hold it in its window, the hop counter and
  `latest` do not move). An input says `allow_non_finite=True` when NaN is data: the feature then checks it itself. The
  opt-outs are the humanoid and mass-spring inputs (`HumanoidSimulator`, `HumanoidOrientations`, `GenericModel*`,
  `PointsPredictor`: a NaN joint is a dropout the model handles; an infinity or an all-NaN frame is still
  `INVALID_INPUT`) and the input of `EnsembleDominance` (a NaN complexity index is a participant without one, ignored by
  design). An input that is cast to an integer (`SequenceDetector`) says `integer=True` and also rejects values beyond the
  integer range. A feature that checks first or more specifically (an empty frame, a degenerate shape) keeps its own
  reason. A result that overflows (finite data, 1e300) is `INVALID_INPUT` "the result is not finite" through
  `_finite_result(...)`, used by the features whose arithmetic can overflow; that rejection comes after the block advanced (see work
  package H).
- **Labels.** For a dict frame, a feature that reads named joints (`LabelGuard`: `KineticEnergy`, `MotionNoiseDetector`,
  `Symmetry` ratio) checks it centrally: a joint it needs that is missing gives `INVALID_INPUT` "missing joints: a, b";
  when `labels` are configured, a key that is not one of them raises `ValueError` (a wrong joint name is a
  configuration error). The humanoid features set `_dropouts = True` and keep their dropout handling.
- **Empty outputs.** `OutputsMixin.result` ignores every value it is given when the status is `INVALID_INPUT`: all
  outputs are empty and `valid` is `False` for all. `WARMING_UP` and `NO_OUTPUT` are as before.
- **Time.** A timestamp that is NaN or infinite gives `INVALID_INPUT` "non-finite timestamp" (every feature, timed or not;
  work package H). After a timed call, a timestamp that is not larger than the previous one gives `INVALID_INPUT`
  "non-increasing timestamp" and changes nothing (the previous time stays). The previous timestamp is `None`, not 0,
  when unknown (the first call, after `reset()`, after a call without timestamp, after a state reset). A call with no
  previous timestamp has the step `1 / sampling_rate`, else 1 s per sample with the per-sample note in `reason`,
  whatever the absolute value of its timestamp (epoch seconds). A call without timestamp has the same step and makes
  the previous timestamp unknown. A rejected call carries no per-sample note.
- **Live validation.** `check_range` (`base/core_feature.py`) runs wherever parameters are set (constructor, setters,
  `_set_param`): the parameters in `_POSITIVE_PARAMS` (rates, window sizes, widths, counts, ...) and
  `_NON_NEGATIVE_PARAMS` (thresholds, weights, damping, fractions, seed, ...) raise `ValueError` for a negative (or
  zero) number and leave the feature as it was. The parameters that take any sign by design are listed with the reason
  in `ACCEPTS_NEGATIVE` of `test_live_validation_all_features.py`.

### Contract changes of work package B (2026-10-14)

Naming and signatures; `tests/unit_tests/test_naming.py` enforces the list of forbidden synonyms over the catalog.

- **One spelling per concept.** `number_of_inputs` (and `number_of_event_classes`, `number_of_points`, `number_of_regions`,
  `number_of_subsamples`); `window` for every length in samples (also `FilterContour`, `Videogram`, `ScalarPeakDetector`,
  the `Rarity` memory, the potentials); `cells_along_x` / `cells_along_y`; `gaussian_sigma`, `gaussian_sigma_x`,
  `gaussian_sigma_y`, `gaussian_correlation`; no EyesWeb pin abbreviations (`gesture_duration`, `quantity_of_motion`,
  `contraction_index`, `custom_amplitude`, `center_of_gravity`, `reference_direction`, inputs `first_signal` /
  `second_signal`, ...). Outputs have specific names and every boolean output is `is_<something>`.
- **Core names.** A core-backed feature maps its public names to those of the block with `_core_names` (`CoreFeature`); the
  core is not changed. Public signature, setters and `_params` use the public name. A parameter left at its default reads
  back as the signature default.
- **Choices.** `method=` picks an algorithm (`Suddenness`, `SuddennessImpulsivity`, `Periodicity`; `Symmetry` aggregates
  with `aggregation=`); `output_dims` is components versus scalar (`Symmetry`, `PointsDensity`, `Kinematics`); the core
  member `COMPONENT` is spelled `"components"` (`choice_name`).
- **Signatures.** Keyword-only after `window, hop` and after the joint arguments; everything annotated. A missing required
  argument raises a `TypeError` naming the public class and saying what `window` is. A variant feature shows the default
  method's parameters first and the parameters of only some methods are keyword-only.
- **Hop.** Default 1 everywhere. `EventSynchronization` and `EventSynchronizationMECS` accumulate across windows: `hop=None`
  is `window` (non-overlapping) and the only valid value. `CurvatureDispersion` has no hop (a result per call).
- **Rate.** `sampling_rate` defaults to `None` everywhere. The window metrics (`SpectralArcLength`, `LogDimensionlessJerk`,
  `Harmonicity`, `SubmovementCount`, `CurvatureVelocityCorrelation`) have no time axis and raise at construction without it
  (`_rate_required`). `ContractionImpulsivity.frames` is `sampling_rate`; without it the index is per frame.
- **Symmetry.** Both methods take `labels`/`skeleton`, `pairs` (names) and `reference_point` (`None`: barycentre for
  `"reflection"`); output labels of `"reflection"` are joint names; a frame of another size than `labels` is a shape error.
- **Other.** `PhaseLockingValue` takes `low_frequency`, `high_frequency`, `sampling_rate` instead of `filter_params`;
  `RecurrencePlot` / `CrossRecurrencePlot` `multiple_epsilons=None` is `epsilon` for each of the `window` samples;
  `MultiScaleEntropy` defaults to `window=3000` and its minimum-window error explains `max_scale * minimum_points`;
  `Equilibrium.margin` defaults to 0.1 m (the 100 mm of the original).

### Contract changes of work package C (2026-10-14)

Results, recorder and discoverability.

- **`parts=`.** `SilhouetteCentroids` (`center_of_gravity`, `head`, `left_shoulder`, ...), `SilhouetteBodyParts` (`right_leg`,
  `left_leg`, `trunk`, `right_arm`, `left_arm`, `head`) and `RegionDependingPotentials` (`potential`, `hit_regions`,
  `hit_region_indexes`, `region_values`, which are also its output names) take `parts=` instead of the bool switches
  (14, 6 and 4). Default: the parts the switches had on (all, all, `("potential",)`), read from the block. Names are
  case-insensitive with `-` or a space for `_`; a wrong name raises `ValueError` listing the options; the value reads back
  as a tuple in declaration order; it is live where the switches were (`feature.parts = [...]`).
- **Other open points of B, decided.** `TrajectoryNonPlanarity` defaults are kept; the `Kinematics` modes stay
  `tangential` / `module` / `global`; no rate is derived from timestamps; the PLV `filter_order` is not exposed (the core fixes 4).
- **Private helpers.** `result`, `no_output`, `finite_result`, `INPUTS` and `OUTPUTS` are now `_result`, `_no_output`,
  `_finite_result`, `_INPUTS` and `_OUTPUTS`. `feature.parameters` is a read-only mapping of the constructor parameters
  and their current values (as `get_params`); a parameter that is resolved at construction and not kept (`skeleton`) is not listed.
- **`Status`.** `str(Status.OK)` is `"OK"` (also in f-strings); `int(Status.OK)` is still 0.
- **`Recorder`.** `repr` shows the feature, rows, columns and status counts; `rec[3]` and `rec[-1]` are `Result`s (`reason`
  and `valid` included), `rec[2:5]` is a list of them, `rec["name"]` is still a column; `rec.<output>` (or a flat name) is a
  column; `to_frame()` has the status names in `status`. `latest` stays on `Feature`; there are no `computed()` / `held()` views.
- **Units of the outputs.** `Output.unit` is documentation in terms of the data: `"<length>"` is the length unit of the
  data, `"<input>"` the unit of the input, `"samples"`, `"frames"`, `"px"`, `"deg"`, `"s"`; a feature with `units=` writes the
  unit it was given (`"mm/s"`; `Kinematics`, `TrajectoryNonPlanarity`, the humanoid features). An empty unit means dimensionless
  and is listed with its reason in `tests/unit_tests/test_units_all_features.py` (booleans need no entry); a new feature
  with an output that has no unit fails that test.
- **Public names.** `dir(pyeyesweb)` lists the public modules (`datasets` included) and `Layer`, `Timescale`, `catalog`, `catalog_table`,
  `SeriesBuffer` (loaded from the core on demand, not in `__all__`); `pyeyesweb.base` and `pyeyesweb.utils` are internal
  and not listed; a package lists its `__all__` and not its submodules. `TimeWindowSynchronizer` and `SynchronizedWindow`
  are public in `pyeyesweb.physical_signals` (they need the core, so not in `data_models`), next to `MassSpringModel`.
- **Layer placement rule** (in the `catalog` docstring). Physical signals produce a signal from raw frames or a model and
  give a signal again; low-level measures a frame or a short window the feature buffers itself; mid-level needs a whole gesture; high-level needs several people; an analysis primitive knows nothing of bodies or geometry. Moved:
  `FilterContour` to `pyeyesweb.low_level` (with the other contour features, in `shape.py`), `TrajectoryNonPlanarity` and
  `average_curvature_3d` to `pyeyesweb.mid_level` (superseded in work package D: `Directness` too moved to low-level).
  `ContourFeature` now lives in `low_level/shape.py`.
- **`GenericModel*`.** Each docstring has an example, and the error for a wrong `model=` names
  `MassSpringModel.from_xml_file(path)`, `from_xml_string(xml)` and `add_mass` / `add_spring`.

### Contract changes of work package D (2026-10-14)

- **Placement.** `Directness`, `TrajectoryNonPlanarity` and `average_curvature_3d` are in `pyeyesweb.low_level` (files
  `low_level/directness.py` and `low_level/non_planarity.py`): a path given as a list of points is low-level, mid-level is
  a whole gesture. The `catalog` placement rule says so. `Result.to_flat_dict()` keeps integer statuses.
- **Core version (Q9).** `eyesweb_core` has `__version__` (the CMake project version of EyesWebCore, bumped with the
  bindings) and `__build__` (git short hash at configure time). `pyeyesweb/_core.py` requires `REQUIRED_CORE` (major.minor,
  now 2.0) and raises `ImportError` for another version or a module without a version. `EYESWEB_CORE_PATH` is put first on
  `sys.path` by `_core.py` itself, and the import fails when `eyesweb_core` was already loaded from another place.
- **Signatures (Q7, Q8).** Annotations of the nanobind signature text are resolved by `typing.get_type_hints` against a
  fixed namespace (no `eval` of module globals); the text is still parsed with `ast`, defaults with `ast.literal_eval`.
  `from_*` constructors are descriptors (`_InputModeFactory`) that build the function per class on access, so a
  subclass or grandchild shows and checks its own parameters; the parent's is never touched.
- **Humanoid (Q16).** The joint and bone tables and `MassSpringModel` are in `physical_signals/_humanoid_model.py`;
  `HUMANOID_JOINTS`, `HUMANOID_BONES` and `MassSpringModel` stay public from `pyeyesweb.physical_signals`.
- **Tests (Q10, Q11, Q12).** Helpers are in `tests/_support/` and documented in `tests/conftest.py`. The legacy oracles
  (`tests/reference`, 13 modules) were removed with the parity comparisons against them; the only regeneration code of frozen data was the `--capture`
  option of `test_trajectory_parity.py`, now `tools/regenerate_trajectory_reference.py` (the other `.npz` files have no
  generator in the repository). `tests/benchmarks` (animation scripts on the 1.x API, not benchmarks) deleted
  (with `SlidingWindow`, removed on 2026-10-14); `pytest-benchmark` is not added.
- **Build (Q13).** Strict warnings (`/W4`, `-Wall -Wextra`) apply to the core, the tests and the bindings;
  `-DEW_WARNINGS_AS_ERRORS=ON` turns them into errors. `.gitignore` covers `examples/scratch/` (build outputs were
  already covered).

- **Core package (2026-10-15).** The core is its own wheel `eyesweb-core` (import name `eyesweb_core`) that pyeyesweb will depend on; `_core.py` imports only `eyesweb_core` (no bundled `pyeyesweb._eyesweb_core`), `EYESWEB_CORE_PATH` stays the development override.

### Contract changes of work package H (2026-10-15)

From the suspected-bugs list of the fact sheet (S1 to S7, S8, S10).

- **Recorder of a fast-path `run` (S1).** `KineticEnergy.run` builds its `Recorder` from the feature (`Recorder.from_arrays(self, ...)`),
  not from the schema: every `run` gives `Recorder(<Feature>, ...)` whose rows are `<Feature>Result`.
  `test_contract_all_features.py` checks it for every feature.
- **Non-finite timestamp (S7).** One central rule in `Feature._input_problem`: a NaN or infinite `timestamp` is `INVALID_INPUT` with
  reason "non-finite timestamp", empty outputs, nothing changed (the previous time stays), in every feature (timed or not). It
  was a `ValueError` raised in `_time_step` by the timed features only. `run` agrees with the loop of `process`
  (`KineticEnergy.run` falls back to it for such a recording).
- **`Symmetry(method="ratio")` reference (S4).** With `skeleton=` and `reference_type="label"` (the default) the reference joint is that of the
  skeleton, else the given `reference_point`; a preset that defines none (`mediapipe`, `qualisys_sport` until their `TODO(fill)` is
  filled) raises `ValueError` at construction naming the preset and asking for `reference_point=` (`reference_type="barycenter"` no longer exists: see work package I-a).
  Before, the core default `"neck"`, which is no joint of those presets, was kept and the core silently skipped the translation.
- **`KineticEnergy(weights=...)` (S5).** A sequence of weights is read as one weight per label (`labels=` or `skeleton=`); another length
  raises `ValueError` ("weights has 1 value, the skeleton has 3 joints"), as does a sequence without labels or a value that is neither
  mapping nor sequence. No other feature takes `weights`; `MotionNoiseDetector`, `PointsDensity` and `PointsPredictor` take `labels` only.
- **Constructor error of `window`/`hop` (S8).** It names the class, as the setter's does.
- **Overflow does not roll the state back (S6, documented, not changed).** `"the result is not finite"` is detected after the block
  processed the sample, and the core cannot undo that. A stateful feature (`KineticEnergy` in position mode keeps the overflowing frame as
  the previous one; a windowed feature holds the sample in its window until it leaves) can therefore return `INVALID_INPUT` on the
  next valid call too. The other rejections (non-finite values, missing joints, non-increasing or non-finite timestamp) never
  reach the block and change nothing. Pinned by `test_an_overflow_has_advanced_the_state_of_the_block` in `test_input_safety.py`.
- **Wording.** `Result.timestamp` is in seconds; `HumanoidSimulator.process` outputs are in the unit of `units`; layer 4 is "qualities
  communicated" (as the catalog table says); the stale lines of the package docstring and of sections 3 and 4 were fixed.

### Contract changes of work package I (2026-10-15)

#### I-a

- **`MotionNoiseDetector.is_noisy` flipped.** `True` now means the motion is noisy (random, jumpy: the mean speed variance exceeds
  `noise_threshold`); it is `False` for a still body, a uniform motion and the first 14 frames (before: the reverse). Done in
  `_to_result` (`not raw`); statuses and warm-up are unchanged; `noise_threshold <= 0` now flags every frame as noisy. `GestureSegmenter`
  is untouched: its `noise` input blocks the start of a gesture while set (`True` = judged to be noise), so a pipeline passes `is_noisy`
  directly (the docstrings, `test_parity_gesture_segmenter.py` and `test_time_and_units.py` do it; the first version of this note asked for
  `not is_noisy`, which blocked every smooth gesture; `tests/data/gesture_segmenter_reference.npz` was regenerated with the direct wiring).
  With several joints the alphabetically last joint name decides the flag, whatever the order of `labels` (the behaviour of the underlying
  EyesWeb block: only one joint decides).
- **`Suddenness.gamma`** has no unit (dimensionless, a ratio of quantile differences); listed in `EXEMPT` of `test_units_all_features.py`.
  The classification of a still or constant-speed window as sudden is unchanged.
- **`CurvatureVelocityCorrelation` velocity in seconds.** `velocity` and `velocity_std` are length/s in both modes: with the default
  `differentiate=False` the Python layer multiplies the per-sample values of the filters by `sampling_rate` (with `True` they already are).
  Ellipse of the docstring (window=100, hop=100, rate 100): `velocity[0, 50, 99]` was `0.03254869, 0.06225254, 0.03302909` and is
  `3.25486865, 6.22525408, 3.30290899`, `velocity_std` `0.011044` -> `1.104400` (= the `differentiate=True` values); `smoothness`
  (-0.94339) and `curvature_std` (0.57435) unchanged. The core reads `velocity_threshold` nowhere (dead parameter, documented as
  without effect); `standard_deviation_threshold` and the `"simplified"` index act on the core's velocity (per sample when
  `differentiate=False`), not converted so that their values keep their meaning (documented). With 1 channel the curvature
  depends on the mode (`|y''| / (1 + y'^2)^1.5`).
- **`Symmetry(method="ratio")` `reference_type`.** The core translates the frame only for `"label"`; `"barycenter"` and `"point"` are
  unimplemented there (the original did nothing, and `"point"` has no point parameter). They raise `ValueError` at construction and on
  assignment (`_coerce_choices`); `"label"` stays. A skeleton without reference joint now only suggests `reference_point=`.

#### I-b

- **`SpikeSynchronization(mode="timings")` is public.** The core takes the spike times of the trains as the rows of one matrix, all trains
  with the same number of spikes (`SpikeES::validate`), and keeps no state between calls. So in `"timings"` mode the declared input is
  `spike_times`, `InputKind.MATRIX` of shape `(number_of_inputs, window)` (`window` = spikes per train, live: `configure` updates
  `feature.inputs`), `process` takes one such matrix and returns the result for it (status `OK`, no buffering, no warm-up, `hop` unused),
  and `run` takes `(T, number_of_inputs, window)`, one row of the recorder per set of trains. Times must be `> 0` and strictly increasing
  within a train, else `INVALID_INPUT` (the core does not check the order); NaN and a non-finite timestamp follow the central rules; a
  matrix of another shape, including trains with different numbers of spikes, is a `ValueError`. Trains with different numbers of spikes
  would need a core change (a ragged input in `SpikeES::process`); not done. The `TypeError` pointing at `_process_window` is gone.
- **`MassSpringModel.to_xml()` / `save_xml_file()` write relative damping.** The core loads the damping attributes as relative (1 =
  critical, as `CSpringImpl`) and writes the absolute coefficient (as the EyesWeb estimator does), so a saved model did not reload to
  the same configuration. The Python wrapper now divides the damping of the core's XML by `0.5 * sqrt(mass2 * stiffness)` (the factor the
  loader multiplies by), so `from_xml_*(m.to_xml())` has the configuration of `m` (to rounding, about 1e-16 relative); loading is unchanged and
  existing files read as before. A spring with zero stiffness or tip mass has no relative damping and is written as 0. The core's own
  `to_xml` still writes absolute values; making it symmetric would be a core change (not needed here).
- **`CoarseGraining` cadence is the core's, documented.** The EyesWeb block counts its activations modulo `factor` and computes only on
  activation 0 (`CoarseGraining::process`), so with `hop` the series is produced on the first full window and then every `factor * hop`
  samples; the other windows are `NO_OUTPUT` "not recomputed on this activation". Not a defect: kept, described in the docstring and pinned by
  `test_coarse_graining_is_computed_every_factor_th_window`.

## 4. Parameters

### Names (**Decided**)

- **No one-character identifiers anywhere in the Python code**, whether public parameters, function arguments, local
  variables, loop or comprehension variables, lambda arguments or `except ... as` names. Only `_` for an unused value.
  Use names that explain the value: `timestamp`, `index`, `point`, `window`, `series`, `embedding_dimension`,
  `tolerance`. `tests/unit_tests/test_naming.py` fails the build otherwise, and also checks every public constructor
  parameter of every feature.
- snake_case, descriptive, the same concept has the same name in every feature (`window`, `hop`, `sampling_rate`,
  `dims`, `tolerance`, `embedding_dimension`...).
- Savitzky-Golay parameters are always `filter_window_length` and `filter_polyorder`, in every feature (no unprefixed forms).
- Feature names are the plain name, with no `Get` prefix and no `Index` suffix (`KineticEnergy`, `CurvatureVelocityCorrelation`,
  `CurvatureDispersion`). The EyesWeb block name lives only in the `@describe(eyesweb=...)` metadata.

### Choices are strings (**Decided**)

- A parameter that picks one of several algorithms or modes is a lower-case string, typed
  `Literal["ratio", "reflection"]`, as in scikit-learn (`Symmetry(method="reflection")`).
- An `input_mode` that changes what one call takes for the same quantity (`KineticEnergy`: positions or velocities;
  `Kinematics`: a point or a series; `LogDimensionlessJerk`: a speed or an acceleration) also gets one `@classmethod`
  constructor per mode (`KineticEnergy.from_position(...)`, `from_velocity(...)`), made with `input_mode_factory`
  (`base/signatures.py`); `input_mode` stays an ordinary constructor parameter. A `method=` is for a different algorithm
  on the same input; two different quantities are two classes.
- Strings are case-insensitive and `-` or a space count as `_`; a wrong value raises `ValueError` listing the valid
  options. The coercion is central (`base/choices.py`, `CoreFeature`); do not write per-feature parsing.
- Do not export C++ enums into the public namespaces and do not document enum members. Core enum members passed by
  mistake are still accepted silently.
- A group of on/off switches that select what a feature outputs (the 14 centroids of `SilhouetteCentroids`, the 6 parts of
  `SilhouetteBodyParts`, the outputs of `RegionDependingPotentials`) is one `parts=` sequence of names, validated like any
  choice; declared once in `_parts = {name: block switch}` (`CoreFeature`).
- An on/off switch is a **bool** (`True`/`False` only; words such as "on" or "yes" are rejected with a `TypeError`).
  Do not model on/off as an enum, in C++ or in Python.
- Selectors of a `VariantFeature` (`method`) are fixed at construction.

### Signatures are explicit

Every feature shows its parameters and defaults to `inspect.signature` and IDEs; there is no `**params` in a public
signature. For core-backed features the signature is derived once from the nanobind annotations (`base/signatures.py`),
so the core binding must name every parameter descriptively and give it a default. A misspelled keyword raises a
`TypeError` that names the feature and suggests the right spelling.

### Live and structural parameters (**Decided**)

A parameter must be changeable while a feature runs, as in real-time use:

- **Live**: applied in place, the state is kept (thresholds, weights, kernels).
- **Structural**: it sizes or shapes the state (lengths, dimensions, filter order, number of inputs). The state restarts
  and the next result says "parameters changed: state reset" in `reason`.

The classification is decided per parameter from the original EyesWeb source (what `Init()` reads versus
`Execute()`); where it is uncertain the parameter is structural. In C++ every block with parameters has
`bool adoptParams(const Block& fresh)` (see `CONVENTIONS.md`, "Changing parameters at run time"). A bad new value
raises at the setter and leaves the feature unchanged, for the same values the constructor refuses (see "Live validation"
below). New features add their cases to the live-parameter tests.

`window` and `hop` of a `WindowedFeature` are live: the Python buffer keeps the newest samples (`configure`), a shorter window
gives a result at once, a longer one warms up again (`test_live_window_hop.py`). Exceptions, structural because the state is
sized by them: `CurvatureVelocityCorrelation` (`window`, `hop`, `sampling_rate`: its filters need the same length and overlap in
consecutive windows), `Rarity(method="information")` `window` (memory in the core), `Videogram.window` and
`ScalarPeakDetector.window` (buffers in the core). Making those three live needs a core change: resize the buffer keeping the
newest values in `adoptParams` (`ShiftWindow` has no resize; `VideoGram` would crop or pad its image). `EventSynchronization*`
change `window` and `hop` together with `configure(window=, hop=)`.

### Time (**Decided**)

All time is in **seconds**. Features with derivatives follow one rule: the `timestamp`/`timestamps` argument if given,
else `sampling_rate` (Hz, int or float), else per-sample derivatives (and the `reason` says so). The wrapper
computes the time step `dt` and hands it to the core; the core never sees timestamps, ticks or time modes. Do not
add time-mode parameters. Details (the first call, a call without timestamp, a timestamp that does not increase) are
in "Contract changes of work package A".

### Units (**Decided**)

Thresholds and lengths are in metres, as in EyesWeb. A feature with unit-sensitive parameters takes
`units="m"|"mm"`, declared once through `_unit_params = {name: power}` (power 1 for a length or speed, 2 for an area
or an energy). The parameters are scaled, the data and the outputs never are. Do not rescale data silently.

- Exception: the humanoid features. `HumanoidSimulator` works internally in mm (the EyesWeb body model is defined in mm
  and its spring forces depend on the length unit): `units` declares the unit of the user's frames, of `gravity` /
  `floor_position` and of the outputs, and the wrapper converts at the boundary (frames x 1000 in, joints / 1000 out for
  `"m"`; nothing for `"mm"`). The `GenericModel*` features run in the unit of the user's model and `units` only names
  it (no scaling). Time is the shared rule (`sampling_rate` default None, no 25 Hz default).

### Dimensions

Do not make the user declare what the data already says. `dims` defaults to `None` and is inferred from the first
frame (`InferredDims`, lazily built block); an explicit `dims` fixes the shapes before any data, which a host that
declares outputs ahead of data needs. A frame of another dimension later raises the shape `ValueError`.

### Skeletons and joints

Features that must know joints (`KineticEnergy`, `MotionNoiseDetector`, `Symmetry` (both methods), `PointsDensity`)
take `skeleton=`: the name of a lab preset (`"kinect_v2"`, `"qualisys_sport"`, `"mediapipe"`, `"openpose"`) or a
`pyeyesweb.skeletons.Skeleton` you build yourself (joints, pairs, reference, weights). Explicit `weights=`, `pairs=`
and `labels=` override it. Without any joint information they raise a clear `ValueError` at construction. Presets
are data in `skeletons.py`; fields not filled yet are listed in `SKELETON_TODO`. There are no legacy device modes
(no OpenNI, no Kinect SDK v1 tables, no `input_type`/`skeleton_mode`). Do not add them back.

## 5. Fidelity to EyesWeb and bug policy (**Decided**)

- A port reproduces the original block: same formulas, same order of floating-point operations where it matters, same
  defaults, same edge cases. The EyesWeb source is the only authority; never invent maths that is not in the tree.
- Hangs, crashes and undefined behaviour are never reproduced: implement the evident intent and document it in the
  block header.
- A deviation from the original that changes numbers needs a maintainer decision. Once decided, the corrected
  behaviour is the behaviour of the core: **no boolean `fix_*` flags** (all existing ones were resolved and
  removed). Record every correction in one line under "Corrected in the core (no flag)" in
  `EyesWebCore/PORTING_STATUS.md`. While a correction is undecided, ask; do not guess and do not add a flag.
- Blocks the maintainer retires are removed from the core, the bindings and the Python package together, and noted
  under "Removed blocks" in `PORTING_STATUS.md`.
- Lab features (no EyesWeb block) are tested by behaviour, the catalog-wide suites and frozen data in `tests/data`; there
  are no legacy oracles.

## 6. How to add a feature

1. Core: header with the documentation comment (EyesWeb id, source, inputs, outputs, formula, state, quirks), source,
   `Params` with the original defaults, validating constructor (`std::invalid_argument`), `process`, `reset`,
   `adoptParams`, tests in `EyesWebCore/tests/<area>/`, a binding in `EyesWebCore/bindings` ending with `EW_REGISTER_BINDING(...)`, and the
   shared helpers in `EyesWebCore/bindings/convert.h`. Follow `CONVENTIONS.md`.
2. Python class in the right layer package: `@describe(...)`, base class (`CoreFeature` / `WindowedFeature` /
   `VariantFeature` / `FrameFeature`), `_OUTPUTS` schema, `_inputs()`, `_schema()` if parameter dependent,
   `_process`/`_process_window`, a docstring with `Parameters` and `Returns` (units stated), export in the layer's
   `__init__` and `__all__`.
3. Tests: the contract suite (`tests/_support/contract_suite.py`, `check_feature_contract`) so `process` and `run` agree and
   results are well formed; the live-parameter suite (`tests/_support/live_param_suite.py`) for every parameter, live or
   structural; parity against the C++ or reference implementation; error cases (wrong shape, NaN, too short).
   `tests/test_signatures.py`, `tests/unit_tests/test_choices_everywhere.py` and `test_naming.py` pick the new
   feature up automatically through `catalog()`: they must pass without changes.
4. Update `EyesWebCore/PORTING_STATUS.md` for ported blocks.

## 7. Code style

- Python 3.10 or newer; type-annotate public signatures. Minimal, organised code: no repetition, no dead code, no
  helper that is used once. Reuse `base/` helpers (`non_finite`, `train`, `points_input`, `InferredDims`,
  `MinimumWindow`) instead of rewriting them. One mechanism per problem: do not add a second way to validate a window,
  to dispatch on a method, to pick a time step.
- Comments say why, not what. Docstrings are numpy style (`Parameters`, `Returns`) and must stay true: when you
  change behaviour, change the docstring in the same edit.
- C++: C++17, 4-space indent, 120 columns, `camelCase` functions and members (`trailing_` for private),
  `PascalCase` types. Names in the core that are visible from Python (parameter names in bindings, properties)
  follow the Python naming rules above, including no one-letter names. One-letter locals in numerical C++ code are
  tolerated for now; do not add new ones in new code.
- No `from x import *` in new code, no global state, no behaviour that depends on import order.

## 8. Build and test

Python 3.11 virtual environment. The C++ is built in the private EyesWebCore repository (a sibling checkout of PyEyesWeb);
PyEyesWeb itself has nothing to compile. The compiled module is the `eyesweb_core` package when installed, or the build
in the directory named by `EYESWEB_CORE_PATH` (and on `PYTHONPATH`) during development. CMake option
`-DEW_WARNINGS_AS_ERRORS=ON` makes any compiler warning an error (CI); strict warnings apply to every target.

```
# C++ core, tests and compiled module (repository EyesWebCore, a sibling checkout)
cmake -S <EyesWebCore> -B <EyesWebCore>/build -G "Visual Studio 17 2022" -A x64 ^
      -DEW_BUILD_PYTHON=ON -Dnanobind_DIR=<python -m nanobind --cmake_dir> -DPython_EXECUTABLE=<python 3.11>
cmake --build <EyesWebCore>/build --config Release --parallel
<EyesWebCore>/build/Release/ew_tests.exe [name filter]       # C++ tests; the module lands in the same folder
                                                             # (run cmake twice after adding or removing files)
python <EyesWebCore>/bindings/tests/test_bindings.py <EyesWebCore>/build/Release   # binding smoke test

# Python tests (from PyEyesWeb)
set PYTHONPATH=<EyesWebCore>/build/Release;<PyEyesWeb>
set EYESWEB_CORE_PATH=<EyesWebCore>/build/Release
python -m pytest -q
```

On Git Bash use `;` as the `PYTHONPATH` separator when the paths are Windows paths, and prefix commands whose arguments
start with `/` with `MSYS_NO_PATHCONV=1`. Without the core only the pure data-model tests run and the rest are skipped,
which is expected.

Before you say a change is done:

- C++ tests, the binding test and the whole `pytest` suite pass, with and without the core on the path (the pure tests).
- `tests/unit_tests/test_naming.py` passes (no one-character names), and a linter such as `pyflakes` shows no new
  unused imports or variables.
- No numeric test was edited to make it pass: if a number changed, the change needs a decision (section 5).
- You did not add public API that this document forbids (enums as parameters, `time_mode`, `fix_*` flags, `**params`
  in a public signature, public `process_window`, one-letter parameters).

## 9. Working rules for agents and contributors

- Read the code and the documents named above before changing anything; verify facts in the code, not in memory.
- Keep the scope of a change to what was asked. Report anything you notice outside it instead of fixing it silently.
- Do not remove or rename public names without a decision, and do not leave compatibility aliases: version 2.0.0 is
  unreleased, so renames are clean.
- The documentation pages, README, CHANGELOG and the structure review are updated in dedicated passes by the maintainer;
  do not edit them as a side effect of a code change, except where this document or the maintainer says so. Keep
  `PORTING_STATUS.md` and the docstrings of the code you touch correct.
- Ask the maintainer when a decision is open (an unclear original behaviour, a block that may be retired, a name that
  could be read two ways) and do not choose silently.
