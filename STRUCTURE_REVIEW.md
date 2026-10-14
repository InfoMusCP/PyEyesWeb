# Structure review notes

Decisions taken while reorganising the package by the conceptual model, to be reviewed with colleagues. Layers are a
conceptual model, not a strict pipeline; the table records where each feature **is placed today**, not where it
must stay. Guideline used: an *analysis primitive* is a metric applicable to any movement feature at any layer, not a
movement feature itself.

## 1. Features that straddle layers (placement chosen, to discuss)

| Feature | Placed in | Why it could also be elsewhere |
|---|---|---|
| `GetTrajectoryFeatures` (length, directness index) | Layer 3, `mid_level.directness` | Length of a trajectory is low level; directness of a gesture over seconds is mid level |
| `PositionDependingPotentials`, `RegionDependingPotentials` | Layer 3, `mid_level.space_occupation` | They accumulate occupation of space over time (mid level), but update per frame (low level) |
| `Periodicity` | Analysis primitive | A rhythm feature when applied to movement (mid level); the transform itself applies to any signal |
| `Curvature`, `ConvexHull`, `BodyPartsFromCurvature` | Layer 2, `low_level.shape` | Frame-level contour geometry, which could be Layer 1 (virtual sensor on a contour) |
| `GetAverageCurvature` (`AverageCurvature`) | Layer 2, `low_level.shape` (to relocate to `trajectory`) | 3D trajectory non-planarity / local plane distance; misfiled under shape contours |
| `Kinematics`, `GetKinematicalFeatures` | Layer 2 (decided) | Derivatives of a trajectory over a short window |
| `GestureSegmenter`, `MotionDuration` | Layer 3, `mid_level.segmentation` | Segmentation is frame-level, the segments it yields are mid level |
| `NoPreparationDetector(2)` (DANCE) | Layer 3, `mid_level.suddenness` | Event on a 3-sample peak (low level) judged against a gesture duration |
| `SkeletonManipulator`, `FilterContour`, `HitCellDetector`, trajectory generators | Layer 1 | Preprocessing / virtual sensors; could be "utilities" outside the model |
| Synchronization, recurrence plots, correlation matrices, `SequenceDetector`, `ZeroCross`, `ScalarPeakDetector`, `SampleEntropy`, `CoarseGraining`, `Rarity` | Analysis primitives | Applicable to features of any layer |

## 2. Same concept, different metric

Resolved while porting the native features to C++ (decisions of the maintainer):

