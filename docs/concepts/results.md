# Results, statuses and recorders

A feature answers every call with the same kind of object, whatever it computes. This page describes the objects:
what a feature declares it will return ({py:class}`~pyeyesweb.data_models.Schema`), what one call returns
({py:class}`~pyeyesweb.data_models.Result`), why a call may return no value
({py:class}`~pyeyesweb.data_models.Status`), and how a whole recording is stored
({py:class}`~pyeyesweb.data_models.Recorder`).

| Call | Returns | Use |
|---|---|---|
| `feature.process(*sample, timestamp=None)` | a `Result` | streaming: one sample or frame at a time, state kept between calls |
| `feature.run(*recording, timestamps=None, reset=True)` | a `Recorder` | offline: a whole recording, one row per sample |
| `feature.outputs` | a `Schema` | what the feature returns, known before any data |
| `feature.latest` | a `Result` or `None` | the last result that was `OK` |
| `feature.reset()` | nothing | forget the accumulated state |

`run` gives the same numbers as a loop of `process` calls. It starts from a fresh state unless `reset=False` is passed,
which continues from the previous call (for a long recording processed in chunks).

## What a feature returns: the schema

`feature.outputs` is a `Schema`, an ordered, read-only collection of {py:class}`~pyeyesweb.data_models.Output`
declarations: name, shape, kind (`float`, `int` or `bool`), the names of the components or labels, a unit and a one-line
description. It is fixed when the feature is built.

```{doctest}
>>> from pyeyesweb.low_level import Kinematics
>>> seconds = np.arange(30) / 100.0
>>> positions = np.outer(seconds, [0.5, 0.0, 0.25])     # a point moving at the constant velocity (0.5, 0, 0.25) m/s
>>> kinematics = Kinematics(output_type=["velocity", "direction"], output_dims="components", dims=positions.shape[1], sampling_rate=100.0)
>>> kinematics.outputs
Schema(Output('velocity', shape=(3,), unit='m/s'), Output('direction', shape=(3,)))
>>> kinematics.outputs["velocity"].shape, kinematics.outputs["velocity"].unit
((3,), 'm/s')
>>> kinematics.outputs["direction"].axis_names
(('x', 'y', 'z'),)
>>> kinematics.outputs.flat_names
('velocity_x', 'velocity_y', 'velocity_z', 'direction_x', 'direction_y', 'direction_z')
```

The **flat names** are the scalar columns that the outputs make up, in a fixed order: they are the columns of a table of
results, and of `Result.to_array()`. Outputs whose size depends on the data (an image, a variable-length list, joints
labelled at run time) have no flat names; they are available on each result but are not part of the numeric table.

Units are written in terms of the data. `<length>` stands for the length unit of the data, and a feature given `units="mm"`
writes the concrete unit (`mm/s`). An empty unit means a dimensionless quantity. See {doc}`time_units_parameters`.

## One call: the result

A result has the same fields on every call. For each output it has one read-only attribute with the output's name, and it also
carries the call's status and timing.

```{doctest}
>>> for index, position in enumerate(positions):
...     result = kinematics.process(position, timestamp=index / 100.0)
>>> result
KinematicsResult(status=OK, velocity=[0.5 , 0.  , 0.25], direction=[0.8944, 0.    , 0.4472])
>>> result.status.name, result.ok, result.timestamp
('OK', True, 0.29)
>>> result.velocity.round(3).tolist()
[0.5, 0.0, 0.25]
>>> result["direction"].round(3).tolist()
[0.894, 0.0, 0.447]
```

| Field | Meaning |
|---|---|
| `status` | a {py:class}`~pyeyesweb.data_models.Status`: why the call did or did not produce output |
| `reason` | text that explains a status other than `OK`; empty when `OK` |
| `timestamp` | the time of the call in seconds as given, `NaN` when none was given |
| `valid` | for each output, whether it holds a value |
| the outputs | one attribute per output, also readable as `result["name"]` |
| `ok` | `True` when the status is `OK` |

A result is immutable, and the arrays it holds are read-only. It converts to plain Python and NumPy objects in three ways:

```{doctest}
>>> result.to_array().round(3).tolist()
[0.5, 0.0, 0.25, 0.894, 0.0, 0.447]
>>> sorted(result.to_dict())
['direction', 'velocity']
>>> {key: round(value, 3) for key, value in result.to_flat_dict().items() if key.startswith("velocity")}
{'velocity_x': 0.5, 'velocity_y': 0.0, 'velocity_z': 0.25}
>>> result.to_flat_dict()["status"], result.to_flat_dict()["timestamp"]
(0, 0.29)
>>> result.with_time(2.0).timestamp
2.0
```

`to_array()` is the vector of the flat names; `to_dict()` maps each output to its value; `to_flat_dict()` maps each flat name
to a number, with the status as an integer (`0` for `OK`), for logging or a data frame row. `with_time()` returns a copy with
another timestamp.

