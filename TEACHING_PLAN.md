# PyEyesWeb 2.0 — Educational Materials Plan and status (for the finalizing agent)

Paths are relative to the root of the PyEyesWeb repository (branch `feature/v2-eyesweb-core`). Companion of `DOCS_PLAN.md` (same stack: Sphinx + PyData theme; its section 10 describes the gallery as built) and of `ALPHA_REVIEW.md` (section 8.4 is the master list for data and cleanup). Run with `PYTHONPATH="<EyesWebCore>/build/Release;<PyEyesWeb>" EYESWEB_CORE_PATH=<EyesWebCore>/build/Release python ...` (or the installed `eyesweb-core` once packaged).

**Where to start.** The ten tutorials are written, executed by every docs build and pass. **What is left is section 9 (T6 and T7)**: the data decision, the removal of the old examples and scratch material, a reader sign-off, and the points that the final pass must reflect (section 10). Sections 1 to 8 record what was decided and built.

## Status (2026-10-16)

| WP | Content | Status | Evidence |
|---|---|---|---|
| T0 | Curriculum re-derived from `catalog()`; decisions | DONE | section 3 below (every one of the 60 features is imported and used in a script) |
| T1 | Gallery wiring | DONE | `docs/conf.py` (`sphinx_gallery_conf`, one gallery per folder), `docs/_ext/tutorial_reset.py`, `examples/GALLERY_HEADER.rst` and one per folder, `docs/_ext/feature_pages.py` (back-references) |
| T2 | Helpers and data access | DONE | `examples/helpers.py` (166 lines), `pyeyesweb/datasets.py` (+ `_datasets_registry.py`, `docs/api/datasets.md`, `tests/unit_tests/test_datasets.py`), `tools/trim_example_data.py`, `docs/howto/load_data.md` |
| T3 | Tutorials 01 and 02 | DONE | `examples/01_getting_started/plot_01_first_feature.py`, `plot_02_the_contract.py` |
| T4 | Tutorials 03 to 09 | DONE | `plot_03_points.py`, `plot_04_images.py`, `plot_05_motion.py`, `plot_06_shape.py`, `plot_07_gestures.py`, `plot_08_primitives.py`, `plot_09a_synchronization_signals.py`, `plot_09b_synchronization_events.py` |
| T5 | Tutorial 10, exercises and solutions | DONE | `examples/06_capstone/plot_10_capstone.py`; each script ends with "Try it", "Solutions" and "Next steps" |
| T6 | Data: trim, licence, host | OPEN (maintainer decisions) | trimming tool and registry exist; `BASE_URL` is `None`; no licence file; `examples/data/README.md` not rewritten |
| T7 | Delete the old examples, final checks, sign-off | OPEN | section 9 |

State on 2026-10-16: the whole gallery runs in 36.9 s (11 files, the slowest `plot_07_gestures.py` 7.2 s); `abort_on_example_error=True`, so a failing script fails the docs build; `pytest` 2963 passed and 12 skipped.

## 1. Pipeline: percent scripts to sphinx-gallery (as built)

The scripts are the single source; sphinx-gallery executes each on every docs build, renders HTML with embedded figures and generates a downloadable `.ipynb` and `.py` per tutorial (no Binder or JupyterLite: the compiled core cannot run in a browser). Notebooks are not committed. The mechanism, settings, naming rules, template and "how to add a script" are in `DOCS_PLAN.md` section 10; only what concerns the teaching is repeated here.

