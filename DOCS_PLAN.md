# PyEyesWeb 2.0 — Documentation Plan (for an executing agent)

Root: `C:\Users\Nicola\Desktop\CP\EwbTD\PyEyesWeb` (below: `PEW/`). C++ core build (private repository EyesWebCore, sibling checkout): `C:\Users\Nicola\Desktop\CP\EwbTD\EyesWebCore\build\Release` (check the path exists; the repository layout changed on 2026-10-14, older notes say `EyesWebTD`).
Run the library with:
```
PYTHONPATH="<EyesWebCore/build/Release>;<PEW>" EYESWEB_CORE_PATH=<EyesWebCore/build/Release> C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe
```
**Sources of truth, in this order** (if two disagree, the earlier one wins; when the code and a document disagree, the code wins and the disagreement goes on a list for the maintainer):
1. the code and `pyeyesweb.catalog()` (60 `FeatureInfo` entries, re-counted 2026-10-15: 11 physical_signals, 22 low_level, 7 mid_level, 1 high_level, 19 analysis_primitives; work packages A-D moved features between layers);
2. `PEW/DEVELOPMENT_SPEC.md` (the current contract, including "Contract changes of work package A-D"), then `PEW/OPEN_POINTS.md`, `EyesWebCore/CONVENTIONS.md`, `EyesWebCore/PORTING_STATUS.md`;
3. `PEW/examples/scratch/*.py` + `common.py` (real usage; written before packages B-D, so names may be stale: verify by running).

Everything under `PEW/docs/`, `README.md`, `CHANGELOG.md`, `STRUCTURE_REVIEW.md`, `examples/*.ipynb`, `mkdocs.yml`, `site/` describes the **old** library unless proven otherwise. Stale names listed anywhere in this plan (including §1.3) were true on 2026-10-14 and **may have changed again: re-verify against the code, do not copy.**

Standing rules: no edits to docs, README, CHANGELOG or docstrings until the companion AI executes this plan; documentation page content must match the current code; packaging is last (work package E of `ALPHA_REVIEW.md`), so this plan only *prepares* the `docs` extra and the CI recipe, it does not edit the packaging metadata beyond that. The public repository must never contain C++ sources (nothing from `EyesWebCore` is copied, vendored or quoted at length into docs; describe behaviour, not code).

The workspace is **not a git repository**. Before WP1 make a dated backup of `PEW/docs`, `README.md`, `CHANGELOG.md`, `mkdocs.yml`, `examples/` (or ask the maintainer to initialise git).

---

## 0. Decided stack (final, from the maintainer)

| Concern | Choice | Replaces |
|---|---|---|
| Generator / theme | **Sphinx + PyData Sphinx Theme** (`pydata-sphinx-theme`) | mkdocs, mkdocs-material/readthedocs theme |
| Docstrings | numpydoc style, **decided**: the `numpydoc` extension (validation hook), not napoleon | mkdocstrings numpy handler |
| API pages | `sphinx.ext.autosummary` (+ `autodoc`) and **one generated page per catalog feature** through a small in-repo extension (`docs/_ext/feature_pages.py`, directive `.. feature:: Name`) reading `catalog()` and the feature's `inputs`, `outputs` (Schema), `parameters` | `docs/scripts/gen_pages.py`, `tools/update_catalog_docs.py`, mkdocs-gen-files, literate-nav, section-index |
| Tutorials | **`sphinx-gallery`** over the percent scripts (see TEACHING_PLAN.md) | mkdocs-jupyter, `examples/build.py`, `examples/check.py` |
| References | `sphinxcontrib-bibtex`, one `docs/references.bib`, a "References" block per metric, **ACM style** (§4.3) | `TODO(ref)` placeholders in docstrings |
| Cross-links | `intersphinx` to python, numpy, scipy, pandas, matplotlib | — |
| Layout widgets | `sphinx-design` (cards, grids, tabs, dropdowns) | pymdownx tabbed/details/admonition |
| Math | `sphinx.ext.mathjax` (built in) | `docs/javascripts/mathjax.js` |
| Source format | **Decided: MyST Markdown (`myst-parser`) for the prose pages** (reuses the old `.md`; directives via MyST `{directive}` syntax, maths via `dollarmath`/`amsmath`), docstrings in numpydoc/RST, API pages generated, gallery text blocks in RST (checked 2026-10-15 in the sphinx-gallery syntax documentation, 0.22: text blocks are reST only, there is no Markdown/MyST option). `index` and generated pages may stay `.rst`; do not mix within one page | Markdown |
| Hosting | GitHub Pages (as now), built in CI | `mkdocs gh-deploy` |

