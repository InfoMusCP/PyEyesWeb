# PyEyesWeb 2.0 — Educational Materials Plan (for an executing agent)

Root: `C:\Users\Nicola\Desktop\CP\EwbTD\PyEyesWeb` (`PEW/`). Companion of `DOCS_PLAN.md` (same stack: Sphinx + PyData theme; read its §0, §2 fact sheet, §4.5 core-wheel constraint and §4.6 checks first). Source material: `PEW/examples/scratch/` (`00_tour`..`08_humanoid` percent scripts `.py` + executed `.ipynb`, `common.py`, `build.py`, `README.md`, `live_parameters_classification.md`), ~5200 lines. They were current on 2026-10-14 and are written for a *reviewer*, not a learner; they predate some of the renames of packages B-D, so **re-run every script and fix names against the code** (e.g. `sampling_rate` default `None`, `parts=`, `number_of_*`, `Recorder` indexing, `Status` names, `feature.parameters`, `latest`, units on outputs, `SlidingWindow` removed). Goal: tutorials for colleagues and students that **replace** `PEW/examples/*.ipynb`, built by **sphinx-gallery**.
Run with: `PYTHONPATH="<EyesWebCore/build/Release>;<PEW>" EYESWEB_CORE_PATH=<EyesWebCore/build/Release> C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe`. The workspace is not a git repo: back up `examples/` before deleting anything. Facts must match the fact sheet of the docs plan. Standing rules: no edits until the companion AI executes the plan; content matches the current code. `examples/scratch/` is git-ignored and is not shipped.

## 1. Pipeline: percent scripts → sphinx-gallery (replaces `examples/build.py` and `examples/check.py`)

The scripts are the single source; sphinx-gallery executes each on **every docs build**, renders HTML with embedded figures, and generates a downloadable `.ipynb` and `.py` per tutorial (no Binder/JupyterLite: the compiled core cannot run in a browser; each page offers the downloadable `.ipynb`/`.py`, whose first cell is `%pip install pyeyesweb`). Notebooks are therefore no longer committed; `examples/build.py` is dropped; execution errors fail the docs build (`abort_on_example_error: True`), which is the guarantee that tutorials match the code.

Layout (**proposal**, maintainer has no preference: gallery grouped by layer, numbered names kept):
```
examples/                 gallery source (public): README.rst (gallery intro) + one folder per layer, each with its own README.rst/GALLERY_HEADER.rst
  00_getting_started/     01_getting_started.py, 02_the_contract.py
  01_physical_signals/    03_physical_signals_points.py, 04_physical_signals_images.py
  02_low_level/           05_low_level_motion.py, 06_low_level_shape.py
  03_mid_level/           07_mid_level.py
  04_analysis_primitives/ 08_analysis_primitives.py, 09_synchronization.py
  05_capstone/            10_capstone.py
  helpers.py, data/ (trimmed Qualisys; synthetic generators in helpers.py)
docs/tutorials/           gallery_dirs target (generated, git-ignored): index + one page per script + .ipynb/.py downloads
```
`conf.py`:
```
sphinx_gallery_conf = {
  "examples_dirs": "../examples", "gallery_dirs": "tutorials",   # with subfolders, examples_dirs/gallery_dirs may be lists of one entry per layer folder or one parent dir with subsections
  "filename_pattern": r"/\d\d_",            # default is plot_*.py: our files are NN_name.py (works in the layer subfolders)
  "ignore_pattern": r"helpers\.py|build\.py",
  "within_subsection_order": "FileNameSortKey",
  "backreferences_dir": "api/generated/backreferences",
  "doc_module": ("pyeyesweb",), "reference_url": {"pyeyesweb": None},
  "abort_on_example_error": True, "plot_gallery": True,
  "download_all_examples": True, "remove_config_comments": True,
  "capture_repr": ("_repr_html_", "__repr__"),
  "image_scrapers": ("matplotlib",), "thumbnail_size": (320, 240),
  "default_thumb_file": "docs/assets/gallery_thumb.png",   # layer/palette placeholder
  "first_notebook_cell": "%matplotlib inline",
  "min_reported_time": 5, "show_memory": False,
  "reset_modules": ("matplotlib", "seaborn"),
  "expected_failing_examples": [], "run_stale_examples": False,
  "junit": "docs/_build/sphinx-gallery-junit.xml",
}
```
(`junit` makes per-example run times visible in CI for the time budgets of §4.)

