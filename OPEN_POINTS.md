# PyEyesWeb port: what is still open

Updated 2026-10-14. State: catalog 60 features (low-level 20, analysis primitives 19, physical signals 12,
mid-level 8, high-level 1); pytest 2956 passed and 2 skipped (43 without the core); C++ tests 523; bindings checks
87; scratch notebooks 00 to 08 build with 0 errors. Everything you decided is implemented and recorded in
`EyesWebTD/PORTING_STATUS.md` ("Corrected in the core", "Removed blocks", "Deviations"). This file lists only what is
still open.

## 1. Waiting for a decision from you

Nothing. Resolved on 2026-10-14: (1) `skeletons.py` split (`Skeleton` in `data_models/skeleton.py`, `LabelGuard` in
`base/labels.py`, presets stay in the public `skeletons.py`, which re-exports `Skeleton`); (2) degenerate inputs
(`BoundingBoxFilledArea`, `Rarity` mode distance with NaN) are `INVALID_INPUT`, the `KineticEnergy` first frame stays
`OK`; (3) `CentroidsCalc` box-relative smoothing kept, the region-clipping guard deleted.

## 2. Memos to discuss with your colleague

Nothing to be discussed.

## 3. To fill in (yours)

Skeleton presets, `pyeyesweb/skeletons.py`: `qualisys_sport` needs the reference joint and the weights; `mediapipe`
needs the reference joint (it has no pelvis or neck landmark) and the weights; `openpose` needs the weights.
`kinect_v2` is complete. Literature references for the metrics go into the docstrings in the documentation pass
(`SpectralArcLength` already cites Balasubramanian 2015).

## 4. To investigate later (analysis, not bugs)

Features that did not separate the example conditions: `CurvatureVelocityCorrelation` (mean about -0.43 against
-0.49, wrong direction in one of three pairs), `Harmonicity` (0.97 to 0.99 everywhere), `Suddenness`,
`SuddennessImpulsivity` and `Directness` on these recordings, and `PhaseLockingValue` on the vertical axis for
clapping (the wrong axis for a horizontal movement: the analysis, not the feature). Where to look: scratch notebook
`02` section "Do the metrics separate the two conditions?", `04` section 8, `06` the comparison table. A feature
failing to separate two trials does not make it wrong: the trials are few and the pairs may not differ in the
measured quantity.

## 5. Deferred to the end

- **Signature generation:** the runtime signature code parses nanobind's signature strings with `ast`/`eval`;
  replace it with generated stubs or build-time data (packaging step).
- **Documentation pass (G):** docs pages, README, CHANGELOG, STRUCTURE_REVIEW, `mkdocs.yml`, `site/`, public example
  notebooks and benchmarks all still describe the old library; docstrings of untouched code that are now false;
  new pages for the imaging and humanoid features, the `IMAGE` input kind, `joint_map`, units, the time rule, the
  `from_*` constructors, the `high_level` layer and the dropped blocks.
- **Packaging and deployment (H):** pure Python wheel depending on the binary wheel `eyesweb-core` (built from the private EyesWebCore repository), version 2.0.0, Python
  pin, CI, license check for the imported MIT code.
- **TouchDesigner CHOPs:** addressed after packaging; the `chop/` folder is ignored until then (several CHOP sources
  already name removed or renamed blocks).
- **Artifacts** (review, architecture): stale, ignored for now.
- **Cleanup when you say:** `examples/scratch/` (personal review notebooks), scratchpad build folders (`sb`,
  `chop_b`, `xcheck`), and the stray folder `C:\c` (created by an agent by mistake; my safety check blocked its
  deletion, please remove it by hand).
- **Environment note:** `EyesWebTD/build/Release` is current; a Jupyter kernel that imports the core locks the
  `.pyd`, so restart kernels before the next rebuild.

## 6. Record of rules decided

Docstrings stay untouched until the documentation pass (D5). New defaults that fix bugs are kept (`#19`: segmenter
frame 9, humanoid damping 10, ...). Event-synchronization classes are not merged (D2). One-letter locals in numerical
C++ are accepted as math notation (F1). The humanoid features are kept (decided 2026-10-14); their `control` input now
takes the same parent-relative directions as the extractor's output. A new catalog feature must pass the contract test
(`tests/unit_tests/test_contract_all_features.py`). Dropped (all removed from the Python layer and the core, listed
under "Removed blocks"): `CannyEdgeDetector`, `Lightness`, `ZeroCross`, `Clusterability`, `StatisticalMoment`, the
trajectory datatype and transforms, `NoPreparationDetector(2)`, MECS v1, `EventSynchronizationRealTime`,
`TauEstimator`, `ScalarBinarySyncDetector`, `SkeletonManipulator`, OpenNI and the legacy device presets.