A value that was not produced is never `None`. It is `NaN` for a float output, `0` for an integer and `False` for a boolean;
an array output has its declared shape filled that way, and an output whose labels are only known at run time is an empty dict.
This makes results safe to stack in arrays without checks.

## Status: why a call may have no value

`Status` has four members. It is an integer enumeration, so a status can be stored in a numeric column (`0` is `OK`);
`str(status)` is the name.

| Status | When | `reason` |
|---|---|---|
| `OK` | the call produced output | empty |
| `WARMING_UP` | a window is still filling; some outputs may already be valid | the sample count, `"k of N samples"` |
| `NO_OUTPUT` | the feature emits only on some calls, and this was not one of them | `"between windows"` for a windowed feature with `hop > 1` |
| `INVALID_INPUT` | the call is not data | what is wrong |

### Warming up

A windowed feature needs `window` samples before its first value. Until then every call has status `WARMING_UP`, the outputs
are empty and the `reason` counts the samples collected. The first complete window gives the first `OK`, at call number
`window`.

```{doctest}
>>> from pyeyesweb.low_level import SpectralArcLength
>>> signal = np.abs(np.sin(np.linspace(0.0, 3.0, 14))) + 0.5
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> [(str(result.status), result.reason) for result in (feature.process(value) for value in signal[:11])][8:]
[('WARMING_UP', '9 of 10 samples'), ('OK', ''), ('OK', '')]
```

### Between windows

A windowed feature also has a `hop`: the number of new samples between two windows (default 1). With a larger hop, the calls
between two windows have nothing new to say, and return `NO_OUTPUT`:

```{doctest}
>>> feature = SpectralArcLength(window=10, hop=5, sampling_rate=100.0)
>>> recording = feature.run(np.abs(np.sin(np.linspace(0.0, 6.0, 30))) + 0.5)
>>> recording
Recorder(SpectralArcLength, rows=30, columns=['spectral_arc_length'], status={'OK': 5, 'WARMING_UP': 9, 'NO_OUTPUT': 16})
>>> [str(recording[index].status) for index in (8, 9, 10, 13, 14)]
['WARMING_UP', 'OK', 'NO_OUTPUT', 'NO_OUTPUT', 'OK']
```

### Input that is not data

`INVALID_INPUT` means that the call itself cannot be processed: NaN or infinity in the values, an empty frame, a joint missing
from a dict frame, a timestamp that goes back or is not a finite number, a result that overflows. The result has every output
empty and `valid` is `False` for all of them, whatever the feature could have computed; the explanation is only in `reason`.

```{doctest}
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> bad = feature.process(float("inf"))
>>> bad.status.name, bad.reason, bad.spectral_arc_length, bad.valid
('INVALID_INPUT', 'NaN or infinite values', nan, {'spectral_arc_length': False})
>>> feature.process(1.0, timestamp=float("nan")).reason
'non-finite timestamp'
```

A rejected call changes nothing: the sample is not buffered, the counters do not move and `latest` is untouched, so the next
valid call behaves as if the rejected one had never happened.

```{doctest}
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> _ = [feature.process(value) for value in signal[:3]]
>>> feature.process(float("nan")).status.name
'INVALID_INPUT'
>>> feature.process(signal[3]).reason
'4 of 10 samples'
```

## The last good result: `latest`

`feature.latest` is the last result whose status was `OK`. It is `None` until there is one, and `reset()` clears it.
`WARMING_UP`, `NO_OUTPUT` and `INVALID_INPUT` calls do not touch it, so it is the value to display or hold in a live loop
when the current call has no value.

```{doctest}
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> feature.latest is None
True
>>> for value in signal[:10]:
...     _ = feature.process(value)
>>> feature.latest
SpectralArcLengthResult(status=OK, spectral_arc_length=-1.5415)
>>> _ = feature.process(float("nan"))
>>> feature.latest is not None
True
>>> feature.reset()
>>> feature.latest is None
True
```

## A whole recording: the recorder

`run` applies `process` to every sample and stores the results as columns, with one row per call. A `Recorder` keeps one
NumPy column per output and the status, reason and timestamp of each row, so a long recording is not a list of objects.

```{doctest}
>>> recording = kinematics.run(positions, timestamps=seconds)
>>> recording
Recorder(Kinematics, rows=30, columns=['velocity', 'direction'], status={'OK': 29, 'INVALID_INPUT': 1})
>>> len(recording), recording.velocity.shape
(30, (30, 3))
>>> recording.timestamps[:3].tolist()
[0.0, 0.01, 0.02]
```

A recorder reads like a table and like a list.

| Expression | Value |
|---|---|
| `rec["velocity"]`, `rec.velocity` | the column of an output: an array of shape `(n,) + output shape` |
| `rec["velocity_x"]` | one flat column, shape `(n,)` |
| `rec[3]`, `rec[-1]` | one row as a `Result`, with its `reason` and `valid` |
| `rec[2:5]` | a list of results |
| `rec.status` | the integer status of each row |
| `rec.ok` | a boolean mask of the rows that are `OK` |
| `rec.valid["velocity"]` | whether that output was produced in each row |
| `rec.timestamps` | the timestamp of each row in seconds, `NaN` where unknown |
| `rec.to_frame()` | a pandas DataFrame, with the status names in `status` |
| `rec.to_numpy()` | the numeric columns as one array, in the order of the flat names |

