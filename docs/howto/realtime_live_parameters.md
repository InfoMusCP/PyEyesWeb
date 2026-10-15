# A real-time loop with live parameters

In a live set-up there is no recording to hand to `run`: a frame arrives, the features are updated, the next frame arrives. This
page shows the loop, how to give it time, and how to change a parameter of a running feature without stopping the stream. The
tutorial {ref}`sphx_glr_tutorials_06_capstone_plot_10_capstone.py` builds a longer chain on a motion-capture recording and
checks it against `run`; the rules behind this page are in {doc}`../concepts/results` and
{doc}`../concepts/time_units_parameters`.

## The loop

`process` takes one sample (or one frame) and returns a {py:class}`~pyeyesweb.data_models.Result`. A feature keeps what it needs
between calls, so the loop only has to call it in order. The stream below is a hand moving on an ellipse, sampled at 100 Hz;
in your program the values come from the sensor, a file reader or a network socket.

```{doctest}
>>> from pyeyesweb.low_level import Kinematics, SpectralArcLength
>>> rate = 100.0
>>> def stream(count=600):
...     for index in range(count):
...         stamp = index / rate                                   # seconds
...         yield stamp, (0.3 * np.sin(np.pi * stamp), 0.2 * np.cos(np.pi * stamp), 0.0)
>>> kinematics = Kinematics(sampling_rate=rate)
>>> arc = SpectralArcLength(window=100, hop=10, sampling_rate=rate)
>>> arc.latest is None
True
```

The first feature turns the position into a speed, the second measures the smoothness of the speed over the last 100 samples (one
second) and produces a value every 10 samples. Between two values the feature has nothing new to say, and during the first
second it has not seen enough samples: those calls are not errors, they are results with a status other than `OK`
({py:class}`~pyeyesweb.data_models.Status`).

```{doctest}
>>> from collections import Counter
>>> statuses, held = Counter(), []
>>> for stamp, point in stream(300):
...     speed = kinematics.process(point, timestamp=stamp)
...     result = arc.process(speed.velocity, timestamp=stamp)
...     statuses[result.status.name] += 1
...     held.append(arc.latest.spectral_arc_length if arc.latest else float("nan"))
>>> statuses
Counter({'NO_OUTPUT': 180, 'WARMING_UP': 99, 'OK': 21})
>>> result
SpectralArcLengthResult(status=OK, spectral_arc_length=-2.69518)
>>> arc.latest.timestamp
2.99
```

`feature.latest` is the last result whose status was `OK`, and `None` before the first one and after `reset()`. A loop that needs
a continuous signal, such as a parameter sent to a synthesiser, holds it: `value = result if result.ok else feature.latest`. The
list `held` above does exactly that, and is `NaN` until the first window is complete.

```{doctest}
>>> held[98], held[99], held[100], held[109], held[110]
(nan, -2.6867218106842063, -2.6867218106842063, -2.766859267025632, -2.766859267025632)
```

## Time: `timestamp` or `sampling_rate`

All time is in seconds, and the library never reads a clock: a feature knows the time only from what you give it. The step
between two samples is, in this order,

1. the difference between the `timestamp` of this call and the previous one, when both were given;
2. otherwise `1 / sampling_rate`, when the feature has a rate;
3. otherwise one second per sample, and the `reason` of the result says "no time given: per-sample derivatives".

With a steady stream `sampling_rate` is enough. With a stream that arrives with jitter, give the timestamps of the samples,
because they are the true times. The example is a hand that moves at exactly 1 m/s along a line, sampled at about 100 Hz with
irregular intervals; the kinetic energy of a joint of weight 1 is {math}`\tfrac12 v^2 = 0.5` at every call.

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy
>>> clock = np.cumsum(np.random.default_rng(3).uniform(0.005, 0.015, 100))          # seconds, jittered
>>> points = np.stack([clock, 0 * clock, 0 * clock], axis=1)[:, None, :]            # 1 m/s along x
>>> def energy():
...     return KineticEnergy(labels=["hand"], weights={"hand": 1.0}, sampling_rate=100.0)
>>> timed = energy()
>>> [round(timed.process(point, timestamp=stamp).kinetic_energy, 3) for point, stamp in zip(points[:5], clock[:5])]
[0.0, 0.5, 0.5, 0.5, 0.5]
>>> untimed = energy()
>>> [round(untimed.process(point).kinetic_energy, 3) for point in points[:5]]
[0.0, 0.271, 0.847, 0.586, 0.176]
```

Without timestamps the feature assumes that samples are 10 ms apart, so the energy follows the jitter. Take the timestamp from the
source of the data when it has one (a frame counter or the time of the sensor). Otherwise take it from a monotonic clock, and
count from the start of the stream so that the numbers stay small:

```python
import time

start = time.perf_counter()
while True:
    sample = read_sample()                       # blocks until the next frame
    stamp = time.perf_counter() - start          # seconds since the start
    result = feature.process(sample, timestamp=stamp)
