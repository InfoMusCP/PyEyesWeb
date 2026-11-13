# Migrating from 1.x

PyEyesWeb 2.0 is a new library with the same aim as 1.x. It keeps the names of some features, but the call contract, the
results, the parameters and the installation are different, and several features were removed. This page lists what changed
and how to translate a 1.x script. "1.x" is the 1.1.1 release; "development" is an intermediate state of the work on 2.0 (some
names that were in use only there are listed too, because notebooks and notes written during the development use them).

```{note}
`pip install pyeyesweb` installs 2.x. To keep a 1.x script running unchanged, install `pyeyesweb<2`.
```

## What changed in one page

**The contract.** In 1.x a feature was called with a `SlidingWindow` (`feature(window)`) or with an array
(`feature.compute(array)`), and returned a feature-specific `FeatureResult` that could hold `None`. In 2.0 every feature
declares its `inputs`, its `outputs` (a `Schema`) and its `parameters` before it sees data, and has the same three methods:

- `process(*sample, timestamp=None)` takes one sample or frame and returns an immutable `Result`;
- `run(*recording, timestamps=None, reset=True)` takes a whole recording and returns a `Recorder`, with the numbers of a loop
  of `process`;
- `reset()` clears the state.

A feature that works on a window owns its buffer (`window`, `hop`): there is no `SlidingWindow` to fill. A result has a
`status` (`OK`, `WARMING_UP`, `NO_OUTPUT` or `INVALID_INPUT`), a `reason`, a `timestamp` in seconds and one attribute per
declared output; a value that was not produced is `NaN`, `0` or `False`, never `None`. `latest` holds the last `OK` result
(`None` before the first one). See {doc}`concepts/inputs` and {doc}`concepts/results`.

**The model.** Features live in the packages of the layers of the conceptual model (`physical_signals`, `low_level`,
`mid_level`, `high_level`, `analysis_primitives`), and `pyeyesweb.catalog()` lists the {{ n_features }} of them. Time is in
seconds, always passed as the keyword `timestamp` or `timestamps`; a rate is `sampling_rate` in hertz and has no default.
Choices are lower-case strings, not enums. Joints are named (`labels=` or a `skeleton=` preset), not numbered. A parameter has
one spelling in the whole library. See {doc}`concepts/time_units_parameters`.

**The install.** The features run in a compiled core, the Python module `eyesweb_core`, which is a separate package from
`pyeyesweb`. `pip install pyeyesweb` brings both; to work from a clone with a development build of the core,
`EYESWEB_CORE_PATH` points at it (see {doc}`getting_started/install`). `import pyeyesweb`, `pyeyesweb.data_models` and the
enumerations `Layer` and `Timescale` work without the core; `pyeyesweb.catalog()` and the layer packages do not.

## Five common usages, before and after

The "before" code is 1.x (or development) code; it does not run with 2.0 and is not tested. The "after" blocks are run when the
documentation is tested.

### A window of samples

Before (1.x): a `SlidingWindow` is filled by hand and passed to the feature.

```text
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import DirectionChange

feature = DirectionChange(epsilon=0.5, num_subsamples=20, metrics=["cosine"])
window = SlidingWindow(max_length=20, n_signals=1, n_dims=2)
for point in trajectory:                  # one (x, y) per sample
    window.append(point)
    result = feature(window)              # or feature.compute(window_array)
    if result.is_valid:
        print(result.cosine)
```

After: the feature owns the window, and the first calls say that they are warming up.

```{doctest}
>>> from pyeyesweb.low_level import DirectionChange
>>> angle = np.linspace(0, 2 * np.pi, 60)
>>> trajectory = np.c_[np.cos(angle), np.sin(angle)]       # one (x, y) point per row
>>> feature = DirectionChange(window=20, metrics=["cosine"], epsilon=0.5)
>>> feature.process(trajectory[0])
DirectionChangeResult(status=WARMING_UP, reason='1 of 20 samples', cosine=nan)
>>> recording = feature.run(trajectory)                    # the whole recording in one call
>>> recording
Recorder(DirectionChange, rows=60, columns=['cosine'], status={'OK': 41, 'WARMING_UP': 19})
>>> round(float(recording[-1].cosine), 4)
0.6441
>>> round(float(feature.latest.cosine), 4)                 # the last OK result
0.6441
```

### Smoothness of a speed profile

Before (1.x; `SpeedSmoothness` in development): one class computes up to seven metrics from a window of speeds.

```text
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import Smoothness

smoothness = Smoothness(rate_hz=50.0, metrics=["sparc", "ldlj_v"])
window = SlidingWindow(max_length=60, n_signals=1, n_dims=1)
for speed in speeds:
    window.append(speed)
    result = smoothness(window)
    if result.is_valid:
        print(result.sparc, result.ldlj_v)
```

After: one class per metric, each with a required `sampling_rate`.

```{doctest}
>>> from pyeyesweb.low_level import SpectralArcLength, LogDimensionlessJerk
>>> rate = 50.0
>>> time = np.arange(150) / rate
>>> speed = 0.6 * np.exp(-0.5 * ((time - 1.5) / 0.4) ** 2)
>>> sparc = SpectralArcLength(window=60, sampling_rate=rate)
>>> ldlj = LogDimensionlessJerk(window=60, sampling_rate=rate, input_mode="velocity")
>>> sparc.outputs, ldlj.outputs
(Schema(Output('spectral_arc_length')), Schema(Output('log_dimensionless_jerk')))
>>> first = sparc.run(speed, timestamps=time)[-1]
>>> second = ldlj.run(speed, timestamps=time)[-1]
>>> first.status.name, second.status.name
('OK', 'OK')
```