| Concept | Outcome |
|---|---|
| Kinetic energy | one `KineticEnergy` (EyesWeb) with `input_mode` POSITION / VELOCITY; `VelocityKineticEnergy` removed. Atomicity: users can differentiate with `Kinematics` first |
| Ellipsoid sphericity | one `EllipsoidSphericity`; the PCA fit is inside (`process_points`), `axis_ratio` keeps the old metric; `EllipsoidFitSphericity` removed |
| Rarity | **to be merged into one `Rarity`** (maintainer decision): EyesWeb (user bin widths, -log(A*B) score) and `HistogramRarity` (adaptive bins, |mode - last| * probability gap). Neither is a special case of the other, so the merged class selects an algorithm; done together with the unified input contract (the two take different inputs today) |
| Impulsivity | **to be merged into one `Impulsivity`** (with `method="suddenness"` and `method="contraction"`): `SuddennessImpulsivity` becomes the trajectory method (autonomous wrapper, stripped of redundant intermediate outputs, fixed input asymmetry); `Impulsivity` becomes the contraction dynamics method, exposing `motion_threshold` (formerly hardcoded 0.01 in EyesWeb) alongside `peak_threshold` (see `IMPULSIVITY_DESIGN.md`). |
| Lightness | **Requires full review & redesign**: current formulation computes sliding-window `HistogramRarity` over the inverted vertical energy share, leading to inverted polarity (heavy bursts in light movement score high lightness), unbounded output, hardcoded vertical axis 1, and inability to separate experimental conditions (see `LIGHTNESS_DESIGN.md`). |
| Smoothness | **kept both**: `Smoothness` (EyesWeb) and `SpeedSmoothness`, reduced to SPARC, LDLJ, harmonicity and sub-movements. **To investigate**: better design / naming for the two curvature-based smoothness metrics (`CurvatureVelocitySmoothness` vs `CurvatureSmoothness`, see below) |
| Symmetry | **to be merged into one `Symmetry`** (maintainer decision): `GeometricSymmetry` (reflect the right joint, 3-D distance to the left one, one score per pair) and `SymmetryIndex3D` (per-axis ratio of left/right magnitudes with a sign condition, aggregated, global or per axis). Related, not nested; done together with the input contract. `TriangleSymmetry` stays separate (three points; to modernize with 2D/3D support, inversion to true symmetry, and vertex order invariance, see `TRIANGLE_SYMMETRY_DESIGN.md`) |
| Multi-scale entropy dominance | **to be decoupled**: introduce a standalone `MultiScaleEntropy` feature for single-subject/single-signal complexity analysis ($\text{SampEn}(\tau)$ curve and Complexity Index $\int \text{SampEn} d\tau$), and separate `EnsembleDominance` as a Layer 4 social interaction metric; resolve monolithic coupling in `MultiScaleEntropyDominance` (see `MULTISCALE_ENTROPY_DESIGN.md`). |
| Sample entropy | **Adaptive tolerance redesign**: replace the arbitrary absolute default $r=0.3$ (which blows up to `inf` for mm/s signals) with automatic standard-deviation scaling ($r = 0.2 \times \sigma$) when $r$ is omitted, guaranteeing scale invariance (see `SAMPLE_ENTROPY_DESIGN.md`). |
| Points density | EyesWeb replaces the Python one (superset) |
| Clusterability | **to be modernized & trajectory-adapted**: default `n_neighbors=2`, replace stochastic sampling with deterministic quasi-random/grid sequences to eliminate jitter across runs, and introduce trajectory arc-length decimation / landmark dwell-clustering to eliminate the continuous-curve artifact where all gestures score $H > 0.9$ (see `CLUSTERABILITY_DESIGN.md`). |
| Curvature | Ambiguity between `Curvature` (contour perimeter in `shape.py`) and trajectory curvature in `Kinematics(output_type="curvature")`. Rename contour feature to `ContourCurvature` to eliminate confusion (see `CURVATURE_ORGANIZATION_DESIGN.md`). |
| Gesture segmentation | `GestureSegmenter` embeds the entire `KineticEnergyIndex` internally. Decouple it to accept 1D energy/speed directly, eliminating redundant skeleton logic and enabling segmentation on arbitrary motion signals (see `GESTURE_SEGMENTER_DESIGN.md`). |
| Phase locking value | **Input contract & signal filtering redesign**: prevent silent truncation of channels ($C > 2$), raise an immediate validation error if number of signals $\ne 2$ or enforce an explicit bivariate signature `signal1, signal2` in `process()` and `run()`; address Hilbert transform collapse on broadband unfiltered motion (default bandpass or warning); see `PHASE_LOCKING_VALUE_DESIGN.md`. |
| Event synchronization | **Unification of the 6 event sync features**: merge `EventSynchronization`, `EventSynchronizationMECS (v1 & v2)`, `SpikeSynchronization`, and `TauEstimator` into a single, unified `EventSynchronization` class. Express $\tau$ as `tau: int | float | Literal["adaptive", "estimated"]` (`"adaptive"` for Kreuz 2015 ISI tolerance, `"estimated"` for minimum-distance heuristic), unify MECS kernels under `kernel: Literal["rectangular", "linear", "gaussian", "uniform"]`, and auto-dispatch based on channel count. Decouple `EventSynchronizationRealTime` into `EventSyncCounter` (see `EVENT_SYNCHRONIZATION_DESIGN.md`). |

