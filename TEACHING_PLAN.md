# PyEyesWeb 2.0 — Educational Materials Plan (for an executing agent)

Root: `C:\Users\Nicola\Desktop\CP\EwbTD\PyEyesWeb` (`PEW/`). Source material: `PEW/examples/scratch/` (`00_tour`..`08_humanoid` percent scripts `.py` + executed `.ipynb`, `common.py`, `build.py`, `README.md`, `live_parameters_classification.md`), ~5200 lines. They are current and correct; they are written for a *reviewer*, not a learner. Goal: teaching notebooks for colleagues and students that **replace** `PEW/examples/*.ipynb`.
Run with: `PYTHONPATH="<EyesWebTD/build/Release>;<PEW>" EYESWEB_CORE_PATH=<EyesWebTD/build/Release> C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe`. Workspace is not a git repo: back up `examples/` before deleting anything. Facts (contract, seconds, units, strings, statuses, dropped list) must match `docs/_snippets/facts.md` from the docs plan.

## 1. Audit of the scratch scripts
Reviewer-only material counted by grep (`Notes for the reviewer|where(|call_path|_process_window`): 00:27, 01:5, 02:32, 03:31, 04:30, 05:31, 06:68, 07:0, 08:0. `_process_window` direct calls: 00:12, 02:17, 03:5, 04:10, 05:17, 06:46.

| Script (lines) | Teaches | Remove / rework |
|---|---|---|
| `00_tour` (746) | data, Schema/Result/Recorder, inputs + shape check, process vs run, windowed statuses, runtime params, catalog | "Notes for the reviewer" (l.718+), CoreFeature internals, "where the C++ loads", `where()`/`call_path`, class-pattern map → developer guide. Split into NB01 + NB02 |
| `01_physical_signals` (158) | FilterContour, HitCellDetector | reviewer notes (l.148+) |
| `02_low_level_motion` (604) | Kinematics, KineticEnergy, smoothness family, Curvature* | reviewer notes (l.570+), 17 `_process_window` calls → `process`/`run` |
| `03_low_level_shape` (669) | shape features, Equilibrium, DirectionChange, contour, hull, NonPlanarity | `where`, `_process_window` |
| `04_mid_level` (745) | GestureSegmenter (+KE, MotionNoiseDetector), MotionDuration, Suddenness, impulsivity, Directness, potentials | same |
| `05_analysis_primitives` (755) | entropy, CoarseGraining, Rarity, MSE + EnsembleDominance, Periodicity, ScalarPeakDetector | same |
| `06_synchronization` (571) | 11 sync blocks | heaviest: 46 `_process_window` calls, bug-hunt / cross-check cells vs EyesWeb numbers → keep one "validation" idea as a sidebar at most |
| `07_imaging` (175) | IMAGE input, silhouettes, Videogram, BinaryPulsesRegularity, TimeWindowSynchronizer | clean; check TimeWindowSynchronizer is public |
| `08_humanoid` (337) | HumanoidSimulator (damping, flutter limitation), orientations, `control`, joint_map with Qualisys, PointsPredictor, mass-spring family, GenericModelEstimator (`seed`) | clean; keep limitation numbers but phrase for learners |

Also remove in every script: references to resolved issues/fix numbers, "faithful vs corrected" debates (replace by one sentence "Corrected in the core" where relevant), timing/benchmark cells unless pedagogical.

`common.py` functions: `Recording`, `load(trial, standardize)`, `describe`, `peek`, `trace`, `shade_status`, `plot_recorder`, `draw_skeleton`, `show_frames`, `options`, `where`, `call_path`, `synthetic_silhouette`.
Decision (recommended, confirm with maintainer):
- **library** (`pyeyesweb.utils` or a new public `pyeyesweb.datasets`/`plotting` module, optional matplotlib extra): `load`/`Recording` only if a Qualisys TSV loader belongs in the library; `describe` (≈ a pretty print of FeatureInfo) could become `catalog()` / `FeatureInfo.describe()`.
- **examples helper** `examples/helpers.py` (not installed): `plot_recorder`, `shade_status`, `draw_skeleton`, `show_frames`, `synthetic_silhouette`, `peek`, `trace`.
- **drop from teaching** (move to `dev/` tools): `where`, `call_path`, `options`, `_snake`.
Learners must be able to read every helper; keep it < 250 lines, documented.

