# PyEyesWeb 2.0 — Documentation Plan and status (for the finalizing agent)

Paths are relative to the root of the PyEyesWeb repository (branch `feature/v2-eyesweb-core`; the core is the sibling checkout `EyesWebCore`, private). Run the library and the docs with:
```
PYTHONPATH="<EyesWebCore>/build/Release;<PyEyesWeb>" EYESWEB_CORE_PATH=<EyesWebCore>/build/Release python ...
```
(Windows paths: `;` as separator; on Git Bash prefix with `MSYS_NO_PATHCONV=1`.) Once the `eyesweb-core` wheel exists (`ALPHA_REVIEW.md` 8.1) no path variable is needed.

**Where to start.** Work packages WP0 to WP8 are done and committed; **what is left is section 11 (WP9 and the release items)**, which follows `ALPHA_REVIEW.md` section 8.3. Sections 0 to 10 record the decisions and the mechanisms that were built; read them when you touch the mechanism. Companions: `DEVELOPMENT_SPEC.md` (contract and rules), `ALPHA_REVIEW.md` (section 8 is the master list of remaining work), `TEACHING_PLAN.md` (the gallery).

## Status (2026-10-16)

| WP | Content | Status | Evidence in the repository |
|---|---|---|---|
| WP0 | Audit | DONE | stale-name grep, doctests, catalog dump (kept outside the repository); `docs/_data/instantiation.yaml` is its output |
| WP1 | Sphinx skeleton, CI | DONE (CI never run) | `docs/conf.py`, `docs/requirements.txt`, `docs/Makefile`, `docs/make.bat`, `docs/build.ps1`, `docs/_static/custom.css`, `docs/_templates/core_version.html`, `.github/workflows/docs.yml`; the mkdocs files and the TSV reader pages are deleted |
| WP2 | Fact sheet | DONE | `docs/_snippets/facts.md` (internal; 19 sections with the run output) |
| WP3 | Generated API | DONE | `docs/_ext/feature_pages.py`, `docs/_data/{families,instantiation,wp4_waivers}.yaml`, `docs/api/*.md` (layer pages, `overview`, `data_models`, `skeletons`, `catalog`, `datasets`), `tests/unit_tests/test_docs_feature_pages.py`; 60 generated pages |
| WP4 | Docstrings | DONE (references open) | numpydoc docstrings of the 60 classes and the data model; `wp4_waivers.yaml` is empty; 92 doctests (`pytest --doctest-modules pyeyesweb`) |
| WP5 | Getting started, concepts | DONE | `docs/getting_started/{install,quickstart}.md`, `docs/concepts/{layers,inputs,results,time_units_parameters}.md`; executed `{doctest}` blocks |
| WP6 | Theory, user guide | DONE (15 citations missing) | `docs/theory/{framework,notation,kinematics_energy,smoothness,shape_symmetry_balance,impulsivity_suddenness,gesture_segmentation,entropy_rarity_periodicity,synchronization,dominance,humanoid_models,imaging}.md`, `docs/user_guide/{physical_signals,low_level,mid_level,high_level,analysis_primitives}.md`, `docs/references.bib` (27 entries), `docs/references.md` |
| WP7 | Gallery | DONE (data and cleanup open: `TEACHING_PLAN.md` T6, T7) | `docs/_ext/tutorial_reset.py`, `examples/` (10 tutorials, `helpers.py`), `pyeyesweb/datasets.py`, `tools/trim_example_data.py`; gallery run 36.9 s |
| WP8 | How-tos, developer guide, README, changelog | DONE | `docs/howto/{load_data,map_skeleton,realtime_live_parameters,batch_to_pandas,images}.md`, `docs/developer/{architecture,conventions,adding_a_feature,building_the_docs,porting_status}.md`, `docs/migration.md`, `docs/changelog.md`, `README.md`, `CHANGELOG.md` (2.0.0 entry) |
| WP9 | Polish, gate, first deploy | OPEN | section 11 |

State: `python -m sphinx -b html -W --keep-going docs docs/_build/html` and the doctest builder (856 tests) pass; `pytest` 2963 passed and 12 skipped; `pytest --doctest-modules pyeyesweb` 92 passed. `nitpicky` is still off (`docs/conf.py`). The release items (packaging, data, tag) are in `ALPHA_REVIEW.md` section 8.

**Rules that still apply.** Documentation content matches the code (the code wins; report the disagreement). Docs are part of the code review (`DEVELOPMENT_SPEC.md` section 9). The public repository never contains C++ sources or the URL of the private repository; nothing from `EyesWebCore` is quoted at length in the docs (describe behaviour, not code). `docs/_legacy` and the local `site/` hold the old mkdocs pages and describe the 1.x library: mine them, never copy names from them.

**Sources of truth, in this order** (the earlier wins; a disagreement goes on a list for the maintainer): 1. the code and `pyeyesweb.catalog()` (60 `FeatureInfo` entries: 11 physical_signals, 22 low_level, 7 mid_level, 1 high_level, 19 analysis_primitives); 2. `DEVELOPMENT_SPEC.md`; 3. `docs/_snippets/facts.md` (verified on 2026-10-15/16; sections that changed afterwards are listed in 11.4).

---

## 0. Decided stack (final, from the maintainer)

| Concern | Choice | Replaces |
|---|---|---|
| Generator / theme | **Sphinx + PyData Sphinx Theme** (`pydata-sphinx-theme`) | mkdocs, mkdocs-material/readthedocs theme |
| Docstrings | numpydoc style, **decided**: the `numpydoc` extension (validation hook), not napoleon | mkdocstrings numpy handler |
| API pages | `sphinx.ext.autosummary` (+ `autodoc`) and **one generated page per catalog feature** through a small in-repo extension (`docs/_ext/feature_pages.py`: at `builder-inited` it writes one reST page per feature under `docs/api/generated/`; the layer tables use the directive `.. feature-table:: <layer>`) reading `catalog()` and the feature's `inputs`, `outputs` (Schema), `parameters` | `docs/scripts/gen_pages.py`, `tools/update_catalog_docs.py`, mkdocs-gen-files, literate-nav, section-index |
| Tutorials | **`sphinx-gallery`** over the percent scripts (see TEACHING_PLAN.md) | mkdocs-jupyter, `examples/build.py`, `examples/check.py` |
| References | `sphinxcontrib-bibtex`, one `docs/references.bib`, a "References" block per metric, **`unsrt` numeric labels, no custom style** (decided, §4.3) | `TODO(ref)` placeholders in docstrings |
| Cross-links | `intersphinx` to python, numpy, scipy, pandas, matplotlib | — |
| Layout widgets | `sphinx-design` (cards, grids, tabs, dropdowns) | pymdownx tabbed/details/admonition |
| Math | `sphinx.ext.mathjax` (built in) | `docs/javascripts/mathjax.js` |
| Source format | **Decided: MyST Markdown (`myst-parser`) for the prose pages** (reuses the old `.md`; directives via MyST `{directive}` syntax, maths via `dollarmath`/`amsmath`), docstrings in numpydoc/RST, API pages generated, gallery text blocks in RST (checked 2026-10-15 in the sphinx-gallery syntax documentation, 0.22: text blocks are reST only, there is no Markdown/MyST option). `index` and generated pages may stay `.rst`; do not mix within one page | Markdown |
| Hosting | GitHub Pages (as now), built in CI | `mkdocs gh-deploy` |

Tone: scientific and institutional, like the scikit-learn, SciPy and NumPy documentation: definitions, notation, theory pages, references; not marketing. One-line pitch on the landing page, no superlatives.

Dependencies for the build go in a **`docs` extra** of `pyproject.toml` (replacing the mkdocs lines in `dev`) and a pinned `docs/requirements.txt` for CI; both list: `sphinx`, `pydata-sphinx-theme`, `numpydoc`, `sphinx-gallery`, `sphinxcontrib-bibtex`, `sphinx-design`, `matplotlib`, `pandas`, `scipy`, `pillow` (gallery thumbnails). Python 3.11 (CI also tests 3.10-3.13, §4.5). `myst-parser`, `sphinx-copybutton` and `pooch` (the `datasets` extra) are in the list too. `docs/requirements.txt` holds the exact pins the docs were built with; the `docs` extra holds minimum versions. The rest of `pyproject.toml` (still the 1.1.1 setuptools file) is packaging work: `ALPHA_REVIEW.md` 8.1 (E4).

---

## 1. Inventory of existing artefacts and disposition

### 1.1 `docs/` pages (the old mkdocs Markdown, 1836 lines)

Historical inventory. **Status 2026-10-16: every row is done** (last column). The old pages that were not deleted are in `docs/_legacy/` (`index.md` and `user_guide/`, 26 files; excluded from the build by `exclude_patterns`), kept only for mining text and references; **delete the folder in WP9** (11.5). The built mkdocs output `site/` is untracked and git-ignored; delete the local copy by hand.

