# Conventions

The rules below keep the library uniform: a concept has one name, a quantity one unit, a choice one form. Most of them are
checked by the tests, and a rule that is checked says so. Where a rule here conflicts with older code, the rule wins and the code
is a defect to fix.

## Names

- **No one-character identifier** anywhere in the Python code: not in parameters, arguments, local variables, loop or
  comprehension variables, lambda arguments or `except ... as` names. Only `_` is allowed, for an unused value. Use names that
  say what the value is (`timestamp`, `index`, `point`, `window`, `series`, `embedding_dimension`, `tolerance`).
  `tests/unit_tests/test_naming.py` scans the package with the AST and also checks every public constructor parameter of every
  feature and every parameter of the compiled core.
- snake_case, descriptive, and **the same concept has the same name in every feature**: `window`, `hop`, `sampling_rate`, `dims`,
  `tolerance`, `embedding_dimension`. The Savitzky-Golay parameters are always `filter_window_length` and `filter_polyorder`.
- Feature names are plain: no `Get` prefix and no `Index` suffix (`KineticEnergy`, `CurvatureDispersion`). The name of the EyesWeb
  block lives only in the `eyesweb=` argument of `@describe`.
- No EyesWeb pin abbreviations as parameter, input or output names: `gesture_duration`, `quantity_of_motion`,
  `contraction_index`, `first_signal` and `second_signal` rather than the abbreviations of the blocks.
- A boolean output is named `is_<something>`. Outputs have specific names (not `value`, `matrix` or `x`).
- A feature that reads a name from the compiled core maps it with `_core_names`; the core is not changed to suit the Python name.

### The list of forbidden synonyms

`test_naming.py` holds the table `FORBIDDEN`, spelling to use in place of the forbidden one, and checks it over the parameters,
inputs and outputs of every feature in `catalog()`. The groups are these; the test has the complete table.

| Concept | The spelling | Forbidden |
|---|---|---|
| number of inputs, event classes, points, regions, subsamples | `number_of_inputs`, `number_of_event_classes`, `number_of_points`, `number_of_regions`, `number_of_subsamples` | `n_inputs`, `input_number`, `time_series_number`, `event_class_number`, `points_number`, `num_of_regions`, `num_subsamples` |
| a length in samples | `window` | `window_size`, `window_length`, `length`, `buffer_length`, `data_memory` |
| grid cells | `cells_along_x`, `cells_along_y` | `cells_x`, `cells_y` |
| Gaussian widths | `gaussian_sigma`, `gaussian_sigma_x`, `gaussian_sigma_y`, `gaussian_correlation` | `sigma_value`, `std_dev_x`, `std_dev_y`, `rho` |
| sampling rate, duration of a gesture | `sampling_rate`, `gesture_duration` | `frames`, `ges_dur` |
| pairs of joints, centre of symmetry | `pairs`, `reference_point` | `couples`, `joint_pairs`, `center_of_symmetry` |
| choice of algorithm, kind of measure | `method`, `measure` | `algorithm`, `algo`, `type` |
| band of a filter | `low_frequency`, `high_frequency` | `filter_params` |
| two signals, and the outputs of an interdependence | `first_signal`, `second_signal`, `first_to_second_interdependence`, `second_to_first_interdependence` | `x`, `y`, `ts1`, `ts2`, `xy`, `yx` |
| EyesWeb abbreviations | `quantity_of_motion`, `contraction_index`, `center_of_gravity`, `reference_direction`, `correlations_matrix`, `phase_locking_value`, `recurrence_matrix` | `sqom`, `ci`, `cog`, `ref_dir`, `cpr`, `plv`, `plot` |
| custom amplitude and distance | `use_custom_amplitude`, `custom_amplitude`, `use_custom_distance`, `custom_distance` | the `cust_` abbreviations |
| spelling | `synchronization` | `synchronisation` |

A new feature that uses a forbidden spelling fails the test; a new synonym that should be forbidden is added to the table.

## Choices are strings

- A parameter that picks one of several algorithms or modes is a lower-case string typed `Literal["ratio", "reflection"]`, as in
  scikit-learn. Strings are case-insensitive and `-` or a space counts as `_`; a wrong value raises `ValueError` that lists the
  options, from the constructor and from the setter. The coercion is central (`pyeyesweb.base.choices` and `CoreFeature`): do not write
  per-feature parsing.
- Do not export enumerations of the compiled core into a public namespace and do not document their members. The only public
  enumerations are `Layer`, `Timescale`, `InputKind` and `Status`.
- A group of on/off switches that select what a feature outputs is one `parts=` sequence of names.
- An on/off switch is a real `bool`: `True` or `False`, and `"on"` or `"yes"` raise `TypeError`. Never model on/off as an enumeration.
- `method=` is for a different algorithm on the same input. Two different quantities are two classes. An `input_mode` that changes what
  one call takes for the same quantity also gets one `from_*` constructor per mode.
- A selector of a variant feature (`method`) is fixed at construction.

## Units

- Lengths and thresholds are in metres, as in EyesWeb. A feature with unit-sensitive parameters takes `units="m"` or `"mm"`
  (default `"m"`), declared once with `_unit_params = {name: power}`: power 1 for a length or a speed, 2 for an area or an energy.
  The **parameters are scaled, the data and the outputs never are.** Do not rescale data silently.