Tone: scientific and institutional, like the scikit-learn, SciPy and NumPy documentation: definitions, notation, theory pages, references; not marketing. One-line pitch on the landing page, no superlatives.

Dependencies for the build go in a **`docs` extra** of `pyproject.toml` (replacing the mkdocs lines in `dev`) and a pinned `docs/requirements.txt` for CI; both list: `sphinx`, `pydata-sphinx-theme`, `numpydoc`, `sphinx-gallery`, `sphinxcontrib-bibtex`, `sphinx-design`, `matplotlib`, `pandas`, `scipy`, `pillow` (gallery thumbnails). Python 3.11 (CI also tests 3.10-3.13, §4.5). Add `myst-parser` to the list. (Touching `pyproject.toml` here is limited to this extra and is coordinated with work package E.)

---

## 1. Inventory of existing artefacts and disposition

### 1.1 `docs/` pages (mkdocs Markdown, 1836 lines total)

Target form is the Sphinx page named in §3. Keep prose and theory where it is still true; fix names.

| Path (under `docs/`) | Topic | Status | Notes |
|---|---|---|---|
| `index.md` | Home | **rewrite** → `index.md` (MyST) | landing page (§4.4); keep EU/CP logos and funding text |
| `user_guide/getting_started.md` (91) | install + first example | **rewrite** | old `SlidingWindow` + `SpeedSmoothness` style; new: install, core loading, `process`/`run`, `Recorder` |
| `user_guide/library_structure.md` (49) | packages | **rewrite** → `concepts/layers` | layers + `catalog()` |
| `user_guide/input_contract.md` (83) | inputs | **rewrite** → `concepts/inputs` | dict / `(N,3)` / `(n,D)` forms, `labels=`, skeleton presets, `joint_map` (verify it still exists), `InputKind.IMAGE`, `from_*`, shape `ValueError` vs `INVALID_INPUT` |
| `user_guide/output_contracts.md` (162) | outputs | **rewrite** → `concepts/results` | `Schema/Output/Result/Status/Recorder/latest`; see DEVELOPMENT_SPEC §3 and work packages A, C |
| `user_guide/integrations.md` (8) | TD/Unity/Max | **delete or merge** into how-tos | claim only integrations that exist; TouchDesigner is the separate later site (§8) |
| `.../theoretical_framework.md` (64) | conceptual model | **keep, edit** → `theory/framework` | keep `assets/ConceptualModel.png`; fix class names; layer table must match `catalog.Layer`/`Timescale` |
| `.../physical_signals/physical_signals.md` (37), `low_level.md` (79), `mid_level.md` (80), `high_level.md` (58), `analysis_primitives.md` (93) | layer pages | **rewrite** | catalog tables become a generated `.. feature-table:: <layer>` directive (from `catalog()`); one real narrative per layer |
| `low_level/contraction_expansion.md`, `direction_change.md`, `kinetic_energy.md`, `geometric_symmetry.md`, `postural_balance.md`, `smoothness.md` | per-topic theory | **merge** into `theory/` pages (one per family, see §3) | keep the theory paragraphs; smoothness becomes the smoothness family (SpectralArcLength, LogDimensionlessJerk, SubmovementCount, Harmonicity, Curvature*); verify membership and layer in code |
| `mid_level/impulsivity.md`, `suddenness.md` | per-topic theory | **merge** | |
| `mid_level/lightness.md`, `analysis_primitives/clusterability.md`, `statistical_moments.md` | dropped features | **delete** | listed on the "Removed features" page only |
| `analysis_primitives/mse_dominance.md`, `rarity.md`, `synchronization.md` | theory | **merge/rewrite** | sync becomes a family page (12 classes, verified 2026-10-15) |
| `utils/index.md` (0), `utils/tsv_reader.md` (394) | TSV reader | **delete both** (decided 2026-10-15): `TSVReader` (`pyeyesweb/utils/tsv_reader.py`) was removed from the library; loading data is covered by the `pyeyesweb.datasets` helper and the gallery (TEACHING_PLAN §5). Delete the pages at WP1 | |
| `assets/*` | logos, figures | **keep** (inventory in §4.4); SVG logo wanted | |
| `javascripts/*`, `overrides/*`, `scripts/gen_pages.py` | mkdocs machinery | **delete** (superseded by `conf.py`, `_static/custom.css`, `_ext/`) | |
| `mkdocs.yml`, `site/` | mkdocs config and built output (6.6 MB) | **delete from repo** after the Sphinx build is green; `_build/` into `.gitignore` | `site/` is also excluded from release (ALPHA_REVIEW Q6) |