| Path (under `docs/`) | Topic | Plan | Notes | Done |
|---|---|---|---|---|
| `index.md` | Home | **rewrite** → `index.md` (MyST) | landing page (§4.4); keep EU/CP logos and funding text | landing page built; the executed example, the timescale line and the citation block are still `TODO` comments in `index.md` (11.4) |
| `user_guide/getting_started.md` (91) | install + first example | **rewrite** | old `SlidingWindow` + `SpeedSmoothness` style; new: install, core loading, `process`/`run`, `Recorder` | `getting_started/install.md`, `quickstart.md` |
| `user_guide/library_structure.md` (49) | packages | **rewrite** → `concepts/layers` | layers + `catalog()` | `concepts/layers.md` |
| `user_guide/input_contract.md` (83) | inputs | **rewrite** → `concepts/inputs` | dict / `(N,3)` / `(n,D)` forms, `labels=`, skeleton presets, `joint_map` (verify it still exists), `InputKind.IMAGE`, `from_*`, shape `ValueError` vs `INVALID_INPUT` | `concepts/inputs.md` |
| `user_guide/output_contracts.md` (162) | outputs | **rewrite** → `concepts/results` | `Schema/Output/Result/Status/Recorder/latest`; see DEVELOPMENT_SPEC §3 and work packages A, C | `concepts/results.md` |
| `user_guide/integrations.md` (8) | TD/Unity/Max | **delete or merge** into how-tos | claim only integrations that exist; TouchDesigner is the separate later site (§8) | deleted |
| `.../theoretical_framework.md` (64) | conceptual model | **keep, edit** → `theory/framework` | keep `assets/ConceptualModel.png`; fix class names; layer table must match `catalog.Layer`/`Timescale` | `theory/framework.md` |
| `.../physical_signals/physical_signals.md` (37), `low_level.md` (79), `mid_level.md` (80), `high_level.md` (58), `analysis_primitives.md` (93) | layer pages | **rewrite** | catalog tables become a generated `.. feature-table:: <layer>` directive (from `catalog()`); one real narrative per layer | `user_guide/<layer>.md` and the generated `api/<layer>.md` (`feature-table` directive) |
| `low_level/contraction_expansion.md`, `direction_change.md`, `kinetic_energy.md`, `geometric_symmetry.md`, `postural_balance.md`, `smoothness.md` | per-topic theory | **merge** into `theory/` pages (one per family, see §3) | keep the theory paragraphs; smoothness becomes the smoothness family (SpectralArcLength, LogDimensionlessJerk, SubmovementCount, Harmonicity, Curvature*); verify membership and layer in code | merged into `theory/{kinematics_energy,smoothness,shape_symmetry_balance}.md` |
| `mid_level/impulsivity.md`, `suddenness.md` | per-topic theory | **merge** | | `theory/impulsivity_suddenness.md`, `theory/gesture_segmentation.md` |
| `mid_level/lightness.md`, `analysis_primitives/clusterability.md`, `statistical_moments.md` | dropped features | **delete** | listed on the "Removed features" page only | deleted; the names are in `migration.md` |
| `analysis_primitives/mse_dominance.md`, `rarity.md`, `synchronization.md` | theory | **merge/rewrite** | sync becomes a family page (12 classes, verified 2026-10-15) | `theory/entropy_rarity_periodicity.md`, `dominance.md`, `synchronization.md` |
| `utils/index.md` (0), `utils/tsv_reader.md` (394) | TSV reader | **delete both** (decided 2026-10-15): `TSVReader` (`pyeyesweb/utils/tsv_reader.py`) was removed from the library; loading data is covered by the `pyeyesweb.datasets` helper and the gallery (TEACHING_PLAN §5). Delete the pages at WP1 | | deleted |
| `assets/*` | logos, figures | **keep** (inventory in §4.4); SVG logo wanted | | kept; the SVG logo is still open (11.3) |
| `javascripts/*`, `overrides/*`, `scripts/gen_pages.py` | mkdocs machinery | **delete** (superseded by `conf.py`, `_static/custom.css`, `_ext/`) | | deleted |
| `mkdocs.yml`, `site/` | mkdocs config and built output (6.6 MB) | **delete from repo** after the Sphinx build is green; `_build/` into `.gitignore` | `site/` is also excluded from release (ALPHA_REVIEW Q6) | `mkdocs.yml` deleted; `site/` untracked and ignored |

### 1.2 Root files
| File | Plan | Action | Done |
|---|---|---|---|
| `README.md` | **rewrite** | example uses `SpeedSmoothness` + `SlidingWindow` (both gone). New: one-paragraph pitch, install (the wheel depends on `eyesweb-core`; `EYESWEB_CORE_PATH` for dev builds), a 10-line example with `process`/`run`/`Recorder` that is **executed in WP8**, links to docs and gallery, citation, funding | DONE (2.0 example, executed in WP8) |
| `CHANGELOG.md` | **rewrite** | single 2.0.0 entry (Keep a Changelog): Added / Changed / Removed / Fixed ("Corrected in the core") + migration table old→new, built from `PORTING_STATUS.md` and DEVELOPMENT_SPEC "Contract changes". 1.x entries kept below untouched. Included in the docs as the Changelog page | DONE (2.0.0 entry, 'unreleased'; date and wording come with the release, `ALPHA_REVIEW.md` E8) |
| `STRUCTURE_REVIEW.md`, `DESIGN_PROPOSALS.md`, `OPEN_POINTS.md`, `ALPHA_REVIEW.md`, `DOCS_PLAN.md`, `TEACHING_PLAN.md` and the other agentic-development notes | internal | **move to the private repository** (`EyesWebCore/dev-notes/`) **before release**; not in the public repo, docs, sdist or wheel; conclusions go into the developer guide | OPEN: move before release (11.5) |
| `DEVELOPMENT_SPEC.md` | source | **kept and published** as the "Contributing / development spec" page for open-source contributors: MyST `{include}` (do not copy; update only in the source). Needs a pass first to remove private repository names and C++ internals (WP8) | OPEN: public pass and the decision how it is published (11.5); no page includes it yet |
| `CITATION.cff` | **update** | version 2.0.0, date | OPEN: no `version` and no `date-released` yet (release step E8) |
| `main.py` | delete (ALPHA_REVIEW Q6) | | DONE (deleted) |
| `pyeyesweb/utils/tsv_reader.py` | **removed 2026-10-15** | its docs page and `utils/index.md` are on the deletion list (§1.1); the 2.0.0 CHANGELOG entry lists `TSVReader` under Removed | DONE |
| `tools/update_catalog_docs.py` | **delete** | superseded by the generated pages | DONE (deleted) |
| `docs/conf.py`, `docs/Makefile`/`make.bat` | **new** | WP1 | DONE |

### 1.3 Docstrings (checked in WP0 and WP4; the stale-name grep becomes part of the gate, 11.2)
Grep across `pyeyesweb/**/*.py` found no occurrences of `SpeedSmoothness`, `Smoothness(`, `time_mode`, `fix_`, `SkeletonManipulator`, `Lightness`, `ZeroCross`, `StatisticalMoment`, `Clusterability`, `Trajectory(`, `GetKinematical`. Suspects to re-check:
- `SlidingWindow` was **removed on 2026-10-14**: any remaining mention (it was in `data_models/sliding_window.py:37`) must be gone.
- `process_window`: only the private `_process_window` exists; no public docstring may mention it.
- `>>>` examples: run `python -m pytest --doctest-modules pyeyesweb` (core on the path) and fix every failure; in Sphinx also enable `sphinx.ext.doctest` only if the maintainer wants doctests in the docs (the gallery already executes code).
- `Enum` in several files: the public API uses **string choices**; docstrings list the strings, never enum members.
- Old parameter names: after package B every parameter has a single spelling (`number_of_inputs`, `window`, `cells_along_x`, `gaussian_sigma`, `filter_window_length`, `gesture_duration`, `first_signal`/`second_signal`, ...). Grep docstrings against `feature.parameters` of every catalog class (script: for each class compare the names in the `Parameters` section with `inspect.signature`); every mismatch is a finding.
- Other stale items: `rate_hz` (now `sampling_rate`, default `None`), `t=`/`ts=` (now `timestamp`/`timestamps`, seconds), boolean `fix_*`, `output_dims` values, `COMPONENT` (spelled `"components"`), bool switches replaced by `parts=`.
Record results in a table (file:line, wrong text, fix) in WP0.

Stale names now survive only in `docs/_legacy`, in the old `examples/*.ipynb` (both to be deleted), and deliberately in the changelog, migration and porting-status pages: `SpeedSmoothness`, `Lightness`, `StatisticalMoment`, `Clusterability`, `HistogramRarity`, `Synchronization`, `SlidingWindow`, `dims=3`, `fix_`, `SkeletonManipulator`, `ZeroCross`, `GetKinematical`. The list of the gate is in 11.2.

---