Points to review (decided: leave as is, keep the TODO): `Suddenness.is_sudden` is `gamma * (1 - alpha / 2) * beta >= 0`, which reduces to `beta >= 0` (a TODO
already in the Python); `MultiScaleEntropyDominance` uses EyesWeb's sample-entropy counting (N-m templates) rather than the
Python's (N-m-1), hence O(1/N) differences.

## 3. Open points

* `pyeyesweb.eyesweb` is dissolved: every class is defined in its layer module (with its `@describe` decorator) and
  the layer packages import them directly; the base class is `pyeyesweb._core_feature.CoreFeature`.
* C++ stays organised by EyesWeb catalog (`motion`, `trajectory`, `space`, `sync`, `dance`).
* Layer 4 (`high_level`) is empty.
* `tests/benchmarks/direction_change_benchmark.py` passes arguments `DirectionChange` no longer has (pre-existing).
* `pyproject.toml` version is still 1.1.1; packaging of the C++ core into the wheel is not done.
* Python-origin metrics were not placed in a timescale more precise than the layer default.
* Input contract: defined (`docs/user_guide/input_contract.md`) and applied to every feature. To do: notebooks / benchmarks / docs pages on the new calls; merge `Symmetry` and `Rarity`; discuss `FeatureSet`.
* `Rarity` and `GestureSegmenter` keep state across `reset()` (faithful EyesWeb quirks), so `run` is only repeatable with `fix_reset_discretized` / `fix_reset_speed_history`.
* The compiled core is required by every feature (`pyeyesweb._core`); importing a layer package without it raises an `ImportError`.
* Factory constructors & input modality: drop `signal` in favor of `input_mode` (no backward compatibility) in `LogDimensionlessJerk` and introduce `@classmethod` factories (`.from_*`) on features that have `input_mode` (`KineticEnergy`, `Kinematics`, `LogDimensionlessJerk`), while keeping `method` parameters (`Symmetry`, `Rarity`) as constructor arguments (see `CLASSMETHOD_INPUT_MODE.md`).
* KineticEnergy algorithm: evaluate dropping the legacy `"bones"` modality to keep only points in Python, aligning with modern joint-array pipelines and simplifying the API (see `KINETIC_ENERGY_BONES_NOTE.md`).
* Curvature smoothness design: investigate a better architecture and naming for `CurvatureVelocitySmoothness` (power-law correlation from raw positions) and `CurvatureSmoothness` (geometric dispersion requiring manual velocity + acceleration vectors). Evaluate clearer naming or consolidation into a unified `PathSmoothness` class (see `CURVATURE_SMOOTHNESS_DESIGN.md`).
* TriangleSymmetry modernization: upgrade to support both 2D and 3D points (intrinsic plane projection or projection plane), invert the index to a true symmetry score (`symmetry = 1.0 - asymmetry`), and make the calculation invariant to input vertex order (auto-apex detection); see `TRIANGLE_SYMMETRY_DESIGN.md`).
* Equilibrium redesign: simplify by delegating floor-plane projection to the user (accepting 3 2D points: `left_foot`, `right_foot`, `barycenter`), eliminating the confusing `axes` coordinate-trap parameter and `*_idx` row indices, with an optional high-level `.from_skeleton` helper; see `EQUILIBRIUM_DESIGN.md`).
* DirectionChange redesign: accept standard 1D point frames `(D,)` and 2D trajectories `(T, D)` directly without artificial `[:, None, :]` dummy signals axes; drop the redundant `dims` parameter and `InferredDims` complexity by averaging multi-signal frames upon ingest; see `DIRECTION_CHANGE_DESIGN.md`).
* Curvature organization: rename generic `Curvature` in `shape.py` to `ContourCurvature` to clearly distinguish 2D silhouette boundary curvature from trajectory path curvature in `Kinematics(output_type="curvature")`; evaluate adding a first-class `TrajectoryCurvature` feature; see `CURVATURE_ORGANIZATION_DESIGN.md`).
* AverageCurvature relocation & renaming: move out of `low_level.shape` (it is a 3D trajectory feature, not a 2D contour metric) to `low_level.trajectory`, and rename to accurately describe what it measures (3D local plane deviation / non-planarity, e.g. `TrajectoryNonPlanarity` or `OutOfPlaneDeviation`, not geometric curvature or smoothness); see `CURVATURE_ORGANIZATION_DESIGN.md`).
* GestureSegmenter decoupling: remove embedded `KineticEnergyIndex` from `GestureSegmenter` so it operates as a pure 1D signal segmenter (accepting pre-computed energy or speed), eliminating redundant skeleton code and enabling segmentation from any signal (total energy, hand speed, etc.); see `GESTURE_SEGMENTER_DESIGN.md`).
* Unified Impulsivity & SQOM threshold: merge `Impulsivity` and `SuddennessImpulsivity` into a single `Impulsivity` class with `method: Literal["suddenness", "contraction"]` (and `.from_trajectory` / `.from_contraction` classmethods); expose the hardcoded `kMotionThreshold = 0.01` from EyesWeb C++ as a configurable `motion_threshold` parameter alongside `peak_threshold`; simplify `suddenness` output schema by removing redundant intermediate values (see `IMPULSIVITY_DESIGN.md`).
* Lightness full review & redesign: current formulation computes local rarity over inverted vertical kinetic energy share, leading to inverted polarity (heavy bursts in light windows score high), unbounded output, hardcoded vertical axis 1 (breaks on z-up datasets), and failure to discriminate expressive conditions in empirical testing; requires comprehensive theoretical and architectural redesign (see `LIGHTNESS_DESIGN.md`).
* SampleEntropy adaptive tolerance: automatically set tolerance $r = 0.2 \times \text{std}(\text{window})$ when $r$ is omitted (`tolerance=None`), eliminating the arbitrary default $r=0.3$ and ensuring scale-invariance across arbitrary physical units (see `SAMPLE_ENTROPY_DESIGN.md`).
* MultiScaleEntropy decoupling & standalone feature: introduce a standalone `MultiScaleEntropy` class for single-subject complexity analysis (returning the multiscale curve and Complexity Index without ensemble baggage), and separate `EnsembleDominance` as a dedicated multi-agent social metric (see `MULTISCALE_ENTROPY_DESIGN.md`).
* Clusterability trajectory adaptation: provide `n_neighbors=2` default, replace pseudo-random uniform points with deterministic low-discrepancy/grid sampling, and introduce arc-length subsampling or landmark dwell-clustering to break the trivial continuous-curve artifact where all trajectories score $H > 0.90$ (see `CLUSTERABILITY_DESIGN.md`).
* PhaseLockingValue input contract & strange results: address the silent truncation bug where $C > 2$ channels are dropped without warning (causing single-hand 3D trajectories $(x, y, z)$ to silently compute PLV between $X$ and $Y$); either raise an immediate `ValueError` if the number of signals is not exactly 2 or adopt an explicit bivariate signature `process(signal1, signal2)` and `run(signal1, signal2)`; resolve empirical anomalies where unfiltered signals glue to 1.0 or unsynchronized clapping scores higher than synchronized by establishing default bandpass pre-filtering ($0.5 - 5.0\text{ Hz}$) and spatial axis awareness (see `PHASE_LOCKING_VALUE_DESIGN.md`).
* Unified EventSynchronization architecture: merge the fragmented suite (`EventSynchronization`, `EventSynchronizationMECS`, `SpikeSynchronization`, and `TauEstimator`) into a single `EventSynchronization` class; support `tau: int | float | Literal["adaptive", "estimated"]` (`"adaptive"` for Kreuz 2015 ISI tolerance, `"estimated"` for minimum-distance heuristic), unify MECS kernels under `kernel: Literal["rectangular", "linear", "gaussian", "uniform"]`, and automatically dispatch between pairwise ($N=2$) and multi-class/ensemble ($N \ge 2, M \ge 1$) schemas while keeping C++ kernels untouched; decouple `EventSynchronizationRealTime` into `EventSyncCounter` (see `EVENT_SYNCHRONIZATION_DESIGN.md`).


