# PyEyesWeb 2.0.0a1: alpha review and action plan

Review of 2026-10-14, read-only: no code was changed. Four independent passes (correctness and numerics, public API
and usability, code quality and release readiness, documentation and teaching plans), merged here with duplicates
combined. Every finding was confirmed by a probe or a precise code reference unless marked *suspect*. State at review
time: 60 features in `catalog()`, pytest 2959 passed and 2 skipped (43 without the core), C++ tests 523, bindings
checks 87. TouchDesigner CHOPs are out of scope.

Companion files, to hand to the executing agents:
- `DOCS_PLAN.md`: documentation plan (inventory of the 27 docs pages, target structure, generated reference, work
  packages WP0 to WP8).
- `TEACHING_PLAN.md`: plan to turn `examples/scratch/` into teaching notebooks that replace `examples/*.ipynb`
  (10-notebook course, work packages T0 to T7).

How to read the items: **severity** (blocker, high, medium, low), **size** (S under an hour, M a few hours, L a day
or more), and an **id** from the original pass (C correctness, U usability, Q quality). Items are grouped in work
packages in the order I recommend; each package is self-contained and can be given to one agent.

## 0. Before anything else (blockers outside the code): DONE on 2026-10-14

- Q1: the C++ core is now its own repository, `EyesWebCore` (https://github.com/InfoMusCP/EyesWebCore.git, branch
  `main`, first commit pushed). `EyesWebCore` is private and closed source: it holds the C++ core, its tests, the nanobind bindings
  (`bindings/`) and the build of the compiled module (`-DEW_BUILD_PYTHON=ON`); the wheel `eyesweb-core` is built there.
  PyEyesWeb is pure Python (no submodule, no C++).
- Q2: the 2.0 work is committed on `feature/v2-eyesweb-core` of PyEyesWeb (two commits: the work, then the submodule)
  and the branch is pushed. `main` is untouched (still v1.1.1).