Layout actually used (the proposal of the first version, `00_getting_started` and `NN_name.py`, was replaced):
```
examples/
  GALLERY_HEADER.rst        overview text of docs/tutorials/index.rst (written by docs/conf.py)
  01_getting_started/       GALLERY_HEADER.rst, plot_01_first_feature.py, plot_02_the_contract.py
  02_physical_signals/      plot_03_points.py, plot_04_images.py
  03_low_level/             plot_05_motion.py, plot_06_shape.py
  04_mid_level/             plot_07_gestures.py
  05_analysis_primitives/   plot_08_primitives.py, plot_09a_synchronization_signals.py, plot_09b_synchronization_events.py
  06_capstone/              plot_10_capstone.py
  helpers.py, requirements.txt (pyeyesweb, matplotlib, pandas, pooch)
  data/ (sensor data about 160 MB, videos removed), data_trimmed/ (git-ignored)
docs/tutorials/             generated and git-ignored: one gallery per folder + the overview
```
Rules the build relies on: `filename_pattern` `[/\\]plot_\d\d[ab]?_` (so `plot_09a_` and `plot_09b_` run; any other file, such as `helpers.py`, is not a tutorial: `ignore_pattern` `^(?!plot_)`); one gallery per layer folder (a folder needs `GALLERY_HEADER.rst` and one script), not one gallery with sub-sections (sphinx-gallery would pick up `examples/scratch/`); text blocks are reStructuredText (sphinx-gallery has no Markdown option); the downloaded notebook starts with a cell that installs `pyeyesweb[datasets] matplotlib pandas` and fetches `helpers.py` from a raw GitHub URL (`_HELPERS_URL` in `docs/conf.py`, on the `main` branch: pin it, T6). The old `examples/build.py` and `examples/check.py` no longer exist (their jobs: the gallery executes everything; the catalog-coverage and stale-name checks are the gate of `DOCS_PLAN.md` 11.2, not yet implemented).

## 2. The scratch scripts: used and done

`examples/scratch/` (`00_tour` to `08_humanoid` scripts and notebooks, `common.py`, `build.py`; git-ignored, never shipped) was the source material, written for a reviewer. Their content was rewritten into the tutorials (tour into 01 and 02, 01 into 03, 02 into 05, 03 into 06, 04 into 07, 05 into 08, 06 into 09a, 09b, 07 into 04, 08 into 03; `common.py` into `helpers.py` and `pyeyesweb.datasets`); `where`, `call_path`, `options` and `_snake` were dropped. Nothing is left to mine: delete the folder in T7 (it also contains a stale mention of `pyeyesweb._eyesweb_core`, `ALPHA_REVIEW.md` B21).

## 3. Curriculum as built

One script is one gallery page and one downloadable notebook; each has 2 to 3 exercises with solutions. Features listed are those named in the code cells of the script (checked 2026-10-16 with a script over `examples/*/plot_*.py` against `pyeyesweb.catalog()`; comments are ignored).

