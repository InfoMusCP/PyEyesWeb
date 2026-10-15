# Time, units and parameters

The same few rules apply to every feature: time is in seconds, lengths are in metres, a choice is a string, and parameters
are validated when they are set. This page states them.

## Time is in seconds

Every quantity that has time in it, whether a speed, a frequency or a duration, is expressed in seconds, never in frames.
Time reaches a feature in two ways.

- `timestamp` (a number, in seconds) given to `process`, and `timestamps` (one per sample) given to `run`. They are
  keyword-only. Nothing is ever stamped with the wall clock.
- `sampling_rate`, a constructor parameter, in hertz. It is a parameter of 16 classes and its default is `None` in all of them:
  there is no hidden rate.

A feature that needs the time between two samples decides it in this order:

1. the difference between the `timestamp` of this call and the previous one, if both were given;
2. otherwise `1 / sampling_rate`, if a rate was given;
3. otherwise one second per sample, and the `reason` of the result says `"no time given: per-sample derivatives"`.

The `KineticEnergy` of a point of unit weight is {math}`\tfrac12 v^2`, which makes the step visible. The point moves 0.1 m
between the two calls:

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy
>>> def energy(**parameters):
...     return KineticEnergy(labels=["a"], weights={"a": 1.0}, **parameters)
>>> def run(feature, timestamps=None):
...     rows = []
...     for index, x in enumerate([0.0, 0.1]):
...         stamp = None if timestamps is None else timestamps[index]
...         result = feature.process({"a": (x, 0.0, 0.0)}, timestamp=stamp)
...         rows.append((round(float(result.kinetic_energy), 6), result.reason))
...     return rows[1]
>>> run(energy(), [0.0, 0.5])                      # 0.1 m in 0.5 s: v = 0.2 m/s
(0.02, '')
>>> run(energy(sampling_rate=100.0))               # 0.1 m in 0.01 s: v = 10 m/s
(50.0, '')
>>> run(energy(sampling_rate=100.0), [0.0, 0.5])   # both given: the timestamps win
(0.02, '')
>>> run(energy())                                  # neither: 1 s per sample
(0.005, 'no time given: per-sample derivatives')
```

Two details follow from the rule. The **first** timed call has no previous timestamp (it is the first call, or follows
`reset()`, or follows a call made without a timestamp), so its step is `1 / sampling_rate` or one second: an absolute time is
never taken as a step, and epoch seconds such as `1.7e9` are fine. And without a sampling rate even a call with a timestamp
reports the per-sample note, until a second timestamp gives a difference.

The checks on the timestamp are central: a timestamp that is NaN or infinite gives `INVALID_INPUT` with the reason
`"non-finite timestamp"` in every feature. A timestamp that does not exceed the previous one gives `INVALID_INPUT`
(`"non-increasing timestamp"`) in the features that use time between calls, and the previous time is kept, so the next valid
call has the right step:

```{doctest}
>>> feature = energy()
>>> _ = feature.process({"a": (0.0, 0.0, 0.0)}, timestamp=1.0)
>>> repeated = feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=1.0)
>>> repeated.status.name, repeated.reason
('INVALID_INPUT', 'non-increasing timestamp')
>>> round(float(feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=1.5).kinetic_energy), 6)
0.02
>>> feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=float("nan")).reason
'non-finite timestamp'
```

### Window metrics need a rate

Five low-level metrics work on a window of a speed or acceleration profile, which has no time axis of its own:
`SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount` and `CurvatureVelocityCorrelation`. They
require `sampling_rate` and raise `ValueError` at construction without it. They use `timestamp` only to label the result:
it does not enter the computation and its order is not checked.

## Windows and hops

Features that work on a window of recent samples are configured with two numbers, both counted in samples.

`window`
: the number of samples in a window. It has no default in most classes (a missing one raises a `TypeError` that says what `window`
  is); the four smoothness metrics default to 60 samples and `MultiScaleEntropy` to 3000.

`hop`
: the number of new samples between two windows, default 1. With `hop = window` the windows do not overlap.

There are 22 such classes, subclasses of {py:class}`~pyeyesweb.data_models.WindowedFeature`. Until the first window is full the
status is `WARMING_UP`; with a hop larger than 1, the calls between windows are `NO_OUTPUT` (see {doc}`results`).

```{doctest}
>>> import pyeyesweb
>>> from pyeyesweb.data_models import WindowedFeature
>>> windowed = [info for info in pyeyesweb.catalog() if issubclass(info.cls, WindowedFeature)]
>>> len(windowed)
22
>>> import inspect
>>> {info.name: inspect.signature(info.cls).parameters["window"].default for info in windowed if inspect.signature(info.cls).parameters["window"].default is not inspect.Parameter.empty}
{'SpectralArcLength': 60, 'LogDimensionlessJerk': 60, 'Harmonicity': 60, 'SubmovementCount': 60, 'MultiScaleEntropy': 3000}
```

A window can be changed on a running feature. `window` and `hop` are neither live nor structural in the sense below: the newest
samples are kept, and a window that grew reports `WARMING_UP` until it is full again. `configure(window=, hop=)` changes both at
once, and both are validated together (`1 <= hop <= window`).

```{doctest}
>>> from pyeyesweb.low_level import SpectralArcLength
>>> feature = SpectralArcLength(window=10, hop=2, sampling_rate=100.0)
>>> feature.configure(window=20, hop=5)
>>> feature.parameters["window"], feature.parameters["hop"]
(20, 5)
>>> feature.hop = 30
Traceback (most recent call last):
  ...