Script conventions required by sphinx-gallery:
- first block: a module docstring (title with `===` underline in RST, then a short abstract: it becomes the page heading and the **gallery card text**); then `# %%` blocks. Text blocks are comments starting `# %%` followed by `# ` lines **in reStructuredText** (sphinx-gallery has no Markdown/MyST option for text blocks: checked in its syntax documentation, 0.22; prose pages of the docs are MyST, gallery text is RST): the existing markdown cells (`# %% [markdown]`) must be converted to RST (headings, `:class:` roles to `:class:\`~pyeyesweb.low_level.Kinematics\``, math with `:math:`/`.. math::`); this is a mechanical but manual pass: verify by building. Section headings use `# %%` + `# Title` + `# -----`.
- **Cross-references**: every public class in prose is a role (`:class:`) so back-references fill the "Examples using X" gallery on each generated feature page (and feed the catalog coverage check of the docs plan §4.6). No `_` names in code cells (they would not link).
- **Thumbnails**: `# sphinx_gallery_thumbnail_number = N` in each script to choose the figure that is the card (one deliberately telling figure per tutorial; fallback `default_thumb_file`).
- Per-script options as comments where needed: `# sphinx_gallery_capture_repr = ()` to hide noisy reprs, `# sphinx_gallery_dummy_images = N` is **not** used (we execute everything).
- Downloads: sphinx-gallery adds "Download Jupyter notebook" and "Download Python source code" at the foot of each page and a `download_all_examples` zip; the notebooks contain a first cell `%matplotlib inline`; they run with `pip install pyeyesweb` + the tutorials' requirements (`docs`-independent: matplotlib, pandas, numpy, scipy). A downloaded notebook starts with `%pip install pyeyesweb` (a `first_notebook_cell` of `"%pip install pyeyesweb\n%matplotlib inline"`); state on the tutorials index how to run them locally. **How a downloaded notebook gets `helpers.py`** (proposal): inline the three needed functions (`plot_recorder`, `shade_status`, `load`) in a first-cell block only in notebooks where they are used, or, simpler, the first cell downloads the file (`urllib.request.urlretrieve(<raw URL of helpers.py on the tagged release>, "helpers.py")`); in the docs build and in a checkout the file is simply next to the scripts. Default: the download cell, guarded by `if not Path("helpers.py").exists()`.
- Execution budget (**proposal**, DOCS_PLAN §4.5): each script < 60 s, whole gallery < 10 min on a GitHub Actions `ubuntu-latest` runner with the released wheel, docs job timeout 30 min, executed outputs cached keyed on the script hash; `junit` output checked in CI; cut data by time slices; no benchmark/timing cells.
- Data location: scripts find data through `pyeyesweb.datasets` / `helpers.data_path(name)` (see §5), never through absolute paths or the cwd, so they run from the docs build, from a downloaded notebook, and from a checkout.
- Figures: matplotlib only, dpi 80-100 (`plt.rcParams["figure.dpi"]`), axes labelled with units, time axis in seconds, status shading via `shade_status`; one concept per figure.

The old `examples/build.py` (nbclient/nbformat) is deleted together with the committed notebooks; `examples/check.py` is not written: its jobs move to the docs build (execution = gallery; catalog coverage and stale-name grep = the small docs-build check of the docs plan §4.6, which reads sphinx-gallery back-references).

## 2. Audit of the scratch scripts
Reviewer-only material counted by grep (`Notes for the reviewer|where(|call_path|_process_window`, on 2026-10-14, re-run): 00:27, 01:5, 02:32, 03:31, 04:30, 05:31, 06:68, 07:0, 08:0. `_process_window` direct calls: 00:12, 02:17, 03:5, 04:10, 05:17, 06:46.