## 2. Facts every page must reflect (the "2.0 fact sheet")
**Done in WP2 (2026-10-15): `docs/_snippets/facts.md`** (MyST, `orphan`, excluded from the build by `exclude_patterns`, internal: move it to `dev-notes/` or strip it before release). Every item has its statement, the `file:line` evidence, the snippet that was run with its real output and a status. The list below is the **verified summary**; where it and the sheet differ, the sheet (and the code) win. Page writers read the sheet, not this list.
1. **Contract**: `feature.process(*sample, timestamp=None)` (keyword-only; returns an immutable feature-specific `<Feature>Result`, a `Result` subclass), `feature.run(*recording, timestamps=None, reset=True)` (a `Recorder`, numbers identical to a loop of `process`), `reset()`, `inputs`, `outputs` (the `Schema`, known before data), `latest` (last `OK` result, **`None` before the first one** and after `reset()`), `parameters` (read-only mapping; a parameter resolved at construction and not kept, `skeleton`, is not listed). One documented extra entry point: `EllipsoidSphericity.process_axes`.
2. **Result**: `status`, `reason`, `timestamp` (s, NaN unknown), `valid` (per output), one attribute per output (`result.kinetic_energy`, `result["radii_0"]`); a missing value is NaN/0/False, never `None` (checked on all 60 features); also `ok`, `is_valid` (alias), `with_time`, `to_dict`, `to_array`, `to_flat_dict()` (integer statuses).
3. **Status**: `OK`, `WARMING_UP`, `NO_OUTPUT`, `INVALID_INPUT`; `str(Status.OK) == "OK"`, `int(Status.OK) == 0`. The `WARMING_UP` reason is a **sample count** ("k of N samples"), `NO_OUTPUT` is "between windows". `INVALID_INPUT`: every output empty and `valid` all False; state unchanged for the finite check, a missing joint and a non-increasing timestamp, **not** for an overflow ("the result is not finite").
4. **Recorder**: `repr`, `rec[3]`/`rec[-1]` are `Result`s, `rec[2:5]` a list, `rec["name"]`/`rec.<output>` a column, `timestamps`, `to_frame()` (status names), **`to_numpy()`** (not `to_array()`); images never in `to_numpy()`/`to_frame()` (verified).
5. **Errors**: wrong shape/kind -> `ValueError`; bad data -> `INVALID_INPUT` + `reason`; too few samples -> `WARMING_UP`; invalid parameters raise at construction **and at setters** (the feature is left unchanged); an unknown key in a dict frame raises only when labels are configured (a missing joint is `INVALID_INPUT`); misspelled keyword -> `TypeError` naming the feature; a non-finite timestamp raises `ValueError` (timed classes).
6. **Time rule**: seconds everywhere; step = difference of `timestamp`s, else `1/sampling_rate`, else 1 s per sample with "no time given: per-sample derivatives" in the `reason`. `sampling_rate` (Hz) is a parameter of 16 classes, **default `None` in all**. The timestamp checks (non-increasing -> `INVALID_INPUT`, non-finite -> `ValueError`) belong to the 9 `_timed` classes only; the five window metrics (`SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount`, `CurvatureVelocityCorrelation`) raise at construction without `sampling_rate` and ignore `timestamp`. First timed call: step `1/sampling_rate` or 1 s, never the absolute time. `ContractionImpulsivity.frames` is now `sampling_rate`.
7. **Windows**: 22 `WindowedFeature` classes with `window` (samples) and `hop` (default 1); `window` has no default except the four smoothness metrics (60) and `MultiScaleEntropy` (3000); `EventSynchronization*` `hop=None` = `window` (the only valid value); `CurvatureDispersion` has `window` and no `hop`; six more classes have a `window` parameter without being windowed features.
8. **Units**: lengths and thresholds in metres; `units="m"|"mm"` in **exactly 10 classes** (default "m"); parameters are scaled, data and outputs never; `Output.unit` is documentation and follows the parameters (`"<length>"`, `"<input>"`, `"samples"`, `"frames"`, `"px"`, `"deg"`, `"s"`, `"cells"`, compounds, the concrete unit when `units=` was given). **Humanoid exception verified** (`HumanoidSimulator` converts at the boundary around an internal millimetre model; `GenericModel*` run in the unit of the user's model, `units` only names it).
9. **Choices**: lower-case strings, case-insensitive, `-`/space count as `_`, wrong value lists the options (also from setters); real bools; no enum in a parameter (the only public enums are `Layer`, `Timescale`, `InputKind`, `Status`); `parts=` for `SilhouetteCentroids`, `SilhouetteBodyParts`, `RegionDependingPotentials`, read back as a tuple in the block's order (not the documented order); `output_dims` vocabularies differ (`Kinematics` components|tangential, `PointsDensity` components|module, `Symmetry` global|components).
10. **Constructors**: `from_*` exist in exactly three classes (six constructors): `KineticEnergy.from_position/from_velocity`, `Kinematics.from_point/from_series`, `LogDimensionlessJerk.from_velocity/from_acceleration`; list by introspection.
11. **Skeletons**: presets `kinect_v2` (complete), `qualisys_sport`, `mediapipe` (no reference, no weights), `openpose` (no weights) documented as incomplete (`SKELETON_TODO`; `TODO(fill)` at `skeletons.py:71,72,89,90,103`); missing weights silently become uniform 1.0; `skeleton=` in five classes (`KineticEnergy`, `MotionNoiseDetector`, `Symmetry`, `PointsDensity`, `PointsPredictor`); `labels=`, `pairs=`, `weights=` override; **`joint_map` only on the six humanoid/generic-model classes**.
12. **Dims**: `dims=None` (inferred from the first frame, forgotten by `reset()`) exists in four classes only: `Kinematics`, `CurvatureDispersion`, `Suddenness`, `SuddennessImpulsivity`.
13. **Layers and catalog**: 60 features: **11 physical_signals, 22 low_level, 7 mid_level, 1 high_level, 19 analysis_primitives** (verified 2026-10-15); the synchronization package has **12** classes; the placement rule is in the `catalog` docstring (`FilterContour`, `Directness`, `TrajectoryNonPlanarity` are low-level); `dir(pyeyesweb)` lists the public modules, `base`/`utils` are internal (not listed, still reachable) and are not documented.
14. **Live vs structural**: live = applied in place, structural = state resets and the next `reason` says "parameters changed: state reset"; `window`/`hop` keep the newest samples. Per-parameter source: the `LIVE`/`STRUCTURAL` tables of `tests/unit_tests/test_live_parameters*.py` (table generated in the sheet; `examples/scratch/live_parameters_classification.md` is git-ignored).
15. **Removed features**: complete old-name -> new-name/removed table with reasons in the sheet (section 18), absence verified by import.
16. **Fidelity policy**: ports are faithful; a corrected defect is the core's behaviour with no flag (no `fix_*`/`legacy` parameter exists) and the page says **"Corrected in the core"** with the one-line text taken from the private `PORTING_STATUS.md` (63 entries).
17. **Install/core**: `pyeyesweb._core` requires `REQUIRED_CORE` (major.minor, 2.0) and raises `ImportError` for another version or none (texts in the sheet); `import pyeyesweb` and `data_models` need no core, `catalog()` does. **`pip install pyeyesweb` pulling `eyesweb-core` is not yet true** (`pyproject.toml` is still the 1.1.1 file with numpy, scipy, scikit-learn and tqdm; `ALPHA_REVIEW.md` E4 and E6): the install pages state the decision and carry a pre-release note until then.

---

## 3. Target information architecture (toctree)
```
index                         Landing page (§4.4)
Getting started
  install                     pip, core wheel, EYESWEB_CORE_PATH, version check
  quickstart                  process vs run, Recorder, plot (executed code)
Concepts
  layers                      layers, timescales, catalog(), placement rule
  inputs                      forms, labels, skeletons, joint_map, images, from_*
  results                     Schema, Result, Status, Recorder, latest, errors
  time_units_parameters       seconds, sampling_rate, m/mm, humanoid exception, strings/bools, live vs structural
Theory (notation, definitions, references; one page per family, bibtex)
  framework                   Camurri et al. conceptual model (kept page + ConceptualModel.png)
  kinematics_energy | smoothness | shape_symmetry_balance | impulsivity_suddenness | gesture_segmentation
  entropy_rarity_periodicity  | synchronization | dominance | humanoid_models | imaging
User guide (narrative per layer, "choosing a feature", links to API pages and gallery)
  physical_signals | low_level | mid_level | high_level | analysis_primitives
API reference
  overview                    generated layer tables
  <layer>/<Name>              GENERATED, one page per catalog feature (§4.2)
  data_models                 Feature, WindowedFeature, Inputs/Input/InputKind, Schema/Output, Result, Status, Recorder, Skeleton (autosummary)
  skeletons                   presets, get_skeleton, with_skeleton
  catalog                     Layer, Timescale, FeatureInfo, catalog, catalog_table
Tutorials                     sphinx-gallery (TEACHING_PLAN.md): auto_examples/ or tutorials/
How-tos                       load the example data (`pyeyesweb.datasets`); map a skeleton; real-time loop with live parameters; batch a recording to pandas; images
Developer guide               architecture and contract (DEVELOPMENT_SPEC include) | conventions | porting status (public summary only) | adding a feature | building the docs
Changelog                     CHANGELOG.md, 2.0.0 + migration guide 1.x → 2.0 + removed features
References                    bibliography (`.. bibliography::`)
```

## 4. Tooling

### 4.1 `conf.py`
Extensions: `sphinx.ext.autodoc`, `sphinx.ext.autosummary` (`autosummary_generate = True`), `numpydoc` (or napoleon), `sphinx.ext.intersphinx` (python, numpy, scipy, pandas, matplotlib), `sphinx.ext.mathjax`, `sphinx.ext.viewcode` (**decide**: shows Python source only, fine because the repo is public Python; the C++ is never reachable), `sphinx_gallery.gen_gallery`, `sphinxcontrib.bibtex` (`bibtex_bibfiles = ["references.bib"]`), `sphinx_design`, `sphinx.ext.githubpages`, and the local extension `_ext/feature_pages`. `nitpicky = True` once the page set is stable (see 4.6). `html_theme = "pydata_sphinx_theme"`.
The docs import the library: `conf.py` puts the repository root on `sys.path` and honours `EYESWEB_CORE_PATH` (the library does this itself in `_core.py`; do not duplicate logic, only document it). If the core is missing the build must **fail with a clear message** (never silently build empty API pages).

### 4.2 The generated feature pages (the key mechanism)
A small extension (`docs/_ext/feature_pages.py`, ≤ ~200 lines, no C++ knowledge) that, at `builder-inited`, iterates `pyeyesweb.catalog()` and writes `docs/api/generated/<layer>/<Name>.rst` (generated into the source tree, git-ignored). Each page contains, **all taken from code so pages cannot drift**:
- title = class name, one-line summary (`FeatureInfo.summary`), badges: layer (`Layer.title`), timescale (`Timescale.value`), EyesWeb block (`FeatureInfo.eyesweb_block`, shown as "EyesWeb: …" or omitted for lab features);
- **Parameters** table from `feature.parameters` of a default-constructed instance when possible, otherwise from `inspect.signature` (classes with required arguments such as `window`: instantiate with the minimum arguments from a small per-class override table in the extension, or read the signature only; **decide in WP3**): name, default, type annotation; the docstring `Parameters` section supplies units and the *(live)*/*(structural)* mark (the extension checks the docstring covers every signature name and fails the build otherwise);
- **Inputs** from `feature.inputs` (name, kind, shape, labels), **Outputs** from `feature.outputs` (Schema: name, shape, kind, **unit**, doc), constructors `from_*` found by introspection;
- the docstring body (numpydoc: What it measures, Notes, **References**, Examples) through `autodoc`; the "Corrected in the core" note is in Notes;
- cross-links: layer page, theory page of its family (`:family:` attribute in a small table `docs/_data/families.yaml` the extension reads; every catalog feature must be assigned or the build fails), gallery examples that use it (sphinx-gallery back-references, `backreferences_dir`).
The extension also provides `.. feature-table:: <layer>` (the layer tables, replacing `catalog_table()` use). A `.. removed-features::` directive was not built: the removed names are a plain table in `docs/migration.md`. Features that cannot be instantiated without the core fail the build (intended). Private modules (`_*.py`) and `pyeyesweb.base`/`utils` never appear.
Acceptance of this mechanism is a test (`tests/unit_tests/test_docs_feature_pages.py`): the number of generated pages equals `len(catalog())`. **New feature checklist:** a new catalog class needs an entry in `docs/_data/families.yaml` (and in `instantiation.yaml` if it has required arguments), otherwise the build fails; `docs/_data/wp4_waivers.yaml` must stay empty.

### 4.3 References
`docs/references.bib` with all literature; each metric docstring has a numpydoc "References" section using `:cite:` keys.
**Citation style: not strict (maintainer, 2026-10-15): any supported format.** sphinxcontrib-bibtex ships `alpha`, `plain`, `unsrt`, `unsrtalpha` (no CSL, no ACM). Start with `unsrt` and numeric labels (`bibtex_reference_style = "label"`, the scikit-learn/SciPy look), zero maintenance; in WP4 check whether a maintained APA/ACM pybtex plugin exists and switch only if it costs nothing. No custom `acm_style.py`. **First step of the references task: mine the citations already present** in `docs/` (theory pages) and in the `pyeyesweb` docstrings (grep for years, `et al.`, `doi`, `TODO(ref)`) into `docs/references.bib`, then fill the gaps (OPEN_POINTS §3). Known: SpectralArcLength → Balasubramanian, Melendez-Calderon, Roby-Brami, Burdet (2015), "On the analysis of movement smoothness", J NeuroEng Rehabil 12:112. The rest are supplied by the maintainer (OPEN_POINTS §3); until then the key `TODO` is **allowed only in a draft build** and the final gate (WP9) fails on it. Add the Camurri et al. papers for the conceptual model and the EyesWeb reference.
**Status 2026-10-16:** `docs/references.bib` has 27 entries (mined in WP0, extended in WP6; 12 carry a `DRAFT:` note), the `References` sections of 15 class docstrings use `:cite:` keys, and the theory pages carry 15 `**[citation needed]**` markers: the task list is 11.1.

### 4.4 Identity and landing page
- Logo inventory (`docs/assets/`): `eyesweb-logo.png` (main mark: header logo, light and dark variants under `html_theme_options["logo"]`; if the PNG suits only one background, an inverted copy is needed for the other theme), `favicon-32x32.png` (favicon), `cp-logo.png` and `cp-logo-squared.png` (Casa Paganini; footer, the squared one for narrow layouts), `eu-logo.png` and `resilence-logo.png` (footer, funding text), `ConceptualModel.png` (theory figure, not a logo). PNG is acceptable now; **SVG versions of the EyesWeb logo and favicon would be better** (sharp in both themes, recolourable): ask the maintainer for the sources. Palette derived from the EyesWeb logo (sample its dominant colours, check contrast), set through `_static/custom.css` + pydata CSS variables, light and dark.
- Landing page: one-sentence pitch (research toolkit for expressive movement analysis, built on the EyesWeb Expressive Gesture Analysis library), install line, a 10-line executed example, then a `sphinx-design` **grid of cards, one per layer** (title, timescale, number of features from `catalog()`, link), and cards for Getting started / Concepts / Gallery / API. No marketing copy; funding and citation at the foot.
- Version switcher: **decide** (pydata `switcher.json`, needs versioned deploys) or drop; start with a single "stable" build plus "latest".

### 4.5 Hosting, the core wheel and CI (decided 2026-10-15; budgets and runner are proposals)
**Decision:** the compiled core is published to PyPI as a **public binary wheel `eyesweb-core`**, built in the private repository with cibuildwheel for Linux (manylinux), Windows and macOS; an alpha `2.0.0a1` is acceptable and is the first release. The C++ sources stay private. The docs CI installs `pip install pyeyesweb` plus the docs extra from PyPI or TestPyPI: no private artifact, no token, forks and PRs can build. **Packaging (WP E of `ALPHA_REVIEW.md`) is a prerequisite of docs CI; until it is done the docs are built locally** against the dev build (`PYTHONPATH`/`EYESWEB_CORE_PATH` as in the header; `sphinx-build -b html docs docs/_build/html`). Workflow files contain no C++ paths or sources.

**Proposals to confirm** (the maintainer has no preference; these are defaults):
- Runner: GitHub Actions `ubuntu-latest` (free for public repositories, 4 vCPU / 16 GB) for the docs job, Python 3.11.
- Tests: matrix ubuntu / windows / macos x Python 3.10-3.13 (confirmed: build for multiple OS and Python versions) (`pyproject.toml`: `requires-python >=3.10`, classifiers 3.10 to 3.13, done 2026-10-20).
- Budgets: each gallery script < 60 s, whole gallery < 10 min, docs job `timeout-minutes: 30`.
- sphinx-gallery cache of executed outputs keyed on the script hash.
- `sphinx-build -W --keep-going` (warnings are errors).
- Deploy to GitHub Pages from `main` with `actions/deploy-pages`; pull-request builds run the same without deploying.
- Pin the `eyesweb-core` version in the docs extra; the page footer prints `eyesweb_core.__version__`.

**Status 2026-10-16:** `.github/workflows/docs.yml` (HTML build with `-W` on ubuntu, 30 minute timeout, deploy with `actions/deploy-pages` on a push to `main`; it does not run the doctest builder) and `tests.yml` (ubuntu, windows, macos by Python 3.10 to 3.13) exist and have **never run**; `pypi_deploy.yml` was the 1.x release file. **Update 2026-10-20 (E7):** the three workflows were reviewed and rewritten (core from TestPyPI by the variable `CORE_FROM_TESTPYPI` or the manual input, until `eyesweb-core` is on PyPI; docs install from the pinned `docs/requirements.txt`; the doctest builder and the docstring doctests run in `docs.yml`; `pypi_deploy.yml` builds the pure wheel and sdist, `twine check --strict`, TestPyPI on a manual run, PyPI on a published release, trusted publishing); YAML validated and `actionlint` 1.7.12 clean, but **nothing has run on GitHub**. The remaining CI work is in 11.2 and 11.6.

### 4.6 Docs-build checks (small, replace `examples/check.py`)
**Not implemented, except the family, docstring-signature and page-count checks of `feature_pages.py`.** What is missing and how to build it: 11.2.

`docs/_ext/` (or `docs/check.py` run as the last CI step) asserts: every `catalog()` name has a generated page and appears in at least one gallery script (**catalog coverage**; `sphinx-gallery` back-references give the data) or is listed in an explicit allow-list with a reason; every feature has a family; grep for **stale names** over `docs/`, `README.md`, `examples/*.py`, docstrings (`SpeedSmoothness|SlidingWindow|HistogramRarity|StatisticalMoment|Lightness|Clusterability|dims=3|rate_hz|fix_|time_mode|_process_window` outside the changelog/migration/removed-features pages) = 0 hits; no `TODO` reference keys in a release build. Plus: `-W` (warnings are errors), `linkcheck` builder run weekly, and docstring validation by `numpydoc` (`numpydoc_validation_checks`) limited to the catalog classes.

---

## 5. Docstring conventions and per-feature checklist
numpydoc style. Class docstring of every catalog feature:
- one-line summary (it is the catalog `summary`: keep it ≤ 100 characters, one sentence); a short **what it measures** paragraph (movement meaning, not only the algorithm), with the definition in math (`.. math::`) and notation consistent with the theory pages;
- **Parameters**: each with type, default, **unit** (s, m/mm, Hz, rad, dimensionless), allowed strings, and *(live)* or *(structural)*; use the single public spelling (DEVELOPMENT_SPEC WP B);
- **Inputs**: names and shapes of `process` (and `run`);
- **Returns / Outputs**: each output with unit and range, matching the Schema (the generated page also prints the Schema: the docstring must not contradict it);
- **Statuses**: when the result is not `OK` (warm-up length in seconds, when `INVALID_INPUT`);
- **Notes**: EyesWeb origin block (also in metadata); **"Corrected in the core: …"** where applicable; known limitations (e.g. humanoid flutter);
- **References**: `.. [Key]`/`:cite:` entries from `references.bib`; none invented;
- **Examples**: a ≤ 10-line synthetic example that runs (doctest, executed by `pytest --doctest-modules`).
The checklist table of 60 rows was not built: the checks that exist are the signature/`Parameters` match of `feature_pages.py`, `pytest --doctest-modules pyeyesweb` and the contract tests; `numpydoc_validation_checks` is still off (11.2). Docstrings change in the same commit as the behaviour they describe (`DEVELOPMENT_SPEC.md` section 9).

## 6. Work packages: acceptance criteria

The status of each package is in the table at the top. The acceptance criteria that were set and met for WP0 to WP8: WP1 build `-W` green, `site/` and mkdocs files out of the build path; WP2 every fact cited to `file:line` and run; WP3 pages generated equal `len(catalog())`, docstring/signature coverage, a unit test of the extension (`tests/unit_tests/test_docs_feature_pages.py`); WP4 `pytest --doctest-modules pyeyesweb` green, no docstring names a private method, a removed class or a stale parameter (`wp4_waivers.yaml` is empty); WP5 every code block executed by the doctest builder (`{doctest}` blocks) or the `plot` directive, one mechanism; WP6 every catalog feature linked from a theory or user-guide page, notation page present; WP7 gallery builds and executes within budget (36.9 s for 11 files); WP8 README example runs verbatim, migration table covers every removed or renamed name, internal documents not in the toctree. **WP9 (polish and gate), acceptance:** `sphinx-build -W` green in CI, the checks of 11.2 enforced by the build, no marker or draft reference, maintainer sign-off, first Pages deploy (11.6).

Order followed: WP0, WP1, WP2, WP3, WP4, WP5, WP6, WP7, WP8; next WP9.

## 7. Risks
- The core wheel is needed at docs time (CI cannot build without it); a changed Linux wheel or expired token breaks all builds: pin the core version in the workflow.
- The docs import the library; a docs build against a **different core version** than the docs describe: the build prints `eyesweb_core.__version__` and `__build__` into the page footer.
- References (11.1) and the wording of retired features depend on the maintainer.
- Generated pages hide per-class failures if the extension swallows errors: it must raise.
- Parameters that need required arguments to instantiate: handled by signature fallback (§4.2).
- Gallery execution time grows the docs build (budgets in `TEACHING_PLAN.md`; 36.9 s today). The gallery reads `examples/data` of the checkout: until the data decision (`TEACHING_PLAN.md` T6) a CI clone carries 939 MB.
- `viewcode` and autodoc expose Python source only; confirm no private paths or tokens leak into docstrings or build logs.

## 8. Out of scope now: the artists' site (TouchDesigner CHOPs)
A **second, separate site** for artists and creatives, documenting the TouchDesigner CHOPs (layer "EyesWebTD"), is **not part of this plan** and is a later work package, after packaging and the CHOP sources are updated (OPEN_POINTS §5: the `chop/` folder is ignored until then). Boundary: this site documents the Python library for researchers and developers; the artists' site has **no maths, no paper citations**, uses patches and screenshots, and describes "what it feels like" (what a movement quality looks like in a patch, typical ranges, recipes). It would **reuse**: the generated feature metadata (names, layer, timescale, inputs/outputs, parameters from `catalog()` and the CHOP-facing equivalents), the same Sphinx toolchain and extension (a second `conf.py`, a different template for the feature page), its own theme colours and logo, and links to the corresponding scientific page for anyone who wants the definition. Nothing is built for it now; keep the extension of §4.2 data-driven (families, metadata in `docs/_data/`) so a second site can consume it.

## 9. Decisions taken (2026-10-15) and what remains open
Taken by the maintainer:
1. **Core wheel**: public binary wheel `eyesweb-core` on PyPI (cibuildwheel: Linux manylinux, Windows, macOS; first release `2.0.0a1`); sources private; docs CI installs from PyPI/TestPyPI; WP E is a prerequisite of docs CI, docs are built locally until then (§4.5).
2. **Formats**: prose pages in MyST Markdown, docstrings numpydoc (`numpydoc` extension), API pages generated, gallery text blocks RST (no MyST option in sphinx-gallery; §0).
3. **Citation style**: not strict, `unsrt` numeric labels, no custom style (§4.3; built that way in `docs/conf.py`); the existing citations were mined into `references.bib`.
4. **Internal agentic-development documents** move to the private repository (`EyesWebCore/dev-notes/`) before release; `DEVELOPMENT_SPEC.md` is kept and published as "Contributing / development spec" after a pass removing private repository names and C++ internals.
5. **Logos** are in `docs/assets/` (inventory and use in §4.4); palette derived from the logo; SVG wanted.
6. **Public repository layout** (below).
7. **TSV reader removed** from the library (data ships in `examples/`; the two docs pages are deleted); the incomplete skeleton presets `qualisys_sport`, `mediapipe`, `openpose` stay with their `TODO(fill)` markers, documented as incomplete; the maintainer fills them later.
8. **Creatives site**: its own repository, much later (after docs, PyPI release and the TouchDesigner wrapper).
9. **Gallery details** (proposals, no maintainer preference; TEACHING_PLAN §1, §5): layout by layer, no Binder/JupyterLite, `pyeyesweb.datasets` helper with `pooch`, `examples/helpers.py`.
10. **Data** (decided 2026-10-20): the **videos are private** and out of the repository; the public data is **sensor data only** (qualisys, kinect, imu, `markers_mappings.json`) and feeds the examples and educational material. The licence and performer consent for it are **still the maintainer's to supply**: a `TODO(maintainer)` marker in `examples/data/README.md` and `examples/GALLERY_HEADER.rst`, counted in `docs/_data/gate.yaml`, so a release build fails until it is resolved. **Update 2026-10-20: the data licence is the MIT licence of the repository (decided); the licence TODO markers are gone.**
11. **Exercise solutions**: executed code in a dropdown was the wish, but it is awkward in sphinx-gallery: **skipped** (maintainer: if awkward, skip); exercises are plain "Try it" sections.
12. **Features that did not separate the example conditions** are documented as if they work (no caveat pages); the OPEN_POINTS §4 analysis remains an internal to-do.
13. **Budgets and CI class**: no preference from the maintainer; proposals in §4.5.

**Public repository layout** (state of 2026-10-16; nothing else ships: no internal notes, no `site/`, no C++):
```
pyeyesweb/              library (pure Python), datasets.py, _datasets_registry.py
tests/                  unit_tests/, _support/, data/ (small frozen references), conftest.py
docs/                   conf.py, index.md, requirements.txt, references.bib, references.md, Makefile, make.bat, build.ps1
  _ext/                 feature_pages.py, tutorial_reset.py
  _data/                families.yaml, instantiation.yaml, wp4_waivers.yaml (must stay empty)
  _static/ _templates/  custom.css, core_version.html (footer)
  _snippets/facts.md    the fact sheet (INTERNAL: excluded from the build; move to the private repository, 11.5)
  _legacy/              the old mkdocs pages, kept for mining (DELETE in WP9, 11.5)
  assets/               logos (PNG) and ConceptualModel.png
  getting_started/ concepts/ theory/ user_guide/ howto/ developer/ api/   (api/generated/, tutorials/, sg_execution_times.rst are generated and git-ignored)
  changelog.md migration.md                                               (changelog.md includes CHANGELOG.md)
examples/               gallery: 01_getting_started .. 06_capstone with plot_NN_*.py and GALLERY_HEADER.rst, GALLERY_HEADER.rst (overview), helpers.py, requirements.txt, data/ (sensor data only, see TEACHING_PLAN.md T6), data_trimmed/ (git-ignored); the old notebooks, utils/ and scratch/ are deleted
tools/                  trim_example_data.py, regenerate_trajectory_reference.py, regenerate_gesture_segmenter_reference.py
.github/workflows/      tests.yml, docs.yml, linkcheck.yml, pypi_deploy.yml (2.0 pure wheel, trusted publishing; rewritten 2026-10-20, never run)
root                    README.md, CHANGELOG.md, CITATION.cff, LICENSE.txt, DEVELOPMENT_SPEC.md, pyproject.toml (2.0.0a1), MANIFEST.in, .gitignore, conftest.py;
                        internal notes to move before release: ALPHA_REVIEW.md, DOCS_PLAN.md, TEACHING_PLAN.md, OPEN_POINTS.md, STRUCTURE_REVIEW.md, DESIGN_PROPOSALS.md
```
Leave the public tree at the release: `site/` (untracked), `docs/_legacy/`, `docs/_snippets/facts.md`, the internal `.md` notes above (to the private repository's `dev-notes/`), (the old notebooks, `examples/utils/` and `examples/scratch/` are already deleted).

**Release checklist item (partly done)**: the wheel and the sdist do not bundle the data (verified 2026-10-20 with `python -m build`: `ALPHA_REVIEW.md` E5); the licence and consent of the sensor data are still open (`TEACHING_PLAN.md` T6). **Update 2026-10-20: the data licence is the MIT licence of the repository (decided); the licence TODO markers are gone.**

**Remaining open**: see section 11 (and `ALPHA_REVIEW.md` section 8 for packaging, data and release).

## 10. Gallery conventions (WP7, as built; the teaching content is in `TEACHING_PLAN.md`)

**What was built.** `docs/conf.py` (gallery settings), `docs/_ext/tutorial_reset.py` (reset between scripts), `docs/_ext/feature_pages.py` (back-references), `examples/` with ten tutorials and `helpers.py`, `pyeyesweb/datasets.py` (+ `_datasets_registry.py`, `docs/api/datasets.md`, `tests/unit_tests/test_datasets.py`), `tools/trim_example_data.py`, `docs/howto/load_data.md`.

**Layout and names.** `examples/NN_<layer>/plot_NN_<name>.py`, six folders: `01_getting_started`, `02_physical_signals`, `03_low_level`, `04_mid_level`, `05_analysis_primitives`, `06_capstone`. The script number is global (01 to 10); tutorial 09 is split in two files, `plot_09a_synchronization_signals.py` and `plot_09b_synchronization_events.py`, both in `05_analysis_primitives`. The name must match `filename_pattern` = `[/\\]plot_\d\d[ab]?_` (so a new split uses `a`/`b`); `ignore_pattern` = `^(?!plot_)` makes every other file (`helpers.py`) a non-tutorial. The files are listed with their features in `TEACHING_PLAN.md` section 3.

**How the gallery is wired.** One sphinx-gallery per layer folder: `sphinx_gallery_conf["examples_dirs"]` is the list of the folders that match `\d\d_\w+`, have a `GALLERY_HEADER.rst` and at least one `plot_NN*_*.py` (found by `docs/conf.py`; the output folders are `docs/tutorials/<folder>`). Not one gallery with sub-sections: sphinx-gallery takes every folder of `examples/` with a README, including the git-ignored `examples/scratch/`. `docs/tutorials/index.rst` is written at configuration time from `examples/GALLERY_HEADER.rst` plus a toctree of the layer galleries; everything under `docs/tutorials/` is generated and git-ignored. A new folder appears when its first script is added. Labels for `:ref:`: `sphx_glr_tutorials_<folder>_<file>.py`. Settings: `abort_on_example_error=True`; thumbnails 320x240 with `# sphinx_gallery_thumbnail_number = N` per script, `default_thumb_file` the logo; `reset_modules` = matplotlib reset plus `reset_tutorial_state` (dpi 90, `numpy.random.seed(0)`, print options); `junit` at `<html>/sphinx-gallery/junit-results.xml`; `min_reported_time=5`; `first_notebook_cell` (only in the downloaded `.ipynb`: `%pip install --quiet pyeyesweb[datasets] matplotlib pandas`, `%matplotlib inline` and a download of `helpers.py` from `_HELPERS_URL`, a raw GitHub URL of the `main` branch: **pin to the release tag**, `TODO(release)` in `docs/conf.py`); `suppress_warnings=["config.cache"]`. Executed results are cached by script hash in `docs/tutorials/`; delete that folder for a clean run.

**Back-references.** sphinx-gallery writes `docs/api/generated/backreferences/<module>.<Class>.examples` for each documented class a script imports and uses; `feature_pages.py` includes that file at the end of every generated feature page ("Examples using ..."). To make a feature appear on its page, import it by name in a code cell and use it; a class only named in prose is not recorded. The coverage check of 11.2 reads the same files.

**Script template and rules** (`plot_01_first_feature.py` is the worked example): module docstring (title, abstract = the gallery card text, `:Goals:`, `:Prerequisites:`, `:Data:`, `:Time:`), then `# %%` blocks in reStructuredText with one concept per section (text, minimal code, figure, one-sentence `# **Takeaway.** ...`), "Try it" (2 to 3 numbered exercises), "Solutions" (plain executed cells, no dropdown), "Next steps" (links to concept, theory and API pages, then the next tutorial as a `:ref:`). A role for every class named in prose and the class imported and used in a code cell; public names only (no identifier starting with `_`, nothing from `pyeyesweb.base` or `utils`); no reviewer notes, no resolved-issue talk, at most one sentence "Corrected in the core"; features that did not separate conditions are presented as working; units stated (Qualisys positions are mm: `trial.to_units("m")` or `units="mm"`), time in seconds; `# sphinx_gallery_thumbnail_number = N` on the figure that should be the card.

**How to add a script.** (1) A folder needs a `GALLERY_HEADER.rst`; (2) write `plot_NN_name.py` from the template; read data only through `pyeyesweb.datasets.load_qualisys_trial(n, start=, stop=)` inside the trimmed range of `tools/trim_example_data.py` (edit `PLAN` there and re-run it if a script needs more); (3) plot through `examples/helpers.py` (`use_style`, `speed`, `vertical_axis`, `shade_status`, `plot_recorder`, `draw_skeleton`, `show_frames`, `synthetic_silhouette`; 166 lines, public API only; a helper used by one script stays in the script); (4) run it alone with the core, the repository and `examples/` on `PYTHONPATH`; (5) build the docs and check the page and the back-references; (6) `grep -n "\._[a-z]"` over its code is empty and `pyflakes` is clean; (7) its time is in `junit-results.xml`.

**Runtime and data rules.** Each script under 60 s (all eleven files are under 8 s; the gallery runs in 36.9 s), the whole gallery under 10 min; fix a slow script by slicing the data. Figures: matplotlib, 8 inches wide, dpi 90, labelled axes with units, time in seconds, status shading by `shade_status`/`plot_recorder`. Synthetic data: `numpy.random.default_rng(seed)`. Data: `pyeyesweb.datasets` looks in `PYEYESWEB_DATA`, then `examples/data` of the checkout, then downloads (optional `pooch`; `BASE_URL` is `None`: without a local copy the error says "not available online yet"). `PYEYESWEB_DATA=examples/data_trimmed` makes the scripts read the trimmed `.tsv.gz` copies (14.9 MB, written by `tools/trim_example_data.py`, git-ignored); the docs build currently uses the full files of `examples/data`. Trimmed files keep the original time column, so `start=` and `stop=` mean the same in both.

**What is in `pyeyesweb.datasets` and what is not.** In the library (`load_qualisys_trial`, `fetch_data_file`, `cache_dir`, `available_trials`, `QualisysTrial`): finding, downloading (SHA-256 sums) and reading a recording, the unit (`to_units`), the 20-joint skeleton, the task and condition of a trial, `joint`, `window`. In `examples/helpers.py`: everything that plots or derives a signal for a figure.

**Open points of the gallery** are in `TEACHING_PLAN.md` section 9 (data host and licence, the helpers URL, the old examples) and in 11.4 of this file (the "next tutorial" sentences). The `TODO(WP7): gallery link` comments of the five `docs/user_guide/*.md` pages and of `docs/howto/load_data.md` were resolved in WP8 (verified: no `TODO(WP7)` remains).

## 11. Status and remaining work (WP9 and the release items)

Everything in 11.1 to 11.6 is open; the order is that of `ALPHA_REVIEW.md` 8.3, which is the master list (items marked **[maintainer]** need an input an agent cannot supply). Do B1 to B7 of `ALPHA_REVIEW.md` 8.2 first (they change wording) and, ideally, E6 (so the install pages are true). Tick a box only when its acceptance criterion holds on a clean build.

### 11.1 References

| Done | Task | Acceptance |
|---|---|---|
| [ ] | **[maintainer]** supplies the sources for the 15 `**[citation needed]**` markers below; an agent adds the entries to `docs/references.bib` and replaces each marker by `{cite}` keys. Do not invent entries. | `grep -rn "citation needed" docs --include=*.md` finds only the two instruction lines (`developer/adding_a_feature.md:56`, `developer/conventions.md:114`) |
| [ ] | **[maintainer]** says which of the 45 classes whose docstring has no `References` section need one (15 have it: `KineticEnergy`, `BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity`, `Symmetry`, `SpectralArcLength`, `LogDimensionlessJerk`, `CurvatureVelocityCorrelation`, `Equilibrium`, `Suddenness`, `SuddennessImpulsivity`, `ContractionImpulsivity`, `EnsembleDominance`, `MultiScaleEntropy`, `PhaseLockingValue`). Plumbing and geometry blocks (`FilterContour`, `ConvexHull`, `CoarseGraining`, `SequenceDetector`, ...) may need none; the list is `catalog()` minus those 15. | each of the 45 either cites or is named in the maintainer's "none needed" list |
| [ ] | **[maintainer]** verifies the 12 entries of `docs/references.bib` whose `note` starts with `DRAFT:` (`camurri2004toward`, `volpe2016designing`, `romano2024computational`, `mazzarino2009need`, `ghisio2015open`, `camurri2018energylift`, `balasubramanian2015analysis`, `piana2013fullbody`, `alborno2016interactive`, `mcculloch1986stable`, `costa2005multiscale`, `sabharwal2026pyeyesweb`: truncated author lists, missing publisher, venue or pages) and confirms the key `mazzarino2009need` (cited by the framework and impulsivity pages; its note says publisher, place and pages are unknown). `ALPHA_REVIEW.md` 8.3 speaks of two DRAFT entries: the file has 12. | no `DRAFT` note left; the header comment of the file (`% citations_mined.bib -- DRAFT ...`) is removed |
| [ ] | The final gate fails on a marker or a `DRAFT` note (11.2) | the build fails if one is added |

The 15 markers (`path:line`, claim, probable source to confirm with the maintainer):

| Page | Claim | Hint |
|---|---|---|
| `theory/entropy_rarity_periodicity.md:24` | sample entropy | Richman and Moorman (2000) |
| `theory/entropy_rarity_periodicity.md:116` | the rarity and contrast measures (probabilities from the bin occupancy) | EyesWeb rarity measure: lab publication (maintainer) |
| `theory/entropy_rarity_periodicity.md:151` | Periodicity Transform | Sethares and Staley (1999) |
| `theory/gesture_segmentation.md:30` | Savitzky-Golay smoothing | Savitzky and Golay (1964) |
| `theory/humanoid_models.md:13` | original mass-spring humanoid models of the EyesWeb libraries | publication that introduced the HumanoidModel blocks (maintainer) |
| `theory/imaging.md:123` | motiongram | Jensenius (2006) |
| `theory/imaging.md:189` | extremities of a body from the curvature of its silhouette | EyesWeb silhouette analysis (maintainer) |
| `theory/kinematics_energy.md:56` | Savitzky-Golay differentiation | Savitzky and Golay (1964) |
| `theory/smoothness.md:21` | minimum-jerk model of reaching | Flash and Hogan (1985) |
| `theory/smoothness.md:171` | Savitzky-Golay filter | Savitzky and Golay (1964) |
| `theory/synchronization.md:32` | nonlinear interdependence | Arnhold et al. (1999) |
| `theory/synchronization.md:100` | event synchronization | Quian Quiroga et al. (2002) |
| `theory/synchronization.md:123` | multi-event-class event synchronization (MECS) | maintainer |
| `theory/synchronization.md:145` | SPIKE-synchronization | Kreuz et al. (2015) |
| `theory/synchronization.md:168` | recurrence plots and cross-recurrence | Eckmann et al. (1987); Marwan et al. (2007) |

(The hints are the names the pages already give; check the bibliographic details before adding them.)

### 11.2 Automated checks (the gate): none of these exists yet

`docs/_ext/feature_pages.py` already fails the build for an unassigned family, a class that cannot be instantiated, a docstring whose `Parameters` do not match the signature, and a count of pages different from `len(catalog())`; `tests/unit_tests/test_docs_feature_pages.py` tests it. `docs/_data/wp4_waivers.yaml` must stay empty. The rest of section 4.6 is **not implemented**. Implement it as a second small extension `docs/_ext/docs_gate.py` (listed in `extensions`; it raises at `build-finished` so `-W` is not needed to see it) or as functions in `feature_pages.py`, with a unit test next to `test_docs_feature_pages.py`:

| Done | Check | Where and acceptance |
|---|---|---|
| [x] | **Marker and draft gate** (2026-10-16: `docs/_ext/docs_gate.py`, data in `docs/_data/gate.yaml`: a marker not listed under `open` fails every build, a stale count too, and `PYEYESWEB_DOCS_RELEASE=1` fails on any open marker; 32 open today) | scan the source of `docs/**/*.md` (not `_legacy`, not `_snippets`) for `[citation needed]`, `TODO`, `TBD`, `FIXME`, and `docs/references.bib` for `DRAFT`; fail on any hit except the two instruction lines in the developer guide (put them in a small allow-list with the reason). Include the `TODO(...)` comments of `docs/index.md` (landing example, timescale line, citation block), of `docs/conf.py` and of `docs/_static/custom.css`. Acceptance: adding a marker to a page fails the build |
| [x] | **Stale-name grep** (2026-10-16: in `docs_gate.py`, tracked files only, public docstrings parsed with `ast`, `pyeyesweb.base`/`utils` skipped; `dims=3` dropped from the list because `Kinematics(dims=3)` is valid 2.0 code) | over `docs/` (sources), `README.md`, `examples/**/plot_*.py`, `examples/helpers.py` and the docstrings of `pyeyesweb`: `SpeedSmoothness`, `SlidingWindow`, `HistogramRarity`, `StatisticalMoment`, `Lightness`, `Clusterability`, `dims=3`, `rate_hz`, `fix_`, `time_mode`, `_process_window`, `TSVReader`, `SkeletonManipulator`, `ZeroCross`, `GetKinematical`, ... outside `docs/changelog.md`, `docs/migration.md` and `docs/developer/porting_status.md` (the pages that list removed names; keep an allow-list of files, not of lines). Acceptance: 0 hits |
| [x] | **Catalog coverage by back-references** (2026-10-16: in `docs_gate.py` at `build-finished`; 60 of 60 covered, `coverage_allowed` empty) | after the gallery ran, every `catalog()` name has a non-empty file `docs/api/generated/backreferences/<module>.<Class>.examples`, or is on an explicit allow-list with a reason (sphinx-gallery touches an empty file for each class: test for content). Today every one of the 60 names is imported and used in at least one script of `examples/` (checked 2026-10-16; the list per script is in `TEACHING_PLAN.md` section 3), so the allow-list starts empty. Acceptance: removing a feature from the scripts fails the build |
| [x] | **`nitpicky = True`** (2026-10-16: on in `docs/conf.py`, `nitpick_ignore` empty; 204 warnings fixed, see 11.8) | uncomment in `docs/conf.py` (line "nitpicky"); fix or list in `nitpick_ignore` the unresolved references; Acceptance: `-W` build green with it |
| [x] | **`linkcheck`** (2026-10-16: weekly workflow `.github/workflows/linkcheck.yml`; first local run 250 working, 136 internal, 2 ignored with a reason in `linkcheck_ignore` of `docs/conf.py`: the ACM DOI (403 to scripts) and a 1.x commit no longer in the history) | `python -m sphinx -b linkcheck docs docs/_build/linkcheck`; fix or ignore (`linkcheck_ignore`) with a reason; add a weekly scheduled workflow (`on: schedule`) that is not a PR gate |
| [x] | **numpydoc validation** (2026-10-16: 25 checks of form in `numpydoc_validation_checks`, 0 failures; the checks not enabled and their counts are in the comment of `docs/conf.py`) | set `numpydoc_validation_checks` in `docs/conf.py` (numpydoc validates the objects the build documents; limit it with `numpydoc_validation_exclude` if the data-model internals produce noise). Start narrow, for example `{"SS03", "PR01", "PR02", "PR06"}` (summary ends with a period; parameters documented, no unknown ones, type spelling), and widen with the maintainer. Acceptance: the build is green with the chosen set on the 60 classes and the data model |
| [x] | **Spelling** (2026-10-16: `codespell` step in `docs.yml`, project words in `docs/spelling_wordlist.txt`; 0 hits) | add `sphinxcontrib-spelling` (or a CI `codespell` step: simpler, no system dependency) over `docs/`, `README.md` and the docstrings; project vocabulary in `docs/spelling_wordlist.txt` |
| [x] | **Doctest builder in CI** (2026-10-16: `docs.yml` runs the doctest builder, `pytest --doctest-modules pyeyesweb` and `tools/check_gallery_times.py`; never run in CI) | `docs.yml` runs only the HTML build; add `python -m sphinx -b doctest docs docs/_build/doctest`, `pytest --doctest-modules pyeyesweb` and a step that fails if any script in `sphinx-gallery/junit-results.xml` exceeds 60 s or the total exceeds 10 min (budgets of 4.5) |

### 11.3 Identity

| Done | Task | Acceptance |
|---|---|---|
| [ ] | **[maintainer]** supplies the SVG sources of the EyesWeb logo and favicon (the PNGs in `docs/assets/` stay as fallback: `eyesweb-logo.png`, `eyesweb-logo-dark.png`, `favicon-32x32.png`) | SVG in `docs/_static/`, wired in `html_theme_options["logo"]` and `html_favicon` |
| [ ] | Palette: `docs/_static/custom.css` carries a muted blue "chosen for contrast" with a `TODO(WP9)`; **[maintainer]** confirms it against the logo; check the AA contrast in light and dark mode | no `TODO` in the css file; contrast checked on text, links, admonitions, code |
| [ ] | Footer logos: `cp-logo.png` (`cp-logo-squared.png` for narrow layouts), `eu-logo.png`, `resilence-logo.png` are in `docs/assets/` and not shown (`TODO(WP9)` in `docs/conf.py`); add them with the funding sentence of `docs/index.md` | logos visible, alt text set, no horizontal scroll at phone width |
| [ ] | Dark mode and mobile check of the landing page, a generated feature page, a theory page with maths, a tutorial and a wide table (the live/structural table, the layer tables) | no clipped formula, readable figures (look at the gallery figures in the dark theme and decide whether they need a background or a theme-aware style) |
| [ ] | **[maintainer]** version switcher: yes (pydata `switcher.json`, needs versioned deploys) or no; the first release is a single "latest" build | decision written in 11.6; no dead switcher in the theme options |

### 11.4 Text issues found during the build, and the fact sheet

| Done | Where | Issue and fix |
|---|---|---|
| [x] | `docs/index.md` (3 places; done 2026-10-16: README example as `{doctest}`, `{{ ts_<layer> }}` substitutions from `catalog()` in `conf.py`, citation text and BibTeX from `CITATION.cff`) | `TODO(WP5)`: replace the paragraph under the install line by the executed 10-line example (the same as the README, as a `{doctest}` block); `TODO(WP6)`: the timescale line of the first layer card (the other cards have none: give every card a timescale from `catalog()`); `TODO(WP8)`: the citation block under "Funding and citation" (from `CITATION.cff`) |
| [x] | (done 2026-10-16) `docs/theory/synchronization.md`, section "Event series", paragraph "The counts are accumulated across windows ..." (lines about 113 to 120) | the accumulation is said twice ("The counts are accumulated across windows ..." and "By default the counts of `EventSynchronization` accumulate across windows ...") and the paragraph ends with an unrelated remark about the corrections of the core; split it into the accumulation rule (with `reset_every_buffer`), the dependence on `tau`, and "Corrected in the core" |
| [x] | (done 2026-10-16) `examples/03_low_level/plot_05_motion.py` and `examples/04_mid_level/plot_07_gestures.py`, last bullet of "Next steps" | "The next tutorial ..." is plain text: use `:ref:` with the labels `sphx_glr_tutorials_03_low_level_plot_06_shape.py` and `sphx_glr_tutorials_05_analysis_primitives_plot_08_primitives.py` (as `plot_08_primitives.py` does for 09a) |
| [x] | (done 2026-10-16: the table and the humanoid paragraph are only in the how-to, label `which-parameters-are-live`; not generated from the tests) `docs/concepts/time_units_parameters.md` ("Live and structural parameters") and `docs/howto/realtime_live_parameters.md` | the same table (live and structural parameters per feature) appears on both pages; keep it on one (the how-to) and link from the other. It is taken from the `LIVE`/`STRUCTURAL` tables of `tests/unit_tests/test_live_parameters*.py` (`facts.md` section 14): regenerate it from there rather than by hand |
| [x] | (found 2026-10-16: the concepts copy listed `gaussian_sigma` only, the how-to copy `gaussian_sigma`, `window`, as the tests do; the concepts copy is gone) the `FilterContour` row of that table | `ALPHA_REVIEW.md` 8.3 names this row as wrong; the coordinator could not find the defect: the row (`gaussian_sigma`, `window` live), the docstring (both marked live) and `test_live_parameters_motion.py` agree. `FilterContour` is one of six classes with a `window` parameter that are not windowed features (`facts.md` section 7), which may be what is meant: ask the maintainer, then fix the row or the page |
| [x] | (done 2026-10-16) `docs/index.md` line 9 and `docs/api/overview.md` line 3 | "five layers": the conceptual model has four layers and the analysis primitives (`facts.md` section 13 and `theory/framework.md` say so; `catalog.py` too): write "four layers and the analysis primitives" |
| [ ] | `docs/getting_started/install.md` | "The core ships with the package: there is nothing to compile" and "3.10, 3.11 and 3.12 are declared": after E4 and E6 the core is the dependency wheel `eyesweb-core`, and 3.13 is a classifier; rewrite with the real install line and remove the pre-release admonition at the release |
| [ ] | `docs/_snippets/facts.md` section 17 (install and core; the sheet has 21 sections, the last one lists the changes after its first version) | "`pip install pyeyesweb` pulling `eyesweb-core` is not yet true": regenerate after E4 to E6 |
| [ ] | `docs/_snippets/facts.md` other sections | **regenerate or re-verify** the sections whose statements changed after the sheet: the Symmetry `reference_type` (only `"label"`; B1 still lists the other two in the signature), `MotionNoiseDetector.is_noisy` (flipped), `Suddenness.gamma` (dimensionless), `CurvatureVelocityCorrelation` velocity (per second), `SpikeSynchronization(mode="timings")` (public), the XML round trip of `MassSpringModel`, the `Recorder` (B5 adds `reason`), the item "S9 stale words" (the private notes), section 18 (migration table) against `docs/migration.md`, and the counts (2963 passed and 12 skipped, 92 doctests, 856 sphinx doctests, 11 tutorial files in 36.9 s) |
| [ ] | `CITATION.cff` | add `version` and `date-released` at the release (`ALPHA_REVIEW.md` E8); keep the `preferred-citation` (the paper) unless the maintainer says otherwise |
| [ ] | after B1 to B7 of `ALPHA_REVIEW.md` 8.2 | grep the docs and the tutorials for the sentences those items change (`Suddenness` beta range, `ConvexHull` integer coordinates, `Recorder` reasons, `KineticEnergy(labels=...)`) and update them in the same commit as the code |

### 11.5 Public and private, and cleanup

| Done | Task | Acceptance |
|---|---|---|
| [x] | (done 2026-10-16) Delete `docs/_legacy/` (26 tracked files of the old mkdocs site; `docs/conf.py` lists it in `exclude_patterns`: remove it there too) after a last grep that nothing else is to be mined (the references were mined into `docs/references.bib` in WP0) | folder gone, build green |
| [ ] | Make `docs/_snippets/facts.md` internal only: it is excluded from the build (`exclude_patterns`) but is tracked and says "internal"; move it (with `STRUCTURE_REVIEW.md`, `DESIGN_PROPOSALS.md`, `OPEN_POINTS.md`, `ALPHA_REVIEW.md`, `DOCS_PLAN.md`, `TEACHING_PLAN.md`) to the private repository's `dev-notes/` at the end, after the finalizing agent has used them; leave one line in `docs/developer/building_the_docs.md` if a page mentions it | `git ls-files` lists none of them; grep for their names in `docs/` and `pyproject.toml` is empty |
| [~] | (pass done 2026-10-16, the publishing decision is open) `DEVELOPMENT_SPEC.md` public pass (its new section 10 lists the sentences) and **[maintainer]** decision how it is published: a "Contributing" page that includes the file (MyST `{include}` of `../DEVELOPMENT_SPEC.md`: no page does it yet; the developer guide pages `architecture`, `conventions`, `adding_a_feature`, `porting_status` summarise it) or `CONTRIBUTING.md` at the root | the page builds; grep for `EyesWebCore`, `PORTING_STATUS`, `CONVENTIONS`, `nanobind`, `.cpp` in it is empty |
| [x] | (done 2026-10-16) Check the existing developer pages for private names: `docs/build.ps1` and `docs/developer/building_the_docs.md` mention the sibling checkout `EyesWebCore` (as a path to the dev build, no URL): reword to "a development build of the core" for the public site; `docs/developer/porting_status.md` and `conventions.md`: no C++ file names, no private paths | `grep -rn "EyesWebCore" docs README.md pyeyesweb tests tools .github` empty except what the maintainer allows |
| [x] | (done 2026-10-16) No local paths: the docstrings of `tests/unit_tests/test_sync_corrections.py` (`PORTING_STATUS.md`) and `tests/_support/live_param_suite.py` (`EyesWebCore/CONVENTIONS.md`) cite private notes: reword (no absolute local path or private URL is tracked today: checked 2026-10-16) | `grep -rn "C:/Users\|EyesWebTD" .` over tracked files is empty |
| [x] | (done 2026-10-20) The old notebooks and scratch files (`examples/*.ipynb`, `examples/utils/`, `examples/scratch/`) are deleted | grep empty |

### 11.6 GitHub Pages and the first deploy

| Done | Task | Acceptance |
|---|---|---|
| [ ] | `ALPHA_REVIEW.md` E1 to E6 done: the install in a clean environment gives the core (docs CI cannot build without it) | `pip install ".[docs]"` in a clean venv, then the build |
| [ ] | Check `.github/workflows/docs.yml` (written, never run): action versions (`checkout@v4`, `setup-python@v5`, `upload-pages-artifact@v3`, `deploy-pages@v4`), the data: the gallery reads `examples/data` of the checkout (939 MB today, `TEACHING_PLAN.md` T6) or `PYEYESWEB_DATA`; the `-W` build on a pull request must pass without deploying | green run on a branch |
| [ ] | Repository settings: Pages with the source "GitHub Actions"; **[maintainer]** custom domain or none; `docs/conf.py` `html_baseurl` if a domain is set | the site is served from the Pages URL named in `CITATION.cff` (`infomuscp.github.io/PyEyesWeb`) |
| [ ] | First deploy from `main` after the merge of `feature/v2-eyesweb-core`; check the footer prints the core version, the downloads of two tutorials run, the search works | maintainer sign-off |

### 11.7 Build and verify

Local build (Windows, from the repository root; the script finds the core in `..\EyesWebCore\build\Release` or in the folder given with `-Core`, sets `EYESWEB_CORE_PATH` and `PYTHONPATH`, builds with `-W --keep-going` and opens the result; `-Live` needs `sphinx-autobuild`):

```
.\docs\build.ps1 -Core <EyesWebCore>\build\Release
```

Without the script (any platform):

```
export EYESWEB_CORE_PATH=<EyesWebCore>/build/Release
export PYTHONPATH="$EYESWEB_CORE_PATH:$PWD"           # ";" on Windows
python -m sphinx -b html -W --keep-going docs docs/_build/html
python -m sphinx -b doctest docs docs/_build/doctest
```

CI (`.github/workflows/docs.yml`): `pip install ".[docs]"` (the `eyesweb-core` wheel comes with the dependencies) then `python -m sphinx -b html -W --keep-going docs docs/_build/html`; deploy with `actions/deploy-pages` on a push to `main`.

How to verify (all must pass before a box is ticked):

1. `-W` HTML build: 0 warnings; delete `docs/tutorials` first to force a clean run of the gallery (a normal build reuses executed outputs by script hash).
2. The doctest builder (the `{doctest}` blocks of the prose pages; 856 tests on 2026-10-16) reports 0 failures.
3. `python -m pytest -q` (2963 passed, 12 skipped on 2026-10-16) and `python -m pytest --doctest-modules pyeyesweb` (92 passed), with the core on the paths.
4. Gallery timing: `docs/sg_execution_times.rst` (generated, git-ignored) and `docs/_build/html/sphinx-gallery/junit-results.xml`. On 2026-10-16: 36.9 s for the 11 scripts, the slowest `plot_07_gestures.py` 7.2 s and `plot_10_capstone.py` 6.0 s; the budget is 60 s per script and 10 min in total.
5. After the gate of 11.2 exists: the same build proves the markers, the stale names and the catalog coverage.

### 11.8 Work log

**2026-10-16, branch `docs/wp9-gate`** (from `feature/v2-eyesweb-core`). Environment: core built from the sibling checkout
`EyeswebCore/EyeswebCore` (last commit 2026-10-14) with Python 3.14 and the pins of `docs/requirements.txt`, venv next to the
repository (`..\.venv`, where `docs/build.ps1` looks for it). `docs/build.ps1` defaults to `..\EyesWebCore\build\Release`: pass
`-Core` when the core checkout is elsewhere.

Done:
- 11.2 gate: `docs/_ext/docs_gate.py` (in `extensions`) with `docs/_data/gate.yaml`; markers, stale names (tracked files only)
  at `builder-inited`, catalog coverage at `build-finished`; `PYEYESWEB_DOCS_RELEASE=1` for the release build. Test:
  `tests/unit_tests/test_docs_gate.py` (8 tests). CI: `docs.yml` gains codespell, the gallery budget
  (`tools/check_gallery_times.py`), the doctest builder and `pytest --doctest-modules pyeyesweb`; new weekly `linkcheck.yml`.
  Project words for codespell: `docs/spelling_wordlist.txt`.
- 11.4 text: `index.md` (four layers and the analysis primitives, executed example, timescales from `catalog()`, citation),
  `api/overview.md`, the "Event series" paragraph of `theory/synchronization.md`, the "next tutorial" links of tutorials 05 and
  07, the live/structural table kept only in `howto/realtime_live_parameters.md` (the concepts copy had a wrong `FilterContour`
  row, which was the defect reported in `ALPHA_REVIEW.md` 8.3).

Verified on this environment: `-W` HTML build green with the gate (excluding the untracked `user_guide/native_features.md`, which
is in no toctree and fails `-W`); doctest builder 866 tests, 0 failures; `pytest --doctest-modules pyeyesweb` 92 passed;
`pytest` 2971 passed, 4 failed, 12 skipped. The 4 failures are not caused by these changes: three negative-value checks done by
the core (`SampleEntropy.tolerance`, `EventSynchronizationMECS.gaussian_sigma`, `gaussian_mean`; the core checkout is probably
older than the one of the 2963-passed run) and `test_naming` on the untracked `pyeyesweb/native/`.

`nitpicky` (same day): a `-n` build gave 204 unresolved references. About 190 came from the default autosummary class template,
whose member tables list members that were never documented, inherited `int`/`dict` members included: the new template
`docs/_templates/autosummary/class.rst` lists the members of the class itself and documents them (`:members:`). The rest:
`py:module` targets on the API pages of `catalog`, `data_models`, `datasets`, `skeletons`; `QUALISYS_TRIALS` and `BASE_URL` as
`py:data` entries of `api/datasets.md`; a "Supporting classes" section on `api/physical_signals.md` (`MassSpringModel`,
`TimeWindowSynchronizer`, `SynchronizedWindow`, which had no page); `:attr:` references of `Feature` qualified
(`~Feature.inputs`, `~OutputsMixin.outputs`), so that the inherited docstring of `WindowedFeature.process` resolves; the
`space_occupation` module reference of `HitCellDetector` replaced by the two potential classes. Result: 0 warnings,
`nitpick_ignore` empty. Verified on a clean build (`docs/tutorials` and `docs/api/generated` deleted): `-W` HTML with
`nitpicky` green, gate green (31 open markers), 60 of 60 features covered, gallery 85.4 s for 11 scripts (slowest
`plot_07_gestures.py` 18.6 s on this machine), doctest builder 866 tests and 0 failures, `pytest --doctest-modules pyeyesweb`
92 passed, `test_docs_gate.py` and `test_docs_feature_pages.py` 14 passed.

Still open: every CI workflow is unrun (packaging).

**2026-10-16, second pass (same branch).**
- numpydoc validation on (`docs/conf.py`): 25 checks of form; fixed the 12 docstrings that failed them (the parameter order
  of `Symmetry`, the section order of `MultiScaleEntropy`, the summary of `MotionNoiseDetector`, `QualisysTrial.skeleton`,
  the six `from_*` constructors, the `Returns` text of `load_qualisys_trial`, `cache_dir`, `get_skeleton`); the fields of
  `Output`, `Result` and the members of `Status` (no docstring of their own) are in `numpydoc_validation_exclude`. The
  `MotionNoiseDetector` summary is the catalog summary too: it now ends with a period instead of a question mark.
- `linkcheck`: see the 11.2 row.
- `docs/_legacy/` deleted (the citations it held were already in `references.bib`), and removed from `exclude_patterns` and
  from the gate.
- Private names: `docs/build.ps1` takes `-Core` or `EYESWEB_CORE_PATH` (no default sibling path; falls back to the `python`
  on the PATH when `..\.venv` is missing), `docs/developer/building_the_docs.md` and the header of `docs/conf.py` say "a
  development build of the core"; the docstrings of `pyeyesweb/base/core_feature.py`, `tests/_support/live_param_suite.py`
  and `tests/unit_tests/test_sync_corrections.py` point at the public pages instead of the private notes.
- `DEVELOPMENT_SPEC.md`: public-safe pass of its section 10 (now a record of the pass); the C++ parts (tiers, core steps of
  adding a feature, C++ style, the CMake build and its tests, the core-side reasons of some contract changes) moved to
  `dev-notes/DEVELOPMENT_SPEC_core.md` of the core checkout (written, not committed there). How the file is published is the
  maintainer's decision.

### 11.9 Release flow and Pages while 1.x is still served (maintainer, 2026-10-20)

Work is merged into `dev` before `main`; GitHub Pages is still served from the branch `gh-pages` (the 1.x documentation at its
root), and it must not break until the development release is done. Therefore `docs.yml` builds on pull requests and on pushes to
`main` and `dev`, and a push to `dev` publishes the 2.x build to the folder `v2-dev/` of `gh-pages` (`peaceiris/actions-gh-pages`,
`destination_dir: v2-dev`, only that folder is replaced; `contents: write`): <owner>.github.io/PyEyesWeb/v2-dev/. The Pages source
stays "Deploy from a branch". At the release: switch the source to "GitHub Actions", deploy this build at the root with
`actions/upload-pages-artifact` and `actions/deploy-pages` (the job was removed for now) and decide where the 1.x site goes (a versioned
folder, or the gh-pages history). Publishing workflows (`pypi_deploy.yml`, and `wheels.yml` in the private core repository) run on a pushed
tag `v*` (from the tagged commit: no default-branch requirement) and upload to TestPyPI; a published GitHub release uploads to PyPI;
a manual run needs the workflow file on the default branch.