```

A timestamp must be finite and larger than the previous one. A call that breaks the rule returns `INVALID_INPUT` and changes
nothing, so the loop goes on with the next sample:

```{doctest}
>>> repeated = timed.process(points[4], timestamp=clock[4])
>>> repeated.status.name, repeated.reason
('INVALID_INPUT', 'non-increasing timestamp')
>>> timed.process(points[5], timestamp=clock[5]).kinetic_energy
0.5
```

A call that has no previous timestamp (the first call, the first one after `reset()`, and the first one after a call made without a
timestamp) uses `1 / sampling_rate`, or one second without a rate. The absolute value of a timestamp, seconds since the epoch for
example, never enters the step.

## Changing a parameter while the stream runs

A parameter is set by assigning the attribute, `feature.name = value`. It is validated as in the constructor and takes effect on
the next call. What happens to the state depends on the parameter.

Live
: applied in place, the accumulated state is kept. Thresholds, weights and the sampling rate are live.

Structural
: the parameter sizes or shapes the state (a filter length, the number of channels, a mode). The state restarts and the
  `reason` of the next result says "parameters changed: state reset", once.

`window` and `hop` of a windowed feature are in neither class: the feature keeps the newest samples. A shorter window gives a
result at once, a longer one reports `WARMING_UP` until it is full again. Both can be changed together with
`configure(window=..., hop=...)`.

The loop below changes one live and one structural parameter while it runs, at samples 300 and 400, and records every `reason`
that is not empty.

```{doctest}
>>> kinematics.reset(); arc.reset()
>>> notes = []
>>> for index, (stamp, point) in enumerate(stream(600)):
...     if index == 300:
...         arc.amplitude_threshold = 0.1                  # live
...     if index == 400:
...         kinematics.filter_window_length = 9            # structural
...     speed = kinematics.process(point, timestamp=stamp)
...     result = arc.process(speed.velocity, timestamp=stamp)
...     for name, step in (("kinematics", speed), ("arc", result)):
...         if step.reason and step.status.name != "NO_OUTPUT" and step.status.name != "WARMING_UP":
...             notes.append((index, name, step.reason))
>>> notes
[(0, 'kinematics', 'parameters changed: state reset'), (400, 'kinematics', 'parameters changed: state reset')]
```

The note at sample 0 is the one that follows `reset()`; the one at sample 400 is the structural change, and it appears only on the feature it was applied to. The smoothness of the second feature kept its
window through the live change. A change of `window` on a running feature:

```{doctest}
>>> arc.window = 200
>>> arc.process(0.3, timestamp=6.0).reason
'101 of 200 samples'
>>> arc.window = 50
>>> arc.process(0.3, timestamp=6.01).status.name
'OK'
```

A value that the constructor would refuse is refused by the setter too, and the feature is left as it was:

```{doctest}
>>> arc.amplitude_threshold = -1.0
Traceback (most recent call last):
  ...
ValueError: SpectralArcLength: amplitudeThreshold must be in [0, 1]
>>> arc.parameters["amplitude_threshold"]
0.1
```

### Which parameters are live

The classification was made parameter by parameter from the original EyesWeb block: a value read at every call is live, one read
when the block is created is structural, and when in doubt the parameter is structural. The class documentation of each
feature marks its parameters *(live)* or *(structural)* where the distinction applies. The table is taken from the test suite
(`tests/unit_tests/test_live_parameters*.py`), which changes each listed parameter on a running feature and checks the result
against a feature built with the new value.

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
| `FilterContour` | `gaussian_sigma`, `window` | |
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

A parameter that is not in the table belongs to a feature whose parameters are not changed one by one by those tests, or has no
live meaning; the class documentation says which. In the humanoid and generic-model features every tested parameter is live
(`damping`, `viscosity`, `gravity`, the forces, `integration_step`, `floor_position`, the predictor and estimator parameters,
`sampling_rate`), except the `seed` of `GenericModelEstimator`, the replacement of the `model` by one with another topology, and
the `reference_direction` of `HumanoidOrientations`, which are structural. Four features have a structural `window`, because the state of the core is sized by it: `Rarity(method="information")`,
`Videogram` and `ScalarPeakDetector`, and `CurvatureVelocityCorrelation`, whose `hop` and `sampling_rate` are structural too
(its filters need the same length and overlap in consecutive windows).
`EventSynchronization` and `EventSynchronizationMECS` change `window` and `hop` together, with `configure(window=, hop=)`.

## The loop gives the numbers of `run`

`run` is a loop over `process`, and the two give the same numbers. A program that prototypes on a recording and then goes live does
not change its results.

```{doctest}
>>> recording = np.array([point for _, point in stream(300)])
>>> stamps = np.arange(300) / rate
>>> offline = Kinematics(sampling_rate=rate).run(recording, timestamps=stamps).velocity
>>> live = Kinematics(sampling_rate=rate)
>>> online = np.array([live.process(point, timestamp=stamp).velocity for point, stamp in zip(recording, stamps)])
>>> bool(np.array_equal(offline, online))
True
```

`run` starts from a fresh state unless it is called with `reset=False`, which continues from the state left by the previous call:
a long recording can be processed in chunks, and a loop can be mixed with a `run` on the data that were buffered meanwhile.

## Practical notes

- One feature object holds the state of one stream. Two performers, or two sensors, need two objects; do not share one.
- Keep the call in the loop cheap: build the features before the loop, never inside it. The parameters are read back with
  `feature.parameters`, a read-only mapping.
- A call that returns `INVALID_INPUT` (a dropped marker, NaN, a timestamp that goes back) leaves the state unchanged, so the stream
  recovers by itself with the next good sample; check `result.ok` or `result.status` before using a value.
- Images arrive as arrays too: see {doc}`images` for the memory they need.