`jerk_rms` and `samp_en` are gone: use `Kinematics(output_type="jerk")` and `SampleEntropy`.

### Synchronization

Before (1.x): one class on a window of several signals, with a dictionary of filter parameters.

```text
from pyeyesweb.analysis_primitives import Synchronization

sync = Synchronization(filter_params={"low": 1.0, "high": 10.0})
result = sync.compute(window_data)        # (time, signals, dims); result.plv
```

After: `PhaseLockingValue` takes the two signals as two inputs; the filter band is in hertz and needs `sampling_rate`.

```{doctest}
>>> from pyeyesweb.analysis_primitives import PhaseLockingValue
>>> rng = np.random.default_rng(0)
>>> time = np.arange(500) / 50.0
>>> first = np.sin(2 * np.pi * 1.0 * time)
>>> second = np.sin(2 * np.pi * 1.0 * time + 0.5) + 0.1 * rng.normal(size=500)
>>> plv = PhaseLockingValue(window=200, hop=50, low_frequency=0.5, high_frequency=3.0, sampling_rate=50.0)
>>> plv.inputs
Inputs(first_signal: sample (1) - one value per call, second_signal: sample (1) - one value per call)
>>> recording = plv.run(first, second)
>>> recording
Recorder(PhaseLockingValue, rows=500, columns=['phase_locking_value'], status={'OK': 7, 'WARMING_UP': 199, 'NO_OUTPUT': 294})
>>> round(float(recording[-1].phase_locking_value), 3)
0.996
```

### Choices: strings instead of enums

Before (development): a choice was a member of an enumeration.

```text
from pyeyesweb.low_level import KineticEnergy, KineticEnergyInputMode

energy = KineticEnergy(labels=labels, input_mode=KineticEnergyInputMode.VELOCITY)
```

After: a lower-case string, checked against the allowed choices; a constructor `from_velocity` is a shorthand.

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy
>>> weights = {"hand": 1.0}
>>> energy = KineticEnergy(labels=["hand"], weights=weights, input_mode="velocity")
>>> energy.parameters["input_mode"]
'velocity'
>>> KineticEnergy.from_velocity(labels=["hand"], weights=weights).parameters["input_mode"]
'velocity'
>>> KineticEnergy(labels=["hand"], weights=weights, input_mode="speed")
Traceback (most recent call last):
    ...
ValueError: input_mode: invalid value 'speed'; choose one of 'position', 'velocity'
>>> energy.process(np.array([[3.0, 4.0, 0.0]])).kinetic_energy      # half of the weight times the squared speed
12.5
```

### Joints: names and presets instead of indices

Before (1.x): joints are positions in the array, and the reference is an index.

```text
from pyeyesweb.low_level import GeometricSymmetry

