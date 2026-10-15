# PyEyesWeb 2.0 — Documentation Plan (for an executing agent)

Root: `C:\Users\Nicola\Desktop\CP\EwbTD\PyEyesWeb` (below: `PEW/`). C++ core build (private repository EyesWebCore, sibling checkout): `C:\Users\Nicola\Desktop\CP\EwbTD\EyesWebCore\build\Release` (check the path exists; the repository layout changed on 2026-10-14, older notes say `EyesWebTD`).
Run the library with:
```
PYTHONPATH="<EyesWebCore/build/Release>;<PEW>" EYESWEB_CORE_PATH=<EyesWebCore/build/Release> C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe
```
**Sources of truth, in this order** (if two disagree, the earlier one wins; when the code and a document disagree, the code wins and the disagreement goes on a list for the maintainer):
1. the code and `pyeyesweb.catalog()` (60 `FeatureInfo` entries on 2026-10-14: 12 physical_signals, 20 low_level, 8 mid_level, 1 high_level, 19 analysis_primitives; **re-count in WP0**, work packages A-D moved features between layers);
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
| Docstrings | numpydoc style (existing docstrings are already numpy style); `numpydoc` or `sphinx.ext.napoleon` (decide in WP1; `numpydoc` gives the validation hook) | mkdocstrings numpy handler |
| API pages | `sphinx.ext.autosummary` (+ `autodoc`) and **one generated page per catalog feature** through a small in-repo extension (`docs/_ext/feature_pages.py`, directive `.. feature:: Name`) reading `catalog()` and the feature's `inputs`, `outputs` (Schema), `parameters` | `docs/scripts/gen_pages.py`, `tools/update_catalog_docs.py`, mkdocs-gen-files, literate-nav, section-index |
| Tutorials | **`sphinx-gallery`** over the percent scripts (see TEACHING_PLAN.md) | mkdocs-jupyter, `examples/build.py`, `examples/check.py` |
| References | `sphinxcontrib-bibtex`, one `docs/references.bib`, a "References" block per metric | `TODO(ref)` placeholders in docstrings |
| Cross-links | `intersphinx` to python, numpy, scipy, pandas, matplotlib | — |
| Layout widgets | `sphinx-design` (cards, grids, tabs, dropdowns) | pymdownx tabbed/details/admonition |
| Math | `sphinx.ext.mathjax` (built in) | `docs/javascripts/mathjax.js` |
| Source format | reStructuredText for pages with directives and maths; MyST (`myst-parser`) optional for prose pages: **decide once in WP1, do not mix without reason** | Markdown |
| Hosting | GitHub Pages (as now), built in CI | `mkdocs gh-deploy` |

Tone: scientific and institutional, like the scikit-learn, SciPy and NumPy documentation: definitions, notation, theory pages, references; not marketing. One-line pitch on the landing page, no superlatives.

Dependencies for the build go in a **`docs` extra** of `pyproject.toml` (replacing the mkdocs lines in `dev`) and a pinned `docs/requirements.txt` for CI; both list: `sphinx`, `pydata-sphinx-theme`, `numpydoc`, `sphinx-gallery`, `sphinxcontrib-bibtex`, `sphinx-design`, `matplotlib`, `pandas`, `scipy`, `pillow` (gallery thumbnails). Python 3.11. (Touching `pyproject.toml` here is limited to this extra and is coordinated with work package E.)

---

## 1. Inventory of existing artefacts and disposition

### 1.1 `docs/` pages (mkdocs Markdown, 1836 lines total)

Target form is the Sphinx page named in §3. Keep prose and theory where it is still true; fix names.

| Path (under `docs/`) | Topic | Status | Notes |
|---|---|---|---|
| `index.md` | Home | **rewrite** → `index.rst` | landing page (§4.4); keep EU/CP logos and funding text |
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
| `analysis_primitives/mse_dominance.md`, `rarity.md`, `synchronization.md` | theory | **merge/rewrite** | sync becomes a family page (11 classes; verify count) |
| `utils/index.md` (0), `utils/tsv_reader.md` (394) | TSV reader | `pyeyesweb.utils` is **internal** since work package C (not listed in `dir(pyeyesweb)`): check whether a TSV loader is public; if not, delete the page and cover loading in a how-to using the gallery download/loader helper | |
| `assets/*` | logos, figures | **keep**, add SVG logo (§4.4) | |
| `javascripts/*`, `overrides/*`, `scripts/gen_pages.py` | mkdocs machinery | **delete** (superseded by `conf.py`, `_static/custom.css`, `_ext/`) | |
| `mkdocs.yml`, `site/` | mkdocs config and built output (6.6 MB) | **delete from repo** after the Sphinx build is green; `_build/` into `.gitignore` | `site/` is also excluded from release (ALPHA_REVIEW Q6) |