| # | Script | Teaches | Data | Features used |
|---|---|---|---|---|
| 01 | `01_getting_started/plot_01_first_feature.py` | load a trial, one feature with `run`, plot, `Recorder` (15 min) | trial 7, 4 to 19 s | `Kinematics`, `KineticEnergy` |
| 02 | `01_getting_started/plot_02_the_contract.py` | `process` vs `run`, `reset`, `Result` and `Schema`, `Status` and warm-up, `latest`, `parameters`, seconds and `sampling_rate`, m/mm, live vs structural parameters, `from_*`, skeleton presets, `catalog()` (25 min) | trial 7, 5 to 15 s | `Kinematics`, `KineticEnergy`, `Suddenness` |
| 03 | `02_physical_signals/plot_03_points.py` | hit cells, humanoid and mass-spring simulation, prediction, estimation, a real recording through `joint_map` (30 min) | trial 10, trial 7 (3 to 5.5 s for `joint_map`), synthetic swing | `HitCellDetector`, `HumanoidSimulator`, `HumanoidOrientations`, `GenericModelOrientations`, `GenericModelSimulator`, `GenericModelPredictor`, `GenericModelEstimator`, `PointsPredictor` |
| 04 | `02_physical_signals/plot_04_images.py` | the `IMAGE` input, silhouette centroids and body parts (`parts=`), videogram, pulses (20 min) | synthetic silhouettes, no video files | `SilhouetteCentroids`, `SilhouetteBodyParts`, `Videogram`, `BinaryPulsesRegularity` |
| 05 | `03_low_level/plot_05_motion.py` | velocity, energy, the smoothness family, noise, directness (30 min) | synthetic reaches and ellipses, trials 11 to 14, 21, 25 | `Kinematics`, `KineticEnergy`, `SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount`, `CurvatureDispersion`, `CurvatureVelocityCorrelation`, `MotionNoiseDetector`, `Directness`, `TrajectoryNonPlanarity` |
| 06 | `03_low_level/plot_06_shape.py` | contraction and expansion, symmetry, balance, direction change, contours (30 min) | trials 3 to 8, 10 to 14, 17 to 19 | `BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity`, `Symmetry`, `TriangleSymmetry`, `Equilibrium`, `DirectionChange`, `FilterContour`, `ContourCurvature`, `ConvexHull`, `BodyPartsFromCurvature` |
| 07 | `04_mid_level/plot_07_gestures.py` | segmenting gestures, suddenness, impulsivity, potentials (30 min) | trials 20 to 25, 0 to 24 s, trial 18 | `GestureSegmenter`, `MotionDuration`, `Suddenness`, `SuddennessImpulsivity`, `ContractionImpulsivity`, `PositionDependingPotentials`, `RegionDependingPotentials`, and `HitCellDetector`, `KineticEnergy`, `BoundingBoxFilledArea`, `MotionNoiseDetector` as inputs |
| 08 | `05_analysis_primitives/plot_08_primitives.py` | entropy across scales, rarity, peaks, periodicity, dominance (30 min) | trials 7, 11, 12, 20, 21, 24 | `SampleEntropy`, `CoarseGraining`, `MultiScaleEntropy`, `Rarity`, `Periodicity`, `ScalarPeakDetector`, `EnsembleDominance` (and `KineticEnergy`) |
| 09a | `05_analysis_primitives/plot_09a_synchronization_signals.py` | synchronization of continuous signals, trials 5 and 6 (25 min) | trials 5, 6, 5 to 21 s | `PhaseLockingValue`, `CorrelationsMatrix`, `PartialRecurrenceSynchronization`, `GeneralisedAutoCorrelation`, `NonlinearInterdependence`, `RecurrencePlot`, `CrossRecurrencePlot` |
| 09b | `05_analysis_primitives/plot_09b_synchronization_events.py` | event series, trials 7 and 8 (25 min) | trials 7, 8, 5 to 21 s | `ScalarPeakDetector`, `EventSynchronization`, `EventSynchronizationMECS`, `SpikeSynchronization`, `SequenceDetector`, `TemporalSynchronization`, `PhaseLockingValue` |
| 10 | `06_capstone/plot_10_capstone.py` | real-time loop with a live and a structural parameter change; a batch of features to a table (30 min) | trials 3 to 8 (5 to 21 s, trial 7 for the loop), 11 to 14 | `Kinematics`, `KineticEnergy`, `Symmetry`, `SpectralArcLength`, `MotionNoiseDetector`, `GestureSegmenter`, `MotionDuration`, `PhaseLockingValue` |

**Coverage.** All 60 catalog features are imported and used in at least one script: no catalog feature is missing from the tutorials (an automatic check of this is part of the gate, `DOCS_PLAN.md` 11.2). Caveat: "used" means named in a code cell, not explained at length; the thinnest are the features that appear only as one call in a larger pipeline (`BoundingBoxFilledArea` and `HitCellDetector` in 07, `Suddenness` in 02, `PhaseLockingValue` in 10). The tutorials that name a feature only in prose (without an import) do not feed the back-references.

Exercises: 2 to 3 per script in "Try it"; the solutions are ordinary executed cells under "Solutions" (the dropdown was skipped, maintainer 2026-10-15). Acceptance: every solution executes (it does: the build would fail otherwise).

## 4. Conventions

See `DOCS_PLAN.md` section 10 (template, rules, how to add a script, runtime and data rules). In short: one concept per section (text, minimal code, figure, one-sentence takeaway); public API only; plain, sober English; time in seconds and lengths with their unit stated (Qualisys raw data are millimetres); every class in prose has a role and is imported and used in code; header fields `:Goals:`, `:Prerequisites:`, `:Data:`, `:Time:`; budgets 60 s per script and 10 min in total from the `junit` output.

