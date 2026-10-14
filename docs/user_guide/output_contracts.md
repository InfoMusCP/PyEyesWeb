# Output contracts

Every PyEyesWeb feature, whether written in Python or ported from an EyesWeb block, returns its values through
the same contract. The goal is that you can write code against a feature **before you have seen a single
result**: you can ask it what it will output, every call returns the same fields, and an unusable call is
described by a status instead of a `None` or an exception.

## At a glance

```python
import numpy as np
from pyeyesweb.low_level import GeometricSymmetry

# five joints: two symmetric pairs (0, 1) and (2, 3) around a centre joint (4)
sym = GeometricSymmetry(joint_pairs=[(0, 1), (2, 3)], center_of_symmetry=4)

sym.outputs                       # what the feature returns, known before any data
# Schema(Output('pair_error', shape=(2,)))
sym.outputs.flat_names            # ('pair_error_0_1', 'pair_error_2_3')

result = sym.compute(frame)       # frame: (5 joints, 3 dims)
result.pair_error                 # array([1.        , 0.89855235]), shape (2,)
result.status                     # Status.OK
result.to_array()                 # one float vector, same layout every call
result.to_flat_dict("sym")        # {'sym_status': 0, 'sym_t': nan, 'sym_pair_error_0_1': 1.0, 'sym_pair_error_2_3': 0.8985...}
```

The pair labels come from the joint indices (`<left>_<right>`); a different list of pairs gives a different schema.

## The rules

1. **A feature declares its outputs once.** `feature.outputs` is a `Schema`: for each output its name, shape,
   component or label names, type and unit. It depends only on the constructor parameters, so it is available
   before any data arrives. Use it to create channels or CSV headers, preallocate arrays, or generate documentation.
2. **Every call returns the same fields.** Results are immutable `Result` objects with one read-only attribute per
   declared output. There is no `Optional`: the attributes always exist.
3. **A missing value is `NaN`** (`0` for integer outputs, `False` for boolean outputs), never `None`. The array
   shapes stay the same, so downstream code does not need to special-case an unusable call.
4. **`status` says whether the call produced output, and why not.** `result.ok` is `status is Status.OK`.
5. **`result.valid` says which outputs were produced**, per output, for the features where some outputs are
   conditional.
6. **Types are predictable:** scalars are Python `float`, `int` or `bool`; vectors and matrices are read-only NumPy
   arrays; labelled data known only at run time (a skeleton) is a `dict` of arrays.

## Status

| Status | Meaning | Typical case |
|---|---|---|
| `OK` | The call produced output. | |
| `WARMING_UP` | The window or internal state is still filling. Some outputs may already be valid. | A window shorter than the feature needs; the first frames of an EyesWeb block |
| `NO_OUTPUT` | The feature emits only on some calls and this was not one of them. | An event-based or decimating EyesWeb block |
| `INVALID_INPUT` | The input cannot be processed; `result.reason` says why. | An empty point set, a degenerate window |

`Status` is an `IntEnum`, so it can be stored directly in a numeric column.

```python
r = feature(window)
if not r.ok:
    print(r.status.name, r.reason)        # WARMING_UP needs at least 5 samples
```

## Getting values out

| Method | Gives | Use it for |
|---|---|---|
| `result.<output>` or `result["<output>"]` | The typed value | Normal code |
| `result["centroid_x"]` | One scalar by flat name | Quick access |
| `result.to_array()` | A float64 vector of the **fixed** outputs, in `schema.flat_names` order | Real-time: one TouchDesigner CHOP sample, a model input |
| `result.to_dict()` | `name -> value`, same keys every call | Passing results on |
| `result.to_flat_dict(prefix, meta=True)` | One scalar per key, plus `status` and `t` | Logging a row |

The flat names are built from the schema: `name`, `name_x` (with component names), `name_<label>`,
`name_<label>_<component>`, or `name_0`, `name_1`, ... Outputs whose size depends on the data (a curve with one value
per sample, a skeleton) are not part of `to_array()`; `to_flat_dict()` expands them by the size and labels they have
in that result.

```python
sym.outputs.flat_names                    # use as channel names, once
for frame in stream:
    sample = sym.compute(frame).to_array()  # same length every frame, NaN where there was no output
```

## Recording many frames