ValueError: SpectralArcLength: window must be >= 1 and 1 <= hop <= window (got window=20, hop=30)
```

Some exceptions are worth knowing. `EventSynchronization` and `EventSynchronizationMECS` accumulate across windows, so
`hop=None` means `hop = window` and no other value is accepted. Six classes have a `window` parameter without being windowed
features: `Videogram`, `CurvatureDispersion`, `FilterContour`, `PositionDependingPotentials`, `Rarity` and
`ScalarPeakDetector`. There `window` is a length of the feature's own, in samples, described on its page.
`CurvatureDispersion` has no `hop` and returns a result for every call.

## Units

Lengths, positions, and thresholds that are lengths are in **metres**, the unit of the EyesWeb blocks. Ten classes take
`units="m"` (the default) or `units="mm"` for data recorded in millimetres:

```{doctest}
>>> with_units = [info.name for info in pyeyesweb.catalog() if "units" in inspect.signature(info.cls).parameters]
>>> len(with_units)
10
>>> with_units
['HumanoidSimulator', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator', 'HitCellDetector', 'Kinematics', 'CurvatureDispersion', 'Equilibrium', 'MotionNoiseDetector', 'TrajectoryNonPlanarity']
```

The rule is that **parameters are scaled and data are not**. A threshold is always written in metres, whatever `units` says,
and `units` says in which unit your data and the outputs are. A feature given `units="mm"` converts its own length
thresholds internally and writes the unit it was given in the output, but the values you pass and the values it returns are
untouched. `feature.parameters` reads a threshold back as you wrote it.

```{doctest}
>>> from pyeyesweb.low_level import Kinematics
>>> Kinematics().outputs
Schema(Output('velocity', unit='m/s'))
>>> Kinematics(units="mm").outputs
Schema(Output('velocity', unit='mm/s'))
>>> Kinematics(units="mm", movement_threshold=0.05).parameters["movement_threshold"]
0.05
```

The unit of an output (`Output.unit`) is documentation in the terms of the data. `<length>` is the length unit of the data,
`<input>` is the unit of the input, `samples`, `frames`, `px`, `deg`, `s` and `cells` are what they say, and compounds such
as `<length>/s` combine them. The text follows the parameters: the duration of `MotionDuration` is in `frames` without a rate
and in `s` with one.

```{doctest}
>>> KineticEnergy(skeleton="kinect_v2").outputs
Schema(Output('kinetic_energy', unit='<length>^2/s^2'))
>>> energy(sampling_rate=100.0).outputs["kinetic_energy"].unit
'<length>^2/s^2'
```

### The humanoid model

`HumanoidSimulator` works internally in millimetres, because the body model of EyesWeb and its spring forces are defined in
that unit. It still follows the same rule: `units` declares the unit of your frames, of `gravity` and `floor_position`, and of
the output, and the wrapper converts at the boundary. A body run in metres and the same body run in millimetres give the same
motion, to rounding:

```{doctest}
>>> from pyeyesweb.physical_signals import HumanoidSimulator
>>> pose = HumanoidSimulator(sampling_rate=25.0).process({"head": (0.0, 1.7, 0.0)}).joints      # metres
>>> in_metres = HumanoidSimulator(sampling_rate=25.0)
>>> in_millimetres = HumanoidSimulator(sampling_rate=25.0, units="mm")
>>> for step in range(5):
...     a = in_metres.process(pose + 0.001 * step).joints
...     b = in_millimetres.process(pose * 1000 + 1.0 * step).joints
>>> bool(np.allclose(a * 1000, b))
True
>>> in_millimetres.outputs
Schema(Output('joints', shape=(21, 3), unit='mm'))
```

The `GenericModel*` features are different: they run in the unit of the model you give them, and `units` only names it, so
`"m"` and `"mm"` give the same numbers.

## Choices are strings, switches are booleans

A parameter that picks one of several algorithms or modes is a lower-case string, as in scikit-learn
(`Symmetry(method="reflection")`). Matching is case-insensitive, `-` and a space count as `_`, and a wrong value raises
`ValueError` listing the options, also from a setter. An on/off switch is a real `bool`; `"on"` or `1` raises `TypeError`.
No parameter takes an enumeration: the only enumerations in the public interface are `Layer`, `Timescale`, `InputKind` and
`Status`.

```{doctest}
>>> Kinematics(output_dims="Components", dims=2).parameters["output_dims"]
'components'
>>> Kinematics(output_dims="bogus")
Traceback (most recent call last):
  ...
ValueError: output_dims: invalid value 'bogus'; choose one of 'components', 'tangential'
>>> HumanoidSimulator(length_forces="on")
Traceback (most recent call last):
  ...
TypeError: length_forces must be True or False, got 'on'
```

A feature with variants (`Symmetry` has `method="ratio"` and `"reflection"`) refuses the parameters of the other variant:

```{doctest}
>>> from pyeyesweb.low_level import Symmetry
>>> Symmetry(skeleton="kinect_v2", method="reflection", aggregation="mean")
Traceback (most recent call last):
  ...
TypeError: method='reflection' does not take aggregation
```

A few features choose which outputs they compute with `parts=`, a sequence of names validated like any other choice:
`SilhouetteCentroids`, `SilhouetteBodyParts` and `RegionDependingPotentials`. The value is read back as a tuple in the order of
the block, which is not necessarily the order you gave.

```{doctest}
>>> from pyeyesweb.physical_signals import SilhouetteBodyParts
>>> SilhouetteBodyParts(parts=["head", "trunk"]).parameters["parts"]
('trunk', 'head')
>>> SilhouetteBodyParts(parts=["tail"])
Traceback (most recent call last):
  ...
ValueError: parts: invalid value 'tail'; choose one of 'right_leg', 'left_leg', 'trunk', 'right_arm', 'left_arm', 'head'
```

Not every `output_dims` has the same vocabulary: `Kinematics` accepts `components` or `tangential`, `PointsDensity`
`components` or `module`, and `Symmetry` `global` or `components`.

## Reading and setting parameters

`feature.parameters` is a read-only mapping of the constructor parameters and their current values. A parameter that is
resolved at construction and not kept, such as `skeleton`, is not listed (it becomes `labels`, `weights` and `pairs`). The
parameters are also attributes with setters, validated like the constructor: a value out of range raises `ValueError` and
leaves the feature exactly as it was.

```{doctest}
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> feature.parameters["window"] = 20
Traceback (most recent call last):
  ...
TypeError: 'mappingproxy' object does not support item assignment
>>> feature.window = -3
Traceback (most recent call last):
  ...
ValueError: SpectralArcLength: window must be >= 10 (got -3)
>>> feature.parameters["window"]
10
>>> feature.amplitude_threshold = 0.5
>>> feature.parameters["amplitude_threshold"]
0.5
```

## Live and structural parameters

A parameter set on a running feature either applies at once or restarts the feature.

Live
: the parameter is applied in place and the accumulated state is kept: a threshold, a weight, a sampling rate.

Structural
: the parameter sizes or shapes the state (the number of channels, a filter length, a mode), so the state is restarted. The
  `reason` of the next result says `"parameters changed: state reset"`, once.

```{doctest}
>>> kinematics = Kinematics(sampling_rate=100.0, filter_window_length=15)
>>> for index in range(3):
...     _ = kinematics.process((index * 0.01, 0.0, 0.0))
>>> kinematics.movement_threshold = 0.1                  # live
>>> kinematics.process((0.04, 0.0, 0.0)).reason
''
>>> kinematics.filter_window_length = 9                  # structural
>>> kinematics.process((0.05, 0.0, 0.0)).reason
'parameters changed: state reset'
>>> kinematics.process((0.06, 0.0, 0.0)).reason
''
```

The classification was made parameter by parameter from the original EyesWeb block (a value read at every call is live, one
read when the block is created is structural; when in doubt, structural). The page of each feature marks its parameters
*(live)* or *(structural)* where the distinction applies. The table lists the parameters that the test suite changes one by
one on a running feature and checks against this classification; it is taken from those tests.

| Feature | Live | Structural |
|---|---|---|
| `SilhouetteCentroids` | `add_intermediate_centroids`, `parts` | `silhouette` |
| `SilhouetteBodyParts` | `arm_percentage`, `parts` | |
| `Videogram` | | `mode`, `window` |
| `HitCellDetector` | `x_max` | |
| `Kinematics` | `movement_threshold` | `filter_polyorder`, `output_type` |
| `KineticEnergy` | `weights` | `input_mode` |
| `BoundingBoxFilledArea` | `epsilon` | |
| `PointsDensity` | `distance_type` | |
| `Symmetry` | `aggregation`, `reference_point` | |
| `SpectralArcLength` | `amplitude_threshold`, `maximum_cutoff_frequency`, `minimum_cutoff_frequency`, `sampling_rate` | |
| `LogDimensionlessJerk` | `input_mode`, `sampling_rate` | |
| `Harmonicity` | `sampling_rate` | |
| `SubmovementCount` | `prominence_factor`, `sampling_rate` | |
| `CurvatureVelocityCorrelation` | `upper_limit` | `filter_window_length` |
| `Equilibrium` | `margin` | |
| `DirectionChange` | `epsilon` | |
| `FilterContour` | `gaussian_sigma` | |
| `ConvexHull` | `integer_coordinates` | |
| `BodyPartsFromCurvature` | `minimum_distance` | |
| `TrajectoryNonPlanarity` | `radius` | |
| `GestureSegmenter` | `firing_threshold` | `filter_window_length` |
| `MotionDuration` | `sampling_rate` | |
| `SuddennessImpulsivity` | `direction_change_epsilon` | |
| `ContractionImpulsivity` | `motion_threshold`, `peak_threshold`, `sampling_rate` | |
| `PositionDependingPotentials` | `gaussian_sigma_x` | `potential_type` |
| `RegionDependingPotentials` | `parts` | `potential_type` |
| `SampleEntropy` | `relative_tolerance`, `tolerance` | |
| `CoarseGraining` | | `factor` |
| `Rarity` | `alpha`, `measure` | `window` |
| `BinaryPulsesRegularity` | `threshold` | |
| `MultiScaleEntropy` | `tolerance` | |
| `Periodicity` | `threshold` | |
| `ScalarPeakDetector` | `threshold` | `window` |
| `PhaseLockingValue` | `low_frequency` | |
| `GeneralisedAutoCorrelation` | `epsilon` | `output_type`, `tau_spread` |
| `EventSynchronization` | `tau` | `reset_every_buffer` |
| `EventSynchronizationMECS` | `kernel` | `number_of_event_classes`, `tau` |
| `NonlinearInterdependence` | `neighbours` | |
| `SequenceDetector` | `inter_event_time` | `sequence` |
| `RecurrencePlot` | `epsilon` | |
| `CrossRecurrencePlot` | `epsilon` | |
| `TemporalSynchronization` | `thresholds` | `number_of_inputs` |

In the humanoid and generic-model features every tested parameter is live (`damping`, `viscosity`, `gravity`, the forces,
`integration_step`, `reference_direction`, `floor_position`, the predictor and estimator parameters, `sampling_rate`), except the
`seed` of `GenericModelEstimator`, a replacement of the `model` by one of a different topology, and the
`reference_direction` of `HumanoidOrientations`, which are structural.