### 1.2 Root files
| File | Status | Action |
|---|---|---|
| `README.md` | **rewrite** | example uses `SpeedSmoothness` + `SlidingWindow` (both gone). New: one-paragraph pitch, install (the wheel depends on `eyesweb-core`; `EYESWEB_CORE_PATH` for dev builds), a 10-line example with `process`/`run`/`Recorder` that is **executed in WP8**, links to docs and gallery, citation, funding |
| `CHANGELOG.md` | **rewrite** | single 2.0.0 entry (Keep a Changelog): Added / Changed / Removed / Fixed ("Corrected in the core") + migration table old→new, built from `PORTING_STATUS.md` and DEVELOPMENT_SPEC "Contract changes". 1.x entries kept below untouched. Included in the docs as the Changelog page |
| `STRUCTURE_REVIEW.md`, `DESIGN_PROPOSALS.md`, `OPEN_POINTS.md`, `ALPHA_REVIEW.md`, `DOCS_PLAN.md`, `TEACHING_PLAN.md` and the other agentic-development notes | internal | **move to the private repository** (`EyesWebCore/dev-notes/`) **before release**; not in the public repo, docs, sdist or wheel; conclusions go into the developer guide |
| `DEVELOPMENT_SPEC.md` | source | **kept and published** as the "Contributing / development spec" page for open-source contributors: MyST `{include}` (do not copy; update only in the source). Needs a pass first to remove private repository names and C++ internals (WP8) |
| `CITATION.cff` | **update** | version 2.0.0, date |
| `main.py` | delete (ALPHA_REVIEW Q6) | |
| `pyeyesweb/utils/tsv_reader.py` | **removed 2026-10-15** | its docs page and `utils/index.md` are on the deletion list (§1.1); the 2.0.0 CHANGELOG entry lists `TSVReader` under Removed |
| `tools/update_catalog_docs.py` | **delete** | superseded by the generated pages |
| `docs/conf.py`, `docs/Makefile`/`make.bat` | **new** | WP1 |

### 1.3 Docstrings (sample check done 2026-10-14; **repeat in WP0**)
Grep across `pyeyesweb/**/*.py` found no occurrences of `SpeedSmoothness`, `Smoothness(`, `time_mode`, `fix_`, `SkeletonManipulator`, `Lightness`, `ZeroCross`, `StatisticalMoment`, `Clusterability`, `Trajectory(`, `GetKinematical`. Suspects to re-check:
- `SlidingWindow` was **removed on 2026-10-14**: any remaining mention (it was in `data_models/sliding_window.py:37`) must be gone.
- `process_window`: only the private `_process_window` exists; no public docstring may mention it.
- `>>>` examples: run `python -m pytest --doctest-modules pyeyesweb` (core on the path) and fix every failure; in Sphinx also enable `sphinx.ext.doctest` only if the maintainer wants doctests in the docs (the gallery already executes code).
- `Enum` in several files: the public API uses **string choices**; docstrings list the strings, never enum members.
- Old parameter names: after package B every parameter has a single spelling (`number_of_inputs`, `window`, `cells_along_x`, `gaussian_sigma`, `filter_window_length`, `gesture_duration`, `first_signal`/`second_signal`, ...). Grep docstrings against `feature.parameters` of every catalog class (script: for each class compare the names in the `Parameters` section with `inspect.signature`); every mismatch is a finding.
- Other stale items: `rate_hz` (now `sampling_rate`, default `None`), `t=`/`ts=` (now `timestamp`/`timestamps`, seconds), boolean `fix_*`, `output_dims` values, `COMPONENT` (spelled `"components"`), bool switches replaced by `parts=`.
Record results in a table (file:line, wrong text, fix) in WP0.

