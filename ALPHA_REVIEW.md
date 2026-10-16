# PyEyesWeb 2.0.0a1: alpha review, action plan and remaining work

**Status on 2026-10-16.** The review of 2026-10-14 produced work packages 0, A to G. Done and committed on the branch
`feature/v2-eyesweb-core`: package 0 (repositories), A (validation and status contract), B (naming and signatures), C (results,
recorder, discoverability), D (machinery), plus H and I (fixes found while verifying the facts for the documentation), the
documentation work packages WP0 to WP8 of `DOCS_PLAN.md` and the gallery of `TEACHING_PLAN.md` (T1 to T5). **What is left is in
section 8 ("Remaining work")**: packaging and release (package E, the prerequisite of everything public), the final documentation
pass (WP9), the data decision and the removal of the old examples (T6, T7), and a backlog of code, core and documentation
corrections found along the way. Read section 8 first; sections 1 to 7 are the record of what was decided and done.

Review of 2026-10-14, read-only: no code was changed. Four independent passes (correctness and numerics, public API
and usability, code quality and release readiness, documentation and teaching plans), merged here with duplicates
combined. Every finding was confirmed by a probe or a precise code reference unless marked *suspect*. State at review
time: 60 features in `catalog()`, pytest 2959 passed and 2 skipped (43 without the core), C++ tests 523, bindings
checks 87. State on 2026-10-16: 60 features, pytest 2963 passed and 12 skipped (34 without the core), 92 doctests, the docs
build with `-W` and the doctest builder (856 tests) pass, 10 gallery tutorials. TouchDesigner CHOPs are out of scope.

Companion files, to hand to the executing agents:
- `DEVELOPMENT_SPEC.md`: the binding contract and conventions (read first).
- `DOCS_PLAN.md`: documentation plan and status (WP0 to WP8 done, WP9 and the release items open).
- `TEACHING_PLAN.md`: gallery and teaching plan and status (tutorials 01 to 10 written; data, cleanup and checks open).
- `OPEN_POINTS.md`: older list of open items; section 8 below supersedes it (it keeps the notes on the skeleton presets and on
  the analysis of features that did not separate the example conditions).
- `docs/_snippets/facts.md`: the verified fact sheet (internal) with the suspected inconsistencies and the migration table.

How to read the items: **severity** (blocker, high, medium, low), **size** (S under an hour, M a few hours, L a day
or more), and an **id** from the original pass (C correctness, U usability, Q quality). Items are grouped in work
packages in the order I recommend; each package is self-contained and can be given to one agent.

## 0. Before anything else (blockers outside the code): DONE on 2026-10-14

- Q1: the C++ core is now its own repository, `EyesWebCore` (private repository of the lab's GitHub organisation, branch
  `main`). `EyesWebCore` is private and closed source: it holds the C++ core, its tests, the nanobind bindings
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
| Q3 | blocker for release (OPEN: section 8.1) | `pyproject.toml` has version 1.1.1 and a setuptools build; the compiled module is not built here. | The compiled module is built in the private `EyesWebCore` (binary wheel `eyesweb-core`, top-level module `eyesweb_core`); PyEyesWeb's own wheel is pure Python with a dependency on it; version `2.0.0a1`. | L |
| Q4 | high | Dependencies scipy, scikit-learn and tqdm are declared but the package only imports numpy. | `numpy` only; extras `test`, `docs`, `bench`. | S |
| Q5 | high | No LICENSE in `EyesWebTD`; the MIT code from your colleague's `eyw_core` and pocketfft (BSD) are not credited; 92 core `.cpp` files have no license header. | LICENSE and THIRD_PARTY_NOTICES; one SPDX line per file. | S/M |
| Q6 | high | Files that must not ship: the design notes (`DESIGN_PROPOSALS`, `OPEN_POINTS`, `STRUCTURE_REVIEW`, this file), `examples/scratch`, `main.py`, `site/` (6.6 MB of built docs), `archive_prototype/`. | Exclude in the sdist and wheel; delete `main.py`; move `site/` out of the repository (it is a build output). | S |
| Q14 | medium | No CI. | cibuildwheel on Windows, Linux and macOS, Python 3.10 to 3.13, warnings as errors. | M |
| Q17 | low | Python 3.13 not listed. | Add it; consider nanobind's stable ABI for 3.12+. | S |