| Script (lines) | Teaches | Remove / rework |
|---|---|---|
| `00_tour` (746) | data, Schema/Result/Recorder, inputs + shape check, process vs run, windowed statuses, runtime params, catalog | "Notes for the reviewer" (l.718+), CoreFeature internals, "where the C++ loads", `where()`/`call_path`, class-pattern map → developer guide. Split into NB01 + NB02 |
| `01_physical_signals` (158) | contours, hit cells | reviewer notes (l.148+); `FilterContour` is now **low-level** (check): move to NB06 |
| `02_low_level_motion` (604) | Kinematics, KineticEnergy, smoothness family, Curvature* | reviewer notes (l.570+), 17 `_process_window` → `process`/`run` |
| `03_low_level_shape` (669) | shape features, Equilibrium, DirectionChange, contour, hull | `where`, `_process_window`; `Directness` and `TrajectoryNonPlanarity` are low-level now |
| `04_mid_level` (745) | GestureSegmenter (+KE, MotionNoiseDetector), MotionDuration, Suddenness, impulsivity, potentials | same; `Directness`/`TrajectoryNonPlanarity` leave this notebook |
| `05_analysis_primitives` (755) | entropy, CoarseGraining, Rarity, MSE + EnsembleDominance, Periodicity, ScalarPeakDetector | same |
| `06_synchronization` (571) | 11 sync blocks | heaviest: 46 `_process_window`, bug-hunt / cross-check cells vs EyesWeb numbers → at most one "validation" sidebar |
| `07_imaging` (175) | IMAGE input, silhouettes, Videogram, BinaryPulsesRegularity, TimeWindowSynchronizer | clean; `TimeWindowSynchronizer`/`SynchronizedWindow` are public in `pyeyesweb.physical_signals`; `parts=` replaces bool switches |
| `08_humanoid` (337) | HumanoidSimulator (damping, flutter limitation), orientations, `control`, `joint_map` with Qualisys, PointsPredictor, mass-spring, GenericModelEstimator (`seed`) | clean; keep limitation numbers phrased for learners; units rule (mm internal, converted at the boundary) |

Also remove in every script: references to resolved issues/fix numbers, "faithful vs corrected" debates (replace by one sentence "Corrected in the core" where relevant), timing cells unless pedagogical, comparisons that show features failing to separate two conditions (OPEN_POINTS §4: `CurvatureVelocityCorrelation`, `Harmonicity`, `Suddenness`, `SuddennessImpulsivity`, `Directness`, PLV on the vertical axis): **decided 2026-10-15: document them as if they work** (no caveat pages, no "fails to separate" text); the analysis of OPEN_POINTS §4 remains an internal to-do for the maintainer. Prefer a synthetic or well-chosen condition in the tutorial where the feature visibly responds.

`common.py` functions: `Recording`, `load(trial, standardize)`, `describe`, `peek`, `trace`, `shade_status`, `plot_recorder`, `draw_skeleton`, `show_frames`, `options`, `where`, `call_path`, `synthetic_silhouette`.
Decision:
- **library**: the TSV reader is **removed from the library** (decided 2026-10-15; data ships in `examples/`). One small addition is proposed: `pyeyesweb.datasets` (§5). `describe` is covered by `catalog()` / `feature.parameters` / `feature.inputs` / `feature.outputs`.
- **`examples/helpers.py`** (not installed, plain file next to the scripts; sphinx-gallery puts the examples folder on `sys.path`): `data_path`, `load`/`Recording`, `plot_recorder`, `shade_status`, `draw_skeleton`, `show_frames`, `synthetic_silhouette`, `peek`, `trace`. Learners must be able to read it: < 250 lines, documented; a downloaded notebook obtains it with a first cell (§1, proposal), and the `.py` download page of the gallery header also links it.
- **drop from teaching** (move to a maintainer `dev/` folder): `where`, `call_path`, `options`, `_snake`.

