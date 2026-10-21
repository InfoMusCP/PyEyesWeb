# Roadmap

Only what is still open or must be remembered. What was done is in git. Internal file: not in the sdist.

## 1. Release: 2.0.0a1 to the real release

In this order:

1. Core (private repository): add the macOS arm64 job to `wheels.yml` (dropped for the trial, no runner; GitHub Actions never ran macOS arm64).
2. PyPI and TestPyPI: real trusted publishers for `eyesweb-core` and `pyeyesweb` (workflow `pypi_deploy.yml` here, `wheels.yml` in the core), and the `pypi` environment in both repositories.
3. Delete the repository variable `CORE_FROM_TESTPYPI` (read by `tests.yml`, `docs.yml`, `linkcheck.yml`); then the three workflows install the core from PyPI.
4. Set the release date in the `CHANGELOG.md` heading and in `CITATION.cff` (`version`, and add `date-released`; there is none now).
5. Core licence: the technology-transfer office confirms Italian law and the Court of Genoa, and the legal name of the copyright holder, before the first public PyPI release. The core may become public later under another licence: then replace its `LICENSE`, the SPDX headers and `license` in its `pyproject.toml`.
6. `pyproject.toml`: `eyesweb-core>=2.0.0a1,<2.1` becomes `>=2.0,<2.1` once a stable core exists.
7. `docs/conf.py`: pin `_HELPERS_URL` (marker counted in `docs/_data/gate.yaml`, `open`) to the release tag.
8. Docs: a release build (`PYEYESWEB_DOCS_RELEASE=1`) must pass; it fails while `open` in `gate.yaml` is not empty.
9. Docs Pages: now served from the branch `gh-pages` (1.x at the root, 2.x in `v2-dev/`, pushed from `dev`). Switch the Pages source to "GitHub Actions", deploy at the root with `actions/upload-pages-artifact` and `actions/deploy-pages` (the job was removed), and decide where the 1.x site goes (a versioned folder or the gh-pages history).
10. Merge `dev` into `main` (planned: end of the year), tag `v*`, publish the GitHub release (publishing the release uploads to PyPI; a pushed tag uploads to TestPyPI).
11. Check in a fresh environment: `pip install --pre pyeyesweb` pulls the core and `catalog()` works without `EYESWEB_CORE_PATH`.
12. Data host: `datasets.BASE_URL` is `None` (Zenodo, OSF or a release asset), then regenerate the registry with `tools/trim_example_data.py --write-registry`. Decide whether the trimmed `.tsv.gz` files replace the full ones in the repository (`kinect/` and `imu/` are used by no tutorial).

## 2. Open decisions and questions for the maintainer

Original blocks (ask the original authors):

- `CurvatureVelocityCorrelation`: the intended thresholds and units; `velocity_threshold` is dead in the core.
- `EventSynchronizationMECS`: should it accumulate across windows (it does not, and has no `reset_every_buffer`)?
- `TemporalSynchronization`: the original formulas (`efficiency_step`, `progression`, `stage_weights`), and `CurvatureDispersion`.
- `Periodicity`: `threshold` and `sort_by_power`.
- `ScalarPeakDetector`: the exact delay semantics.

Other decisions:

- `Harmonicity` (about 1.0 for almost any signal): keep or drop.
- `Suddenness`: a still or constant-speed window is classified sudden (alpha 2, beta 0, gamma 0, rule `>= 0`); the maintainer will change the rule later.
- Skeleton presets to fill in `pyeyesweb/skeletons.py`: `qualisys_sport` (reference joint, weights), `mediapipe` (reference joint, weights), `openpose` (weights). Then remove the "incomplete" wording from the docs and from the `Symmetry` error.
- `EllipsoidSphericity.process_axes`: keep as a documented entry point or route it through the wrapper.

Core backlog (changes in the core, some need a regenerated reference):