## 2. Target curriculum
| # | Notebook | Learning goals | Prereq | Data | Features covered | Length |
|---|---|---|---|---|---|---|
| 01 | Getting started | install check, load a trial, one feature with `run`, plot, `Recorder` | Python, numpy | qualisys trial (small) | Kinematics, KineticEnergy | 15 min, ≤20 cells |
| 02 | The contract | `process` vs `run`, `reset`, `Result`/`Schema`, `Status` and warm-up, `latest`, seconds, units m/mm, string choices, live vs structural params, `from_*`, skeleton presets + `joint_map`, `catalog()` | 01 | synthetic + qualisys | Kinematics, a windowed feature | 25 min |
| 03 | Physical signals: points and models | filtering, hit cells, humanoid/mass-spring simulation and prediction, estimator | 02 | qualisys + synthetic | FilterContour, HitCellDetector, Humanoid*, GenericModel*, PointsPredictor | 30 min |
| 04 | Physical signals: images | IMAGE input, silhouettes, videogram | 02 | synthetic silhouettes (no video files) | SilhouetteCentroids, SilhouetteBodyParts, Videogram, BinaryPulsesRegularity | 20 min |
| 05 | Low level: motion and smoothness | velocity/energy; smoothness metrics compared on smooth vs jerky synthetic reaches then real data | 02 | synthetic + trials 5/6 | Kinematics, KineticEnergy, SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount, CurvatureDispersion, CurvatureVelocityCorrelation, MotionNoiseDetector | 30 min |
| 06 | Low level: shape and posture | contraction/expansion, symmetry, balance, contours | 02 | qualisys symmetry trials (3/4) | BoundingBoxFilledArea, PointsDensity, EllipsoidSphericity, Symmetry, TriangleSymmetry, Equilibrium, DirectionChange, ContourCurvature, ConvexHull, BodyPartsFromCurvature, TrajectoryNonPlanarity | 30 min |
| 07 | Mid level: gestures and qualities | segmenting gestures, suddenness, impulsivity, directness, potentials | 05, 06 | qualisys (sudden/impulsive trials per `data/README.md`) | the 8 mid_level features | 30 min |
| 08 | Analysis primitives: complexity, rarity, periodicity | entropy across scales, rarity, peaks, periodicity, dominance | 05 | synthetic + qualisys | SampleEntropy, CoarseGraining, MultiScaleEntropy, Rarity, Periodicity, ScalarPeakDetector, EnsembleDominance, SequenceDetector | 30 min |
| 09 | Synchronization between body parts and people | sync vs unsync trials 3/4, 5/6, 7/8 | 08 | qualisys sync trials | PhaseLockingValue, CorrelationsMatrix, PartialRecurrenceSynchronization, GeneralisedAutoCorrelation, EventSynchronization(+MECS), NonlinearInterdependence, SpikeSynchronization, RecurrencePlot, CrossRecurrencePlot, TemporalSynchronization | 35 min |
| 10 | Capstone: a pipeline | real time loop with `process` + live parameter change; batch features → table → simple classifier/plot | all | qualisys | mix | 30 min |

Coverage rule: every one of the 60 `catalog()` names appears in at least one notebook (table above covers them; verify by script).
Exercises: 2–3 per notebook in a final "Try it" section; solutions in a collapsed `<details>` cell or a separate `solutions/` folder (recommended: `<details>` so a single file stays runnable).
Figures: one figure per concept, matplotlib only, axes labelled with units, time axis in seconds, status shading via `shade_status`.

## 3. Conventions
- One concept per section: markdown (why / what it measures) → minimal code → plot → one-sentence takeaway.
- Public API only: no `_`-prefixed names, no `where/call_path`, no imports from `pyeyesweb.base` internals unless public.
- Source of truth is the percent `.py`; `.ipynb` generated by `build.py` (move it to `examples/build.py`, make `timeout` 300 s, `allow_errors=False`, fail with non-zero exit on any error, strip run-specific metadata).
- Executed outputs **embedded** in committed notebooks (readable on GitHub and rendered by mkdocs-jupyter without the core), but keep image outputs small (dpi 80–100) so each `.ipynb` < 2 MB.
- Runtime: each notebook < 60 s, total < 8 min on a laptop with the released wheel; cut data with time slices.
- Header cell in every notebook: goals, prerequisites, data, estimated time; footer: links to reference pages.
- Language: plain English, define every movement term on first use (link to the theoretical framework page).