symmetry = GeometricSymmetry(joint_pairs=[(4, 8)], center_of_symmetry=0)   # Kinect v2 indices
result = symmetry.compute(frame)          # frame: (n_joints, 3); result.pairs = {...}
```

After: a skeleton preset names the joints, and the pairs are pairs of names. The output is a score per pair, not an error
(see the table of behaviour changes).

```{doctest}
>>> from pyeyesweb.low_level import Symmetry
>>> frame = np.zeros((25, 3))                                  # the 25 joints of the Kinect v2 preset
>>> frame[4], frame[8] = (-0.2, 1.4, 0.0), (0.25, 1.4, 0.0)    # ShoulderLeft, ShoulderRight
>>> symmetry = Symmetry(skeleton="kinect_v2", method="reflection",
...                     pairs=[("ShoulderLeft", "ShoulderRight")], reference_point="SpineBase")
>>> symmetry.process(frame)
SymmetryResult(status=OK, pair_symmetry=[0.9824])
```

Presets are `kinect_v2`, `qualisys_sport`, `mediapipe` and `openpose`; see {doc}`howto/map_skeleton` to map your own.

## Renamed and removed names

"1.x" in the second column means the name existed in the 1.1.1 release; "development" that it existed only in an intermediate
state of the work on 2.0. Every old name was checked: it is not importable from 2.0, and every new name exists in the current
release.

### The call contract and the data model

| Old | From | New |
|---|---|---|
| `SlidingWindow` (`append`, `to_tensor`, `to_flat_array`, `is_full`, `max_length`) | 1.x | removed: a windowed feature buffers its own samples (`window`, `hop`), a whole recording goes to `run` |
| `BaseFeature`, `StaticFeature`, `DynamicFeature` | 1.x | `Feature` and `WindowedFeature` in `pyeyesweb.data_models`; a frame feature has no window |
| `feature(sliding_window)` and `feature.compute(array)` | 1.x | `feature.process(*sample, timestamp=None)` for one sample or frame; `feature.run(*recording, timestamps=None, reset=True)` for a recording |
| `process_series`, `push_trajectory`, `process_trajectory`, `process_points`, `process_samples`, `to_tensor` | development | `process` and `run`; `Kinematics.from_series()` takes a series. One public exception: `EllipsoidSphericity.process_axes(first_axis, second_axis, third_axis)`, the former `process(a, b, c)` |
| `FeatureResult` and the per-feature result classes | 1.x | `Result`, immutable, with a subclass `<Feature>Result` built from `feature.outputs` |
| `result.is_valid` | 1.x | `result.ok`, `result.status` and `result.reason`; `is_valid` stays as an alias of `ok` |
| `None` for a value that was not computed | 1.x | `NaN`, `0` or `False`, with `result.valid[name]`; array shapes do not change between calls |
| `result.to_flat_dict(prefix)`, which dropped the `None` fields | 1.x | `to_flat_dict(prefix="", meta=True)`: the same keys on every call, plus `status` (an integer) and `timestamp` |
| `Result.t`, `process(..., t=None)`, `run(..., ts=None)`, `creation_time` in 100 ns ticks | development | `Result.timestamp`, `process(..., timestamp=None)`, `run(..., timestamps=None)`, in seconds, `NaN` when unknown |
| `rate_hz` (default 50.0 or 25.0) | 1.x, development | `sampling_rate` in hertz, default `None` everywhere; the five window metrics (`SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount`, `CurvatureVelocityCorrelation`) require it |
| `time_mode`, `TimeMode`, `TICKS_PER_SECOND` | development | removed: the step comes from `timestamp` or from `sampling_rate` |
| the boolean flags `fix_*` | development | removed: the corrected behaviour is the only behaviour |
| enumeration parameters (`KineticEnergyInputMode.VELOCITY`, ...) | development | lower-case strings (`input_mode="velocity"`) and the `from_*` constructors |
| groups of boolean switches (14 in `SilhouetteCentroids`, 6 in `SilhouetteBodyParts`, 4 in `RegionDependingPotentials`) | development | `parts=[...]`, a validated sequence of part names |
| `str(Status.OK)` printing `0` | development | `str(Status.OK)` is `"OK"`; `int(Status.OK)` is still 0 |
| `result`, `no_output`, `finite_result`, `INPUTS`, `OUTPUTS` on the feature classes | development | private (`_result`, `_INPUTS`, ...); the public contract is `inputs`, `outputs`, `parameters` |
| `pyeyesweb.Smoothness`, `pyeyesweb.Synchronization` (top-level exports) | 1.x | removed: import from the layer package (`pyeyesweb.low_level`, `pyeyesweb.analysis_primitives`) |
| the package `pyeyesweb.eyesweb`; the aliases `KineticEnergyIndex`, `PeriodicityIndex`, `ImpulsivityIndex`, `RarityIndex`, `SmoothnessIndex`, `TriangleSymmetryIndex`, `TrajectoryFeatures` | development | removed: see "Names of the EyesWeb blocks" below |
| `pyeyesweb.utils.math_utils` (`compute_sparc`, `compute_ldlj`, `compute_jerk_rms`, `compute_sample_entropy`, `compute_harmonicity_index`, `compute_submovement_count`, `normalize_signal`, ...) and `pyeyesweb.utils.signal_processing` (`bandpass_filter`, `compute_hilbert_phases`, `apply_savgol_filter`, ...) | 1.x | removed; the calculations are behind the features; `pyeyesweb.utils` is internal |
| `TSVReader` (`pyeyesweb.utils.tsv_reader`) | 1.x | removed: reading files is not part of the library; the example recordings of the tutorials are loaded by {doc}`pyeyesweb.datasets <api/datasets>` |

### Features of 1.x

| Old (1.x) | New | What changed |
|---|---|---|
| `Smoothness(rate_hz, metrics=[...])` | `SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount` | one class per metric, taking the signal it is defined on (a speed profile or an acceleration, computed with `Kinematics`). Outputs: `sparc` is `spectral_arc_length`; `ldlj_v` and `ldlj_a` are `log_dimensionless_jerk` with `input_mode="velocity"` or `"acceleration"`; `harmonicity`; `n_submovements` is `submovement_count`. Parameters: `rate_hz` is `sampling_rate` (required); `sparc_amplitude_threshold` is `amplitude_threshold`; `sparc_min_fc`, `sparc_max_fc` are `minimum_cutoff_frequency`, `maximum_cutoff_frequency`. `use_filter` is gone. `jerk_rms` and `samp_en` are removed: use `Kinematics(output_type="jerk")` and `SampleEntropy` |
| `Synchronization(filter_params=...)` | `PhaseLockingValue(window, hop, low_frequency, high_frequency, sampling_rate)` | output `plv` is `phase_locking_value`; the filter band is in hertz and needs `sampling_rate` |
| `Rarity(alpha)` | `Rarity(method, number_of_inputs, window, bins, hop, alpha)`, `method` being `"information"` or `"mode_distance"` | the EyesWeb block replaces the 1.x implementation; the two compute different quantities |
| `MultiScaleEntropyDominance(m, r, max_scale, min_points, methods=[...])` | `MultiScaleEntropy` (one complexity index per participant: `embedding_dimension`, `tolerance`, `max_scale`, `minimum_points`) and `EnsembleDominance` (high-level: takes the complexity indices, gives `dominance_score`, `leader_index`, `leader_complexity`) | split in two features |
| `KineticEnergy(weights, labels)`; result `total_energy`, `component_energy`, `joints` | `KineticEnergy(labels or skeleton, weights, input_mode, reference_point, sampling_rate)`; output `kinetic_energy` | only the total remains; `weights` is a mapping from label to weight (a sequence is one weight per label) |
| `GeometricSymmetry(joint_pairs, center_of_symmetry)`; result `pairs` | `Symmetry(method="reflection", pairs=..., reference_point=...)`; output `pair_symmetry`, an array with one value per pair | joint names instead of indices; `reference_point=None` is the barycentre of the frame |
| `Equilibrium(left_foot_idx, right_foot_idx, barycenter_idx, margin_mm, y_weight, axes)`; result `value`, `angle` | `Equilibrium(margin, y_weight, units)` with the three inputs `left_foot`, `right_foot`, `barycenter`; outputs `equilibrium`, `angle` | no indices: pass the three points; `margin` is in metres (the default 0.1 is the former 100 mm) |
| `DirectionChange(epsilon, num_subsamples, metrics)` | `DirectionChange(window, hop, epsilon, number_of_subsamples, metrics)` | `window` and `hop` are parameters; one trajectory per call |
| `Suddenness(algo="new")` | `Suddenness(window, hop, dims)` | `algo="new"` is the constrained fit, the only one; one `(dims,)` point per call |
| `Impulsivity(direction_change_epsilon, suddenness_algo)`; result `impulsivity_index`, `direction_change_val`, `is_sudden` | `SuddennessImpulsivity(window, hop, dims, direction_change_epsilon, method)`; output `impulsivity_index` | the intermediate values are gone; the EyesWeb `ImpulsivityIndex` is a different feature, `ContractionImpulsivity` |
| `BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity` (one shared `ContractionExpansionResult`) | same names | each feature declares its own outputs: `contraction_index`; `sphericity`, `axis_ratio`, `radii`; `density`, `centroid` |

### Parameters and outputs of the feature review

These names existed in the development states and were renamed or removed by the review of the definitions. A lag in
samples is `lag` (one shift) or `max_lag` (the largest shift considered).

| Old | From | New |
|---|---|---|
| `EventSynchronization(tau=...)`, `EventSynchronizationMECS(tau=...)` | development | `max_lag`: two events are coupled when `0 < lag <= max_lag` |
| `EventSynchronization(weighted=...)` | development | removed: every matched pair counts 1 |
| `GeneralisedAutoCorrelation(tau=...)`, `tau_min`, `tau_spread`, `set_tau_min()` | development | `lag` for `output_type="scalar"`; `max_lag` for the curve, which holds the lags 1 to `max_lag` (`tau_spread=n` with `tau_min=1` is `max_lag=n`); a first lag above 1 is not offered |
| `CrossRecurrencePlot(multiple_epsilons=..., use_multiple_epsilons=...)` | development | removed: one `epsilon` for every row; `RecurrencePlot` keeps the per-row thresholds |
| `Suddenness` output `is_sudden`; `Suddenness(method=...)` with `"quantile"` | development | removed: the outputs are `alpha`, `beta` and `gamma`, and the fit is the constrained one, so `method` is gone |
| `CurvatureVelocityCorrelation(velocity_threshold=...)` | development | removed: the block never read it |
| `BodyPartsFromCurvature`: the fixed tracking threshold 0.05; `number_of_points=0` refused | development | `tracking_distance` (default 0.05, in the unit of the contour); `number_of_points=0` is accepted (no maxima, all the minima), as documented |
| `TrajectoryNonPlanarity(output_type="curvature_value")`, output `curvature`; `TrajectoryNonPlanarity(nan_value=...)` | development | removed: the output is always `curvature_radius` (the inverse of this distance has no geometric meaning); an undefined result is `INVALID_INPUT` instead of a marker value |
| `HumanoidSimulator(...)` | development | `MassSpringSimulator(...)` (`model="humanoid"`, the default); the input `skeleton` is `joints` and `control` is `directions`; the result also holds the `directions` |
| `HumanoidOrientations(...).process(skeleton).directions` | development | `MassSpringSimulator(units=...).process(joints).directions` |
| `GenericModelSimulator(model, ...).process(directions)`, output `positions` | development | `MassSpringSimulator(model=model, ...).process(joints)` takes the positions of the masses and reads the bone vectors itself; the bone vectors can still be given, `process(joints, directions)`; the output is `joints` |
| `GenericModelOrientations(model).process(skeleton).directions` | development | `MassSpringSimulator(model=model, units=...).process(joints).directions` |
| `MotionDuration(sampling_rate=..., continuous_output=...).run(is_gesturing)` | development | `GestureSegmenter(sampling_rate=..., continuous_output=...)`: the outputs `motion_duration` and `pause_duration` of the segmenter, measured on its own segmentation |
| `GestureSegmenter.process(intensity, noise)`, input `noise` | development | removed: `process(intensity)`; the noise test is held back and will return inside the segmenter |

### Held back from this release

Kept in the code and investigated for the next release, these features are not exported by their layer package and are not in
`catalog()`: `MassSpringSimulator` (with `MassSpringModel`, `HUMANOID_JOINTS` and `HUMANOID_BONES`), `Harmonicity`,
`MotionNoiseDetector` (its noise test returns inside `GestureSegmenter` later), `Suddenness`,
`SuddennessImpulsivity`, `ContractionImpulsivity`, `PositionDependingPotentials`, `RegionDependingPotentials`,
`NonlinearInterdependence` and `SpikeSynchronization`. The rows that name them below describe the state they will return in.

### Removed features

| Removed | From | Use instead |
|---|---|---|
| `Lightness` | 1.x | removed; its formula is not a valid lightness measure and a redesign is deferred |
| `Clusterability` (Hopkins statistic) | 1.x | removed |
| `StatisticalMoment` | 1.x | `numpy` and `scipy.stats` (`mean`, `std`, `skew`, `kurtosis`) |
| `ZeroCross` | development | `numpy`: count the sign changes, `np.count_nonzero(np.diff(np.sign(x)))` |
| `CannyEdgeDetector` | development | OpenCV, `cv2.Canny` |
| `SkeletonManipulator`, OpenNI and the legacy device presets (`input_type`, `skeleton_mode`), the Bones `algorithm` of `KineticEnergy` | development | `skeleton=` with a preset or your own `Skeleton` |
| `NoPreparationDetector`, `NoPreparationDetector2` | development | removed |
| MECS algorithm v1 (`version=`), `EventSynchronizationRealTime`, `TauEstimator`, `ScalarBinarySyncDetector` | development | `EventSynchronizationMECS` is the former version 2 only |
| the trajectory datatype and its blocks (`Trajectory`, `TrajectoryBuilder`, `GetKinematicalFeatures`, `KinematicalFeatures`, `NumericDerivative`, the `Trajectory` input mode of `Kinematics`) | development | `Kinematics` on plain arrays (`from_point`, `from_series`); `Directness` and `TrajectoryNonPlanarity` take `(n, D)` arrays of points, row 0 the newest |
| the transforms of `GeometricTrajectory3D` (`rotation_matrix`, `rotate_x`, `rotate_y`, `rotate_z`, `rotate`, `scale`, `translate`, `rescale_in_range`, `remap_axis`, `convert_on_2d`) | development | `numpy` |
| `VelocityKineticEnergy`, `EllipsoidFitSphericity` | development | `KineticEnergy(input_mode="velocity")` (or `KineticEnergy.from_velocity`); `EllipsoidSphericity().process(points)`, where `axis_ratio` is the former value |
| `PointsPredictor` | development | removed: it was a constant-velocity extrapolation, `2 * p[t] - p[t-1]` |
| `GenericModelPredictor` | development | removed: it has no published definition |
| `GenericModelEstimator` | development | removed: it has no published definition |
| `CurvatureDispersion` | development | removed: it has no source, and its value depended on the speed, the sampling rate and the unit |
| `ConvexHull` | development | SciPy: `contour[scipy.spatial.ConvexHull(contour).vertices]` |
| `FilterContour` | development | SciPy: `scipy.ndimage.gaussian_filter1d(contour, sigma, axis=0, mode="wrap")` smooths a closed contour |
| `CorrelationsMatrix` | development | `numpy.corrcoef`, the plain Pearson correlation (signed, in [-1, 1]); `PartialRecurrenceSynchronization` takes that matrix |
| `CoarseGraining` | development | removed: it is an internal step of `MultiScaleEntropy`; in `numpy`, `x[:len(x)//f*f].reshape(-1, f).mean(axis=1)` |
| `SequenceDetector` | development | removed: a generic state machine with no published definition |
| `TemporalSynchronization` | development | removed: a generic state machine with no published definition |

### Names of the EyesWeb blocks

These are names of the development states or of the EyesWeb blocks that a user of EyesWeb may expect.

| EyesWeb block or development name | Name in 2.0 | Note |
|---|---|---|
| `KineticEnergyIndex` | `KineticEnergy` | |
| `PeriodicityIndex` | `Periodicity` | |
| `ImpulsivityIndex` | `ContractionImpulsivity` | `ges_dur` is `gesture_duration`; `frames` is `sampling_rate` |
| `RarityIndex`, `HistogramRarity` | `Rarity` | `method="information"` or `"mode_distance"` |
| `SmoothnessIndex` (development `Smoothness`) | `CurvatureVelocityCorrelation` | |
| `GetKinematicalFeatures`, `TrajectoryFeatures` | `Kinematics` | |
| `AverageCurvature` | `TrajectoryNonPlanarity` | it measures the distance from local best-fit planes, not a curvature; for the curvature of a trajectory use `Kinematics(output_type="curvature")` |
| `Curvature` | `ContourCurvature` | |
| `SymmetryIndex3D`, `GeometricSymmetry` | `Symmetry` | `method="ratio"` or `"reflection"` |
| `TriangleSymmetryIndex` | `TriangleSymmetry` | the output `symmetry` is 1 minus the EyesWeb asymmetry |
| the development `GestureSegmenter` that read skeletons | `KineticEnergy` then `GestureSegmenter`, which takes the intensity | |
| `MotionDuration` (display name `SteadyStateLength`) | the outputs `motion_duration` and `pause_duration` of `GestureSegmenter` | durations in seconds instead of milliseconds |
| `PARS` | `PartialRecurrenceSynchronization` | |
| `EventSynchronizationInterdependence` | `NonlinearInterdependence` | outputs `xy`, `yx` are `first_to_second_interdependence`, `second_to_first_interdependence` |
| `SpikeES` | `SpikeSynchronization` | |
| `CentroidsCalc`, `BlobSubRegions`, `VideoGram` | `SilhouetteCentroids`, `SilhouetteBodyParts`, `Videogram` | on full-frame masks |
| `HumanoidSimulator`, `GenericModelSimulator`, `HumanoidOrientationsExtractor`, `GenericModelOrientationsExtractor` | `MassSpringSimulator` | one feature: `model="humanoid"` or a `MassSpringModel`; the bone directions are its `directions` output; `joint_map` names your labels |
| `MassSpringModel`, `TimeWindowSynchronizer` | `pyeyesweb.physical_signals.MassSpringModel`, `TimeWindowSynchronizer` (and `SynchronizedWindow`) | not catalog features |

### Parameter, input and output spellings

A test of the library (`tests/unit_tests/test_naming.py`) forbids the spellings of the first column in every parameter, input and
output of the catalog. Most of them existed only in development states; those of 1.x are `rate_hz`, `num_subsamples`,
`joint_pairs`, `center_of_symmetry`, `algo`, `filter_params`, `plv`, `margin_mm` and the `value` of `Equilibrium`. A boolean
output is always named `is_<something>`, the Savitzky-Golay parameters are always `filter_window_length` and
`filter_polyorder`, and feature names have no `Get` prefix and no `Index` suffix. The last column gives features that use the
new spelling.

| Old spelling | New spelling | Used by |
|---|---|---|
| `n_inputs` | `number_of_inputs` | `EventSynchronizationMECS`, `Rarity`, `SpikeSynchronization` |
| `input_number` | `number_of_inputs` | `EventSynchronizationMECS`, `Rarity`, `SpikeSynchronization` |
| `time_series_number` | `number_of_inputs` | `EventSynchronizationMECS`, `Rarity`, `SpikeSynchronization` |
| `number_of_input_trains` | `number_of_inputs` | `EventSynchronizationMECS`, `Rarity`, `SpikeSynchronization` |
| `event_class_number` | `number_of_event_classes` | `EventSynchronizationMECS` |
| `points_number` | `number_of_points` | `BodyPartsFromCurvature` |
| `num_of_regions` | `number_of_regions` | `RegionDependingPotentials` |
| `num_subsamples` | `number_of_subsamples` | `DirectionChange` |
| `window_size` | `window` | `BinaryPulsesRegularity`, `CrossRecurrencePlot`, `CurvatureVelocityCorrelation` and 21 more |
| `window_length` | `window` | `BinaryPulsesRegularity`, `CrossRecurrencePlot`, `CurvatureVelocityCorrelation` and 21 more |
| `length` | `window` | `BinaryPulsesRegularity`, `CrossRecurrencePlot`, `CurvatureVelocityCorrelation` and 21 more |
| `buffer_length` | `window` | `BinaryPulsesRegularity`, `CrossRecurrencePlot`, `CurvatureVelocityCorrelation` and 21 more |
| `data_memory` | `window` | `BinaryPulsesRegularity`, `CrossRecurrencePlot`, `CurvatureVelocityCorrelation` and 21 more |
| `cells_x` | `cells_along_x` | `HitCellDetector`, `PositionDependingPotentials`, `RegionDependingPotentials` |
| `cells_y` | `cells_along_y` | `HitCellDetector`, `PositionDependingPotentials`, `RegionDependingPotentials` |
| `sigma_value` | `gaussian_sigma` | `EventSynchronizationMECS` |
| `std_dev_x` | `gaussian_sigma_x` | `PositionDependingPotentials` |
| `std_dev_y` | `gaussian_sigma_y` | `PositionDependingPotentials` |
| `rho` | `gaussian_correlation` | `PositionDependingPotentials` |
| `ges_dur` | `gesture_duration` | `ContractionImpulsivity` |
| `frames` | `sampling_rate` | `ContractionImpulsivity`, `CurvatureVelocityCorrelation`, `MassSpringSimulator` and 9 more |
| `use_cust_ampl` | `use_custom_amplitude` | `PositionDependingPotentials` |
| `cust_ampl` | `custom_amplitude` | `PositionDependingPotentials` |
| `use_cust_dist` | `use_custom_distance` | `PositionDependingPotentials` |
| `cust_dist` | `custom_distance` | `PositionDependingPotentials` |
| `reg_init_values` | `region_initial_values` | `RegionDependingPotentials` |
| `ref_dir` | `reference_direction` | `MassSpringSimulator` |
| `filter_params` | `low_frequency`, `high_frequency` | `PhaseLockingValue` |
| `algorithm` | `method` | `Periodicity`, `Rarity`, `SuddennessImpulsivity` and 1 more |
| `algo` | `method` | `Periodicity`, `Rarity`, `SuddennessImpulsivity` and 1 more |
| `type` | `measure` | `Rarity` |
| `couples` | `pairs` | `Symmetry` |
| `joint_pairs` | `pairs` | `Symmetry` |
| `center_of_symmetry` | `reference_point` | `KineticEnergy`, `Symmetry` |
| `sqom` | `quantity_of_motion` | `ContractionImpulsivity` |
| `ci` | `contraction_index` | `BoundingBoxFilledArea`, `ContractionImpulsivity` |
| `cpr` | `correlations_matrix` | `PartialRecurrenceSynchronization` |
| `ts1` | `first_signal` | `EventSynchronization`, `NonlinearInterdependence`, `PhaseLockingValue` |
| `ts2` | `second_signal` | `EventSynchronization`, `NonlinearInterdependence`, `PhaseLockingValue` |
| `x` | `first_signal` | `EventSynchronization`, `NonlinearInterdependence`, `PhaseLockingValue` |
| `y` | `second_signal` | `EventSynchronization`, `NonlinearInterdependence`, `PhaseLockingValue` |
| `plv` | `phase_locking_value` | `PhaseLockingValue` |
| `xy` | `first_to_second_interdependence` | `NonlinearInterdependence` |
| `yx` | `second_to_first_interdependence` | `NonlinearInterdependence` |
| `value` | `equilibrium` | `Equilibrium` |
| `plot` | `recurrence_matrix` | `RecurrencePlot` |
| `synchronisation` | `synchronization` | `EventSynchronization`, `EventSynchronizationMECS` |

## Behaviour changes that alter numbers

A script ported name by name can still give different values. The first table lists what differs from 1.x or from the
development states; the second lists corrections of defects of the original EyesWeb blocks, which apply to features that are new
in 2.0 (each is also stated on the page of the feature, as "Corrected in the core").

| Feature | Change |
|---|---|
| `TrajectoryNonPlanarity` | default `radius` 0.1 m (was 100, a value written for millimetres); a path where no point has another point within `radius` is `INVALID_INPUT` (was 0, which read as "planar"); too many undefined local planes is `INVALID_INPUT` (was the marker 999) |
| `LogDimensionlessJerk` | a flat or null signal (no jerk, or no peak to normalise by) is `INVALID_INPUT` with no value; 1.x and the development state returned 0, the best value of the scale |
| `GestureSegmenter` | the Savitzky-Golay polynomial is fit to the newest `filter_window_length` samples, newest included, and read at their centre (EyesWeb never read the newest sample of a fixed 10-sample window): the detection is one sample earlier, the warm-up is `filter_window_length - 1` samples instead of 10, and any odd window of 5 or more is accepted |
| `GestureSegmenter` (EyesWeb `MotionDuration`) | durations follow the timestamps, `t(end) - t(begin)`, else `sampling_rate`; EyesWeb counted calls. NaN until a phase has ended (EyesWeb gave 0) |
| `SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount` (1.x `Smoothness`) | the Butterworth low-pass filter (`use_filter`) is gone, so the values at the former defaults differ; the rate has no default |
| `MultiScaleEntropy` (1.x `MultiScaleEntropyDominance`) | sample entropy comes from the EyesWeb block; values differ from 1.x by a term of order 1/N |
| `MultiScaleEntropy` (1.x `MultiScaleEntropyDominance`) | the tolerance is `tolerance` times the standard deviation of the original signal at every scale (Costa et al. 2005); 1.x standardised every coarse-grained series again, so the values change at the scales above 1 (white noise now loses entropy with the scale) |
| `MultiScaleEntropy` (1.x `MultiScaleEntropyDominance`) | a scale where no pair of templates matches has a `NaN` entropy, and its signal a `NaN` complexity index with a `reason`; 1.x gave 0, the most regular value, so a signal without enough data looked the least complex and led. With no defined index the status is `INVALID_INPUT` |
| `SampleEntropy` | the default tolerance is relative to the signal (`relative_tolerance=0.2`); an absolute tolerance of 0.3 matched nothing on a signal of another scale and gave infinite entropies |
| `Rarity` | the EyesWeb block replaces the 1.x implementation, which computed a different quantity |
| `Symmetry(method="reflection")` (1.x `GeometricSymmetry`) | 1.x gave the distance between a joint and the reflection of its partner (0 for a mirror image); 2.0 gives a score of the pair in [0, 1] that is 1 for a mirror image |
| `Equilibrium` | the margin is in metres (0.1 m, the former 100 mm); the three points are the inputs |
| `KineticEnergy` | only the total is returned; an empty frame is `INVALID_INPUT` instead of 0.0; `weights` is a mapping or one weight per label |
| `BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity` | an empty frame is `INVALID_INPUT` instead of 0.0; `PointsDensity` is the EyesWeb block, with the options `centroid_type` and `distance_type` |
| `DirectionChange`, `Suddenness` | one trajectory per call: a frame with several markers is rejected (1.x averaged them), average the markers beforehand; the numbers for a single point are unchanged |
| `Equilibrium`, `Symmetry` | a negative joint index is rejected (1.x wrapped around); there are no joint indices any more |
| every feature | NaN or infinite input is `INVALID_INPUT` and does not enter the window; a timestamp that does not increase is `INVALID_INPUT`; a missing value is `NaN`, not `None` |
| every feature | the step between samples is the difference of timestamps in seconds, the first call of a sequence uses `1 / sampling_rate`, and without a rate it is one second per sample (the result says so in `reason`) |
| `Symmetry(method="ratio")` on a preset without a reference joint | 2.0 asks for `reference_point=`; the development default `"neck"` was no joint of `mediapipe` or `qualisys_sport` and the translation to the reference was silently skipped |
| `Symmetry(method="ratio")` | there is no `reference_type` parameter (the core only translates the frame by `reference_point`; `"barycenter"` and `"point"` did nothing in the original block): passing it raises `TypeError` |
| `Symmetry` | `pairs` is validated: an entry that is not two joint names, or a name that is not among the labels, raises `ValueError` |
| `KineticEnergy(reference_point=...)` | a frame without the reference joint is `INVALID_INPUT` ("missing joints"); the EyesWeb block took the origin as the reference, so the energy of the whole movement was reported. A `reference_point` that is not among `labels` raises `ValueError` |
| `KineticEnergy(labels=[...])` | without `weights=` every joint weighs 1.0 (it used to raise); a joint missing from an explicit mapping weighs 0 |
| `CurvatureVelocityCorrelation` (development) | `velocity` and `velocity_std` are per second in both modes of `differentiate`; the development values with `differentiate=False` were per sample |
| `MotionNoiseDetector` (development) | `is_noisy` is `True` for noisy (random, jumpy) motion; it was the reverse |
| `MassSpringModel.to_xml()` (development) | the damping is written as relative damping, so a saved model reloads to the same configuration |
| `SampleEntropy`, `MultiScaleEntropy` (development) | two templates match when their distance is at most the tolerance (`<=`, Richman and Moorman); it was strictly less, as in the EyesWeb block and pyEntropy. Values change only when a distance equals the tolerance, as on quantised data |

| Feature | Correction of the original block |
|---|---|
| `Kinematics` | acceleration and jerk are the true second and third derivatives, and the curvature of the path has the right normalisation |
| `CurvatureVelocityCorrelation` | the curvature used half of the second derivative of the fit |
| `SuddennessImpulsivity` | both terms are evaluated on the same single trajectory (the original took the direction change of the mean of all the signals and the suddenness of the first signal) |
| `MotionNoiseDetector` | `reset()` clears the speed windows |
| `HitCellDetector` | a point on an interior cell edge goes to the upper cell, as the formula says; the original divided by the rounded cell size, which put some edges (0.3, 0.6, 0.7 on `[0, 1]` with 10 cells) in the lower one |
| `RecurrencePlot`, `CrossRecurrencePlot` | a distance equal to `epsilon` is a recurrence (Marwan et al. 2007, eq. 10); the original was strict, so `epsilon=0` gave an empty matrix, even on the diagonal. Values change only when a distance equals the threshold, as on quantised data |
| `Periodicity` | the default `threshold` is 0.1 (the original block's 0.2 is outside the range 0.01 to 0.1 advised by Sethares and Staley), so `"small2large"` reports weaker periods by default; a window where every channel is constant, or `"mbest"` on fewer than 3 samples, is `INVALID_INPUT` (the original gave `NaN` powers or zeros) |
| `EventSynchronizationMECS` | the default `kernel` is `"linear"`, the kernel of the paper; the original block's default was `"uniform"`, so the default values change whenever events are not simultaneous |
| `EventSynchronization` | each window is evaluated on its own by default (`reset_every_buffer=True`); the original block accumulated the counts over the recording, which `reset_every_buffer=False` still does |
| `PhaseLockingValue` | each window is tapered with a Hann window before the Hilbert transform and the 10 % of the phases at each end are left out (Mormann et al. 2000), so the values change slightly (a pure lock gave about 0.98, now 1); a constant signal is `INVALID_INPUT` (two constant windows gave 1) |
| `PartialRecurrenceSynchronization` | a matrix with a condition number above 1e12, or one that is not positive definite, is `INVALID_INPUT` without values; the first port returned zeros with `OK` |
| `GeneralisedAutoCorrelation` | `lag` and `max_lag` must be smaller than `window`, or `ValueError`; the original block cut the lag range to two thirds of the window without telling, and the scalar lag was clamped to the window. A curve that used the cut now gives its full range |
| `BinaryPulsesRegularity` | regular when the spread of the intervals is below `threshold`, `max(I) - min(I) < threshold` (Niewiadomski et al. 2019); the original compared each interval with the first one within `threshold` inclusive, which accepted a spread up to twice the threshold. The threshold shifts by one: the original's `t` is `t + 1`, and the default is 1 (equal intervals, the original's 0) |
| `ScalarPeakDetector` | no peak and status `WARMING_UP` for the first `window - 1` samples: the original analysed a zero-filled buffer, so a signal that starts high and falls gave a false peak |
| `ScalarPeakDetector` | the running maximum was seeded with the smallest positive number, so a signal that stays at or below 0 never produced a peak |
| `SilhouetteBodyParts` | left and right are those of the image (left = smaller x), as in `SilhouetteCentroids`: the original's (and the development's) `right_leg` and `right_arm` are `left_leg` and `left_arm`, and the converse; the order of `regions` follows the new names. A part that touches the first row or column of the frame is found (the original dropped it) |
| `SilhouetteCentroids(silhouette="upper" / "lower" / "left" / "right")` | `center_of_gravity` is the centroid of the mask; the original block reported the edge of the image where it cut the body in two (and its normalised value could reach 1) |
| `Videogram` | each line is the mean of its row or column (Jensenius 2006); the original scaled every line to its own maximum, 255, so the values change, a still frame stays dark and a small movement stays weak |
| `SilhouetteBodyParts`, `Videogram` | the barycentre is the centroid of the mask truncated to whole pixels; the channel sums of the videogram are independent (the original aliased them) |
| `MassSpringSimulator` | the damping force is proportional to the relative velocity of the two masses (the original used speed magnitudes and injected energy); the feet of the T-pose are built along the direction they rest in |

The notes on each family in the theory pages ({doc}`theory/kinematics_energy`, {doc}`theory/smoothness`,
{doc}`theory/imaging`) give the details.