- `Output.unit` documents the unit of the values in terms of the data: `"<length>"` is the length unit of the data, `"<input>"` the
  unit of the input; a feature with `units=` writes the concrete unit (`"mm/s"`); `"samples"`, `"frames"`, `"px"`, `"deg"`, `"s"`,
  `"cells"` and compounds also occur. An empty unit means dimensionless, and every such output is listed with its reason in
  `tests/unit_tests/test_units_all_features.py`; a new output without a unit fails that test (booleans need no entry).
- The exception is the humanoid features, which convert at the boundary around an internal model in millimetres.

## Time

All time is in **seconds**. A feature with derivatives takes the time step from the `timestamp` of the call and the previous one if
both exist, else from `sampling_rate` (Hz), else it works per sample and the `reason` says "no time given: per-sample derivatives".
The Python layer computes the step and gives it to the core; the core never sees timestamps. Do not add time-mode parameters. The
default of `sampling_rate` is `None` in every feature. A window metric that has no time axis (`SpectralArcLength` and the other
speed-profile metrics) requires it and raises at construction without it.

The rules about the first call, a call without timestamp and a timestamp that does not increase are in
{doc}`../concepts/time_units_parameters`, and the catalog-wide tests that pin them are `test_time_rule_all_features.py` and
`test_time_and_units.py`.

## Dimensions and skeletons

Do not make the user declare what the data already says. `dims` defaults to `None` and is taken from the first frame; an explicit
`dims` fixes the shapes before any data, which a host that declares outputs ahead of the data needs. A feature that must know joints
takes `skeleton=`, a preset name or a `Skeleton`, and explicit `labels=`, `weights=` and `pairs=` override it
({doc}`../howto/map_skeleton`). There are no legacy device modes.

## Code style

- Python 3.10 or newer. Annotate the public signatures, which are explicit: no `**params` in a public signature.
- Minimal, organised code: no repetition, no dead code, no helper that is used once. Reuse the helpers of `pyeyesweb.base` instead of
  rewriting them. One mechanism per problem: do not add a second way to validate a window, dispatch on a method or pick a time
  step.
- Comments say why, not what. No `from x import *`, no global state, no behaviour that depends on the import order.
- Private helpers have a leading underscore (`_result`, `_no_output`, `_INPUTS`, `_OUTPUTS`); no public docstring may name a private
  method.

## Docstrings

Docstrings use the numpydoc format (the `numpydoc` extension validates them) and must stay true: when behaviour changes, the
docstring changes in the same edit. The docstring of a catalog feature has these parts, in this order.

1. **Summary**: one sentence of at most 100 characters. It is the `summary` of the catalog entry.
2. A paragraph on **what it measures**: the meaning for movement, not only the algorithm, with the definition in mathematics
   (`.. math::`), in the notation of the theory pages ({doc}`../theory/notation`).
3. **Parameters**: each with its type, default, **unit** (s, m or mm, Hz, rad, dimensionless), allowed strings, and *(live)* or
   *(structural)* where the distinction applies. The generated page fails to build when the section does not cover the
   signature.
4. **Notes**: the inputs (names and shapes of `process` and `run`), the outputs (each with unit and range, matching the schema), the
   statuses (when the result is not `OK`, the length of the warm-up), the EyesWeb origin, **"Corrected in the core"** where it
   applies, and the known limits.
5. **References**: numpydoc entries with `:cite:` keys from `docs/references.bib`. Cite nothing that is not in the file; a source
   that is needed and not yet in it is marked **[citation needed]** until it is added.
6. **Examples**: an example of at most ten lines on synthetic data that runs. `python -m pytest --doctest-modules pyeyesweb` runs it.

## Tests

The tests are in `tests/`; `tests/conftest.py` documents the layout.

- `tests/unit_tests/` holds the tests. `test_parity_*.py` compare a feature with frozen data, `test_contract_*.py` run the shared
  contract check, `test_live_parameters*.py` check which parameters can change on a running feature, and the others test one feature
  or one rule.
- `tests/_support/` holds helpers that are not tests: `contract_suite.py` (`check_feature_contract`: schema, statuses, `run` against
  `process`, reset, chunking), `live_param_suite.py` (live and structural checks) and the input builders for the humanoid,
  imaging and symmetry features. Import them by name; `conftest.py` puts the folder on the path.
- **Catalog-wide suites** pick up every feature through `catalog()` and need no change for a new one: the contract, the invariants
  (non-finite input, empty outputs, state after a rejected call), the time rule, live validation, units, choices, naming and signatures.
  A feature that cannot be built with no arguments has an entry in the table of the suite (`OVERRIDES`), or in `NOT_COVERED` with the
  reason.
- **Known-answer tests**: an input whose result follows from the definition (a box of known size, a sine of known frequency, a straight
  path) or whose ordering is certain. Write these for every new feature. Never edit a numeric test to make it pass: a changed number
  needs a decision ({doc}`porting_status`).
- **Frozen data** are in `tests/data`: outputs of earlier versions of the features or of the original blocks, compared bit for bit by
  the tests that load them. They are the only oracles; there are no legacy implementations to compare with. Their provenance is
  written in `tests/data/README.md`: two files have a script that regenerates them (`tools/regenerate_trajectory_reference.py` and
  `tools/regenerate_gesture_segmenter_reference.py`) and the others are not regenerated, so a file with no generator is changed only
  by a decision and with a note.
- Without the compiled core only the tests of the pure Python data model run and the others are skipped, which is expected.

```bash
python -m pytest -q                          # the whole suite (core on the path)
python -m pytest -q tests/unit_tests/test_naming.py
python -m pytest --doctest-modules pyeyesweb # the examples of the docstrings
```