The **docs** pages and public notebooks are where the stale names live: `SpeedSmoothness` (docs 5 files, 5 notebooks, README 2), `Lightness`, `StatisticalMoment`, `Clusterability`, `HistogramRarity`, `Synchronization`, `SlidingWindow`, `dims=3`, `fix_`, `SkeletonManipulator`, `ZeroCross`, `GetKinematical`. Re-grep.

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
17. **Install/core**: `pyeyesweb._core` requires `REQUIRED_CORE` (major.minor, 2.0) and raises `ImportError` for another version or none (texts in the sheet); `import pyeyesweb` and `data_models` need no core, `catalog()` does. **`pip install pyeyesweb` pulling `eyesweb-core` is not yet true** (pyproject is 1.1.1 with numpy/scipy/scikit-learn/tqdm; packaging WP E is last): install pages state the decision and flag it until WP E lands.

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
A small extension (`docs/_ext/feature_pages.py`, ≤ ~200 lines, no C++ knowledge) that, at `builder-inited`, iterates `pyeyesweb.catalog()` and writes `docs/api/<layer>/<Name>.rst` (generated into the source tree under `docs/api/generated/`, git-ignored). Each page contains, **all taken from code so pages cannot drift**:
- title = class name, one-line summary (`FeatureInfo.summary`), badges: layer (`Layer.title`), timescale (`Timescale.value`), EyesWeb block (`FeatureInfo.eyesweb_block`, shown as "EyesWeb: …" or omitted for lab features);
- **Parameters** table from `feature.parameters` of a default-constructed instance when possible, otherwise from `inspect.signature` (classes with required arguments such as `window`: instantiate with the minimum arguments from a small per-class override table in the extension, or read the signature only; **decide in WP3**): name, default, type annotation; the docstring `Parameters` section supplies units and the *(live)*/*(structural)* mark (the extension checks the docstring covers every signature name and fails the build otherwise);
- **Inputs** from `feature.inputs` (name, kind, shape, labels), **Outputs** from `feature.outputs` (Schema: name, shape, kind, **unit**, doc), constructors `from_*` found by introspection;
- the docstring body (numpydoc: What it measures, Notes, **References**, Examples) through `autodoc`; the "Corrected in the core" note is in Notes;
- cross-links: layer page, theory page of its family (`:family:` attribute in a small table `docs/_data/families.yaml` the extension reads; every catalog feature must be assigned or the build fails), gallery examples that use it (sphinx-gallery back-references, `backreferences_dir`).
The extension also provides `.. feature-table:: <layer>` (the layer tables, replacing `catalog_table()` use) and `.. removed-features::` if the list is kept as data. Features that cannot be instantiated without the core fail the build (intended). Private modules (`_*.py`) and `pyeyesweb.base`/`utils` never appear.
Acceptance of this mechanism is a test: the number of generated pages equals `len(catalog())`.

### 4.3 References
`docs/references.bib` with all literature; each metric docstring has a numpydoc "References" section using `:cite:` keys.
**Citation style: not strict (maintainer, 2026-10-15): any supported format.** sphinxcontrib-bibtex ships `alpha`, `plain`, `unsrt`, `unsrtalpha` (no CSL, no ACM). Start with `unsrt` and numeric labels (`bibtex_reference_style = "label"`, the scikit-learn/SciPy look), zero maintenance; in WP4 check whether a maintained APA/ACM pybtex plugin exists and switch only if it costs nothing. No custom `acm_style.py`. **First step of the references task: mine the citations already present** in `docs/` (theory pages) and in the `pyeyesweb` docstrings (grep for years, `et al.`, `doi`, `TODO(ref)`) into `docs/references.bib`, then fill the gaps (OPEN_POINTS §3). Known: SpectralArcLength → Balasubramanian, Melendez-Calderon, Roby-Brami, Burdet (2015), "On the analysis of movement smoothness", J NeuroEng Rehabil 12:112. The rest are supplied by the maintainer (OPEN_POINTS §3); until then the key `TODO` is **allowed only in a draft build** and the final gate (WP9) fails on it. Add the Camurri et al. papers for the conceptual model and the EyesWeb reference.

### 4.4 Identity and landing page
- Logo inventory (`docs/assets/`): `eyesweb-logo.png` (main mark: header logo, light and dark variants under `html_theme_options["logo"]`; if the PNG suits only one background, an inverted copy is needed for the other theme), `favicon-32x32.png` (favicon), `cp-logo.png` and `cp-logo-squared.png` (Casa Paganini; footer, the squared one for narrow layouts), `eu-logo.png` and `resilence-logo.png` (footer, funding text), `ConceptualModel.png` (theory figure, not a logo). PNG is acceptable now; **SVG versions of the EyesWeb logo and favicon would be better** (sharp in both themes, recolourable): ask the maintainer for the sources. Palette derived from the EyesWeb logo (sample its dominant colours, check contrast), set through `_static/custom.css` + pydata CSS variables, light and dark.
- Landing page: one-sentence pitch (research toolkit for expressive movement analysis, built on the EyesWeb Expressive Gesture Analysis library), install line, a 10-line executed example, then a `sphinx-design` **grid of cards, one per layer** (title, timescale, number of features from `catalog()`, link), and cards for Getting started / Concepts / Gallery / API. No marketing copy; funding and citation at the foot.
- Version switcher: **decide** (pydata `switcher.json`, needs versioned deploys) or drop; start with a single "stable" build plus "latest".

### 4.5 Hosting, the core wheel and CI (decided 2026-10-15; budgets and runner are proposals)
**Decision:** the compiled core is published to PyPI as a **public binary wheel `eyesweb-core`**, built in the private repository with cibuildwheel for Linux (manylinux), Windows and macOS; an alpha `2.0.0a1` is acceptable and is the first release. The C++ sources stay private. The docs CI installs `pip install pyeyesweb` plus the docs extra from PyPI or TestPyPI: no private artifact, no token, forks and PRs can build. **Packaging (WP E of `ALPHA_REVIEW.md`) is a prerequisite of docs CI; until it is done the docs are built locally** against the dev build (`PYTHONPATH`/`EYESWEB_CORE_PATH` as in the header; `sphinx-build -b html docs docs/_build/html`). Workflow files contain no C++ paths or sources.

**Proposals to confirm** (the maintainer has no preference; these are defaults):
- Runner: GitHub Actions `ubuntu-latest` (free for public repositories, 4 vCPU / 16 GB) for the docs job, Python 3.11.
- Tests: matrix ubuntu / windows / macos x Python 3.10-3.13 (confirmed: build for multiple OS and Python versions) (`pyproject.toml` has `requires-python >=3.10` and classifiers 3.10-3.12 only: add 3.13 to the classifiers when its wheel exists).
- Budgets: each gallery script < 60 s, whole gallery < 10 min, docs job `timeout-minutes: 30`.
- sphinx-gallery cache of executed outputs keyed on the script hash.
- `sphinx-build -W --keep-going` (warnings are errors).
- Deploy to GitHub Pages from `main` with `actions/deploy-pages`; pull-request builds run the same without deploying.
- Pin the `eyesweb-core` version in the docs extra; the page footer prints `eyesweb_core.__version__`.

### 4.6 Docs-build checks (small, replace `examples/check.py`)
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
Checklist table (60 rows × these columns, ✔/✘) lives in `docs/dev/feature_checklist` and is produced by a script, not by hand. Standing rule: docstrings are edited only in WP4 and only by the executor.

## 6. Work packages (ordered)
| WP | Content | Acceptance criteria |
|---|---|---|
| WP0 Audit | backup; stale-name grep (§1.3) over docs, README, notebooks, scripts, docstrings; run doctests; dump `catalog()` (layer, timescale, inputs, outputs with units, `parameters`, `from_*`) to a JSON file kept out of the repo; compare docstring `Parameters` with signatures | findings table delivered; doctest failures listed; counts per layer re-verified |
| WP1 Skeleton + CI | `docs/conf.py` (§4.1), theme, empty toctree of §3 with stub pages, `docs` extra + `docs/requirements.txt`, `.gitignore` for `_build/` and generated pages, GitHub Actions workflow (build with `-W`, deploy to Pages) and the **core-wheel acquisition decided and working** (§4.5), local build recipe | CI green on a stub site obtained from the real wheel; local build with `EYESWEB_CORE_PATH` green; `site/` and mkdocs files removed from the build path |
| WP2 Fact sheet | **done 2026-10-15**: `docs/_snippets/facts.md` per §2 | every item cited to file:line and verified by running code; maintainer approves |
| WP3 Generated API | extension of §4.2, `families.yaml`, layer tables, `data_models`/`skeletons`/`catalog` autosummary pages | pages generated = `len(catalog())`; docstring/signature coverage check passes; unit test for the extension; build `-W` green |
| WP4 Docstrings | apply §5 to all catalog classes + `Result/Schema/Recorder/Status/Feature`; `references.bib` first entries | checklist 100% except references awaiting the maintainer; `pytest --doctest-modules pyeyesweb` green; no docstring names a private method, removed class or stale parameter |
| WP5 Concepts + Getting started | pages of §3 (install, quickstart, layers, inputs, results, time/units/parameters) | every code block executed (use `.. jupyter-execute`-free approach: `sphinx.ext.doctest` or `plot` directive, one mechanism, **decide**); consistent with the fact sheet |
| WP6 Theory + User guide | merge old theory pages (§1.1), family pages, per-layer pages, bibliography | every catalog feature is linked from a theory/user-guide page; every cited paper is in `references.bib`; notation page exists |
| WP7 Gallery | percent scripts → `sphinx-gallery` per TEACHING_PLAN.md | gallery builds, executes within budget, catalog coverage check passes |
| WP8 How-tos, developer guide, README, CHANGELOG, CITATION, migration guide | §1.2, DEVELOPMENT_SPEC include | README example runs verbatim; migration table covers every removed/renamed name from WP0; internal documents not in toctree |
| WP9 Polish + gate | identity (§4.4), accessibility and dark-mode check, mobile check, `linkcheck`, spell/grammar pass, stale-name grep, no draft reference keys | `sphinx-build -W` green on CI; stale grep 0 outside changelog/migration; maintainer sign-off; first Pages deploy |

Order: WP0 → WP1 → WP2 → WP3 → WP4 → WP5 → WP6 → WP7 (WP7 may start after WP3, in parallel with WP5/WP6 in a second pass) → WP8 → WP9.

## 7. Risks
- The core wheel is needed at docs time (CI cannot build without it); a changed Linux wheel or expired token breaks all builds: pin the core version in the workflow.
- The docs import the library; a docs build against a **different core version** than the docs describe: the build prints `eyesweb_core.__version__` and `__build__` into the page footer.
- Not a git repository: no rollback (backup in WP0).
- References and retirement wording depend on the maintainer.
- Generated pages hide per-class failures if the extension swallows errors: it must raise.
- Parameters that need required arguments to instantiate: handled by signature fallback (§4.2).
- Gallery execution time grows the docs build (budgets in TEACHING_PLAN.md).
- `viewcode` and autodoc expose Python source only; confirm no private paths or tokens leak into docstrings or build logs.

## 8. Out of scope now: the artists' site (TouchDesigner CHOPs)
A **second, separate site** for artists and creatives, documenting the TouchDesigner CHOPs (layer "EyesWebTD"), is **not part of this plan** and is a later work package, after packaging and the CHOP sources are updated (OPEN_POINTS §5: the `chop/` folder is ignored until then). Boundary: this site documents the Python library for researchers and developers; the artists' site has **no maths, no paper citations**, uses patches and screenshots, and describes "what it feels like" (what a movement quality looks like in a patch, typical ranges, recipes). It would **reuse**: the generated feature metadata (names, layer, timescale, inputs/outputs, parameters from `catalog()` and the CHOP-facing equivalents), the same Sphinx toolchain and extension (a second `conf.py`, a different template for the feature page), its own theme colours and logo, and links to the corresponding scientific page for anyone who wants the definition. Nothing is built for it now; keep the extension of §4.2 data-driven (families, metadata in `docs/_data/`) so a second site can consume it.

## 9. Decisions taken (2026-10-15) and what remains open
Taken by the maintainer:
1. **Core wheel**: public binary wheel `eyesweb-core` on PyPI (cibuildwheel: Linux manylinux, Windows, macOS; first release `2.0.0a1`); sources private; docs CI installs from PyPI/TestPyPI; WP E is a prerequisite of docs CI, docs are built locally until then (§4.5).
2. **Formats**: prose pages in MyST Markdown, docstrings numpydoc (`numpydoc` extension), API pages generated, gallery text blocks RST (no MyST option in sphinx-gallery; §0).
3. **Citation style**: not strict, `unsrt` numeric to start (§4.3); first step: mine existing citations from `docs/` and docstrings into `references.bib`.
4. **Internal agentic-development documents** move to the private repository (`EyesWebCore/dev-notes/`) before release; `DEVELOPMENT_SPEC.md` is kept and published as "Contributing / development spec" after a pass removing private repository names and C++ internals.
5. **Logos** are in `docs/assets/` (inventory and use in §4.4); palette derived from the logo; SVG wanted.
6. **Public repository layout** (below).
7. **TSV reader removed** from the library (data ships in `examples/`; delete `docs/user_guide/theoretical_framework/utils/tsv_reader.md` and `utils/index.md`); the incomplete skeleton presets `qualisys_sport`, `mediapipe`, `openpose` stay with their `TODO(fill)` markers, documented as incomplete; the maintainer fills them later.
8. **Creatives site**: its own repository, much later (after docs, PyPI release and the TouchDesigner wrapper).
9. **Gallery details** (proposals, no maintainer preference; TEACHING_PLAN §1, §5): layout by layer, no Binder/JupyterLite, `pyeyesweb.datasets` helper with `pooch`, `examples/helpers.py`.
10. **Data** (videos, kinect, imu): stay in the repository for now and feed examples and educational material; the licensing/consent question is **parked ("to be discussed")**, not blocking, but a release-checklist item (below).
11. **Exercise solutions**: executed code in a dropdown was the wish, but it is awkward in sphinx-gallery: **skipped** (maintainer: if awkward, skip); exercises are plain "Try it" sections.
12. **Features that did not separate the example conditions** are documented as if they work (no caveat pages); the OPEN_POINTS §4 analysis remains an internal to-do.
13. **Budgets and CI class**: no preference from the maintainer; proposals in §4.5.

**Public repository layout** (nothing else ships: no internal notes, no `site/`, no C++):
```
pyeyesweb/              library (pure Python)
tests/                  unit tests + small reference data
docs/                   conf.py, index.md, requirements.txt, Makefile, make.bat, references.bib
  _ext/                 feature_pages.py
  _data/                families.yaml
  _static/              custom.css, logos (SVG when available)
  assets/               current logos and figures
  getting_started/ concepts/ theory/ user_guide/ howto/ developer/ api/   (generated parts git-ignored)
examples/               gallery scripts in layer folders (TEACHING_PLAN §1), GALLERY_HEADER.rst per folder, helpers.py, requirements.txt, data/ (trimmed)
tools/                  maintained scripts only (regenerate_trajectory_reference.py); update_catalog_docs.py deleted
.github/workflows/      tests.yml, docs.yml
root                    README.md, CHANGELOG.md, CITATION.cff, LICENSE.txt, DEVELOPMENT_SPEC.md, pyproject.toml, .gitignore
```
Leave the public tree: `site/`, `mkdocs.yml`, `main.py`, `docs/javascripts|overrides|scripts`, the internal `.md` plans/reviews (to `EyesWebCore/dev-notes/`), `examples/*.ipynb`, `examples/utils/`, `examples/scratch/`, the TSV reader docs pages.

**Release checklist item (parked)**: before the PyPI sdist/wheel, the wheel/sdist must not bundle the big data (`examples/data`, 939 MB); repository size and the data licence/consent still need a decision.

**Remaining open**:
- Confirm the proposals of §4.5 and TEACHING_PLAN §9.
- Wording for removed features (§2 item 15); the public/private pass of `DEVELOPMENT_SPEC.md`.
- Literature still missing after mining (OPEN_POINTS §3); the Camurri/EyesWeb papers.
- SVG logo sources; version switcher yes/no; custom domain; docs version policy (`2.0.0a1`, `latest`/`stable` URL).
- Doctests inside Sphinx or only `pytest --doctest-modules` (default: only pytest).
- Git for the PyEyesWeb tree.
- Data licence and consent (parked).