## 5. Data

State of `examples/data` (decided 2026-10-20: **videos are private and no longer in the repository** (moved to `../_private_data/videos`; `examples/data/videos/` is git-ignored); **the public data is sensor data only**): `qualisys/` 84 MB (22 trial TSVs: trials 3 to 8 and 10 to 25), `kinect/` 68 MB (`desktop.ini` removed), `imu/` 9 MB, `markers_mappings.json`, `README.md` (rewritten: files, units, rates, marker sets, the trial table of the session of 2024-03-26; one line says that video recordings are not distributed), `ConceptualModel.png`. The tutorials use **only the Qualisys trials and synthetic data**. **The licence and the performer consent of the sensor data are still the maintainer's to supply**: `examples/data/README.md` and `examples/GALLERY_HEADER.rst` carry a `TODO(maintainer)` marker, listed in `docs/_data/gate.yaml` so that a release build fails until it is resolved.

What exists:
- `pyeyesweb/datasets.py` (397 lines, needs no core): `load_qualisys_trial(n, start=, stop=)` returns a `QualisysTrial` (positions in mm, labels, sampling rate; `joint`, `window`, `to_units`, `task`, `condition`), `fetch_data_file`, `cache_dir`, `available_trials`, `BASE_URL`. Lookup order: `PYEYESWEB_DATA`, then `examples/data` of the checkout, then download with the optional `pooch` (extra `datasets`) and a SHA-256 check from `pyeyesweb/_datasets_registry.py`. **`BASE_URL` is `None`**: without a local copy the error says the data are not available online yet.
- `tools/trim_example_data.py` writes `examples/data_trimmed/` (git-ignored): the same TSV format, gzip-compressed, only the frames and markers the scripts need (the `PLAN` table in the tool lists the time range per trial and the script that needs it), the original time column kept, values copied as text, fixed gzip timestamp (reproducible sums); `--write-registry` writes the SHA-256 sums into the registry. Result: **14.86 MB in 21 files, against 84 MB of Qualisys TSVs** (`examples/data_trimmed` is 15 MB on disk). `PYEYESWEB_DATA=examples/data_trimmed` makes the scripts read it (the docs build still reads the full files).
- `docs/howto/load_data.md` explains the lookup to users.

What is open is section 9 (T6): host, licence and consent, which files stay in the repository, the final registry. **Update 2026-10-20: the data licence is the MIT licence of the repository (decided); the licence TODO markers are gone.**

## 6. Fate of the old public notebooks and helpers (the new tutorials replace them)

| Current (all still tracked) | Replacement | Action |
|---|---|---|
| `examples/01_sliding_window.ipynb`, `02_static_vs_dynamic.ipynb`, `03_dual_api.ipynb`, `04_output_contracts.ipynb` | tutorial 02 and the docs Concepts pages | delete |
| `examples/05_theoretical_framework.ipynb` | tutorials 05 to 09 and `docs/theory/framework.md` | delete |
| `examples/06_multimodal_capstone.ipynb` | tutorial 10 (it used IMU and kinect, which are not used by the tutorials) | delete |
| `examples/utils/data_loader.py`, `plot_utils.py` (tracked) | `examples/helpers.py` and `pyeyesweb.datasets` | delete (nothing imports them any more: check with grep) |
| `examples/scratch/` (git-ignored: scripts, 9 executed notebooks, `common.py`, `build.py`, `README.md`, `live_parameters_classification.md`) | tutorials 01 to 10 | delete locally after the maintainer agrees (never shipped) |
| `examples/requirements.txt` | already rewritten (`pyeyesweb`, `matplotlib`, `pandas`, `pooch`) | keep |
| any committed `*.ipynb` | none: the gallery generates the notebooks as downloads | do not commit notebooks |

`examples/build.py` and `examples/check.py` of the 1.x layout do not exist any more.

## 7. Work packages (status in the table at the top)