```{doctest}
>>> recording["velocity_x"].shape, recording.velocity.shape
((30,), (30, 3))
>>> recording[-1].velocity.round(3).tolist()
[0.5, 0.0, 0.25]
>>> int(recording.ok.sum()), recording.status[:3].tolist()
(29, [3, 0, 0])
>>> frame = recording.to_frame()
>>> list(frame.columns)
['status', 'timestamp', 'velocity_x', 'velocity_y', 'velocity_z', 'direction_x', 'direction_y', 'direction_z']
>>> frame[["velocity_x", "velocity_z"]].iloc[-1].round(3).to_dict()
{'velocity_x': 0.5, 'velocity_z': 0.25}
>>> frame["status"].iloc[-1]
'OK'
>>> recording.to_numpy().shape
(30, 6)
```

Only the fixed outputs enter `to_numpy()` and `to_frame()`. An image output, or one with labels known only at run time, stays
in `rec["name"]` as a list, one entry per row. The recorder has no `to_array()`; that name belongs to a single result.

A recorder is the right object to filter on status: `values = rec.velocity[rec.ok]` keeps the rows that have a value.

## Errors, in short

Three mechanisms cover everything that can go wrong, and each has its own place.

| Situation | What happens |
|---|---|
| a sample of the wrong shape or kind | `ValueError` naming the feature and the input |
| values that are not data (NaN, infinity, an empty frame, a missing joint, a timestamp that goes back or is not finite) | `INVALID_INPUT`, with the `reason`; nothing raised |
| too few samples yet | `WARMING_UP` |
| an invalid parameter, at construction or when set | `ValueError`; a feature whose setter failed is left as it was |
| a misspelled keyword, or a required argument left out | `TypeError` naming the feature and listing the valid parameters |
| a dict frame with a key that is not one of the configured labels | `ValueError` listing the expected joints |

The rule is that code which is wrong raises, and data which is bad is reported in the result, so that a live loop does not stop
because of a dropout.

```{doctest}
>>> SpectralArcLength(window=10, sampling_rate=100.0, windw=3)
Traceback (most recent call last):
  ...
TypeError: SpectralArcLength() got unexpected keyword argument(s) 'windw' (did you mean 'window'?); valid parameters: window, hop, sampling_rate, amplitude_threshold, minimum_cutoff_frequency, maximum_cutoff_frequency
>>> SpectralArcLength(window=5, sampling_rate=100.0)
Traceback (most recent call last):
  ...
ValueError: SpectralArcLength: window must be >= 10 (got 5)
>>> SpectralArcLength(window=10)
Traceback (most recent call last):
  ...
ValueError: SpectralArcLength needs sampling_rate (Hz): the window it works on carries no time of its own
```

## Behaviours worth knowing

::::{dropdown} A result can be invalid although the data are finite
An overflow is an `INVALID_INPUT` with the reason `"the result is not finite"`. Unlike every other rejection it is only
detected after the feature has taken the sample into its state, and the state cannot be undone. A stateful feature can
therefore return `INVALID_INPUT` on the following valid call too (and a windowed feature until the sample leaves its window).

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy
>>> energy = KineticEnergy(labels=["a"], weights={"a": 1.0}, sampling_rate=100.0)
>>> _ = energy.process({"a": (0.0, 0.0, 0.0)}, timestamp=0.00)
>>> huge = energy.process({"a": (1e300, 0.0, 0.0)}, timestamp=0.01)
>>> huge.status.name, huge.reason
('INVALID_INPUT', 'the result is not finite')
>>> energy.process({"a": (0.01, 0.0, 0.0)}, timestamp=0.02).status.name
'INVALID_INPUT'
```
::::

::::{dropdown} `run` starts from scratch
Calling `run` twice does not carry the window over from the first call, because `run` resets the feature first. Pass
`reset=False` to continue.

```{doctest}
>>> feature = SpectralArcLength(window=10, sampling_rate=100.0)
>>> _ = feature.run(signal[:7])
>>> [str(row.status) for row in feature.run(signal[7:])][-2:]
['WARMING_UP', 'WARMING_UP']
>>> _ = feature.run(signal[:7])
>>> [str(row.status) for row in feature.run(signal[7:], reset=False)][-2:]
['OK', 'OK']
```
::::

::::{dropdown} The timestamp is keyword-only
`process(frame, 0.0)` is read as a second input and raises `ValueError`; write `process(frame, timestamp=0.0)`. See
{doc}`inputs`.
::::

::::{dropdown} A `NaN` is data for some features
The humanoid models and the ensemble features take a missing joint, or a participant without a value, as part of the data: one
`NaN` joint is a dropout the model handles, and the call is `OK`. Infinity and a frame that is all `NaN` are still
`INVALID_INPUT`. The page of each feature says which rule applies.
::::