## 3. Target curriculum (one script = one gallery page = one downloadable notebook)
| # | Script | Learning goals | Prereq | Data | Features covered | Budget |
|---|---|---|---|---|---|---|
| 01 | `01_getting_started` | install check, load a trial, one feature with `run`, plot, `Recorder` | Python, numpy | qualisys trial (small) | Kinematics, KineticEnergy | 15 min, ≤ 20 blocks, < 30 s |
| 02 | `02_the_contract` | `process` vs `run`, `reset`, `Result`/`Schema`, `Status` and warm-up, `latest`, `feature.parameters`, seconds and `sampling_rate`, units m/mm, string choices, live vs structural params, `from_*`, skeleton presets + `joint_map`, `catalog()` | 01 | synthetic + qualisys | Kinematics, a windowed feature | 25 min, < 40 s |
| 03 | `03_physical_signals_points` | hit cells, humanoid/mass-spring simulation and prediction, estimator | 02 | qualisys + synthetic | HitCellDetector, Humanoid*, GenericModel*, PointsPredictor, … (verify the layer-1 list in `catalog()`) | 30 min |
| 04 | `04_physical_signals_images` | IMAGE input, silhouettes, videogram, stream plumbing | 02 | synthetic silhouettes (no video files) | SilhouetteCentroids, SilhouetteBodyParts (`parts=`), Videogram, BinaryPulsesRegularity, TimeWindowSynchronizer | 20 min |
| 05 | `05_low_level_motion` | velocity/energy; smoothness metrics compared on smooth vs jerky synthetic reaches then real data | 02 | synthetic + trials 5/6 | Kinematics, KineticEnergy, SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount, CurvatureDispersion, CurvatureVelocityCorrelation, MotionNoiseDetector, Directness, TrajectoryNonPlanarity | 30 min |
| 06 | `06_low_level_shape` | contraction/expansion, symmetry, balance, contours | 02 | qualisys symmetry trials (3/4) | BoundingBoxFilledArea, PointsDensity, EllipsoidSphericity, Symmetry, TriangleSymmetry, Equilibrium, DirectionChange, FilterContour, ContourCurvature, ConvexHull, BodyPartsFromCurvature | 30 min |
| 07 | `07_mid_level` | segmenting gestures, suddenness, impulsivity, potentials | 05, 06 | qualisys (sudden/impulsive trials per `data/README.md`) | the mid_level features in `catalog()` | 30 min |
| 08 | `08_analysis_primitives` | entropy across scales, rarity, peaks, periodicity | 05 | synthetic + qualisys | SampleEntropy, CoarseGraining, MultiScaleEntropy, Rarity, Periodicity, ScalarPeakDetector, SequenceDetector, … | 30 min |
| 09 | `09_synchronization` | sync vs unsync trials 3/4, 5/6, 7/8; plus high-level dominance | 08 | qualisys sync trials | the synchronization family (PhaseLockingValue, CorrelationsMatrix, PartialRecurrenceSynchronization, GeneralisedAutoCorrelation, EventSynchronization(+MECS), NonlinearInterdependence, SpikeSynchronization, RecurrencePlot, CrossRecurrencePlot, TemporalSynchronization) + EnsembleDominance | 35 min |
| 10 | `10_capstone` | real-time loop with `process` + live parameter change; batch features → table → simple plot/classifier | all | qualisys | mix | 30 min |

Coverage rule: every `catalog()` name appears in at least one script **as a linked class role and in code** (checked by the docs-build check through back-references; the tables above are provisional, re-derive from `catalog()` in T0 because layers changed).
Exercises: 2-3 per script in a final "Try it" section; **decided: solutions are executed code inside a sphinx-design dropdown**. A reST text block cannot hold executed code, so T1 must verify how to wrap a gallery code cell in a dropdown (a `.. dropdown::` block with a `.. code-block:: python` solution plus an executed check cell, or sphinx-design/CSS wrapping of the cell); acceptance: every solution executes.
Figures: as in §1.

## 4. Conventions
- One concept per section: text block (why / what it measures; link to the theory page) → minimal code → plot → one-sentence takeaway.
- Public API only: no `_`-prefixed names, no `where/call_path`, no imports from `pyeyesweb.base`/`pyeyesweb.utils` (internal).
- Header (module docstring): goals, prerequisites, data, estimated time; footer text block: links to the API pages and the next tutorial.
- Language: plain English, scientific and sober (same tone as the docs plan); define each movement term on first use, with a link to the theory page.
- Time and units in the text are always explicit (s, m or mm); state the Qualisys unit (mm in raw data) and how the script converts or declares it (`units=`).
- Budgets are enforced from the sphinx-gallery junit output (§1); a script over budget is fixed by slicing data.