- `MotionNoiseDetector`: with several joints only the alphabetically last joint decides; regenerate `gesture_segmenter_reference.npz` with `tools/regenerate_gesture_segmenter_reference.py` after a change.
- Humanoid integrator: flutters on real recordings (damping 5 to 30 worse, 60 gives `inf`); needs a stability review; `GenericModelEstimator` is fragile.
- Live windows for `Rarity(method="information")`, `Videogram`, `ScalarPeakDetector` need a `resize` in the core (then move them to LIVE in `test_live_window_hop.py`).
- Ragged spike trains in `SpikeSynchronization(mode="timings")` (equal counts required).
- Overflow (`1e300`): the block has advanced when `INVALID_INPUT` is returned; optional snapshot and rollback.

## 3. Documentation still to do

- Citations: features with no `References` section stay without them for now (the maintainer will add references in the future; add the entry to `docs/references.bib` first).
- Version switcher (pydata `switcher.json`, needs versioned deploys) and custom domain (`html_baseurl`): decide, together with item 9 of section 1.
- SVG sources of the EyesWeb logo and favicon (only PNG in `docs/assets/`).
- Check the links of `README.md`, and the weekly `linkcheck.yml` result once it has run on GitHub.
- Sign-off: a student reads tutorials 01, 02, 05 and 10 on the built site (HTML and a downloaded notebook); read the exercise solutions of 02, 05, 07 and 10 once.
- `DEVELOPMENT_SPEC.md`: the public-safe pass is done (rerun the grep of its section 10 before publishing). Decide how it is published: a "Contributing" page that includes it, or `CONTRIBUTING.md`. Then remove its status paragraph.

## 4. Later

- TouchDesigner wrapper and CHOPs: `EyesWebTD`, own repository (several CHOP sources name removed or renamed blocks).
- Creatives documentation site: own repository, no maths or citations, patches and screenshots, reusing the generated feature metadata.
- Analysis of the features that did not separate the example conditions (`CurvatureVelocityCorrelation`, `Harmonicity`, `Suddenness`, `SuddennessImpulsivity`, `Directness`, `PhaseLockingValue` on the vertical axis for clapping). The tutorials present them as working; a feature that fails to separate two trials is not necessarily wrong.
- A function-level pass for complexity and duplication.

## 5. Facts to remember

- Two repositories: the public pure-Python `PyEyesWeb` (MIT, `Copyright (c) 2025 InfoMusCP`) and the private core repository (C++, binary wheel `eyesweb-core`, licence `LicenseRef-InfoMus-Binary`). The public tree never contains C++ sources or the private URL. The core wheels are built by `wheels.yml` (cibuildwheel) in the private repository.
- Tag flow: a pushed tag `v*` builds and uploads to TestPyPI (both repositories); a published GitHub release uploads to PyPI; a manual run needs the workflow file on the default branch. 2.0.0a1 was tried on TestPyPI for both packages (macOS arm64 core wheel missing).
- Docs preview: every push to `dev` publishes to `v2-dev/` of `gh-pages`; pull requests only build.
- Known limits: the old videos (780 MB) are still in the git history before commit 29f3676 (no history rewrite decided; a clone is about 1.9 GB); the videos are private and `examples/data/videos/` is git-ignored. The data licence is the MIT licence of the repository.
- Rules: no behaviour change without a test; docstrings stay true; the live/structural table lives only in `docs/howto/realtime_live_parameters.md`; a new catalog feature needs the contract test and its entries in `docs/_data/families.yaml` and `instantiation.yaml`.
- Build and test (from the repository root; the core is a development build or the installed wheel):

```
export EYESWEB_CORE_PATH=<core build folder>
export PYTHONPATH="$EYESWEB_CORE_PATH:$PWD"        # ";" on Windows
python -m pytest -q
python -m pytest --doctest-modules pyeyesweb -q
python -m sphinx -b html -W --keep-going docs <output folder>
python -m sphinx -b doctest -q docs <output folder>
```