Release checklist for 2.0.0a1 (from the quality pass): 1. version control for both trees; 2. commit; 3. licenses; 4.
scikit-build-core build, version 2.0.0a1; 5. dependencies trimmed; 6. sdist/wheel exclusions verified with
`python -m build`; 7. core version check; 8. packages A to D done; 9. full test run from the installed wheel in a fresh
virtual environment (without `EYESWEB_CORE_PATH`); 10. CI; 11. CHANGELOG entry, tag, TestPyPI first.

## 6. Work packages F and G: documentation and teaching materials: DONE except the final pass

Executed with the plans of `DOCS_PLAN.md` and `TEACHING_PLAN.md` (stack changed to Sphinx + PyData theme + sphinx-gallery; see
the "Decisions taken" sections there). Done: the Sphinx skeleton and CI workflows (WP1), the verified fact sheet (WP2), the
generated feature pages (WP3), the numpydoc docstrings of the 60 classes and the data model (WP4), the concept and
getting-started pages (WP5), ten theory pages, the notation and framework pages and five user-guide pages (WP6), ten gallery
tutorials with `pyeyesweb.datasets` and the helpers (WP7), how-tos, developer guide, README, changelog, migration guide
(WP8). Open: WP9 (polish and gate) and the items of section 8.

## 7. Order followed

Package 0, A, B and C, D, then H and I (fixes from the fact sheet), then the documentation and gallery (WP0 to WP8), now
packaging (E) and the final documentation pass. The recommended order from here is in section 8.

## 8. Remaining work (actionable, 2026-10-16)

Everything below is open. Items marked **[maintainer]** need a decision or an input that an agent cannot supply; all the
others can be executed by an agent from this document, `DEVELOPMENT_SPEC.md`, `DOCS_PLAN.md` and `TEACHING_PLAN.md`.
Recommended order: 8.1 packaging first (docs CI and the release depend on it), 8.2 in parallel (code fixes that change
documented behaviour), then 8.3 documentation WP9, 8.4 data and examples cleanup, 8.5 release, 8.6 later work.
Rules that still apply: no behaviour change without a test; docstrings true; the public repository never contains C++ sources
or the private repository's URL; do not push the branch `local-backup-pre-split` (it contains the bindings).

### 8.1 Packaging and release (work package E; two repositories)

Decided: the compiled core is its own package, import name `eyesweb_core`, published as the public binary wheel `eyesweb-core`
(first release `2.0.0a1`), built in the private repository `EyesWebCore`; `pyeyesweb` is a pure-Python wheel that depends on it.
Current state: `pyproject.toml` of PyEyesWeb is still the 1.1.1 setuptools file; `_core.py` already imports only `eyesweb_core`
and checks `REQUIRED_CORE = (2, 0)` against `eyesweb_core.__version__` (CMake project version 2.0.0).