- Workspace layout now: `EwbTD/EyesWebCore` (core repo), `EwbTD/PyEyesWeb` (Python repo), `EwbTD/_archive` (old
  prototype), `EwbTD/_standalone` (colleague's code, not part of either repository).
- Still local only: `examples/scratch/` (excluded in `.git/info/exclude`).

## 1. Work package A: input validation and status contract (correctness): DONE on 2026-10-14

The 2959 tests pass yet catch none of these: the rule "bad data gives `INVALID_INPUT` with a reason, never a plausible
number" (`DEVELOPMENT_SPEC.md` section 3) is enforced per feature, and several features miss it. Fix it centrally.

| id | sev | finding | action | size |
|---|---|---|---|---|
| C3, C4, C5, C6, U3 | high | NaN or infinite samples are accepted with status `OK` by `EnsembleDominance` (OK, NaN scores, leader picked or `-1`), `NonlinearInterdependence` (one NaN makes every result NaN with OK until it leaves the window), `Periodicity`, `ScalarPeakDetector`, `ContractionImpulsivity`, `SpikeSynchronization`, `TemporalSynchronization` (OK, NaN silently dropped); `SequenceDetector` raises a raw `ValueError` on NaN and a nanobind `TypeError` on 1e300. | One finite check in the central input validation (`Inputs.check` / the `_checked` wrapper), for every numeric input kind, with an explicit opt-out per input where non-finite values are meaningful. A non-finite sample gives `INVALID_INPUT` "NaN or infinite values" and is not buffered. | M DONE: `Input.problem` in the central wrapper; NaN or infinity is `INVALID_INPUT` and is not buffered; opt-outs `allow_non_finite` (humanoid and mass-spring inputs, `EnsembleDominance`), `integer=True` for `SequenceDetector` (1e300 is `INVALID_INPUT`). |
| C9 | low | `BinaryPulsesRegularity` stays `INVALID_INPUT` after a NaN until it leaves the window, unlike the others. | Follows from the central rule above (not buffered). | S DONE: follows from the central rule; the NaN no longer lingers in the window. |
| U1 | high | Dict input with a missing or an unknown label is accepted with `OK` and `valid=True`: `KineticEnergy(labels=["a","b"], weights={...}).process({"a": (0,0,0)})`. | Central check for dict input: a missing label gives `INVALID_INPUT` "missing joints: b"; an unknown key raises `ValueError` listing the expected labels. | S DONE: `LabelGuard._input_problem`: missing joints give `INVALID_INPUT` "missing joints: ...", with `labels` configured an unknown key raises `ValueError`; humanoid features keep dropouts. |
| C8, U2 | high | `INVALID_INPUT` results still carry plausible numbers: `Rarity().process([1., 2.])` gives `INVALID_INPUT` with `rarity=[36.84, -0.]`; 1e300 gives `-0.`. | Decide once and apply centrally when building the `Result`: on `INVALID_INPUT` the outputs are NaN (or 0/False for integer and boolean outputs) and `valid=False`. Today several fixed features deliberately keep the raw value: choose and make it uniform. | S DONE: `OutputsMixin.result` empties every output and `valid` on `INVALID_INPUT`; the diagnostic is the `reason`. |
| C7 | medium | No invariant "status OK implies every valid output is finite". | Assert it in `Result` construction under tests (or always), and add a catalog-wide test. | S DONE: catalog-wide `test_invariants_all_features.py` (OK implies finite, INVALID_INPUT implies empty, rejected samples not buffered); `finite_result` for overflow in six features. |
| C1 | high | Time rule: a repeated timestamp silently becomes a 1 s step and a decreasing timestamp gives a negative step, both `OK` (`base/core_feature.py` `_time_step`). | After the first call, a non-increasing timestamp gives `INVALID_INPUT` "non-increasing timestamp" and does not advance the state. | S DONE: a non-increasing timestamp is `INVALID_INPUT` "non-increasing timestamp" and changes nothing (`CoreFeature._input_problem`). |
| C2 | medium | Mixing calls with and without `timestamp` resets the previous time to 0, so the next timed call gets a step equal to the absolute time (for example 1e9 s with epoch times). | Track "no previous timestamp" as `None`; on the first timed call use `1 / sampling_rate` or report `WARMING_UP`. | S DONE: the previous timestamp is `None`; a call without previous time uses `1 / sampling_rate` or 1 s with the per-sample note. |
| U25 | low | Some invalid live values are accepted (`Kinematics.movement_threshold = -1`). | The setter validates like the constructor (sign and range). | S DONE: `check_range` in `_coerce_choices` (constructor and live) for two tables of parameter names; `test_live_validation_all_features.py` with `ACCEPTS_NEGATIVE`. |

Tests for the package: a catalog-wide parametrised test (driven by declared inputs, as `test_contract_all_features.py`
is) feeding a NaN frame, an inf frame, an empty frame and a huge value: never raises, gives `INVALID_INPUT`, the next
valid frame behaves as documented; tests for repeated, decreasing and mixed timestamps on every timed feature.

## 2. Work package B: naming and signatures (usability): DONE on 2026-10-14

Open points decided in package C: `parts=` replaces the bool switches (U23/U24); the `TrajectoryNonPlanarity` defaults (U10), the `Kinematics` mode names and the PLV `filter_order` (the core fixes 4) are kept. See `DEVELOPMENT_SPEC.md`, "Contract changes of work packages B and C".

| id | sev | finding | action | size |
|---|---|---|---|---|
| U5 | high | One concept, many names. Number of inputs: `n_inputs`, `number_of_inputs`, `number_of_input_trains`, `time_series_number`, `input_number`. Grid: `cells_x` vs `cells_along_x`. Memory length in samples: `window`, `window_size`, `window_length`, `length`, `buffer_length`, `data_memory`. Gaussian width: `sigma_value`, `std_dev_x`, `gaussian_sigma`. | One spelling per concept (`number_of_inputs`, `window` for every length in samples, one grid and one width name), enforced by a list of forbidden synonyms in `test_naming.py`. | M |
| U6 | high | Abbreviations and EyesWeb pin names in the public API: `ges_dur`, `frames` (a float), inputs `sqom`, `ci`, `cpr`, `ts1`, `ts2`, `x`, `y`; `use_cust_ampl`, `cust_ampl`, `cust_dist`, `std_dev_x`, `rho`, `num_of_regions`, `reg_init_values`; outputs `plv`, `xy`, `yx`. | Rename to spelled-out names (`gesture_duration`, `quantity_of_motion`, `contraction_index`, `custom_amplitude`, `number_of_regions`, `phase_locking_value`, `x_to_y_interdependence`, inputs `first_signal`/`second_signal`, ...). | M |
| U7 | high | Untyped or positional parameters: `MultiScaleEntropy` (no annotations), `PhaseLockingValue(filter_params=None)` (untyped tuple), `Rarity` (`alpha` positional, `type=` shadows a builtin), `Equilibrium` (all positional). | Annotate everything; keyword-only after `window, hop` (or after the joint arguments); rename `type`; replace `filter_params` with explicit `low_frequency`, `high_frequency`, `filter_order`. | S |
| U4 | high | Signatures that contradict behaviour: `Rarity` shows `window` as required but `Rarity()` works and `Rarity().window` raises; `Rarity` has both `window` and `data_memory`; `Symmetry` shows `joint_pairs` with no default. | Fix the signature derivation for both; keep one memory parameter in `Rarity`; `Symmetry`: one pairs argument. | S |
| U18 | medium | `output_dims='component'` (PointsDensity) vs `'components'` (Kinematics); `output_dims` and `output_type` used for the same idea; `algorithm` vs `method` for a choice of algorithm. | `'components'` everywhere; `method=` for algorithms (the spec's rule); `output_dims` only for components versus magnitude. | S |
| U19 | medium | `Symmetry`: the default `method='ratio'` needs a skeleton, `method='reflection'` rejects one; three ways to give pairs and two to give a reference. | Accept the skeleton for both methods (pairs and reference from it); keep one pairs and one reference argument. | M |
| U21 | medium | Generic output names (`value`, `matrix`, `series`, `sequences`); boolean outputs mix `is_sudden`, `gesturing`, `regular`, `found`, `peak`, `completed`. | Specific names (`equilibrium`, `synchronization_matrix`, `coarse_grained`); one style for booleans. | S |
| U11 | medium | `sampling_rate` defaults: `None`, `50.0` (four smoothness features) and `25.0` (`CurvatureVelocityCorrelation`); the time rule says no hidden default rate. | `None` everywhere; features that need a rate require it (or use timestamps) and say so. | S |
| U12, U13 | medium | `hop` is 1 in most windowed features and `None` (= window) in a few; `CurvatureDispersion` has a window but no hop; `window` is required in 15 features with no hint, and the error can name an internal class (`_SeriesBlock.__init__()`). | Document `hop=None` as non-overlapping or use one default; errors name the public class and say what `window` is. | S |
| U8 | high | `MultiScaleEntropy` needs at least 3000 samples with its defaults and the error does not say why. | Explain the minimum in the error (`minimum_points x max_scale`) and choose defaults that work. | S |
| U10 | medium | `Equilibrium` and `TrajectoryNonPlanarity` defaults look like millimetres while the default unit is metres (margin 100, radius 100, nan_value 999). | Check the EyesWeb unit of these defaults; scale them or document them. | S |
| U23, U24 | low | `RecurrencePlot` default `multiple_epsilons=[0.5]*100` floods `help()`; `SilhouetteCentroids` (14), `SilhouetteBodyParts` (6) and `RegionDependingPotentials` (4) have long lists of bool switches. | `None` default meaning one epsilon per channel; optionally a `parts=` sequence instead of the switches (needs a decision). | S/M |
| U22 | low | A 1-element array is not accepted for a `(1,)` input in the smoothness metrics. | Accept it as the declared shape says. | S |

## 3. Work package C: results, recorder and discoverability (usability): DONE on 2026-10-14

See `DEVELOPMENT_SPEC.md`, "Contract changes of work package C".

| id | sev | finding | action | size |
|---|---|---|---|---|
| U14 | medium | `Recorder` prints as an object address; `rec[0]` and `rec.<output>` fail (while `result.<output>` works); `to_frame()` gives statuses as integers. | `__repr__` (feature, rows, columns, status counts), integer and slice indexing returning `Result`s, attribute access to columns, status names in `to_frame()`. Note: you decided against the `computed()`/`held()` views; this item is only indexing and printing. | M |
| U15 | medium | `Status` is an `IntEnum`: `str(Status.OK)` is `'0'`. | `__str__` returns the name. | S |
| U16 | medium | Internals in tab completion (`no_output`, `result`, `INPUTS`, `OUTPUTS`); parameters not discoverable. | Make the two helpers private; add a read-only `parameters` view (as scikit-learn's `get_params`). | S |
| U17 | medium | `dir(pyeyesweb)` shows `_core`, `base`, `utils`; `SeriesBuffer` is advertised but not listed; `skeletons` leaks `Any`, `Dict`, `Tuple`; layer packages show their submodules; `TimeWindowSynchronizer` is in no public `__all__`. | Clean `__init__` exports and `__dir__`; decide where `TimeWindowSynchronizer` and `MassSpringModel` are public. | S |
| U9 | medium | Almost every output has an empty unit (velocity, kinetic energy, radii, durations ...). | Fill `Output.unit` (data-relative: `"<length>/s"`, `"s"`, `"samples"`, `"px"`), and test that features with `units=` have no empty length unit. | M |
| U20 | medium | Layer placement inconsistencies: `FilterContour` in physical signals but the other contour features in low-level; `Directness` (a path measure) in mid-level, `TrajectoryNonPlanarity` in low-level. | Write the placement rule in the catalog docstring and move what does not follow it. | S |
| U26 | low | `GenericModel*` features: only the error explains how to get a `model`. | One example in each docstring; name `MassSpringModel.from_file` in the error. | S |
| on `latest` | decision | Both reviewers agree: keep `latest` on `Feature` (it is state across calls; a `Result` is one immutable call). | No change. | |

## 4. Work package D: base machinery and maintainability (quality): DONE on 2026-10-14

See `DEVELOPMENT_SPEC.md`, "Contract changes of work package D".

| id | sev | finding | action | size |
|---|---|---|---|---|
| Q7 | medium | `base/signatures.py` calls `eval` on annotation text from nanobind signature strings: fragile and coupled to module globals. | Resolve annotations once with `typing.get_type_hints` or `inspect.get_annotations(eval_str=True)` and cache; or generate the signatures at build time (packaging step). | S/M |
| Q8 | medium | `__init_subclass__` sets the signature of `from_*` factories in place; a subclass of a subclass can overwrite the parent's (shared function object). | Wrap per class or compute lazily; test with a grandchild class. | S |
| Q9 | medium | `_core.py` falls back to any `eyesweb_core` on `sys.path`, so a stale development build can be loaded silently; no version check. | Expose a core version or build hash and check it at import. | S |
| Q16 | low | `physical_signals/humanoid.py` is 896 lines and mixes the model tables with the features. | Move the joint and bone tables to a private module. | M |
| Q11 | medium | `tests/reference` keeps 13 legacy oracles beside frozen data in `tests/data` (1.4 MB): two sources of truth. | Keep only the oracles still imported; keep the scripts that regenerated the frozen data in `tools/`. Done: all oracles removed (2026-10-15). | S |
| Q12 | medium | `contract_suite.py`, `live_param_suite.py` and input helpers sit at the test root as non-test modules. | Move them to `tests/_support/` and document the suites in `conftest.py`. | S |
| Q10 | medium | `tests/benchmarks` is outside pytest and not maintained for 2.0. | Convert to `pytest-benchmark` marked slow, or move to `tools/bench`. | M |
| Q13 | medium | Strict warnings (`/W4`, `-Wall -Wextra`) apply only to the core library, not to bindings and tests; no warnings-as-errors option. (The release build has 0 warnings.) | Apply to every target; add an option for CI. | S |
| Q15 | low | `.gitignore` does not cover `build/`, `*.pyd`, `examples/scratch/`. | Add them. | S |

Not covered by this review (the passes were sampled, not exhaustive): a function-level complexity and duplication
scan, consistency of `adoptParams` live/structural classification under live `window` changes, and point or image
inputs under NaN. These deserve a short second pass after package A.

## 5. Work package E: packaging and release (quality; you planned it last)

| id | sev | finding | action | size |
|---|---|---|---|---|
| Q3 | blocker for release | `pyproject.toml` has version 1.1.1 and a setuptools build; the compiled module is not built here. | The compiled module is built in the private `EyesWebCore` (binary wheel `eyesweb-core`, top-level module `eyesweb_core`); PyEyesWeb's own wheel is pure Python with a dependency on it; version `2.0.0a1`. | L |
| Q4 | high | Dependencies scipy, scikit-learn and tqdm are declared but the package only imports numpy. | `numpy` only; extras `test`, `docs`, `bench`. | S |
| Q5 | high | No LICENSE in `EyesWebTD`; the MIT code from your colleague's `eyw_core` and pocketfft (BSD) are not credited; 92 core `.cpp` files have no license header. | LICENSE and THIRD_PARTY_NOTICES; one SPDX line per file. | S/M |
| Q6 | high | Files that must not ship: the design notes (`DESIGN_PROPOSALS`, `OPEN_POINTS`, `STRUCTURE_REVIEW`, this file), `examples/scratch`, `main.py`, `site/` (6.6 MB of built docs), `archive_prototype/`. | Exclude in the sdist and wheel; delete `main.py`; move `site/` out of the repository (it is a build output). | S |
| Q14 | medium | No CI. | cibuildwheel on Windows, Linux and macOS, Python 3.10 to 3.13, warnings as errors. | M |
| Q17 | low | Python 3.13 not listed. | Add it; consider nanobind's stable ABI for 3.12+. | S |

Release checklist for 2.0.0a1 (from the quality pass): 1. version control for both trees; 2. commit; 3. licenses; 4.
scikit-build-core build, version 2.0.0a1; 5. dependencies trimmed; 6. sdist/wheel exclusions verified with
`python -m build`; 7. core version check; 8. packages A to D done; 9. full test run from the installed wheel in a fresh
virtual environment (without `EYESWEB_CORE_PATH`); 10. CI; 11. CHANGELOG entry, tag, TestPyPI first.

## 6. Work packages F and G: documentation and teaching materials

Hand `DOCS_PLAN.md` and `TEACHING_PLAN.md` to the companion agent. Main points:
- Documentation: 27 pages inventoried (the `Lightness`, `Clusterability` and `StatisticalMoment` pages go; the
  navigation points to a missing `statistical_moment.md`); the README example uses the removed `SpeedSmoothness`; the
  feature reference is generated from `catalog()` and replaces the two current generator scripts; every page reflects
  a fixed list of facts (contract, time rule, units and the humanoid exception, string choices and bools, `from_*`,
  skeletons and `joint_map`, layers, live and structural parameters, statuses, `latest`, dropped features, fidelity
  policy); gated by `mkdocs build --strict` and doctests. Docstrings are mostly clean; stale names are in the docs
  pages, the README and the old notebooks.
- Teaching: the scratch notebooks become a 10-notebook course covering all 60 features, without reviewer notes,
  internals (`where`, `call_path`) or private calls (`06_synchronization` has 46 `_process_window` calls to rewrite);
  `common.py` is split into an examples helper module; all 6 current public notebooks are replaced; data: Qualisys and
  synthetic only (`examples/data` is 939 MB, 780 MB of it video, which should not stay in the repository); a check
  script for CI.
- Inputs you must supply: the literature references, the data consent and license, and any wording for the dropped
  features.

## 7. Suggested order and effort

1. Package 0 (commit) now.
2. Package A (validation and status contract): the most important for correctness; about a day.
3. Packages B and C (naming, signatures, results): one to two days; they change the public API, so they go before
   the documentation.
4. Package D (machinery): half a day.
5. Packages F and G (documentation and teaching): with the companion agent, after B and C so the names are final.
6. Package E (packaging and release) last, as planned, then the TouchDesigner CHOPs.
