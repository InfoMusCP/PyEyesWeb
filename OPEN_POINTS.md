# PyEyesWeb port: notes that are still open

**Superseded by `ALPHA_REVIEW.md` section 8 (2026-10-16).** The master list of remaining work (packaging and release, the code and
core backlog B1 to B21, the final documentation pass, the data and the cleanup of the examples) is there; this file keeps only the
notes that are not part of it: the skeleton presets (section 3, B16 of the backlog), the analysis of features that did not separate
the example conditions (section 4) and the record of rules (section 6); the numbering of the old file is kept (sections 1, 2 and 5 are gone). Companion files: `DEVELOPMENT_SPEC.md`, `DOCS_PLAN.md`,
`TEACHING_PLAN.md`.

State on 2026-10-16: 60 features in `catalog()` (11 physical signals, 22 low-level, 7 mid-level, 1 high-level, 19 analysis
primitives); `pytest` 2963 passed and 12 skipped (34 passed without the compiled core); 92 doctests; the docs build with
warnings as errors, the Sphinx doctest builder (856 tests) passes and the ten tutorials run in about 37 s. Every correction decided
so far is implemented and recorded in the private notes `PORTING_STATUS.md` ("Corrected in the core", "Removed blocks",
"Deviations") and, for the public contract, in `DEVELOPMENT_SPEC.md`.

## 3. To fill in (yours)

Skeleton presets, `pyeyesweb/skeletons.py` (`SKELETON_TODO`, `Skeleton.missing()`): `qualisys_sport` needs the reference joint and the
weights; `mediapipe` needs the reference joint (it has no pelvis or neck landmark) and the weights; `openpose` needs the weights.
`kinect_v2` is complete. A missing weight silently becomes 1.0 for every joint, and a preset without reference joint makes
`Symmetry(method="ratio")` ask for `reference_point=`. When filled, remove the "incomplete" wording from the docs and from the
`Symmetry` error (backlog B16). The literature references for the metrics are tracked in `DOCS_PLAN.md` section 11.1.

## 4. To investigate later (analysis, not bugs)

Features that did not separate the example conditions: `CurvatureVelocityCorrelation` (mean about -0.43 against -0.49, wrong
direction in one of three pairs), `Harmonicity` (0.97 to 0.99 everywhere), `Suddenness`, `SuddennessImpulsivity` and `Directness` on
these recordings, and `PhaseLockingValue` on the vertical axis for clapping (the wrong axis for a horizontal movement: the
analysis, not the feature). The tutorials present these features as working (decision of 2026-10-15; the careful
places are listed in `TEACHING_PLAN.md` section 10). The first analysis was made in the scratch notebooks (git-ignored, to be deleted), so repeat it
with the trials of `examples/data`. A feature failing to separate two trials does not make it wrong: the trials are few and the pairs
may not differ in the measured quantity.

## 6. Record of rules decided

Docstrings are true and change with the behaviour they describe (`DEVELOPMENT_SPEC.md` section 9). New defaults that fix bugs are
kept (segmenter frame 9, humanoid damping 10, ...). Event-synchronization classes are not merged. One-letter locals in numerical
C++ are accepted as math notation. The humanoid features are kept (decided 2026-10-14); their `control` input takes the same
parent-relative directions as the extractor's output. A new catalog feature must pass the contract test
(`tests/unit_tests/test_contract_all_features.py`) and needs its entries in `docs/_data/families.yaml` (and `instantiation.yaml`).
Dropped (removed from the Python layer and the core, listed in the migration guide and under "Removed blocks" in the private notes):
`CannyEdgeDetector`, `Lightness`, `ZeroCross`, `Clusterability`, `StatisticalMoment`, the trajectory datatype and transforms,
`NoPreparationDetector(2)`, MECS v1, `EventSynchronizationRealTime`, `TauEstimator`, `ScalarBinarySyncDetector`, `SkeletonManipulator`,
OpenNI and the legacy device presets, and the TSV reader (replaced by `pyeyesweb.datasets`).

Local notes: scratchpad build folders and a stray folder named `c` at the root of the system drive (created by an agent by mistake;
a safety check blocked its deletion) are to be removed by hand. A Jupyter kernel that imports the core locks the compiled module on
Windows: restart kernels before the next rebuild of the core.

Moved to `ALPHA_REVIEW.md` section 8: signature generation (done in package D with `typing.get_type_hints`), the documentation pass
(done except WP9), packaging and deployment (8.1), the TouchDesigner CHOPs and the creatives site (8.6; the `chop/` folder is
ignored until then), the cleanup of `examples/` (8.4).