| # | Task | Where | Acceptance |
|---|---|---|---|
| E1 | scikit-build-core `pyproject.toml` for the core: module `eyesweb_core`, version from the CMake project (`2.0.0a1` as a PEP 440 version: check how `__version__` and `REQUIRED_CORE` map, `2.0.0a1` must satisfy `(2, 0)`), nanobind stable ABI for Python 3.12+ if it works, `EW_BUILD_PYTHON=ON` | EyesWebCore | `pip install .` in a clean venv gives `import eyesweb_core; eyesweb_core.__version__`; `ew_tests` and the binding smoke test still pass |
| E2 | cibuildwheel (Windows, Linux manylinux, macOS x86_64 and arm64), Python 3.10 to 3.13, `-DEW_WARNINGS_AS_ERRORS=ON`, the binding smoke test run inside the wheel build; GitHub Actions in the private repository; publish to TestPyPI first, then PyPI (check that the name `eyesweb-core` is free; trusted publishing recommended) | EyesWebCore | wheels for 3 OSes x 4 Pythons on TestPyPI |
| E3 | LICENSE and `THIRD_PARTY_NOTICES` inside the wheel: the MIT code taken from the colleague's `eyw_core`, `pocketfft` (BSD-3), nanobind (BSD-3); one SPDX line per C++ file (92 `.cpp` files have none); **[maintainer]** check that the original EyesWeb licence allows a closed-source derived core, and choose the licence of `eyesweb-core` | EyesWebCore | licence files in the wheel, `check-wheel-contents` clean, written answer to the licence question |
| E4 | `pyproject.toml` of PyEyesWeb: version `2.0.0a1`; dependencies `numpy` and `eyesweb-core>=2.0,<2.1` only (scipy, scikit-learn, tqdm are not imported: remove; pandas stays optional); extras `docs` (exists), `datasets` (pooch, exists), `test` (pytest), `dev`; `requires-python >=3.10`; classifiers 3.10 to 3.13; check the `license` field format (the venv's setuptools rejects the current `project.license`: use the SPDX string form `license = "MIT"` plus `license-files`); packages limited to `pyeyesweb*`; no `eyesweb_core` inside this wheel | PyEyesWeb | `python -m build` gives a pure wheel and an sdist; `twine check` clean |
| E5 | sdist and wheel exclusions: `examples/` (939 MB of data and scripts), `docs/`, `tests/data` size check, internal notes (`ALPHA_REVIEW.md`, `DOCS_PLAN.md`, `TEACHING_PLAN.md`, `OPEN_POINTS.md`, `STRUCTURE_REVIEW.md`, `DESIGN_PROPOSALS.md`), `tools/`, the root `conftest.py`; keep `LICENSE.txt`, `README.md`, `CITATION.cff`, `CHANGELOG.md` | PyEyesWeb | the sdist lists no data and no notes; size of a few MB |
| E6 | `pip install pyeyesweb` must pull `eyesweb-core` (README, install page, fact sheet section 17 and `DOCS_PLAN.md` say so already: make it true) | both | in a fresh venv `pip install pyeyesweb` (from TestPyPI) then `python -c "import pyeyesweb; pyeyesweb.catalog()"` works without `EYESWEB_CORE_PATH` |
| E7 | CI of PyEyesWeb: `.github/workflows/tests.yml` (ubuntu, windows, macos x Python 3.10 to 3.13, installs from TestPyPI/PyPI, runs the whole suite and `pytest --doctest-modules pyeyesweb`) and `docs.yml` (written, never run: check action versions and permissions; enable GitHub Pages with the "GitHub Actions" source; `pypi_deploy.yml` still describes the 1.x release: replace or delete) | PyEyesWeb | both workflows green on a branch |
| E8 | Release: CHANGELOG heading with the real version and date, `CITATION.cff` `version` and `date-released`, README install line without the pre-release caveat once released, tag `v2.0.0a1`, GitHub release; the PyPI project `pyeyesweb` is at 1.1.1: check ownership and that `2.0.0a1` is a pre-release (not installed by default) | PyEyesWeb | `pip install --pre pyeyesweb` works from PyPI in a clean venv; the full suite passes from the installed wheels |
| E9 | Checks before publishing: no C++ in the public repository (`git ls-files` shows no `.cpp`, `.h`, `.hpp`), no local paths and no private URL in tracked files (grep `C:/Users` and the private repository URL), `examples/data` not in the wheel or sdist | PyEyesWeb | greps empty |

### 8.2 Code and core backlog (found while writing the documentation; none blocks the alpha unless the maintainer says so)

Decided by the maintainer and done: `is_noisy` flipped, `Suddenness.gamma` dimensionless, `CurvatureVelocityCorrelation` velocity per
second, `Symmetry` `reference_type` limited to `"label"`, `SpikeSynchronization(mode="timings")` public, XML round trip,
`GestureSegmenter` fed `is_noisy` directly. Open items, each with a recommended action:

| # | Item | Recommended action | Who |
|---|---|---|---|
| B1 | `Symmetry` signature still lists `reference_type` values `'barycenter'` and `'point'` although they raise `ValueError` | remove them from the `Literal`; update the choices test and the docstring | agent |
| B2 | `Kinematics.reset()` followed by `process` gives the reason "parameters changed: state reset" | find why `reset` is reported as a parameter change; make the reason empty and test it | agent |
| B3 | setter errors show the core's camelCase names (`SpectralArcLength.amplitude_threshold = -1.0` gives "amplitudeThreshold must be in [0, 1]") | translate core names in the wrapper's setter error path (reverse of `_core_names`); catalog-wide test that no error message contains a core name | agent |
| B4 | `ConvexHull()` default `integer_coordinates=True` raises `ValueError` on float contours | decide: default `False` or a clearer error | maintainer, agent |
| B5 | `Recorder` has no `reason` column; live loops keep their own list | add `rec.reasons` and a `reason` column in `to_frame()`; tests; contract text | agent |
| B6 | `KineticEnergy(labels=[...])` alone raises "no joints given" (needs `weights=` or `skeleton=`); a joint missing from an explicit `weights=` mapping weighs 0 | decide whether labels alone mean uniform weights; document either way | maintainer, agent |
| B7 | `Suddenness` docstring says `beta` is in [-1, 1] but outputs reach about 1.24 and -1.19; a still or constant-speed window is classified sudden (alpha 2, beta 0, gamma 0, rule `>= 0`) | fix the docstring now; the classification rule is the maintainer's to change later | agent (docstring), maintainer (rule) |
| B8 | `MotionNoiseDetector`: with several joints only the alphabetically last joint name decides the flag (core behaviour, documented) | review the core block: combine the joints or keep; a change is a core change and a regenerated `gesture_segmenter_reference.npz` (`tools/regenerate_gesture_segmenter_reference.py`) | maintainer, core |
| B9 | `CurvatureVelocityCorrelation`: `velocity_threshold` is dead in the core; `standard_deviation_threshold` and the `"simplified"` index act on per-sample velocity; with `differentiate=False` and one channel the curvature depends on the mode | ask the original author what they mean; remove or implement `velocity_threshold`; decide the units of the thresholds | maintainer, core |
| B10 | `HumanoidSimulator` with `joint_map` on real recordings flutters (excursions of metres; damping 5 to 30 all worse, 60 gives `inf`); `GenericModelEstimator` is fragile (cost falls only for some seeds and `initial_step`); `GenericModelPredictor` `masses_inertia` is no better than holding still | stability review of the model integrator in the core (step size, substeps, clamping); keep the limits documented (theory page) | core |
| B11 | `Rarity(method="information")`, `Videogram` and `ScalarPeakDetector` windows are structural; they could be live (need a `resize` in the core `ShiftWindow` and crop/pad in `VideoGram`, then `adoptParams` without reset) | core change, then move them to LIVE in `test_live_window_hop.py` | core |
| B12 | `SpikeSynchronization(mode="timings")` needs equal spike counts per train (core `validate`); `EventSynchronizationMECS` does not accumulate and has no `reset_every_buffer` | confirm against the original EyesWeb block whether MECS should accumulate; ragged spike trains would need a core change | maintainer, core |
| B13 | `TemporalSynchronization` `efficiency_step` was read from runs (`step/(n+1)`, or `(max_steps-step)/(max_steps-n-1)` with `max_steps`); `progression`, `stage_weights`, `CurvatureDispersion`, `Periodicity` `threshold`/`sort_by_power` and the `ScalarPeakDetector` delay are described only qualitatively | confirm with the original blocks and complete docstrings and theory pages | maintainer |
| B14 | `Harmonicity` is about 1.0 for almost any signal (on the drop-candidate list) | keep or drop | maintainer |
| B15 | `TrajectoryNonPlanarity` defaults (`radius=100`, `nan_value=999`) look like millimetres while `units` defaults to metres; `nan_fraction` has no visible effect; core `Equilibrium` default margin is 100 (the binding passes 0.1) | decided: keep; revisit with the original authors | maintainer |
| B16 | Skeleton presets `qualisys_sport`, `mediapipe` (reference joint, weights) and `openpose` (weights) are incomplete (`TODO(fill)` in `skeletons.py`; `SKELETON_TODO`): missing weights silently become uniform 1.0 | fill them; then remove the "incomplete" wording from the docs and the `Symmetry` error | maintainer |
| B17 | `Symmetry(pairs=[("a",)])` shows the raw nanobind error (ratio method); `run()` with a list of dict frames raises a bare `TypeError` (dict frames only work in `process`) | validate in the wrapper with clear messages | agent |
| B18 | `EllipsoidSphericity.process_axes` is a public entry point that bypasses the central check and `latest` | keep (documented) or route it through the wrapper | maintainer |
| B19 | Overflow (`1e300`) gives `INVALID_INPUT` after the block advanced; the next valid call can also be `INVALID_INPUT` (documented, pinned by a test) | optional: snapshot/restore in the wrapper for stateful features, or a core change | core |
| B20 | The second review pass promised in section 4 (function-level complexity and duplication scan, `adoptParams` consistency, point and image inputs under NaN) was not done | one read-only agent pass, then a fix list | agent |
| B21 | The private notes (`EyesWebCore/PORTING_STATUS.md`, `CONVENTIONS.md`) are stale in places (placement of `Directness`, location of `TimeWindowSynchronizer`); `examples/scratch/00_tour.py` mentions `pyeyesweb._eyesweb_core` | update the private notes; scratch is deleted in 8.4 | agent |

### 8.3 Documentation: final pass (WP9 of `DOCS_PLAN.md`)

Execute after B1 to B7 (they change wording) and, ideally, after E6 (so the install pages are true). Details and acceptance
criteria are in `DOCS_PLAN.md` section 11; in short: (1) references: **[maintainer]** supplies the sources for the 15
`**[citation needed]**` markers in the theory pages and for the features whose docstrings cite nothing, checks
`mazzarino2009impulsivity` and the 12 bib entries marked DRAFT (listed in `DOCS_PLAN.md` section 11.1); then `docs/references.bib` is completed and the gate fails on any
remaining marker; (2) identity (SVG logo, palette, footer logos, dark mode, mobile); (3) automated checks: catalog coverage from the
gallery back-references, stale-name grep, `linkcheck`, numpydoc validation, spelling; (4) known text issues (clumsy paragraph in
`theory/synchronization.md`, plain "next tutorial" sentences at the end of tutorials 05 and 07, the live/structural table duplicated
on two pages, the install section of the fact sheet, "five layers" wording, the three `TODO` comments left in `docs/index.md`); (5) the public/private
pass of `DEVELOPMENT_SPEC.md` and the move of the internal notes to the private repository; (6) first deploy to GitHub Pages.

### 8.4 Data, examples and cleanup (`TEACHING_PLAN.md` T6 and T7)

**[maintainer]** decisions: data host (Zenodo or OSF; `datasets.BASE_URL` is `None`), licence and performer consent, whether the
trimmed `.tsv.gz` files (14.9 MB, written by `tools/trim_example_data.py` into the git-ignored `examples/data_trimmed/`) replace the
full ones in `examples/data`, what happens to videos, kinect and imu (780 MB, 68 MB, 9 MB), the raw URL of `helpers.py` in the
downloadable notebooks (pin to the release tag). Agent tasks after the decisions: delete `examples/*.ipynb`, `examples/utils` and
`examples/scratch` (git-ignored, never shipped); rewrite `examples/data/README.md`, add `examples/data/LICENSE`; check the repository
size; make the stale-name and catalog-coverage checks part of the docs build.

### 8.5 Release readiness checklist (2.0.0a1)

1. 8.1 complete (E1 to E9); 2. B1 to B7 and B17 done; 3. 8.3 gates green on CI; 4. the data decision taken and the wheel and sdist
contain no data; 5. the full suite from the installed wheels in a fresh virtual environment (without `EYESWEB_CORE_PATH`) on
Windows, Linux and macOS; 6. the internal notes moved to the private repository; 7. tag, TestPyPI, then PyPI.

### 8.6 Later (outside this release)

TouchDesigner wrapper and CHOPs (`EyesWebTD`, own repository; several CHOP sources name removed or renamed blocks) and the creatives
documentation site (own repository, no maths or citations, patches and screenshots, reusing the generated feature metadata); the analysis
of features that did not separate the example conditions (`OPEN_POINTS.md` section 4); the core improvements B8 to B12 and B19; a
version switcher and a custom domain for the docs.