## 5. Data: size, licensing, handling
`examples/data` is 939 MB: `videos/` 780 MB, `qualisys/` 84 MB (22+ trial TSVs), `kinect/` 68 MB, `imu/` 8.5 MB, `markers_mappings.json`, `README.md` (trial descriptions, 2024-03-26 session). **Decided 2026-10-15: videos, kinect, imu and the rest stay in the repository for now and are used for examples and educational material; the data/licensing/consent question is parked ("to be discussed"), not blocking.** Release-checklist item: before the PyPI sdist/wheel, the wheel must not bundle the big data (exclude `examples/` from both), and the repository size and the licence still need a decision. The gallery must build from a clean checkout and in CI without the full data.
- Tutorials use **only Qualisys + synthetic** data. Choose ≤ 6-8 trials (3-8 plus the sudden/impulsive ones) and **trim** them (time slice, needed markers only) to ≤ 15 MB total kept in the repository under `examples/data/`; keep the trimming script in the maintainer `dev/` folder (not shipped).
- **Proposal** (no maintainer preference): a small public `pyeyesweb.datasets` helper using `pooch` (optional extra `pyeyesweb[datasets]`, SHA-256 checksums, user cache directory), modelled on the scikit-learn/SciPy dataset fetchers; the trimmed data are small enough to ship in `examples/data`, and the helper falls back to downloading from a persistent host (Zenodo/OSF, to be chosen) when the local file is absent. `helpers.data_path(name)` is a thin wrapper over it. In the docs build the download step is skipped when the trimmed files exist; a downloaded notebook uses the download path. Offline failure gives a clear message.
- Videos, kinect, imu never ship in the **wheel/sdist** (they stay in the repository for now, see above).
- Licensing (parked): when the maintainer settles consent and a data licence (e.g. CC BY 4.0), add `examples/data/LICENSE` and a citation; rewrite `data/README.md` with units (mm raw Qualisys), frame rate, marker set ↔ skeleton preset/`joint_map`; remove `kinect/desktop.ini`. The gallery index states the licence and how to cite the data.
- Synthetic generators live in `helpers.py` and are seeded (`numpy.random.default_rng(seed)`) so figures are reproducible.

## 6. Fate of current public notebooks (all use removed APIs: `SlidingWindow`, `SpeedSmoothness`, `HistogramRarity`, `StatisticalMoment`, `Lightness`, `Synchronization`, `StaticFeature`, `dims=3`)
| Current | Replacement | Action |
|---|---|---|
| `01_sliding_window.ipynb` | tutorial 02 (windows/statuses) | delete |
| `02_static_vs_dynamic.ipynb` | tutorial 02 (`process` vs `run`) | delete |
| `03_dual_api.ipynb` | tutorial 02 | delete |
| `04_output_contracts.ipynb` | tutorial 02 + docs Concepts/Results | delete |
| `05_theoretical_framework.ipynb` | tutorials 05-09 + docs Theory/framework | delete |
| `06_multimodal_capstone.ipynb` | tutorial 10 | delete (reuse its storyline if good; it used IMU/kinect, which are not shipped) |
| `examples/utils/data_loader.py`, `plot_utils.py` | `examples/helpers.py` | delete after porting what is needed (`data_loader.py` has its own `_load_tsv`: it does not use the removed library reader) |
| `examples/requirements.txt` | the tutorials' runtime list (`matplotlib`, `pandas`, `scipy`, `pyeyesweb`); build tools live in the `docs` extra; drop `ipywidgets`, `tqdm`, `opencv-python` unless used | rewrite |
| `examples/scratch/` (including `build.py`, `*.ipynb`) | source for tutorials 01-10; stays git-ignored, excluded from release; deleted after WP T7 when the maintainer says | ask maintainer |
| committed `*.ipynb` anywhere | none: generated by the gallery as downloads | do not commit notebooks |