T0 to T5 are done. **T6** (data trim, `data/README.md`, licence, host upload): acceptance `examples/` below 30 MB in the repository (if the maintainer chooses to ship trimmed data) and checksums verified. **T7** (delete the old notebooks, utils and scratch; `examples/README.md` of one paragraph; link from the docs; docs-build checks; reader sign-off): acceptance, no reference to a deleted file (grep), gallery below 10 min, coverage check passes, maintainer and one student test-reader sign off. Order: T6 decisions, then T7.

## 8. Risks

- CI needs the compiled core (`ALPHA_REVIEW.md` 8.1) and, today, the full `examples/data` of the checkout (sensor data about 160 MB, videos removed), or `PYEYESWEB_DATA` pointing at the trimmed files; without a decision a CI clone is large.
- Execution on every build lengthens CI; seeded data, no network except the cached download, platform differences in numerical results (the text must not quote numbers to many digits; check the numbers printed in the tutorials on Linux and macOS when CI first runs).
- Data consent and licence unknown; trimmed files must still contain what the text claims (trial descriptions).
- Executed outputs live only in the build: no pre-rendered notebooks on GitHub.
- The downloaded notebooks fetch `helpers.py` from the `main` branch: a later change of the helpers breaks old notebooks until the URL is pinned to the release tag.

## 9. Remaining work: T6 and T7 (actionable)

Items marked **[maintainer]** need a decision. The others are for an agent.

| Done | Task | Acceptance |
|---|---|---|
| [ ] | **[maintainer]** Data host (Zenodo or OSF, or a GitHub release asset) and upload of the trimmed files; then set `datasets.BASE_URL` (currently `None`), regenerate the registry with `python tools/trim_example_data.py --write-registry` and test a download into an empty cache (`pooch` installed, no `examples/data`) | `load_qualisys_trial(7)` works in a clean environment without the checkout; `tests/unit_tests/test_datasets.py` still passes |
| [ ] | **[maintainer]** (the only open data item that is licence-related; videos are decided: private) Licence and performer consent for the sensor recordings; then add `examples/data/LICENSE` (for example CC BY 4.0) and a citation, fill the `TODO(maintainer)` lines of `examples/GALLERY_HEADER.rst` and `examples/data/README.md`, and lower their counts in `docs/_data/gate.yaml` | licence file present, the gallery index states how to cite the data | **Update 2026-10-20: the data licence is the MIT licence of the repository (decided); the licence TODO markers are gone.**
| [ ] | **[maintainer]** Decide which files stay in the repository: the trimmed `.tsv.gz` (14.9 MB) in place of the 84 MB of `examples/data/qualisys`; `kinect/` (68 MB) and `imu/` (9 MB), which no tutorial uses (move to the data host or keep); `videos/` is decided: private, out of the repository | repository `examples/` below 30 MB if the trimmed data replace the full ones; the sdist and wheel contain no data (`ALPHA_REVIEW.md` E5) |
| [x] | (done 2026-10-20) `examples/data/README.md` rewritten (sensor data only, units, rates, marker sets, trial table), `examples/data/kinect/desktop.ini` removed. Still open if the full files leave git: make `docs.yml` and `tests.yml` find the data (`PYEYESWEB_DATA`, or the download) | a clean clone builds the gallery in CI |
| [ ] | **[maintainer]** The raw URL of `helpers.py` in the notebook cell: pin `_HELPERS_URL` in `docs/conf.py` to the release tag (and check the owner and repository names in it) | a notebook downloaded from the built site runs from an empty folder |
| [x] | (done by the maintainer, 2026-10-20, commit 29f3676) The old notebooks, `examples/utils`, `examples/scratch` and `tests/benchmarks` are gone. `examples/README.md` is not written (optional) | grep over tracked files is empty |
| [ ] | The two plain "next tutorial" sentences: the last bullet of "Next steps" of `03_low_level/plot_05_motion.py` ("The next tutorial measures the shape of the body ...") and of `04_mid_level/plot_07_gestures.py` ("The next tutorial turns to the analysis primitives ...") become `:ref:` links (`sphx_glr_tutorials_03_low_level_plot_06_shape.py`, `sphx_glr_tutorials_05_analysis_primitives_plot_08_primitives.py`) | both link in the built page |
| [ ] | Update the findings of section 10 in the tutorials after the code items B1 to B7 (`ALPHA_REVIEW.md` 8.2) land | text and code agree |
| [ ] | Runtime table from the last full build: after a clean build (delete `docs/tutorials`) copy the times of `docs/sg_execution_times.rst` into the docs (the developer guide `building_the_docs.md`), or just record them in the release notes; the numbers of 2026-10-16 are in `DOCS_PLAN.md` 11.7 | every script under 60 s, total under 10 min on the CI runner (the local figure is 36.9 s) |
| [ ] | Check that every exercise solution still runs and prints what the text says (the build proves only that it runs); read the exercises of 02, 05, 07 and 10 once | no solution contradicts its question |
| [ ] | Sign-off: a student reads tutorials 01, 02, 05 and 10 on the built site (HTML and a downloaded notebook) and reports what was unclear; the maintainer signs off | written feedback addressed |
| [ ] | Gate: the stale-name grep and the catalog-coverage check run in the docs build (`DOCS_PLAN.md` 11.2) | adding a catalog feature that no script uses fails the build |