## 4. Fate of current public notebooks (all use removed APIs: `SlidingWindow`, `SpeedSmoothness`, `HistogramRarity`, `StatisticalMoment`, `Lightness`, `Synchronization`, `StaticFeature`, `dims=3`)
| Current | Replacement | Action |
|---|---|---|
| `01_sliding_window.ipynb` | NB02 (windows/statuses) | delete |
| `02_static_vs_dynamic.ipynb` | NB02 (`process` vs `run`) | delete |
| `03_dual_api.ipynb` | NB02 | delete |
| `04_output_contracts.ipynb` | NB02 (Result/Schema/Recorder) | delete |
| `05_theoretical_framework.ipynb` | NB05–NB09 + docs concept page | delete |
| `06_multimodal_capstone.ipynb` | NB10 | delete (reuse its storyline if good; it used IMU/kinect) |
| `examples/utils/data_loader.py`, `plot_utils.py` | `examples/helpers.py` | delete after porting what is needed |
| `examples/requirements.txt` | update (matplotlib, pandas, nbclient, nbformat, pyeyesweb==2.0.0) | rewrite |
| `examples/scratch/` | stays as maintainer material, excluded from release/wheel, or deleted after WP5 (its README says "to be deleted") | ask maintainer |

## 5. Data: size and licensing
`examples/data` is 939 MB: `videos/` 780 MB, `qualisys/` 84 MB, `kinect/` 68 MB, `imu/` 8.5 MB, `markers_mappings.json`, `README.md` (trial descriptions, 2024-03-26 recording session).
- Teaching notebooks use **only qualisys + synthetic** data. Choose ≤ 6 trials (e.g. 3–8 plus the sudden/impulsive ones) and, if possible, trim them to ≤ 15 MB total kept in repo; host the full set (videos, kinect, imu) on Zenodo/OSF with a download helper and checksum.
- Videos/kinect/imu must not ship in the repo or wheel (if only notebook 06 used them, they can go).
- Licensing: obtain from the maintainer the consent/licence of the recorded performer(s) and a data licence (e.g. CC BY 4.0); add `examples/data/LICENSE` and a citation; `data/README.md` rewritten to state units (mm in raw Qualisys), frame rate, marker set ↔ skeleton preset/`joint_map`. Remove `kinect/desktop.ini`.

## 6. Work packages
| WP | Content | Acceptance criteria |
|---|---|---|
| T0 | backup; decide `common.py` split (§1) with maintainer; confirm data licence | written decision |
| T1 | `examples/helpers.py` (+ any library additions with tests) | no private names; documented; `ruff` clean |
| T2 | NB01–NB02 from `00_tour` | runs < 60 s; no `_` names (grep `\._[a-z]` in code cells = 0) |
| T3 | NB03–NB09 from scratch 01–08 | each < 60 s; reviewer cells removed (grep `reviewer|where\(|call_path|_process_window` = 0) |
| T4 | NB10 capstone + exercises/solutions in all | every exercise solution executes |
| T5 | data trim, `data/README.md`, LICENSE, download helper | repo `examples/` < 30 MB |
| T6 | delete old notebooks/utils; update `examples/README.md` index; link from docs Tutorials | no reference to deleted files anywhere (grep) |
| T7 | CI script `examples/check.py`: builds all notebooks with the released wheel in a clean venv, asserts zero errors, runtime limits, catalog coverage (every `catalog()` name found in some notebook), stale-name grep (`SpeedSmoothness|SlidingWindow|HistogramRarity|StatisticalMoment|Lightness|Clusterability|dims=3`) = 0 | script passes; maintainer + one student test-reader sign-off |

Risks: dependence on unreleased wheel (build against dev core until release, re-run T7 after); data consent/licence unknown; the scratch scripts call `_process_window` heavily for comparisons — rewriting with `run` may change what is shown; notebook outputs embedded can drift from code (T7 rebuild is the guard).