## 7. Work packages (ordered; docs-plan WP7 = T1-T7 below)
| WP | Content | Acceptance criteria |
|---|---|---|
| T0 | backup; re-derive the curriculum table from `catalog()` (layers moved); decide `helpers.py` split (§2), data host and licence, gallery directory names | written decision; per-feature script assignment table |
| T1 | gallery wiring in `conf.py` (§1) on one converted script (01) + `GALLERY_HEADER.rst`, thumbnails, download links; needs docs-plan WP1 (CI with the core wheel) | gallery page + `.ipynb` + `.py` built in CI; notebook downloaded from the built site runs |
| T2 | `examples/helpers.py` with `data_path`/download helper and checksum table | no private names; documented; `ruff` clean; works from a clean cache and offline with local data |
| T3 | tutorials 01-02 from `00_tour` | each < 60 s; no `_` names (grep `\._[a-z]` in code = 0); all prose RST with roles |
| T4 | tutorials 03-09 from scratch 01-08 | each < 60 s; reviewer cells removed (grep `reviewer|where\(|call_path|_process_window` = 0); stale names re-verified by running |
| T5 | tutorial 10 + exercises and solutions in all | every solution executes (or is explicitly marked) |
| T6 | data trim, `data/README.md`, LICENSE, host upload | repository `examples/` < 30 MB; checksums verified |
| T7 | delete old notebooks/utils/build; update `examples/README.md` (one paragraph: gallery, how to run locally); link from docs Tutorials; docs-build check (catalog coverage, stale names) | no reference to deleted files (grep); gallery total < 10 min; coverage check passes; maintainer + one student test-reader sign-off |

Order: T0 → T1 (after docs-plan WP1) → T2 → T3 → T4 → T5 → T6 → T7. T3/T4 can follow docs-plan WP3 (generated API pages exist for the links).

## 8. Risks
- The gallery needs the compiled core in CI (docs plan §4.5): without a decided way to obtain the wheel nothing builds.
- Execution on every build lengthens CI and amplifies flakiness; seeded data, no network except the cached download, `junit` timing, Linux runner differences in numerical results (figures may differ slightly between platforms: avoid text that quotes numbers to many digits, or print rounded values).
- Data consent/licence unknown; trimmed files must still contain what the text claims (check trial descriptions).
- The scratch scripts call `_process_window` heavily for comparisons: rewriting with `run` can change what is shown; markdown-to-RST conversion is manual and can break math; sphinx-gallery's default file pattern (`plot_*.py`) does not match our names (set `filename_pattern`).
- Executed outputs live only in the build: no pre-rendered notebooks on GitHub; accept, or add a release attachment of the notebooks zip.

## 9. Decisions taken (2026-10-15) and what remains open
Taken by the maintainer (see also DOCS_PLAN §9):
1. **Core wheel**: public `eyesweb-core` binary wheel on PyPI (first release `2.0.0a1`); docs CI installs `pyeyesweb` from PyPI/TestPyPI; packaging (WP E) is a prerequisite of docs CI, until then docs and gallery are built locally. Forks and PRs can therefore build the gallery.
2. Prose pages MyST, docstrings numpydoc; **gallery text blocks RST** (sphinx-gallery has no MyST option).
3. ACM citation style; references mined from the existing docs/docstrings first.
4. Internal agentic documents (including this plan) move to the private repository before release.
5. Public repository layout: DOCS_PLAN §9 (`examples/`: layer folders, `helpers.py`, `requirements.txt`, trimmed `data/`).
6. TSV reader removed from the library; data ships in `examples/`; incomplete skeleton presets stay documented as incomplete.
7. Data (videos, kinect, imu): stay in the repository for now and feed examples and educational material; licensing/consent parked ("to be discussed") but on the release checklist (no big data in wheel/sdist).
8. Exercise solutions: executed code in a sphinx-design dropdown.
9. Features that did not separate conditions: documented as if they work; OPEN_POINTS §4 stays an internal to-do.
10. Creatives site: separate repository, much later.

**Proposals, no maintainer preference (confirm)**: gallery grouped by layer under `examples/` with `filename_pattern` matching the numbered names; no Binder/JupyterLite, downloadable `.ipynb`/`.py` with a first cell `%pip install pyeyesweb`; `pyeyesweb.datasets` with `pooch` (optional extra, checksums, cache dir); `examples/helpers.py` imported next to the scripts, fetched by a first cell in downloaded notebooks; budgets (< 60 s per script, < 10 min total, docs job timeout 30 min), GitHub Actions `ubuntu-latest`, tests on ubuntu/windows/macos x Python 3.10-3.13, executed-output cache keyed on script hash, `-W`, deploy to GitHub Pages from `main`, PR builds without deploy.

**Remaining open**:
- Confirm the proposals above.
- Which trials, trimming rule and host (Zenodo/OSF) for the downloadable data; data licence and consent text (parked).
- Final feasibility of an executed solution inside a dropdown with sphinx-gallery (check in T1; fallback: solution cell directly after the dropdown-closed text).
- Fate of `examples/scratch/` after conversion.