## 10. Findings in the tutorials that the final pass must reflect

The tutorials present every feature as working (decision 2026-10-15), so these are the places where the text is deliberately careful. Keep them true when the code items of `ALPHA_REVIEW.md` 8.2 change:

- `Suddenness` (tutorials 02 and 07): `alpha` is exactly 2 (the Gaussian case) in a window whose speeds have no heavy tail, so `beta` and `gamma` carry the detail; `beta` is not limited to [-1, 1] (B7); a still or constant-speed window is classified sudden (alpha 2, beta 0, gamma 0, rule `>= 0`: B7). `Suddenness`, `SuddennessImpulsivity` and `Directness` did not separate the example conditions (`OPEN_POINTS.md` section 4); the tutorials choose windows where they respond.
- `CurvatureVelocityCorrelation` (tutorial 05): shown on synthetic ellipses and paths where it is strongly negative when the speed follows the curvature; on the real trials it did not separate the conditions (mean about -0.43 against -0.49, `OPEN_POINTS.md` section 4). `velocity_threshold` has no effect and the thresholds act on per-sample velocity (B9). `Harmonicity` is about 1 for almost any signal (B14).
- `MotionNoiseDetector` (tutorials 05, 07, 10): with several joints only the alphabetically last joint name decides the flag (B8); `is_noisy` is passed directly to `GestureSegmenter` (flipped meaning, documented in `DEVELOPMENT_SPEC.md` I-a).
- Humanoid and model features (tutorial 03): a real recording through `joint_map` flutters over long stretches; the tutorial uses trial 7 from 3 to 5.5 s, where it does not (B10); the default damping is 10 (EyesWeb's 0.3 diverges on chains of four or five bones); the model is a pose generator, not a noise filter; `GenericModelEstimator` is fragile (B10).
- `ScalarPeakDetector` (tutorials 08 and 09b): it reports **maxima only**, once the fall that follows is in the buffer, and only when both the rise and the fall exceed `threshold` (a swing in the units of the signal, not a level): the marker comes up to `window` samples after the maximum; the minima are not marked.
- `EventSynchronization` and `EventSynchronizationMECS` (tutorial 09b): the counts accumulate over windows, so `hop` equals `window` and the value of a window describes the recording up to its end; `reset_every_buffer=True` (not available for MECS) makes the windows independent; `Q` depends strongly on `tau`; MECS has no `reset_every_buffer` and whether it should accumulate is open (B12). `SpikeSynchronization(mode="timings")` needs equal spike counts per train (B12).
- `Symmetry` (tutorial 06): `reference_type` is `"label"` only; the presets `qualisys_sport`, `mediapipe` and `openpose` are incomplete (B16): the tutorials name the reference joint (`reference_point="Neck"`) because `qualisys_sport` has none. Remove that explanation when B16 is done.
- `CoarseGraining` and windows with `hop` (tutorial 08): the series is produced on the first full window and then every `factor * hop` samples; the other windows are `NO_OUTPUT`.