A `Recorder` keeps one preallocated, growable column per output, so offline analysis does not go through a list of
Python objects.

```python
from pyeyesweb.data_models import Recorder

rec = Recorder(sym)
for frame in frames:
    rec.append(sym.compute(frame))

rec["pair_error"]         # (n_frames, 2)
rec["pair_error_0_1"]     # (n_frames,)
rec.ok                    # boolean mask of the rows that produced output
rec.valid["pair_error"]   # per-output validity of every row
rec.to_numpy()            # (n_frames, schema.size)
rec.to_frame()            # pandas DataFrame: status (integer codes), t and one column per flat name
```

`rec.run(sym.compute, frames)` does the loop for you. Outputs of variable size are kept as Python lists.

## Writing a feature

Declare the outputs, then build every return value with `self.result(...)`:

```python
import numpy as np
from pyeyesweb.data_models import Output, Schema, Status, StaticFeature

class Spread(StaticFeature):
    OUTPUTS = Schema(
        Output("spread", unit="m", doc="Mean distance of the points from their centroid"),
        Output("centroid", components=("x", "y", "z"), unit="m"),
    )

    def compute(self, frame):
        if len(frame) == 0:
            return self.no_output(Status.INVALID_INPUT, "no points")
        centroid = frame.mean(axis=0)
        return self.result(spread=np.linalg.norm(frame - centroid, axis=1).mean(), centroid=centroid)
```

- **Parameter-dependent outputs:** override `_schema(self)` instead of setting `OUTPUTS`, for example to give one
  value per joint pair or to choose between a scalar and per-axis output. Call `self._outputs_changed()` if a setter
  changes what the schema depends on.
- **Selectable outputs:** when a parameter chooses which quantities are computed (a `metrics` list), keep every
  possible output in `OUTPUTS` and narrow it per instance:
  `def _schema(self): return self.OUTPUTS.select(self.metrics)`, with `self._outputs_changed()` in the setter. Pass
  only the computed values to `self.result(...)`; an output that was not requested is not declared, so it does not
  appear as a column of `NaN`.
- **Sizes:** a shape entry of `None` means the size depends on the data. Prefer a fixed shape whenever the
  parameters determine it, because only fixed outputs take part in `to_array()`.
- **Conditional outputs:** leave an output out of `self.result(...)` (or pass `None`) when this call did not produce
  it; it becomes the empty value and `result.valid[name]` is `False`.
- **Statuses:** return `self.no_output(Status.WARMING_UP, ...)` while a window fills, `Status.INVALID_INPUT` for
  unusable data. Do not return `None` and do not raise for insufficient data.
- **Errors in the declaration raise early:** an undeclared name is a `KeyError`, a value of the wrong shape a
  `ValueError`.

The streaming `__call__` of `StaticFeature` and `DynamicFeature` returns `Status.WARMING_UP` for an empty window and
stamps `result.t` with the newest timestamp of the `SlidingWindow`.

## Features backed by the core

Every feature wraps a C++ block of the compiled core and lives in its layer package
(`pyeyesweb.low_level.KineticEnergy`, ... see [Library structure](library_structure.md)). Besides the common contract
above, the features that port a stateful EyesWeb block (they derive from `CoreFeature`) share these rules.

- **Calls and state:** `process(...)` runs one EyesWeb `Execute()`, and `reset()` restores the state after `Init()`.
  Because EyesWeb blocks keep state between calls (previous frames, filter histories, counters), results depend on
  the sequence of calls, unlike a pure `compute`.
- **Parameters:** constructor keyword arguments, with the EyesWeb defaults. Each `fix_*` argument corrects one
  documented bug of the original block; by default a block reproduces EyesWeb exactly.
- **Schemas follow the parameters:** `SymmetryIndex3D` has one output `symmetry`, a scalar for a global index and a
  3-vector for per-axis components; `Kinematics` has one output named after the selected quantity (`velocity`,
  `acceleration`, ...).
- **Statuses:** a block that writes its output only on some activations reports `NO_OUTPUT` the rest of the time
  (`CoarseGraining`, `MotionDuration`); `GestureSegmenter` reports `WARMING_UP` until its 10-frame window is full.
- **Time:** `result.t` is in seconds when the block is given a creation time in 100 ns ticks, `NaN` otherwise.