### 1.2 Root files
| File | Status | Action |
|---|---|---|
| `README.md` | **rewrite** | example uses `SpeedSmoothness` + `SlidingWindow` (both gone). New: one-paragraph pitch, install (the wheel depends on `eyesweb-core`; `EYESWEB_CORE_PATH` for dev builds), a 10-line example with `process`/`run`/`Recorder` that is **executed in WP8**, links to docs and gallery, citation, funding |
| `CHANGELOG.md` | **rewrite** | single 2.0.0 entry (Keep a Changelog): Added / Changed / Removed / Fixed ("Corrected in the core") + migration table old→new, built from `PORTING_STATUS.md` and DEVELOPMENT_SPEC "Contract changes". 1.x entries kept below untouched. Included in the docs as the Changelog page |
| `STRUCTURE_REVIEW.md`, `DESIGN_PROPOSALS.md`, `OPEN_POINTS.md`, `ALPHA_REVIEW.md` | internal | not in the docs and not in the sdist/wheel (ALPHA_REVIEW Q6); conclusions go into the developer guide. Ask maintainer where they live |
| `DEVELOPMENT_SPEC.md` | source | becomes the developer-guide page: include it with `.. include::` / MyST `{include}` (do not copy; update only in the source). Strip internal remarks (e.g. private repository paths) that the public docs must not show: **maintainer to confirm what in the spec may be public** |
| `CITATION.cff` | **update** | version 2.0.0, date |
| `main.py` | delete (ALPHA_REVIEW Q6) | |
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
Write `docs/facts.rst` (an internal, non-published `.. only:: dev` page, or a `docs/_snippets/facts.rst` included by `.. include::`) first (WP2), each item cited to file:line, verified by running code, and have every page agree with it. Starting list (all from DEVELOPMENT_SPEC on 2026-10-14; **re-verify each**):
1. **Contract**: `feature.process(*sample, timestamp=None)` returns an immutable `Result`; `feature.run(*recording, timestamps=None, reset=True)` returns a `Recorder` and gives numbers identical to a loop of `process`; `feature.reset()`; `feature.inputs`; `feature.outputs` (the `Schema`, known before data); `feature.latest`; `feature.parameters` (read-only mapping of constructor parameters and current values; a parameter resolved at construction and not kept, e.g. `skeleton`, is not listed).
2. **Result**: fields `status`, `reason`, `timestamp` (s, NaN unknown), `valid` (per output), one attribute per output (`result.kinetic_energy`, `result["centroid_x"]`); missing value is NaN/0/False, never `None`; `to_flat_dict()` keeps integer statuses.
3. **Status** names exactly: `OK`, `WARMING_UP`, `NO_OUTPUT` (between hops), `INVALID_INPUT`; `str(Status.OK) == "OK"`, `int(Status.OK) == 0`; when each occurs. `INVALID_INPUT` means every output is empty and `valid` all False, state unchanged (finite check, labels, non-increasing timestamp, overflow).
4. **Recorder**: `repr`, `rec[3]` / `rec[-1]` are `Result`s, `rec[2:5]` a list, `rec["name"]` / `rec.<output>` a column, `to_frame()` (status names), `timestamps`; images never in `to_array()`.
5. **Errors**: wrong shape/kind → `ValueError`; bad data → `INVALID_INPUT` + `reason`; too few samples → `WARMING_UP`; invalid parameters raise at construction **and at setters** (live validation), a wrong joint name raises `ValueError`; misspelled keyword → `TypeError` naming the feature.
6. **Time rule**: seconds everywhere, never frames; `timestamp` if given, else `sampling_rate` (Hz, **default `None` everywhere**), else per-sample derivatives and the `reason` says so; the five window metrics (`SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount`, `CurvatureVelocityCorrelation`) raise at construction without `sampling_rate`; `ContractionImpulsivity.frames` is now `sampling_rate`; non-increasing timestamps are `INVALID_INPUT`.
7. **Windows**: `window` (samples, one spelling) and `hop` (default 1); `EventSynchronization*` use `hop=None` = non-overlapping; `CurvatureDispersion` has no hop. `MultiScaleEntropy` default `window=3000`.
8. **Units**: lengths and thresholds in metres as in EyesWeb; `units="m"|"mm"` for features declaring `_unit_params` (parameters are scaled, data/outputs never); `Output.unit` is documentation (`"<length>"`, `"<input>"`, `"samples"`, `"frames"`, `"px"`, `"deg"`, `"s"`, or the concrete unit when `units=` was given); empty unit = dimensionless. **Humanoid exception** (`HumanoidSimulator` works internally in mm and converts at the boundary; `GenericModel*` run in the unit of the user's model and `units` only names it).
9. **Choices**: lower-case strings (`method=`, `aggregation=`, `output_dims`, `input_mode`), case-insensitive, `-`/space count as `_`, wrong value lists the options; booleans are real bools; no enums in the public API; `parts=` sequences for the silhouette/potential switches (`SilhouetteCentroids`, `SilhouetteBodyParts`, `RegionDependingPotentials`).
10. **Constructors**: `from_*` classmethods per `input_mode` (`KineticEnergy.from_position/from_velocity`, `Kinematics`, `LogDimensionlessJerk`); list them by introspection, do not hand-write.
11. **Skeletons**: presets `kinect_v2`, `qualisys_sport`, `mediapipe`, `openpose` (some fields unfilled: `SKELETON_TODO`; **say so**) or a `pyeyesweb.skeletons.Skeleton`; `skeleton=`, `labels=`, `pairs=`, `weights=` override; `joint_map` (verify).
12. **Dims**: `dims=None` is inferred from the first frame.
13. **Layers and catalog**: `catalog()`, `catalog_table()`, `Layer`, `Timescale`; the five packages and the **placement rule** (copy it from the `catalog` docstring; `FilterContour`, `Directness`, `TrajectoryNonPlanarity` are low-level after C and D). `dir(pyeyesweb)` lists public modules; `pyeyesweb.base` and `pyeyesweb.utils` are internal and are **not documented as API**.
14. **Live vs structural parameters**: live = applied in place, state kept; structural = state resets and the next result says "parameters changed: state reset". Per-parameter source: `examples/scratch/live_parameters_classification.md` (**verify against code**: the `Feature.parameters` / setters).
15. **Removed features** (complete list from `PORTING_STATUS.md` "Removed blocks" and OPEN_POINTS §6): `CannyEdgeDetector`, `Lightness`, `ZeroCross`, `Clusterability`, `StatisticalMoment`, the trajectory datatype and transforms, `NoPreparationDetector(2)`, MECS v1, `EventSynchronizationRealTime`, `TauEstimator`, `ScalarBinarySyncDetector`, `SkeletonManipulator`, OpenNI and legacy device presets, plus API removals: `SlidingWindow`, `SpeedSmoothness`/`Smoothness`, `HistogramRarity`, single `Synchronization`, `fix_*` flags, `time_mode`, enums. Each with "use X instead" or "removed". Wording of the retirements is a maintainer input.
16. **Fidelity policy**: ports are faithful to EyesWeb; where a defect was corrected the behaviour is the core's behaviour (no flag) and the page says **"Corrected in the core"** with a one-line description (source: `PORTING_STATUS.md`).
17. **Install/core**: `pip install pyeyesweb` pulls the binary wheel `eyesweb-core` (module `eyesweb_core`); `pyeyesweb._core` requires `REQUIRED_CORE` (major.minor, 2.0 at the time of writing) and raises `ImportError` otherwise; developers set `EYESWEB_CORE_PATH`. Do not describe the C++ internals.

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
How-tos                       load Qualisys TSV; map a skeleton; real-time loop with live parameters; batch a recording to pandas; images
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
`docs/references.bib` with all literature; each metric docstring has a numpydoc "References" section using `:cite:` keys (e.g. `[Balasubramanian2015]_`-style rendered by sphinxcontrib-bibtex: **decide citation style, e.g. `:cite:p:` in prose and a footnote-style block in the generated page**). Known: SpectralArcLength → Balasubramanian, Melendez-Calderon, Roby-Brami, Burdet (2015), "On the analysis of movement smoothness", J NeuroEng Rehabil 12:112. The rest are supplied by the maintainer (OPEN_POINTS §3); until then the key `TODO` is **allowed only in a draft build** and the final gate (WP9) fails on it. Add the Camurri et al. papers for the conceptual model and the EyesWeb reference.

### 4.4 Identity and landing page
- Custom `_static/custom.css` + `pydata` theme options: a recognisable palette (derive from the EyesWeb/Casa Paganini logos; light and dark variants, both checked for contrast), a SVG logo (light/dark) under `html_theme_options["logo"]`, footer with EU/Casa Paganini/RESILENCE logos and funding text (keep `assets/*logo*.png`), a favicon.
- Landing page: one-sentence pitch (research toolkit for expressive movement analysis, built on the EyesWeb Expressive Gesture Analysis library), install line, a 10-line executed example, then a `sphinx-design` **grid of cards, one per layer** (title, timescale, number of features from `catalog()`, link), and cards for Getting started / Concepts / Gallery / API. No marketing copy; funding and citation at the foot.
- Version switcher: **decide** (pydata `switcher.json`, needs versioned deploys) or drop; start with a single "stable" build plus "latest".

### 4.5 Hosting and the private core (constraint, decision needed; ties to work package E)
Autodoc, the generated pages and the gallery need the compiled `eyesweb_core`, which is closed source and built from the private repository `InfoMusCP/EwbCore` ("EyesWebCore"). The public PyEyesWeb repository must not contain C++ sources, and the docs CI must obtain **the binary wheel** `eyesweb-core` produced by the private repository's own build. Options:
| Option | How | Pros | Cons |
|---|---|---|---|
| A. Artifact from the private repo | private workflow builds the wheel and uploads it as a release asset or workflow artifact; docs workflow downloads it with a fine-grained token (`secrets.EWBCORE_TOKEN`, read-only, `contents`/`actions`) | no extra infrastructure | token management; forks/PRs from outside cannot build docs; artifacts expire |
| B. Private package index | wheels published to a private index (GitHub Packages, Azure Artifacts, devpi, a private PyPI project); docs CI installs with `pip --extra-index-url` and an index token | the normal `pip install` path; same mechanism the release will use | needs an index (cost/setup); same token caveat |
| C. Public PyPI wheel | publish `eyesweb-core` binary-only on PyPI (the compiled module is public, sources stay private) | simplest CI, users get the same | **the maintainer must accept distributing the binary**; license check (ALPHA_REVIEW Q5) first |
| D. Prebuilt docs from a private runner | docs built in the private repo's CI (it already has the core) and pushed to the public Pages branch | no token in the public repo | docs workflow lives next to the closed code; harder for contributors |
Recommendation to put to the maintainer: **C if the binary may be public (it will be, to make `pip install pyeyesweb` work, so this is the same decision as work package E); until then A.** CI details common to all: Windows is the dev platform but the docs job runs on Linux, so it needs the Linux wheel (cibuildwheel matrix of Q14 must include it), Python 3.11, the wheel installed into the job's venv, then `pip install .[docs]`, `sphinx-build -W --keep-going -b html docs docs/_build/html`, deploy with `actions/deploy-pages` (GitHub Pages "GitHub Actions" source) on pushes to main; pull-request builds run the same without deploying. The gallery executes in this job, so the wheel must be available there. The docs job must **not echo or upload** the wheel, and the public repo's workflow files must contain no C++ paths or sources. Local build: `EYESWEB_CORE_PATH=<EyesWebCore>/build/Release` plus `PYTHONPATH` as in the header, then `sphinx-build -b html docs docs/_build/html` (document it in the "Building the docs" page and in `docs/README`-free form: only in the developer guide).

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
| WP2 Fact sheet | `facts` page per §2 | every item cited to file:line and verified by running code; maintainer approves |
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

## 9. Decisions still needed from the maintainer
1. **Core wheel in docs CI** (§4.5): option A, B, C or D; who creates the token or index; may the binary `eyesweb-core` be public on PyPI (also decides work package E)? Which platforms the wheel is built for (docs job needs Linux).
2. Source format: reStructuredText only, or MyST Markdown for prose pages (reuses the old `.md`)? `numpydoc` or `napoleon`?
3. Literature references per metric (OPEN_POINTS §3) and the bibliographic citation style; the Camurri/EyesWeb papers to cite for the conceptual model.
4. Wording for removed features (§2 item 15) and what in `DEVELOPMENT_SPEC.md`/`PORTING_STATUS.md` may be public (private repository names, internal paths).
5. Visual identity: palette, logo (SVG), whether to keep the existing EyesWeb logo as the main mark; version switcher yes/no; custom domain.
6. Where internal documents (`STRUCTURE_REVIEW`, `DESIGN_PROPOSALS`, `OPEN_POINTS`, `ALPHA_REVIEW`) are kept once the repo ships; whether `main.py` and `tools/update_catalog_docs.py` are deleted.
7. Whether the TSV reader is a public utility (page kept) or example-only.
8. Whether docstring doctests are also run inside Sphinx or only by `pytest --doctest-modules`.
9. Skeleton presets still incomplete (`qualisys_sport`, `mediapipe`, `openpose`): document as incomplete or complete them first.
10. Version policy for the docs (2.0.0a1 first, which URL: `latest`/`stable`).
11. Git: initialise version control for the PyEyesWeb tree before the docs work starts (backup alternative).
12. Whether the artists' site (§8) gets its own repository and when.
