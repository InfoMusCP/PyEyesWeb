---
orphan: true
---

# PyEyesWeb 2.0 fact sheet

```{admonition} Internal working document, not part of the published site
:class: warning

Written in WP2 of `DOCS_PLAN.md` (2026-10-15). It is the source of truth for the page writers of WP3 to WP8: every page
must agree with it, and where this sheet and the code disagree the code wins (and the sheet is wrong, fix it).
It is excluded from the build (`exclude_patterns` in `conf.py`) and is also `orphan`. It contains local paths, the name of
the private core repository and maintainer remarks: **move it to the private `dev-notes/` (or strip it) before the release**
(WP8), like the other internal plans.
```

State checked: branch `feature/v2-eyesweb-core`, `eyesweb_core` 2.0.0 build `dbaf21c`, Python 3.11 venv (numpy 2.4.6).
Written at `bc896e1` (`pytest -q`: 2633 passed, 12 skipped) and **updated in WP5 (2026-10-15) for the work packages H and I** at `a8402dd`
(`pytest -q`: 2925 passed, 12 skipped): all 35 snippets were re-run, 4 outputs changed and are pasted below (`i04_recorder`, `i08c_unit_strings`,
`i17_core_version`, `x3_symmetry_ratio_reference`), the statements that depended on them were edited, and section 21 lists the changes that
had no snippet yet.
Counts, names and messages below are from running the code on that state, not copied from the plans.

How to read an item: **Statement** (what pages may say), **Evidence** (`file:line` in `pyeyesweb/`; `DEV` is
`DEVELOPMENT_SPEC.md`), **Run** (the snippet is executed verbatim; the output is pasted by a script, never typed), **Status**
(`verified`, `corrected vs plan` with what changed, or `not yet true`). Snippets that need no core say so.

To re-run any snippet:

```text
MSYS_NO_PATHCONV=1 PYTHONPATH="<workspace>/EyesWebCore/build/Release;<workspace>/PyEyesWeb" \
EYESWEB_CORE_PATH=<workspace>/EyesWebCore/build/Release <workspace>/.venv/Scripts/python.exe snippet.py
```

## Summary

| # | Topic | Status |
|---|---|---|
| 1 | Call contract | verified; corrected: `process` returns a feature-specific `Result` subclass, `latest` is `None` before the first `OK` result |
| 2 | `Result` | verified (`is_valid`, `ok`, `with_time`, `to_dict`, `to_array` also exist) |
| 3 | `Status` | corrected: warm-up `reason` is a sample count; "state unchanged" does not hold for an overflow |
| 4 | `Recorder` | corrected: `to_numpy()`, not `to_array()`; images excluded from `to_numpy()` and `to_frame()` (verified); every `run` gives `Recorder(<Feature>, ...)` with `<Feature>Result` rows (H) |
| 5 | Errors | verified; additions (a timestamp that is not finite is `INVALID_INPUT` in every feature since H, when a wrong joint name raises) |
| 6 | Time rule | corrected: the "non-increasing" check belongs to 9 "timed" classes, the "non-finite" check is central (H), the window metrics ignore the order of `timestamp`; first timed call; reason texts |
| 7 | Windows | corrected: 22 windowed classes; `window` has a default in 5 of them; six more classes have a `window` parameter |
| 8 | Units | corrected: `units` exists in exactly 10 classes; humanoid claim verified; unit text follows the parameters |
| 9 | Choices | verified; corrected: `parts=` reads back in the block's order; `output_dims` differs per feature |
| 10 | `from_*` constructors | corrected: exactly three classes, six constructors |
| 11 | Skeletons | corrected: `joint_map` on 6 classes only, `skeleton=` on 5, `GestureSegmenter` takes none |
| 12 | `dims` | corrected: `dims=None` in 4 classes only |
| 13 | Layers and catalog | corrected: 60 features, 11 / 22 / 7 / 1 / 19; four layers plus the analysis primitives (five groups, not "five layers"); synchronization has 12 classes |
| 14 | Live and structural parameters | verified (per-parameter table generated from the test tables) |
| 15 | Removed features | complete list, absence verified by import |
| 16 | Fidelity policy | verified (no flags in any signature); the list of corrections lives in the private repository |
| 17 | Install and core | corrected: `pip install pyeyesweb` gives the 1.x series today (packaging pending); `_core.py` describes the core as part of the wheel; import error texts re-verified (WP5) |
| 21 | Changes after the sheet (H and I) | `is_noisy` flipped, `gamma` dimensionless, per-second velocity of `CurvatureVelocityCorrelation`, `SpikeSynchronization(mode="timings")`, XML round trip, `Symmetry.reference_type` |

---

## 1. Contract

**Statement.** Every feature has exactly these public members: `process`, `run`, `reset`, `inputs`, `outputs`, `latest`,
`parameters` (windowed features add `window`, `hop`, `configure`). One documented exception: `EllipsoidSphericity.process_axes(first_axis,
second_axis, third_axis, *, timestamp=None)`, the faithful EyesWeb input (B27).

- `feature.process(*sample, timestamp=None)`: one sample or frame per input, `timestamp` is keyword-only and in seconds (a
  second positional argument is read as a second input). Returns an immutable `Result`: the object is an instance of a
  subclass generated from the schema and named `<Feature>Result` (`KineticEnergyResult`), not a dataclass.
- `feature.run(*recording, timestamps=None, reset=True)`: one array per input, time on axis 0; returns a `Recorder`. `reset=True`
  forgets the state first, `reset=False` continues. The numbers equal a loop of `process` (checked for the whole catalog by
  `tests/_support/contract_suite.py::check_feature_contract`, run by `test_contract_all_features.py`).
- `feature.reset()`: forgets the state, including `latest`.
- `feature.inputs` (`Inputs`: kind, shape, labels) and `feature.outputs` (`Schema`) are known from the constructor parameters, before any
  data (a feature with `dims=None` shows the shape once the first frame is known, see item 12).
- `feature.latest`: the last result whose status is `OK`; **`None` before the first one and after `reset()`**; a call that is not
  `OK` does not change it. A caller that needs a continuous signal holds it: `result if result.ok else feature.latest`.
- `feature.parameters`: read-only mapping (`mappingproxy`) of the constructor parameters with their current values. A parameter that
  is resolved at construction and not kept is not listed: `skeleton` becomes `labels` and `weights`. Change a parameter by
  assigning the attribute (`feature.window = 50`): it is validated like in the constructor (item 5) and applied live or restarts
  the state (item 14).

**Evidence.** `data_models/feature.py:161` (`process`), `:164` (`run`, `reset: bool = True`), `:201` (`reset`), `:124` (`latest`, set
by `_remembering` at `:68-77` only when `result.ok`, cleared by `_forgetting` at `:82-90`), `:133` (`parameters`), `:148` (`inputs`);
`data_models/base.py:65` (`outputs`); `data_models/results.py:277` (`result_type`) and `:290` (`Result`, `__setattr__` raises);
`data_models/feature.py:205` (`WindowedFeature`); DEV 49-76.

Run `i01_contract`:

```python
import numpy as np
from pyeyesweb.data_models import Feature, Recorder, Result, WindowedFeature
from pyeyesweb.low_level import KineticEnergy

feature = KineticEnergy(skeleton="kinect_v2", sampling_rate=100.0)
frames = np.random.default_rng(0).normal(size=(5, 25, 3))

print([name for name in ("process", "run", "reset", "inputs", "outputs", "latest", "parameters") if hasattr(feature, name)])
print("public members of Feature:", [n for n in dir(Feature) if not n.startswith("_")])
print("added by WindowedFeature:", sorted({n for n in dir(WindowedFeature) if not n.startswith("_")} - {n for n in dir(Feature) if not n.startswith("_")}))
print("latest before any call:", feature.latest)
result = feature.process(frames[0], timestamp=0.0)
print(type(result).__name__, "is a Result:", isinstance(result, Result), "| latest is result:", feature.latest is result)
try:
    result.status = 1
except AttributeError as error:
    print("immutable:", error)
print(feature.inputs)
print(feature.outputs)

recording = feature.run(frames, timestamps=np.arange(5) / 100)          # reset=True by default
loop = KineticEnergy(skeleton="kinect_v2", sampling_rate=100.0)
values = [loop.process(frame, timestamp=i / 100).kinetic_energy for i, frame in enumerate(frames)]
print("run == loop of process:", np.array_equal(recording.kinetic_energy, values))

print("parameters:", type(feature.parameters).__name__, list(feature.parameters))
try:
    feature.parameters["sampling_rate"] = 1.0
except TypeError as error:
    print("read-only:", error)
feature.reset()
print("latest after reset:", feature.latest)
try:
    feature.process(frames[0], 0.0)           # timestamp is keyword-only
except ValueError as error:
    print("positional timestamp:", str(error)[:110])
```

Output:

```text
['process', 'run', 'reset', 'inputs', 'outputs', 'latest', 'parameters']
public members of Feature: ['inputs', 'latest', 'outputs', 'parameters', 'process', 'reset', 'run']
added by WindowedFeature: ['configure', 'hop', 'window']
latest before any call: None
KineticEnergyResult is a Result: True | latest is result: True
immutable: KineticEnergyResult is immutable
Inputs(skeleton: points (25, 3) - joint positions or velocities)
Schema(Output('kinetic_energy', unit='<length>^2/s^2'))
run == loop of process: True
parameters: mappingproxy ['labels', 'input_mode', 'weights', 'reference_point', 'sampling_rate']
read-only: 'mappingproxy' object does not support item assignment
latest after reset: None
positional timestamp: KineticEnergy: takes 1 input(s) (skeleton), got 2
```


Latest and warm-up (the first result is `OK` at call 10, so `latest` stays `None` until then):

Run `i01b_latest`:

```python
import numpy as np
from pyeyesweb.low_level import SpectralArcLength

feature = SpectralArcLength(window=10, sampling_rate=100.0)
signal = np.sin(np.linspace(0, 3, 12)) + 1.0
for i, value in enumerate(signal):
    result = feature.process(float(value))
    print(i, result.status, "latest:", None if feature.latest is None else round(float(feature.latest.spectral_arc_length), 4))
```

Output:

```text
0 WARMING_UP latest: None
1 WARMING_UP latest: None
2 WARMING_UP latest: None
3 WARMING_UP latest: None
4 WARMING_UP latest: None
5 WARMING_UP latest: None
6 WARMING_UP latest: None
7 WARMING_UP latest: None
8 WARMING_UP latest: None
9 OK latest: -1.6183
10 OK latest: -1.6959
11 OK latest: -1.6584
```


The one extra entry point:

Run `i01c_process_axes`:

```python
import numpy as np
from pyeyesweb.low_level import EllipsoidSphericity

feature = EllipsoidSphericity()
result = feature.process_axes(1.0, 2.0, 3.0)
print("process_axes:", result.status.name, result.sphericity, "| radii (not produced):", result.radii, result.valid)
print("latest after process_axes:", feature.latest)
print("NaN size:", feature.process_axes(1.0, float("nan"), 3.0).reason)
print("shape check bypassed? a bad type raises:", end=" ")
try:
    feature.process_axes("a", 2.0, 3.0)
except Exception as error:
    print(type(error).__name__)
feature.process(np.random.default_rng(1).normal(size=(20, 3)))
print("latest after process:", type(feature.latest).__name__)
```

Output:

```text
process_axes: OK 0.8472861642710162 | radii (not produced): [nan nan nan] {'sphericity': True, 'axis_ratio': False, 'radii': False}
latest after process_axes: None
NaN size: the sizes must be positive and finite
shape check bypassed? a bad type raises: TypeError
latest after process: EllipsoidSphericityResult
```


**Status.** verified. Corrected vs plan: the `Result` type is a per-feature subclass; `latest` is `None` before the first call and
only follows `OK` results (a window that is still filling leaves it `None`).

---

## 2. Result

**Statement.** Fields: `status` (a `Status`), `reason` (`""` when `OK`), `timestamp` (seconds, `NaN` when unknown), `valid` (dict
output name to bool), `schema`, and one attribute per output: `result.kinetic_energy`, or `result["kinetic_energy"]`; a flat name
reads one scalar: `result["radii_0"]`. A value that was not produced is `NaN` (float), `0` (int) or `False` (bool) and
`valid[name]` is `False`; **never `None`** (for scalar outputs shown below; for vector, matrix, variable-size and labelled outputs see item B16 in the behaviours table, checked on 417 results of all 60 features). Other members: `ok`, `is_valid` (alias of `ok`, "kept for the 1.x
API"), `with_time(timestamp)`, `to_dict()`, `to_array()` (fixed outputs as one float vector in `schema.flat_names` order),
`to_flat_dict(prefix="", meta=True)` (status as its **integer code**, plus `timestamp`). Results are immutable and array values
are read-only.

**Evidence.** `data_models/results.py:290-400` (`Result`; `ok` `:329`, `is_valid` `:334`, `valid` `:339`, `with_time` `:343`,
`to_array` `:353`, `to_flat_dict` `:367`, `__getitem__` `:382`); `data_models/base.py:78-125` (`_result`: omitted or `None` output
means not produced).

Run `i02_result`:

```python
import numpy as np
from pyeyesweb.low_level import EllipsoidSphericity, SubmovementCount
from pyeyesweb.mid_level import Suddenness
from pyeyesweb.physical_signals import SilhouetteCentroids

from pyeyesweb.data_models import Result
print("public members of Result:", [n for n in dir(Result) if not n.startswith("_")])
feature = EllipsoidSphericity()
points = np.random.default_rng(1).normal(size=(20, 3))
result = feature.process(points, timestamp=2.5)
print([(name, getattr(result, name)) for name in ("status", "reason", "timestamp")])
print("valid:", result.valid)
print("attribute / item:", result.sphericity == result["sphericity"], "| radii", result.radii.shape)
print("flat name:", feature.outputs.flat_names, result["radii_0"] if "radii_0" in feature.outputs.flat_names else "")
print(result.to_flat_dict())
print("to_array:", result.to_array().shape)
no_time = feature.process(points)
print("timestamp without time given:", no_time.timestamp)

# a result with no output: nothing is None
warming = SubmovementCount(window=20, sampling_rate=100.0).process(1.0)
print(warming.status, warming.reason, "|", warming.submovement_count, type(warming.submovement_count).__name__, warming.valid)
sudden = Suddenness(window=10).process((0.0, 0.0))
print(sudden.status, "|", sudden.is_sudden, type(sudden.is_sudden).__name__, sudden.alpha, sudden.valid["is_sudden"])
print("to_flat_dict keeps integer statuses:", warming.to_flat_dict(), type(warming.to_flat_dict()["status"]).__name__)
```

Output:

```text
public members of Result: ['is_valid', 'ok', 'reason', 'schema', 'status', 'timestamp', 'to_array', 'to_dict', 'to_flat_dict', 'valid', 'with_time']
[('status', <Status.OK: 0>), ('reason', ''), ('timestamp', 2.5)]
valid: {'sphericity': True, 'axis_ratio': True, 'radii': True}
attribute / item: True | radii (3,)
flat name: ('sphericity', 'axis_ratio', 'radii_0', 'radii_1', 'radii_2') 1.1125588048439623
{'status': 0, 'timestamp': 2.5, 'sphericity': 0.8662859806873778, 'axis_ratio': 0.3914903913544603, 'radii_0': 1.1125588048439623, 'radii_1': 0.9455039431542026, 'radii_2': 0.43555608191321343}
to_array: (5,)
timestamp without time given: nan
WARMING_UP 1 of 20 samples | 0 int {'submovement_count': False}
WARMING_UP | False bool nan False
to_flat_dict keeps integer statuses: {'status': 1, 'timestamp': nan, 'submovement_count': 0} int
```


**Status.** verified. Note: the `Result` docstring (`data_models/results.py:300`) still says the timestamp is "seconds or ticks": see the
suspected inconsistencies.

---

## 3. Status

**Statement.** Exactly four members: `OK = 0`, `WARMING_UP = 1`, `NO_OUTPUT = 2`, `INVALID_INPUT = 3` (an `IntEnum`);
`str(Status.OK) == "OK"` (also in f-strings), `int(Status.OK) == 0`.

- `WARMING_UP`: a window is still filling. The `reason` is **a sample count**, `"k of N samples"` (not seconds).
- `NO_OUTPUT`: between two windows (`hop > 1`); `reason` is `"between windows"`. The first window is `OK` at call `window`.
- `INVALID_INPUT`: the call is not data; the `reason` says why; every output is empty and `valid` is `False` for all, **whatever the
  feature computed** (`_result` ignores the values it is given). Reasons seen: `"NaN or infinite values"`, `"empty frame"`,
  `"missing joints: a, b"`, `"non-increasing timestamp"`, `"the result is not finite"`.
- The state is unchanged (nothing buffered, the previous timestamp and the hop counter do not move) for: the finite check, a missing
  joint, a non-increasing timestamp. **It is not unchanged for an overflow** (`"the result is not finite"`: finite data whose result
  overflows): the block has already seen the sample, so the next valid call can be `INVALID_INPUT` too (run `i03c_overflow_state`).

**Evidence.** `data_models/results.py:29-42` (`Status`, `__str__`); `data_models/base.py:103-104` (empty outputs on `INVALID_INPUT`),
`:119-124` (`_finite_result`); `data_models/inputs.py:31` (`NON_FINITE`), `:111-121` (`Input.problem`); `base/labels.py:45-47`;
`base/core_feature.py:222-226` (`_input_problem`, non-increasing timestamp); `data_models/feature.py:285-286` (`WARMING_UP`,
`NO_OUTPUT`); DEV 91-102, 104-138.

Run `i03_status`:

```python
import numpy as np
from pyeyesweb.data_models import Status
from pyeyesweb.low_level import KineticEnergy, SpectralArcLength

print([s.name for s in Status], str(Status.OK), f"{Status.WARMING_UP}", int(Status.OK), [int(s) for s in Status])

feature = KineticEnergy(skeleton="kinect_v2", sampling_rate=100.0)
frame = np.random.default_rng(0).normal(size=(25, 3))
ok = feature.process(frame, timestamp=1.0)
bad = frame.copy(); bad[0, 0] = np.nan
invalid = feature.process(bad, timestamp=2.0)
print("OK:", ok.status, ok.ok, "| INVALID:", invalid.status, repr(invalid.reason), invalid.kinetic_energy, invalid.valid)
back = feature.process(frame, timestamp=0.5)
print("timestamp goes back:", back.status, repr(back.reason))
print("latest still the OK result:", feature.latest is ok)

windowed = SpectralArcLength(window=10, hop=3, sampling_rate=100.0)
print([windowed.process(float(i % 4)).status.name for i in range(16)])
```

Output:

```text
['OK', 'WARMING_UP', 'NO_OUTPUT', 'INVALID_INPUT'] OK WARMING_UP 0 [0, 1, 2, 3]
OK: OK True | INVALID: INVALID_INPUT 'NaN or infinite values' nan {'kinetic_energy': False}
timestamp goes back: INVALID_INPUT 'non-increasing timestamp'
latest still the OK result: True
['WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'OK', 'NO_OUTPUT', 'NO_OUTPUT', 'OK', 'NO_OUTPUT', 'NO_OUTPUT', 'OK']
```


A rejected NaN sample leaves no trace in a windowed feature:

Run `i03b_invalid_state`:

```python
import numpy as np
from pyeyesweb.low_level import SpectralArcLength

a = SpectralArcLength(window=10, hop=1, sampling_rate=100.0)
b = SpectralArcLength(window=10, hop=1, sampling_rate=100.0)
data = np.abs(np.sin(np.linspace(0, 3, 14))) + 0.5
for i, value in enumerate(data):
    a.process(float(value))
    if i == 6:
        print("NaN in the middle:", a.process(float("nan")).status.name, "(not buffered)")
    b.process(float(value))
print("same numbers with and without the rejected NaN:", a.latest.spectral_arc_length == b.latest.spectral_arc_length)
```

Output:

```text
NaN in the middle: INVALID_INPUT (not buffered)
same numbers with and without the rejected NaN: True
```


An overflow is `INVALID_INPUT` but the state advanced (this contradicts the plan's "state unchanged ... overflow"):

Run `i03c_overflow_state`:

```python
from pyeyesweb.low_level import KineticEnergy, SpectralArcLength

energy = KineticEnergy(labels=["a"], weights={"a": 1.0}, sampling_rate=100.0)
control = KineticEnergy(labels=["a"], weights={"a": 1.0}, sampling_rate=100.0)
for feature in (energy, control):
    feature.process({"a": (0.0, 0.0, 0.0)}, timestamp=0.0)
print("overflow:", energy.process({"a": (1e300, 0.0, 0.0)}, timestamp=0.01).status.name)
after = energy.process({"a": (0.01, 0.0, 0.0)}, timestamp=0.02)
expected = control.process({"a": (0.01, 0.0, 0.0)}, timestamp=0.02)
print("next call after the overflow:", after.status.name, after.kinetic_energy, "| control without the overflow:", expected.status.name, expected.kinetic_energy)

# windowed: a 1e300 sample enters the window and poisons the results until it leaves
feature = SpectralArcLength(window=10, sampling_rate=100.0)
statuses = []
for i in range(30):
    value = 1e300 if i == 12 else 1.0 + 0.1 * (i % 5)
    statuses.append(feature.process(value).status.name[:3])
print("1e300 at sample 12 of a window-10 metric:", statuses)
```

Output:

```text
overflow: INVALID_INPUT
next call after the overflow: INVALID_INPUT nan | control without the overflow: OK 0.125
1e300 at sample 12 of a window-10 metric: ['WAR', 'WAR', 'WAR', 'WAR', 'WAR', 'WAR', 'WAR', 'WAR', 'WAR', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK', 'OK']
```


**Status.** corrected vs plan: warm-up `reason` is a sample count; "state unchanged" does not hold for the overflow case (listed in
the suspected inconsistencies); `NO_OUTPUT` reason text added.

---

## 4. Recorder

**Statement.** `Recorder` is returned by `run` (and built by hand with `Recorder(feature)` / `Recorder.from_arrays`).

- `repr(rec)`: `Recorder(<feature>, rows=n, columns=[...], status={...})` (a fast-path `run` too: S1, fixed in H).
- `rec[3]`, `rec[-1]`: a `Result` (with `reason` and `valid`); out of range raises `IndexError`; `rec[2:5]`: a **list** of `Result`s;
  `rec["kinetic_energy"]` and `rec.kinetic_energy`: the column of an output (array `(n,) + shape`, or a list for a variable-size
  output); `rec["radii_0"]`: one flat column `(n,)`.
- `rec.status` (int codes), `rec.ok` (mask), `rec.timestamps` (NaN where unknown), `rec.valid` (per output), `rec.column(name)`,
  `len(rec)`, `append`, `extend`, `run`, `from_arrays`.
- **`rec.to_numpy()`** (float64 matrix `(n, schema.size)`, columns in `schema.flat_names` order) and `rec.to_frame(meta=True)`
  (pandas, optional dependency; `status` holds the **status names**, `timestamp` first). **There is no `Recorder.to_array()`**
  (that name belongs to `Result.to_array()`).
- **Images are never in `to_numpy()` / `to_frame()`**: only the fixed outputs enter; an image output, or a labelled image output such as
  `masks`, is a list in `rec.column(name)` (`schema.fixed_outputs` excludes them and `schema.size` does not count them).

**Evidence.** `data_models/recorder.py:97` (`__repr__`), `:147-166` (`status`, `ok`, `timestamps`, `valid`, `column`), `:172-196` (`__getitem__`, `__getattr__`),
`:206` (`to_numpy`), `:212` (`to_frame`); `data_models/results.py:214` (`fixed_outputs`); DEV 84-89 and 187-189.

Run `i04_recorder`:

```python
import numpy as np
from pyeyesweb.low_level import KineticEnergy
from pyeyesweb.data_models import Recorder

feature = KineticEnergy(skeleton="kinect_v2", sampling_rate=100.0)
recording = np.random.default_rng(0).normal(size=(6, 25, 3))
rec = feature.run(recording, timestamps=np.arange(6) / 100)
print("public members of Recorder:", [n for n in dir(Recorder) if not n.startswith("_")])
print(repr(rec), len(rec))
print(type(rec[3]).__name__, type(rec[-1]).__name__, type(rec[2:5]).__name__, len(rec[2:5]))
print(rec["kinetic_energy"].shape, rec.kinetic_energy.shape, rec["kinetic_energy"] is not None)
print(rec.timestamps, rec.status, rec.ok)
print(rec.to_frame().head(3))
print(type(rec.to_numpy()).__name__, rec.to_numpy().shape, [a for a in dir(rec) if a.startswith("to_")])
print("to_array on Recorder:", hasattr(rec, "to_array"))
try:
    rec[10]
except IndexError as error:
    print(error)
```

Output:

```text
public members of Recorder: ['append', 'column', 'extend', 'from_arrays', 'ok', 'run', 'status', 'timestamps', 'to_frame', 'to_numpy', 'valid']
Recorder(KineticEnergy, rows=6, columns=['kinetic_energy'], status={'OK': 6}) 6
KineticEnergyResult KineticEnergyResult list 3
(6,) (6,) True
[0.   0.01 0.02 0.03 0.04 0.05] [0 0 0 0 0 0] [ True  True  True  True  True  True]
  status  timestamp  kinetic_energy
0     OK       0.00        0.000000
1     OK       0.01    27414.235443
2     OK       0.02    29637.158678
ndarray (6, 1) ['to_frame', 'to_numpy']
to_array on Recorder: False
row 10 out of range for a recorder of 6 rows
```


Images (`SilhouetteBodyParts` has fixed outputs and an image output; `Videogram` has an image output only, so its `schema.size` is 0):

Run `i04b_recorder_images`:

```python
import numpy as np
from pyeyesweb.physical_signals import SilhouetteBodyParts

feature = SilhouetteBodyParts()
print(feature.outputs)
mask = np.zeros((60, 40), dtype=np.uint8)
mask[10:50, 15:25] = 255
mask[10:20, 10:30] = 255
masks = np.stack([mask] * 3)
rec = feature.run(masks)
print(repr(rec))
print("flat names:", feature.outputs.flat_names[:5], "...", len(feature.outputs.flat_names))
print("to_numpy shape:", rec.to_numpy().shape, "| schema.size:", feature.outputs.size)
print("images in to_numpy:", "masks" in feature.outputs.flat_names, "| fixed outputs:", [o.name for o in feature.outputs.fixed_outputs])
print("masks column:", type(rec.masks).__name__, "of", type(rec.masks[0]).__name__, list(rec.masks[0])[:2], next(iter(rec.masks[0].values())).dtype)
print("to_frame columns:", list(rec.to_frame().columns)[:4], "...", "masks" in rec.to_frame().columns)
print("Result.to_array size:", rec[0].to_array().shape)

from pyeyesweb.physical_signals import Videogram
video = Videogram(window=4)
print(video.outputs, "| size:", video.outputs.size, "| flat names:", video.outputs.flat_names)
frames = np.random.default_rng(0).integers(0, 255, size=(6, 8, 8), dtype=np.uint8)
rec = video.run(frames)
print(rec.to_numpy().shape, [type(v).__name__ for v in rec.column("videogram")[:1]])
```

Output:

```text
Schema(Output('regions', shape=(6, 4), kind=int, unit='px'), Output('is_found', shape=(6,), kind=bool), Output('masks', shape=(None, None), kind=int, labelled=True))
Recorder(SilhouetteBodyParts, rows=3, columns=['regions', 'is_found', 'masks'], status={'OK': 3})
flat names: ('regions_right_leg_x', 'regions_right_leg_y', 'regions_right_leg_width', 'regions_right_leg_height', 'regions_left_leg_x') ... 30
to_numpy shape: (3, 30) | schema.size: 30
images in to_numpy: False | fixed outputs: ['regions', 'is_found']
masks column: list of dict ['right_leg', 'left_leg'] int64
to_frame columns: ['status', 'timestamp', 'regions_right_leg_x', 'regions_right_leg_y'] ... False
Result.to_array size: (30,)
Schema(Output('videogram', shape=(None, None, None), kind=int)) | size: 0 | flat names: ()
(6, 0) ['ndarray']
```


**Status.** corrected vs plan: `to_numpy()` instead of `to_array()`; "images never in `to_array()`" is now verified for `Recorder.to_numpy()`,
`to_frame()` and `Result.to_array()`.

---

## 5. Errors

**Statement.**

| Situation | What happens |
|---|---|
| wrong shape or kind of an input | `ValueError` naming the feature and the input (central check in `Inputs`) |
| NaN or infinity, empty frame, a joint missing from a dict frame | `INVALID_INPUT` with a `reason` (never raises) |
| a dict frame with a key that is not a configured label | `ValueError` listing the expected joints (only when `labels` are configured) |
| too few samples | `WARMING_UP` |
| invalid parameter in the constructor | `ValueError` at construction |
| invalid parameter in a setter (`feature.window = -1`) | `ValueError`; the feature is left as it was (live validation) |
| misspelled keyword | `TypeError` naming the feature, with "did you mean" and the valid names |
| a missing required argument (`window`) | `TypeError` naming the public class and saying what `window` is |
| on/off switch given something other than `True` or `False` (`"on"`, `1`) | `TypeError` |
| a timestamp that is NaN or infinite (every feature; S7, fixed in H) | `INVALID_INPUT`, reason `"non-finite timestamp"`, nothing changes |
| `weights=` of the wrong length or kind (`KineticEnergy`; S5, fixed in H) | `ValueError` ("weights has 1 value, the skeleton has 3 joints"); a sequence with one weight per label is accepted |
| `Symmetry(method="ratio", skeleton=<preset without a reference>)` (S4, fixed in H) | `ValueError` naming the preset and asking for `reference_point=` |

**Evidence.** `data_models/inputs.py:98,130,180-181` (shape messages), `base/labels.py:45-47`, `base/signatures.py:112-120`
(`unexpected_keyword`), `base/core_feature.py:68-76` (`check_range`) and `:324` (called by `_coerce_choices` in the constructor and the setters), `:328-329` and
`physical_signals/humanoid.py:62` (bool check), `data_models/feature.py:228-231` (window and hop), `data_models/feature.py` (`_input_problem`, timestamp);
DEV 91-102, 134-138.

Run `i05_errors`:

```python
import numpy as np
from pyeyesweb.low_level import KineticEnergy, SpectralArcLength

def attempt(label, call):
    try:
        outcome = call()
        print(f"{label}: no error, status {outcome.status.name}, reason {outcome.reason!r}" if hasattr(outcome, "status") else f"{label}: no error")
    except Exception as error:
        print(f"{label}: {type(error).__name__}: {str(error)[:150]}")

energy = KineticEnergy(skeleton="kinect_v2")
joints = energy.parameters["labels"]
frame = {name: (0.0, 0.0, 0.0) for name in joints}
attempt("wrong shape", lambda: energy.process(np.zeros((3, 3))))
attempt("NaN data", lambda: energy.process(np.full((25, 3), np.nan)))
attempt("empty frame", lambda: energy.process(np.zeros((0, 3))))
attempt("missing joint", lambda: energy.process({k: v for k, v in frame.items() if k != "Head"}))
attempt("unknown joint", lambda: energy.process({**frame, "Bogus": (0, 0, 0)}))
attempt("too few samples", lambda: SpectralArcLength(window=20, sampling_rate=100.0).process(1.0))
attempt("bad parameter, constructor", lambda: SpectralArcLength(window=-1, sampling_rate=100.0))
attempt("misspelled keyword", lambda: SpectralArcLength(window=20, sampling_rate=100.0, windw=3))

feature = SpectralArcLength(window=20, sampling_rate=100.0)
attempt("bad parameter, setter", lambda: setattr(feature, "window", -1))
attempt("bad parameter, setter (hop)", lambda: setattr(feature, "hop", 99))
print("after the failed setters:", feature.window, feature.hop)
```

Output:

```text
wrong shape: ValueError: KineticEnergy: input 'skeleton' expects points of shape (25, 3), one row per label (25 labels), got shape (3, 3)
NaN data: no error, status INVALID_INPUT, reason 'NaN or infinite values'
empty frame: no error, status INVALID_INPUT, reason 'empty frame'
missing joint: no error, status INVALID_INPUT, reason 'missing joints: Head'
unknown joint: ValueError: KineticEnergy: unknown joint names ['Bogus']; expected ['SpineBase', 'SpineMid', 'Neck', 'Head', 'ShoulderLeft', 'ElbowLeft', 'WristLeft', 'HandLeft',
too few samples: no error, status WARMING_UP, reason '1 of 20 samples'
bad parameter, constructor: ValueError: SpectralArcLength: window must be >= 1 and 1 <= hop <= window (got window=-1, hop=1)
misspelled keyword: TypeError: SpectralArcLength() got unexpected keyword argument(s) 'windw' (did you mean 'window'?); valid parameters: window, hop, sampling_rate, amplitude_thres
bad parameter, setter: ValueError: SpectralArcLength: window must be >= 10 (got -1)
bad parameter, setter (hop): ValueError: SpectralArcLength: window must be >= 1 and 1 <= hop <= window (got window=20, hop=99)
after the failed setters: 20 1
```


Run `i05b_bool`:

```python
from pyeyesweb.physical_signals import HumanoidSimulator

for value in (True, "on", 1):
    try:
        HumanoidSimulator(start_from_input=value)
        print(repr(value), "accepted")
    except Exception as error:
        print(repr(value), type(error).__name__, str(error)[:120])
```

Output:

```text
True accepted
'on' TypeError start_from_input must be True or False, got 'on'
1 TypeError start_from_input must be True or False, got 1
```


**Status.** verified. Corrected: a wrong joint name raises only when labels are configured (a skeleton, `labels=`); a dict that merely lacks a
joint is `INVALID_INPUT`; a frame array of the wrong number of rows raises.

---

## 6. Time rule

**Statement.** All time is in **seconds**, never frames. The step of a call is decided in this order: the difference to the previous
`timestamp` if both are given; else `1 / sampling_rate` (Hz) if given; else **1 s per sample** and the `reason` says
`"no time given: per-sample derivatives"`.

- `sampling_rate` is a parameter of 16 classes; **its default is `None` in every one** (no hidden rate).
- This step logic and the check "timestamp must increase" (`INVALID_INPUT`, `"non-increasing timestamp"`, previous time kept) belong to
  the **9 classes with `_timed = True`**. The check "timestamp must be finite" is central since H (re-verified in WP5): `INVALID_INPUT`,
  `"non-finite timestamp"`, empty outputs, nothing changed, in every feature (it was a `ValueError` in the 9 classes). The 9 classes are `HumanoidSimulator`,
  `GenericModelSimulator`, `GenericModelPredictor`, `GenericModelEstimator`, `Kinematics`, `KineticEnergy`, `CurvatureDispersion`,
  `MotionNoiseDetector`, `ContractionImpulsivity`.
- **First timed call.** With no previous timestamp (first call, after `reset()`, after a call without timestamp, after a state reset) the
  step is `1 / sampling_rate`, else 1 s: an absolute time is never a step (epoch seconds are fine). A rejected call carries no
  per-sample note. A first call with a timestamp and no `sampling_rate` still reports "no time given: per-sample derivatives".
- The five window metrics (`SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount`,
  `CurvatureVelocityCorrelation`) have no time axis of their own: **`sampling_rate` is required** and `ValueError` at construction
  without it. They take `timestamp` only to put it in `result.timestamp`; **it does not enter the computation and is not checked**
  (a decreasing timestamp is accepted; a NaN or infinite one is `INVALID_INPUT`, S7).
- `ContractionImpulsivity`: `frames` is now `sampling_rate`; without it the index is per frame (unit `1/frame`, and the per-sample note).
  `MotionDuration` and `PhaseLockingValue` also take `sampling_rate` (optional; PLV needs it when a filter band is given).

**Evidence.** `base/core_feature.py:28` (note), `:137` (`_timed`), `:156-157`, `:206-220` (`_time_step`), `:222-226`, `:78-81`
(`require_rate`); `analysis_primitives/synchronization/phase.py:76`; DEV 128-133, 161-163, 287-293.

Run `i06_time`:

```python
from pyeyesweb.low_level import KineticEnergy

def energy(**parameters):
    return KineticEnergy(labels=["a"], weights={"a": 1.0}, **parameters)   # 0.5 * v^2 with unit weight

def run(feature, positions, timestamps=None):
    out = []
    for index, x in enumerate(positions):
        result = feature.process({"a": (x, 0.0, 0.0)}, timestamp=None if timestamps is None else timestamps[index])
        out.append((round(float(result.kinetic_energy), 6), result.reason))
    return out

# the point moves 0.1 m between the two calls
print("timestamps 0.0, 0.5 s          ", run(energy(), [0, 0.1], [0.0, 0.5]))
print("sampling_rate=100 only         ", run(energy(sampling_rate=100.0), [0, 0.1]))
print("neither (1 s per sample)       ", run(energy(), [0, 0.1]))
print("both: the timestamp wins       ", run(energy(sampling_rate=100.0), [0, 0.1], [0.0, 0.5]))
print("epoch seconds, first call      ", run(energy(sampling_rate=100.0), [0, 0.1], [1.7e9, 1.7e9 + 0.5]))

feature = energy(sampling_rate=100.0)
feature.process({"a": (0.0, 0.0, 0.0)})                                      # no timestamp: previous time unknown
print("untimed call, then epoch time  ", feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=1.7e9).kinetic_energy)

feature = energy()
feature.process({"a": (0.0, 0.0, 0.0)}, timestamp=1.0)
repeated = feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=1.0)
print("repeated timestamp             ", repeated.status.name, repr(repeated.reason))
print("next valid call (1.5 s)        ", round(float(feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=1.5).kinetic_energy), 6), "(0.1 m over 0.5 s: previous time kept)")

for bad in (float("nan"), float("inf")):
    rejected = feature.process({"a": (0.1, 0.0, 0.0)}, timestamp=bad)
    print("non-finite timestamp:", rejected.status.name, repr(rejected.reason))
```

Output:

```text
timestamps 0.0, 0.5 s           [(0.0, 'no time given: per-sample derivatives'), (0.02, '')]
sampling_rate=100 only          [(0.0, ''), (50.0, '')]
neither (1 s per sample)        [(0.0, 'no time given: per-sample derivatives'), (0.005, 'no time given: per-sample derivatives')]
both: the timestamp wins        [(0.0, ''), (0.02, '')]
epoch seconds, first call       [(0.0, ''), (0.02, '')]
untimed call, then epoch time   50.0
repeated timestamp              INVALID_INPUT 'non-increasing timestamp'
next valid call (1.5 s)         0.02 (0.1 m over 0.5 s: previous time kept)
non-finite timestamp: INVALID_INPUT 'non-finite timestamp'
non-finite timestamp: INVALID_INPUT 'non-finite timestamp'
```


Run `i06b_rate_required`:

```python
import inspect
import pyeyesweb as pew
from pyeyesweb.low_level import CurvatureVelocityCorrelation, Harmonicity, LogDimensionlessJerk, SpectralArcLength, SubmovementCount
from pyeyesweb.mid_level import ContractionImpulsivity

for cls in (SpectralArcLength, LogDimensionlessJerk, Harmonicity, SubmovementCount, CurvatureVelocityCorrelation):
    try:
        cls(window=20)
    except ValueError as error:
        print(cls.__name__, "->", error)

print("ContractionImpulsivity parameters:", list(inspect.signature(ContractionImpulsivity).parameters))
print("per frame without a rate:", ContractionImpulsivity().process(0.2, 0.1).reason or "(no note)")

with_rate = [info.name for info in pew.catalog() if "sampling_rate" in inspect.signature(info.cls).parameters]
print(len(with_rate), "classes take sampling_rate:", with_rate)
print("defaults that are not None:", {info.name: inspect.signature(info.cls).parameters["sampling_rate"].default
                                       for info in pew.catalog() if "sampling_rate" in inspect.signature(info.cls).parameters
                                       and inspect.signature(info.cls).parameters["sampling_rate"].default is not None})
print("classes with the time rule (timestamp checked, previous time tracked):",
      [info.name for info in pew.catalog() if getattr(info.cls, "_timed", False)])
```

Output:

```text
SpectralArcLength -> SpectralArcLength needs sampling_rate (Hz): the window it works on carries no time of its own
LogDimensionlessJerk -> LogDimensionlessJerk needs sampling_rate (Hz): the window it works on carries no time of its own
Harmonicity -> Harmonicity needs sampling_rate (Hz): the window it works on carries no time of its own
SubmovementCount -> SubmovementCount needs sampling_rate (Hz): the window it works on carries no time of its own
CurvatureVelocityCorrelation -> CurvatureVelocityCorrelation needs sampling_rate (Hz): the window it works on carries no time of its own
ContractionImpulsivity parameters: ['gesture_duration', 'peak_threshold', 'motion_threshold', 'sampling_rate']
per frame without a rate: no time given: per-sample derivatives
16 classes take sampling_rate: ['HumanoidSimulator', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator', 'Kinematics', 'KineticEnergy', 'SpectralArcLength', 'LogDimensionlessJerk', 'Harmonicity', 'SubmovementCount', 'CurvatureDispersion', 'CurvatureVelocityCorrelation', 'MotionNoiseDetector', 'MotionDuration', 'ContractionImpulsivity', 'PhaseLockingValue']
defaults that are not None: {}
classes with the time rule (timestamp checked, previous time tracked): ['HumanoidSimulator', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator', 'Kinematics', 'KineticEnergy', 'CurvatureDispersion', 'MotionNoiseDetector', 'ContractionImpulsivity']
```


Run `i06c_window_timestamps`:

```python
import numpy as np
from pyeyesweb.low_level import SpectralArcLength

signal = np.abs(np.sin(np.linspace(0, 3, 40))) + 0.5
irregular = np.cumsum(np.random.default_rng(0).uniform(0.001, 0.5, 40))

def last_value(timestamps):
    feature = SpectralArcLength(window=20, sampling_rate=100.0)
    for index, value in enumerate(signal):
        result = feature.process(float(value), timestamp=None if timestamps is None else timestamps[index])
    return result

without, irregular_result = last_value(None), last_value(irregular)
print("same value with irregular timestamps:", without.spectral_arc_length == irregular_result.spectral_arc_length,
      "| result.timestamp is still recorded:", round(irregular_result.timestamp, 3))
feature = SpectralArcLength(window=20, sampling_rate=100.0)
print("decreasing timestamps are not checked here, a NaN one is rejected:", [feature.process(1.0, timestamp=t).status.name for t in (5.0, 1.0, float("nan"))])
```

Output:

```text
same value with irregular timestamps: True | result.timestamp is still recorded: 10.752
decreasing timestamps are not checked here, a NaN one is rejected: ['WARMING_UP', 'WARMING_UP', 'INVALID_INPUT']
```


**Status.** corrected vs plan: the non-increasing rule applies to the 9 timed classes, the finite rule (H) to every feature; the window
metrics ignore `timestamp`; first-call and reason texts specified. `sampling_rate` default `None` everywhere and the five metrics
raising: verified. "Warm-up says so in seconds": no, it is a sample count (item 3).

---

## 7. Windows

**Statement.** 22 catalog classes derive from `WindowedFeature`: `window` is in **samples**, `hop` (new samples between two windows)
defaults to 1; they report `WARMING_UP` until the first window is full and `NO_OUTPUT` between hops. Setting `window` or `hop` on
a running feature keeps the newest samples (`configure(window=, hop=)` changes both together; both are validated:
`1 <= hop <= window`).

- `window` has **no default** in 17 classes (a missing one raises `TypeError` saying what `window` is); it has a default in five:
  `SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount` (60) and `MultiScaleEntropy` (3000).
- `EventSynchronization` and `EventSynchronizationMECS` accumulate across windows: `hop=None` means `window` (non-overlapping) and the
  only valid `hop` is `window` (the error says "change both with configure()").
- `CurvatureDispersion` has `window` and **no `hop`** (one result per call). Six classes have a `window` parameter without being windowed
  features: `Videogram`, `CurvatureDispersion`, `FilterContour`, `PositionDependingPotentials`, `Rarity`, `ScalarPeakDetector`.
- `MultiScaleEntropy(window=100)` is refused: the minimum is `max_scale * minimum_points = 6 * 500 = 3000` and the error says so.

**Evidence.** `data_models/feature.py:205-300` (`WindowedFeature`; `_validated` `:228`, `configure` `:252`, `process` `:272-290`),
`analysis_primitives/synchronization/events.py:47`; DEV 70-72, 159-160, 168.

Run `i07_windows`:

```python
import inspect
import pyeyesweb as pew
from pyeyesweb.analysis_primitives import EventSynchronization, MultiScaleEntropy
from pyeyesweb.data_models import WindowedFeature
from pyeyesweb.low_level import CurvatureDispersion

windowed = [info for info in pew.catalog() if issubclass(info.cls, WindowedFeature)]
print(len(windowed), "WindowedFeature classes in the catalog")
print("hop defaults other than 1:", {info.name: inspect.signature(info.cls).parameters["hop"].default
                                      for info in windowed if inspect.signature(info.cls).parameters["hop"].default != 1})
print("window without a default:", [info.name for info in windowed if inspect.signature(info.cls).parameters["window"].default is inspect.Parameter.empty])
print("window with a default:", {info.name: inspect.signature(info.cls).parameters["window"].default
                                  for info in windowed if inspect.signature(info.cls).parameters["window"].default is not inspect.Parameter.empty})
print("classes with a window parameter that are not WindowedFeature:",
      [info.name for info in pew.catalog() if "window" in inspect.signature(info.cls).parameters and not issubclass(info.cls, WindowedFeature)])
print("CurvatureDispersion has hop:", "hop" in inspect.signature(CurvatureDispersion).parameters,
      "| window:", "window" in inspect.signature(CurvatureDispersion).parameters)
print("EventSynchronization(window=10).hop =", EventSynchronization(window=10).hop)
try:
    EventSynchronization(window=10, hop=5)
except ValueError as error:
    print(error)
print("MultiScaleEntropy window default:", inspect.signature(MultiScaleEntropy).parameters["window"].default)
try:
    MultiScaleEntropy(window=100)
except ValueError as error:
    print(error)
feature = MultiScaleEntropy()
print("default builds:", feature.window, feature.parameters["window"])
try:
    EventSynchronization()
except TypeError as error:
    print(error)
```

Output:

```text
22 WindowedFeature classes in the catalog
hop defaults other than 1: {'EventSynchronization': None, 'EventSynchronizationMECS': None}
window without a default: ['CurvatureVelocityCorrelation', 'DirectionChange', 'Suddenness', 'SuddennessImpulsivity', 'SampleEntropy', 'CoarseGraining', 'BinaryPulsesRegularity', 'Periodicity', 'PhaseLockingValue', 'CorrelationsMatrix', 'GeneralisedAutoCorrelation', 'EventSynchronization', 'EventSynchronizationMECS', 'NonlinearInterdependence', 'SpikeSynchronization', 'RecurrencePlot', 'CrossRecurrencePlot']
window with a default: {'SpectralArcLength': 60, 'LogDimensionlessJerk': 60, 'Harmonicity': 60, 'SubmovementCount': 60, 'MultiScaleEntropy': 3000}
classes with a window parameter that are not WindowedFeature: ['Videogram', 'CurvatureDispersion', 'FilterContour', 'PositionDependingPotentials', 'Rarity', 'ScalarPeakDetector']
CurvatureDispersion has hop: False | window: True
EventSynchronization(window=10).hop = 10
EventSynchronization accumulates across executions and cannot take overlapping windows: hop must equal window (got window=10, hop=5); change both with configure()
MultiScaleEntropy window default: 3000
MultiScaleEntropy: window must be >= 3000 (max_scale * minimum_points = 6 * 500: the coarsest scale needs minimum_points samples) (got 100)
default builds: 3000 3000
EventSynchronization() missing required argument(s): window (the number of samples in each analysis window)
```


**Status.** corrected vs plan (counts and defaults added; the plan's "MSE default 3000, EventSynchronization* `hop=None`,
CurvatureDispersion no hop" verified).

---

## 8. Units

**Statement.** Lengths and thresholds are in **metres** (the EyesWeb numbers). `units="m"|"mm"` exists in **exactly 10 classes**
(default `"m"`): `HumanoidSimulator`, `GenericModelSimulator`, `GenericModelPredictor`, `GenericModelEstimator`, `HitCellDetector`,
`Kinematics`, `CurvatureDispersion`, `Equilibrium`, `MotionNoiseDetector`, `TrajectoryNonPlanarity` (the same set as the classes with a
`_unit_params` table). **The parameters are scaled, the data and the outputs never**: a threshold is always written in metres
(`Equilibrium(margin=0.1)`, 0.1 m) and `units` says in what unit your data is; `feature.parameters` reads the value back unscaled.
The power in `_unit_params` is 1 for a length or a speed and 2 for a squared quantity (`MotionNoiseDetector.noise_threshold`).

`Output.unit` is documentation in terms of the data: `"<length>"`, `"<input>"` (unit of the input), `"samples"`, `"frames"`, `"px"`,
`"deg"`, `"s"`, `"cells"`, compounds (`"<length>/s"`, `"<length>^2/s^2"`, `"1/<length>"`, `"1/frame"`), or the concrete unit when `units=`
was given (`"m/s"`, `"mm/s"`, `"mm"`). **The text follows the parameters**: `MotionDuration` is in `"frames"` without a rate and in `"s"`
with one. An empty unit means dimensionless.

**Humanoid exception (verified).** `HumanoidSimulator` works internally in millimetres (the EyesWeb body model is in mm and its spring
forces depend on the length unit). `units` declares the unit of your frames, of `gravity` / `floor_position` and of the outputs; the wrapper
multiplies frames by 1000 on the way in and divides joints by 1000 on the way out for `"m"` (nothing for `"mm"`). A body run in
metres equals the millimetre run to rounding (below: 2e-18 mm); metres declared as `"mm"` give a different motion (not scale free).
The `GenericModel*` features run in the unit of **your model** and `units` only names it: the numbers are identical for `"m"`
and `"mm"`. (The `process` docstring of `HumanoidSimulator` still says "in mm": see the suspected inconsistencies.)

**Evidence.** `base/core_feature.py:25` (`_UNIT_FACTORS`), `:123-139`, `:154-155`, `:179-193` (parameters scaled, `units` removed from the
block parameters); `low_level/equilibrium.py:63`, `low_level/kinematics.py:82`, `low_level/motion_noise.py:30`, `low_level/non_planarity.py:25`, `low_level/smoothness.py:245`,
`physical_signals/space.py:32`, `physical_signals/humanoid.py:174-196` (`_Units`, `_internal_mm`, `_to_core`), `:277-285`, `:538-545`; DEV 295-305.

Run `i08_units`:

```python
import inspect
import numpy as np
import pyeyesweb as pew
from pyeyesweb.low_level import Equilibrium, Kinematics

with_units = {info.name: inspect.signature(info.cls).parameters["units"].default
              for info in pew.catalog() if "units" in inspect.signature(info.cls).parameters}
print(len(with_units), "classes take units; defaults:", set(with_units.values()))
print(sorted(with_units))
print("same set as _unit_params:", sorted(with_units) == sorted(info.name for info in pew.catalog() if getattr(info.cls, "_unit_params", None)))
print("Equilibrium margin default (metres):", Equilibrium().parameters["margin"], "| _unit_params:", Equilibrium._unit_params)
print(Kinematics().outputs, Kinematics(units="mm").outputs)

# parameters are scaled, data and outputs are not: the same trajectory in m and in mm
rng = np.random.default_rng(0)
path_m = np.cumsum(rng.normal(scale=0.01, size=(40, 3)), axis=0)
def speed(units, factor, threshold):
    feature = Kinematics(units=units, sampling_rate=100.0, movement_threshold=threshold)
    rec = feature.run(path_m * factor)
    return rec.velocity
metres = speed("m", 1.0, 0.05)
millimetres = speed("mm", 1000.0, 0.05)       # the threshold is still given in metres: 0.05 m
print("velocity mm/s / velocity m/s:", np.round(millimetres[5:9] / metres[5:9], 3))
print("parameter read back unscaled:", Kinematics(units="mm", movement_threshold=0.05).parameters["movement_threshold"])
```

Output:

```text
10 classes take units; defaults: {'m'}
['CurvatureDispersion', 'Equilibrium', 'GenericModelEstimator', 'GenericModelPredictor', 'GenericModelSimulator', 'HitCellDetector', 'HumanoidSimulator', 'Kinematics', 'MotionNoiseDetector', 'TrajectoryNonPlanarity']
same set as _unit_params: True
Equilibrium margin default (metres): 0.1 | _unit_params: {'margin': 1}
Schema(Output('velocity', unit='m/s')) Schema(Output('velocity', unit='mm/s'))
velocity mm/s / velocity m/s: [1000. 1000. 1000. 1000.]
parameter read back unscaled: 0.05
```


Run `i08b_humanoid`:

```python
import numpy as np
from pyeyesweb._core import core
from pyeyesweb.physical_signals import HUMANOID_JOINTS, GenericModelSimulator, HumanoidSimulator, MassSpringModel

positions = core.humanoid.HumanoidSimulator().positions()           # the EyesWeb body, built in millimetres
pose_mm = np.array([positions[name] for name in HUMANOID_JOINTS])
frames_mm = np.stack([pose_mm + 5.0 * np.sin(i / 3.0) * np.eye(21, 3) for i in range(12)])

rec_mm = HumanoidSimulator(units="mm", sampling_rate=25.0).run(frames_mm)
rec_m = HumanoidSimulator(units="m", sampling_rate=25.0).run(frames_mm / 1000.0)
print("left_hand, last frame: mm run", np.round(rec_mm.joints[-1][HUMANOID_JOINTS.index("left_hand")], 3),
      "| m run x 1000", np.round(rec_m.joints[-1][HUMANOID_JOINTS.index("left_hand")] * 1000, 3))
print("max |difference| in mm:", float(np.abs(rec_mm.joints - rec_m.joints * 1000).max()))
wrong = HumanoidSimulator(units="mm", sampling_rate=25.0).run(frames_mm / 1000.0)      # metres declared as millimetres
print("metres declared as mm (wrong): max |difference| to the correct run, metres:", round(float(np.abs(wrong.joints - rec_m.joints).max()), 4))
print(HumanoidSimulator(units="m").outputs, HumanoidSimulator(units="mm").outputs)

model = MassSpringModel()
model.add_mass("a", 1.0, (0, 0, 0)); model.add_mass("b", 1.0, (0.3, 0, 0))
model.add_spring("s", "a", "b", 0.3, 100.0, (1, 0, 0), 10.0, 1.0, 1.0)
directions = np.stack([[[np.cos(0.1 * i), np.sin(0.1 * i), 0.0]] for i in range(8)])      # one spring: one direction per frame
a = GenericModelSimulator(model, units="m", sampling_rate=100.0).run(directions)
b = GenericModelSimulator(model, units="mm", sampling_rate=100.0).run(directions)
print("GenericModelSimulator, units only names the unit: identical numbers:", np.array_equal(a.positions, b.positions),
      "|", GenericModelSimulator(model, units="mm").outputs)
```

Output:

```text
left_hand, last frame: mm run [-4.31564e+02  1.50076e+02 -3.72000e-01] | m run x 1000 [-4.31564e+02  1.50076e+02 -3.72000e-01]
max |difference| in mm: 1.734723475976807e-18
metres declared as mm (wrong): max |difference| to the correct run, metres: 1351.961
Schema(Output('joints', shape=(21, 3), unit='m')) Schema(Output('joints', shape=(21, 3), unit='mm'))
GenericModelSimulator, units only names the unit: identical numbers: True | Schema(Output('positions', shape=(2, 3), unit='mm'))
```


Unit strings as built by the test helper (some features are built with `units=`, a rate or another non-default argument there; the
last lines show how the text follows the parameters):

Run `i08c_unit_strings`:

```python
import collections, sys
import pyeyesweb as pew

tests = r"<workspace>/PyEyesWeb/tests"
sys.path[:0] = [tests + "/unit_tests", tests + "/_support"]
from test_contract_all_features import NAMES, factory_and_recordings    # the test suite's way to build every catalog feature

units = collections.defaultdict(list)
for name in NAMES:
    for output in factory_and_recordings(name)[0]().outputs:
        units[output.unit].append(f"{name}.{output.name}")
for unit, outputs in sorted(units.items()):
    shown = outputs if len(outputs) <= 6 else outputs[:6] + [f"... ({len(outputs)} outputs)"]
    print(f"{unit!r:24s} {', '.join(shown)}")
print(len(NAMES), "of", len(pew.catalog()), "catalog features built by the helper")

# the unit text follows the parameters: a rate turns frames into seconds, units= names the length unit
from pyeyesweb.low_level import TrajectoryNonPlanarity
from pyeyesweb.mid_level import ContractionImpulsivity, MotionDuration
for feature in (MotionDuration(), MotionDuration(sampling_rate=100.0), ContractionImpulsivity(), ContractionImpulsivity(sampling_rate=100.0),
                TrajectoryNonPlanarity(units="mm"), TrajectoryNonPlanarity(output_type="curvature_value")):
    print(type(feature).__name__, feature.outputs)
```

Output:

```text
''                       HumanoidOrientations.directions, GenericModelEstimator.error, SilhouetteCentroids.normalized, SilhouetteBodyParts.is_found, SilhouetteBodyParts.masks, Videogram.videogram, ... (64 outputs)
'1/<length>'             CurvatureVelocityCorrelation.curvature, CurvatureVelocityCorrelation.curvature_std, ContourCurvature.curvature
'1/frame'                ContractionImpulsivity.impulsivity_index
'<input>'                GestureSegmenter.smoothed_intensity, EnsembleDominance.leader_complexity, CoarseGraining.coarse_grained
'<length>'               GenericModelOrientations.directions, PointsPredictor.predicted, EllipsoidSphericity.radii, PointsDensity.density, PointsDensity.centroid, FilterContour.contour, ... (9 outputs)
'<length>/s'             CurvatureVelocityCorrelation.velocity, CurvatureVelocityCorrelation.velocity_std
'<length>^2'             DirectionChange.polygon
'<length>^2/s^2'         KineticEnergy.kinetic_energy
'cells'                  HitCellDetector.cells
'deg'                    Equilibrium.angle
'frames'                 MotionDuration.motion_duration, MotionDuration.pause_duration, ContractionImpulsivity.gesture_duration
'm'                      TrajectoryNonPlanarity.curvature_radius
'm/s'                    Kinematics.velocity
'mm'                     HumanoidSimulator.joints, GenericModelSimulator.positions, GenericModelPredictor.positions, GenericModelEstimator.positions
'px'                     SilhouetteCentroids.centroids, SilhouetteBodyParts.regions
'samples'                Periodicity.periods, GeneralisedAutoCorrelation.taus
60 of 60 catalog features built by the helper
MotionDuration Schema(Output('motion_duration', unit='frames'), Output('pause_duration', unit='frames'))
MotionDuration Schema(Output('motion_duration', unit='s'), Output('pause_duration', unit='s'))
ContractionImpulsivity Schema(Output('impulsivity_index', unit='1/frame'), Output('gesture_duration', unit='frames'))
ContractionImpulsivity Schema(Output('impulsivity_index', unit='1/s'), Output('gesture_duration', unit='frames'))
TrajectoryNonPlanarity Schema(Output('curvature_radius', unit='mm'))
TrajectoryNonPlanarity Schema(Output('curvature', unit='1/m'))
```


**Status.** corrected vs plan: the number of unit-aware classes is 10 and the list is given; unit strings added (`cells`, compounds); "units
exist" is not a property of every feature. Humanoid claim verified by running.

---

## 9. Choices, booleans, parts

**Statement.** A parameter that picks one of several options is a **lower-case string**; matching is case-insensitive, `-` and space count as
`_`, and a wrong value raises `ValueError` listing the options (also from a setter). On/off switches are real `bool`s (`"on"`, `1` raise
`TypeError`). There are no enums in the public parameters: the only `Enum` classes reachable from the public modules are `Layer`,
`Timescale` (catalog metadata), `InputKind` and `Status` (data model). A core enum member passed by mistake is accepted silently.
A variant feature rejects the parameters of another variant (`Symmetry(method="reflection", aggregation=...)` is a `TypeError`).

`parts=` replaces the bool switches in `SilhouetteCentroids` (14 names), `SilhouetteBodyParts` (6) and `RegionDependingPotentials` (4,
default `("potential",)`): a sequence of names, validated like any choice, **read back as a tuple in the block's declaration order**, which is
not the order of the docs: `SilhouetteBodyParts` is `right_leg, left_leg, trunk, right_arm, left_arm, head` (DEV 175 lists it as head, trunk, ...).
It is live where the switches were.

`output_dims` is not one vocabulary: `Kinematics` `components | tangential` (default `tangential`), `PointsDensity` `components | module`
(default `module`), `Symmetry` `global | components` (default `global`).

**Evidence.** `base/choices.py:15-26` (`coerce_choice`), `base/core_feature.py:317` (`_coerce_choices`), `:329` (bool), `:142-149`, `:158-159`, `:181`
(`_parts`); DEV 246-264.

Run `i09_choices`:

```python
import inspect
import pyeyesweb as pew
import pyeyesweb.physical_signals as physical
from pyeyesweb import skeletons
from pyeyesweb.low_level import Symmetry
from pyeyesweb.mid_level import RegionDependingPotentials
from pyeyesweb.physical_signals import SilhouetteBodyParts, SilhouetteCentroids

symmetry = Symmetry(skeleton="kinect_v2", method="Ratio", aggregation="Weighted-Mean")
print(symmetry.parameters["method"], symmetry.parameters["aggregation"])
print(Symmetry(skeleton="kinect_v2", method="REFLECTION").parameters["method"])
try:
    Symmetry(skeleton="kinect_v2", method="reflection", aggregation="mean")
except TypeError as error:
    print(error)
try:
    Symmetry(skeleton="kinect_v2", method="zzz")
except ValueError as error:
    print(error)
try:
    symmetry.aggregation = "median"
except ValueError as error:
    print("setter:", error)

print("parts as given vs read back")
for cls, given in ((SilhouetteCentroids, ["Left-Hand", "head"]), (SilhouetteBodyParts, ["head", "right arm"]), (RegionDependingPotentials, ["region_values", "potential"])):
    feature = cls(parts=given)
    print(f"  {cls.__name__}: {given} -> {feature.parameters['parts']}")
    print("   declared order:", tuple(cls().parameters["parts"]))
try:
    SilhouetteBodyParts(parts=["tail"])
except ValueError as error:
    print(error)
import enum
import pyeyesweb.data_models as data_models, pyeyesweb.high_level as high, pyeyesweb.low_level as low, pyeyesweb.mid_level as mid
import pyeyesweb.analysis_primitives as analysis
modules = (pew, physical, data_models, skeletons, high, low, mid, analysis)
print("Enum classes reachable from the public modules:", sorted({f"{module.__name__}.{name}" for module in modules for name in dir(module)
                                                                  if isinstance(getattr(module, name), type) and issubclass(getattr(module, name), enum.Enum)}))
print("catalog parameters annotated with an Enum:", [(info.name, name) for info in pew.catalog() for name, parameter in inspect.signature(info.cls).parameters.items()
                                                    if isinstance(parameter.annotation, type) and issubclass(parameter.annotation, enum.Enum)])
print("output_dims:", {info.name: str(inspect.signature(info.cls).parameters["output_dims"].annotation).replace("typing.", "") + " = " + repr(inspect.signature(info.cls).parameters["output_dims"].default)
                       for info in pew.catalog() if "output_dims" in inspect.signature(info.cls).parameters})
```

Output:

```text
ratio weighted_mean
reflection
method='reflection' does not take aggregation
method: invalid value 'zzz'; choose one of 'reflection', 'ratio'
setter: aggregation: invalid value 'median'; choose one of 'mean', 'min', 'max', 'weighted_mean'
parts as given vs read back
  SilhouetteCentroids: ['Left-Hand', 'head'] -> ('head', 'left_hand')
   declared order: ('center_of_gravity', 'head', 'left_shoulder', 'left_elbow', 'left_forearm', 'left_hand', 'right_shoulder', 'right_elbow', 'right_forearm', 'right_hand', 'left_knee', 'left_foot', 'right_knee', 'right_foot')
  SilhouetteBodyParts: ['head', 'right arm'] -> ('right_arm', 'head')
   declared order: ('right_leg', 'left_leg', 'trunk', 'right_arm', 'left_arm', 'head')
  RegionDependingPotentials: ['region_values', 'potential'] -> ('potential', 'region_values')
   declared order: ('potential',)
parts: invalid value 'tail'; choose one of 'right_leg', 'left_leg', 'trunk', 'right_arm', 'left_arm', 'head'
Enum classes reachable from the public modules: ['pyeyesweb.Layer', 'pyeyesweb.Timescale', 'pyeyesweb.data_models.InputKind', 'pyeyesweb.data_models.Status']
catalog parameters annotated with an Enum: []
output_dims: {'Kinematics': "Literal['components', 'tangential'] = 'tangential'", 'PointsDensity': "Literal['components', 'module'] = 'module'", 'Symmetry': "Literal['global', 'components'] = 'global'"}
```


**Status.** verified; corrected: read-back order of `parts=`, the `output_dims` vocabularies, the exact list of enums.

---

## 10. `from_*` constructors

**Statement.** Exactly **three classes (six constructors)** have them, one per `input_mode`, each taking the constructor's parameters
except `input_mode`; `input_mode` stays an ordinary parameter. They are descriptors that build the function per class (a subclass shows and
checks its own parameters). List them by introspection, never by hand:

| Class | Constructors | `input_mode` values |
|---|---|---|
| `KineticEnergy` | `from_position`, `from_velocity` | `"position"` (default), `"velocity"` |
| `Kinematics` | `from_point`, `from_series` | `"point"` (default), `"time_series"` |
| `LogDimensionlessJerk` | `from_velocity`, `from_acceleration` | `"velocity"` (default), `"acceleration"` |

**Evidence.** `base/signatures.py:143-167` (`_InputModeFactory`, `input_mode_factory`); `low_level/energy.py:47-56`; DEV 250-254.

Run `i10_from`:

```python
import inspect
import numpy as np
import pyeyesweb as pew
from pyeyesweb.low_level import Kinematics, KineticEnergy, LogDimensionlessJerk

for info in pew.catalog():
    for name in dir(info.cls):
        if name.startswith("from_") and callable(getattr(info.cls, name)):
            print(f"{info.name}.{name}{inspect.signature(getattr(info.cls, name))}"[:170])

velocity = KineticEnergy.from_velocity(skeleton="kinect_v2")
print(velocity.parameters["input_mode"], "|", KineticEnergy.from_position(skeleton="kinect_v2").parameters["input_mode"], "| default:", KineticEnergy(skeleton="kinect_v2").parameters["input_mode"])
for factory in (Kinematics.from_point(), Kinematics.from_series(), LogDimensionlessJerk.from_velocity(sampling_rate=100.0), LogDimensionlessJerk.from_acceleration(sampling_rate=100.0)):
    print(type(factory).__name__, factory.parameters["input_mode"], "|", factory.inputs)
```

Output:

```text
Kinematics.from_point(*, dims: Optional[int] = None, output_dims: Literal['components', 'tangential'] = 'tangential', output_type: Union[Literal['smoothed', 'velocity', '
Kinematics.from_series(*, dims: Optional[int] = None, output_dims: Literal['components', 'tangential'] = 'tangential', output_type: Union[Literal['smoothed', 'velocity', 
KineticEnergy.from_position(labels: Optional[Sequence[str]] = None, skeleton: Any = None, *, weights: collections.abc.Mapping[str, float] | None = None, reference_point: 
KineticEnergy.from_velocity(labels: Optional[Sequence[str]] = None, skeleton: Any = None, *, weights: collections.abc.Mapping[str, float] | None = None, reference_point: 
LogDimensionlessJerk.from_acceleration(window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None)
LogDimensionlessJerk.from_velocity(window: int = 60, hop: int = 1, *, sampling_rate: Optional[float] = None)
velocity | position | default: position
Kinematics point | Inputs(point: sample (?) - position of the point (or value of the signal))
Kinematics time_series | Inputs(series: matrix (?, ?) - (D, N) series, newest sample last)
LogDimensionlessJerk velocity | Inputs(signal: sample (1) [units/s or units/s^2] - speed or acceleration magnitude of the movement, as `input_mode` says)
LogDimensionlessJerk acceleration | Inputs(signal: sample (1) [units/s or units/s^2] - speed or acceleration magnitude of the movement, as `input_mode` says)
```


**Status.** corrected vs plan (the plan said "list by introspection": done; membership is exactly the three classes above).

---

## 11. Skeletons and joints

**Statement.** `pyeyesweb.skeletons` (`__all__`: `Skeleton`, `KINECT_V2`, `QUALISYS_SPORT`, `MEDIAPIPE`, `OPENPOSE`, `SKELETONS`,
`SKELETON_TODO`, `get_skeleton`, `with_skeleton`). A preset is selected by name (`"kinect_v2"`, `"qualisys_sport"`, `"mediapipe"`,
`"openpose"`; case-insensitive, `-` and space count as `_`) or by a `Skeleton(name, joints, pairs=(), reference=None, weights=None)` you build
(frozen; repeated joint names and names that are not joints raise `ValueError`). `Skeleton.index(name)`, `weights_or_uniform()`, `missing()`.

| Preset | Joints | Pairs | Reference | Weights | `SKELETON_TODO` |
|---|---|---|---|---|---|
| `kinect_v2` | 25 | 10 | `SpineShoulder` | filled | `()` complete |
| `qualisys_sport` | 41 | 18 | `None` | `None` | `('reference', 'weights')` |
| `mediapipe` | 33 | 16 | `None` | `None` | `('reference', 'weights')` |
| `openpose` | 25 | 11 | `Neck` | `None` | `('weights',)` |

- **`skeleton=` is accepted by exactly five classes**: `KineticEnergy` (joints, weights), `MotionNoiseDetector`, `Symmetry` (joints, pairs,
  reference; both methods), `PointsDensity`, `PointsPredictor`. (DEV 315 also lists `GestureSegmenter`: it takes none, that sentence is
  stale; `Equilibrium` takes none either.) An explicit `labels=`, `weights=`, `pairs=` always wins over the skeleton; without any joint
  information the feature raises `ValueError` at construction.
- **`joint_map` exists only on six classes**: `HumanoidSimulator`, `HumanoidOrientations`, `GenericModelOrientations`,
  `GenericModelSimulator`, `GenericModelPredictor`, `GenericModelEstimator` (`joint of the model -> label of your data`; HUMANOID_JOINTS has 21 names).
  Other features with `labels`: `PointsPredictor`, `PointsDensity`, `Symmetry`, `KineticEnergy`, `MotionNoiseDetector`.
- **Incomplete presets stay documented as incomplete** (decided). Only the ratio symmetry raises (below). A missing `weights` silently becomes **uniform weights of 1.0**
  (so kinetic-energy values on `qualisys_sport`, `mediapipe` and `openpose` are not comparable with `kinect_v2` and are not the EyesWeb numbers); a missing
  `reference` means: `Symmetry(method="reflection")` uses the barycentre (`reference_point=None`); `Symmetry(method="ratio")` raises
  `ValueError` at construction naming the preset and asking for `reference_point=` (S4, fixed in H; an explicit `reference_point=` works; since I-a `reference_type` accepts only `"label"`, `"barycenter"` and `"point"` raise `ValueError`, see section 21). The `TODO(fill)` markers are at
  `skeletons.py:71,72,89,90,103`; re-check when the maintainer fills them. Naming is inconsistent across presets (`L*/R*`, `*Left/*Right`,
  `left_*/right_*`; `RelbowOut` keeps the TSV spelling): document, do not normalise.
- A dict frame must use the preset joint names (unknown key: `ValueError`; missing weighted joint: `INVALID_INPUT` "missing joints: ..."); an array frame
  must have the preset's number of rows (`ValueError`).

**Evidence.** `skeletons.py:25` (`__all__`), `:71-72,89-90,103` (`TODO(fill)`), `:109` (`SKELETON_TODO`), `:112` (`get_skeleton`), `:124-132`
(`with_skeleton`); `data_models/skeleton.py:9-44`; `base/labels.py:45-47`; DEV 313-320.

Run `i11_skeletons`:

```python
import inspect
import pyeyesweb as pew
from pyeyesweb import skeletons
from pyeyesweb.skeletons import SKELETON_TODO, SKELETONS, Skeleton, get_skeleton
from pyeyesweb.physical_signals import HUMANOID_JOINTS

print(skeletons.__all__)
for name, skeleton in SKELETONS.items():
    print(f"{name:15s} joints={len(skeleton.joints):2d} pairs={len(skeleton.pairs):2d} reference={skeleton.reference!r:15} weights={'yes' if skeleton.weights else 'None':4} todo={SKELETON_TODO[name]}")
print("case/dash insensitive:", get_skeleton("Kinect-V2").name)
try:
    get_skeleton("kinect")
except ValueError as error:
    print(error)
print("classes with skeleton=:", [info.name for info in pew.catalog() if "skeleton" in inspect.signature(info.cls).parameters])
print("classes with labels=:", [info.name for info in pew.catalog() if "labels" in inspect.signature(info.cls).parameters])
print("classes with joint_map=:", [info.name for info in pew.catalog() if "joint_map" in inspect.signature(info.cls).parameters])
print("classes with pairs=:", [info.name for info in pew.catalog() if "pairs" in inspect.signature(info.cls).parameters])
print("classes with weights=:", [info.name for info in pew.catalog() if "weights" in inspect.signature(info.cls).parameters])
print("HUMANOID_JOINTS:", len(HUMANOID_JOINTS), HUMANOID_JOINTS[:3], "...")
```

Output:

```text
['Skeleton', 'KINECT_V2', 'QUALISYS_SPORT', 'MEDIAPIPE', 'OPENPOSE', 'SKELETONS', 'SKELETON_TODO', 'get_skeleton', 'with_skeleton']
kinect_v2       joints=25 pairs=10 reference='SpineShoulder' weights=yes  todo=()
qualisys_sport  joints=41 pairs=18 reference=None            weights=None todo=('reference', 'weights')
mediapipe       joints=33 pairs=16 reference=None            weights=None todo=('reference', 'weights')
openpose        joints=25 pairs=11 reference='Neck'          weights=None todo=('weights',)
case/dash insensitive: kinect_v2
skeleton: invalid value 'kinect'; choose one of 'kinect_v2', 'qualisys_sport', 'mediapipe', 'openpose' (or a Skeleton)
classes with skeleton=: ['PointsPredictor', 'KineticEnergy', 'PointsDensity', 'Symmetry', 'MotionNoiseDetector']
classes with labels=: ['HumanoidSimulator', 'HumanoidOrientations', 'GenericModelOrientations', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator', 'PointsPredictor', 'KineticEnergy', 'PointsDensity', 'Symmetry', 'MotionNoiseDetector']
classes with joint_map=: ['HumanoidSimulator', 'HumanoidOrientations', 'GenericModelOrientations', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator']
classes with pairs=: ['Symmetry']
classes with weights=: ['KineticEnergy']
HUMANOID_JOINTS: 21 ('head', 'left_ankle', 'left_elbow') ...
```


Run `i11b_skeleton_override`:

```python
from pyeyesweb.low_level import KineticEnergy, Symmetry
from pyeyesweb.skeletons import Skeleton

own = Skeleton("tiny", joints=("a", "b", "c"), pairs=(("a", "b"),), reference="c", weights={"a": 1.0, "b": 2.0, "c": 3.0})
print(own.missing(), own.weights_or_uniform())
print(dict(KineticEnergy(skeleton=own).parameters["weights"]))
print(dict(KineticEnergy(skeleton=own, weights={"a": 5.0, "b": 5.0, "c": 5.0}).parameters["weights"]), "(weights= wins)")
print(KineticEnergy(skeleton="mediapipe").parameters["weights"] and set(KineticEnergy(skeleton="mediapipe").parameters["weights"].values()), "(mediapipe: no weights, uniform 1.0)")
try:
    KineticEnergy()
except ValueError as error:
    print(error)
print(Symmetry(skeleton=own).parameters["pairs"] if "pairs" in Symmetry(skeleton=own).parameters else Symmetry(skeleton=own).parameters)
```

Output:

```text
() {'a': 1.0, 'b': 2.0, 'c': 3.0}
{'a': 1.0, 'b': 2.0, 'c': 3.0}
{'a': 5.0, 'b': 5.0, 'c': 5.0} (weights= wins)
{1.0} (mediapipe: no weights, uniform 1.0)
KineticEnergy: no joints given; pass skeleton= (e.g. 'kinect_v2') or your own weights= / pairs=
[('a', 'b')]
```


**Status.** corrected vs plan: `joint_map` is humanoid-only, the exact `skeleton=` list, the uniform-weight fallback (the plan's "verify" is closed).

---

## 12. `dims`

**Statement.** `dims` exists in **four classes only**: `Kinematics`, `CurvatureDispersion`, `Suddenness`, `SuddennessImpulsivity` (all `dims=None`).
`None` is taken from the first frame: before that the shapes of `inputs` are unknown (`?`), after it `parameters["dims"]` reads the value;
a later frame of another size raises the shape `ValueError`; `reset()` forgets the inferred value (an explicit `dims` stays). An explicit `dims` fixes
the shapes before any data (for a host that declares outputs ahead of data). Other features do not take `dims`: their frame sizes are fixed by labels or by the
first call (`WindowedFeature` fixes the number of values at the first frame after `reset()`).

**Evidence.** `base/inputs.py:82-110` (`InferredDims`); DEV 307-311.

Run `i12_dims`:

```python
import inspect
import numpy as np
import pyeyesweb as pew
from pyeyesweb.low_level import Kinematics

print("classes with dims:", {info.name: inspect.signature(info.cls).parameters["dims"].default for info in pew.catalog() if "dims" in inspect.signature(info.cls).parameters})
feature = Kinematics(sampling_rate=100.0)
print("before data:", feature.outputs, "| dims:", feature.parameters["dims"])
feature.process((0.0, 0.0), timestamp=0.0)
print("after a 2D frame:", feature.inputs, "| dims:", feature.parameters["dims"])
try:
    feature.process((0.0, 0.0, 0.0), timestamp=0.01)
except ValueError as error:
    print(error)
fixed = Kinematics(dims=3, sampling_rate=100.0)
print("dims=3:", fixed.inputs)
feature.reset()
print("after reset(), a 3D frame:", feature.process((0.0, 0.0, 0.0), timestamp=0.0).status.name, feature.inputs)
```

Output:

```text
classes with dims: {'Kinematics': None, 'CurvatureDispersion': None, 'Suddenness': None, 'SuddennessImpulsivity': None}
before data: Schema(Output('velocity', unit='m/s')) | dims: None
after a 2D frame: Inputs(point: sample (2) - position of the point (or value of the signal)) | dims: 2
Kinematics: input 'point' expects sample of shape (2,), got shape (3,)
dims=3: Inputs(point: sample (3) - position of the point (or value of the signal))
after reset(), a 3D frame: OK Inputs(point: sample (3) - position of the point (or value of the signal))
```


**Status.** corrected vs plan ("`dims=None` is inferred from the first frame" is true only for these four classes).

---

## 13. Layers and catalog

**Statement.** `pyeyesweb.catalog(layer=None)` returns `FeatureInfo(name, layer, timescale, eyesweb_block, module, summary, cls)` for the
**60** features, in layer order; **11 physical_signals, 22 low_level, 7 mid_level, 1 high_level, 19 analysis_primitives**. `Layer` has
`PHYSICAL_SIGNALS`, `LOW_LEVEL`, `MID_LEVEL`, `HIGH_LEVEL`, `ANALYSIS_PRIMITIVE` (values `physical_signals`, ..., `analysis_primitives`;
`.package`, `.title`); `Timescale` has `FRAME` ("frame"), `SHORT` ("up to ~0.5 s"), `MEDIUM` ("0.5-3 s"), `LONG` ("3 s and above"), `ANY` ("any"); the layer
default timescale is in `catalog.py:64-70`. `catalog_table(layer)` renders `| Feature | Timescale | EyesWeb block |`. 47 features carry an EyesWeb block,
13 are lab features (listed below).

**Placement rule** (the `catalog` docstring, `catalog.py:13-27`): a feature goes to the layer of what it needs as input and gives as output, not of its
EyesWeb block. Physical signals produce a signal from raw frames or a model and give a signal again (simulating a body, centroids or parts from
an image, locating points in a grid; stream plumbing that feeds the features). Low-level measures one frame, or a short window the feature buffers itself, of a signal
(kinematics, energy, symmetry, smoothness), including the shape and filtering of a contour and a path given as a list of points (directness, non-planarity).
Mid-level needs a whole gesture. High-level needs several people. An analysis primitive takes any scalar, vector or event signal and knows nothing of bodies,
skeletons or geometry. `FilterContour`, `Directness`, `TrajectoryNonPlanarity` are **low-level**.

**Layer count (WP5).** The conceptual model has **four layers** (physical signals, low-level, mid-level, high-level: "Layer 1" to "Layer 4" in `Layer.title`); the analysis primitives are a fifth *group*, not a layer
(`Layer.ANALYSIS_PRIMITIVE.title` has no number). Pages say "four layers and the analysis primitives" or "five groups"; the wording "five layers" (`index.md`, `api/overview.md`) is inaccurate.

The synchronization package (`pyeyesweb.analysis_primitives.synchronization`) has **12** classes (the plan said 11): 12 of the 19 analysis primitives; the other 7
are `SampleEntropy`, `CoarseGraining`, `Rarity`, `BinaryPulsesRegularity`, `MultiScaleEntropy`, `Periodicity`, `ScalarPeakDetector`.

Public names: `dir(pyeyesweb)` lists `Layer`, `Timescale`, `catalog`, `catalog_table`, `SeriesBuffer` (loaded from the core on demand, not in `__all__`) and the public
modules `physical_signals`, `low_level`, `mid_level`, `high_level`, `analysis_primitives`, `data_models`, `skeletons`. `pyeyesweb.base` and `pyeyesweb.utils` are internal: not listed
in `dir()`, **but attribute access still works** (`hasattr(pyeyesweb, "base")` is true once imported), so the docs must simply not document them. `pyeyesweb.utils`
holds only `validators`. `physical_signals` also exports non-feature names: `MassSpringModel`, `HUMANOID_JOINTS`, `HUMANOID_BONES`, `SynchronizedWindow`,
`TimeWindowSynchronizer`; `low_level` exports `average_curvature_3d`.

**Evidence.** `catalog.py:1-120`, `__init__.py:1-32`, `analysis_primitives/synchronization/__init__.py`, `physical_signals/__init__.py:9-15`; DEV 195-203, 209-211.

Run `i13_catalog`:

```python
import collections, importlib, inspect
import pyeyesweb as pew
from pyeyesweb import Layer

catalog = pew.catalog()
print(len(catalog), "features;", {layer.value: len(pew.catalog(layer)) for layer in Layer})
print({layer.name: layer.title for layer in Layer})
print("timescales:", {info.layer.value: info.timescale.value for info in catalog})
print("features per synchronization module:", collections.Counter(info.module.rsplit('.', 1)[-1] for info in catalog if "synchronization" in info.module))
print("classes in pyeyesweb.analysis_primitives.synchronization:", len(importlib.import_module("pyeyesweb.analysis_primitives.synchronization").__all__))
print("moved to low_level:", [(info.name, info.layer.value, info.module) for info in catalog if info.name in ("FilterContour", "Directness", "TrajectoryNonPlanarity")])
print("dir(pyeyesweb):", dir(pew))
print("pyeyesweb.__all__:", pew.__all__)
print("hasattr base/utils:", hasattr(pew, "base"), hasattr(pew, "utils"), "| listed in dir:", "base" in dir(pew) or "utils" in dir(pew))
print(pew.catalog_table(Layer.HIGH_LEVEL))
print("with an EyesWeb block:", sum(info.eyesweb_block is not None for info in catalog), "| without (lab features):", [info.name for info in catalog if info.eyesweb_block is None])
print("catalog entries are classes of a FeatureInfo:", type(catalog[0]).__name__, [f for f in catalog[0].__dataclass_fields__])
public_not_in_catalog = {}
for layer in Layer:
    package = importlib.import_module(layer.package)
    listed = {info.name for info in pew.catalog(layer)}
    public_not_in_catalog[layer.value] = [name for name in package.__all__ if name not in listed]
print("exported by a layer package but not catalog features:", public_not_in_catalog)
```

Output:

```text
60 features; {'physical_signals': 11, 'low_level': 22, 'mid_level': 7, 'high_level': 1, 'analysis_primitives': 19}
{'PHYSICAL_SIGNALS': 'Layer 1: physical signals', 'LOW_LEVEL': 'Layer 2: low-level features', 'MID_LEVEL': 'Layer 3: mid-level features', 'HIGH_LEVEL': 'Layer 4: qualities communicated', 'ANALYSIS_PRIMITIVE': 'Analysis primitives'}
timescales: {'physical_signals': 'frame', 'low_level': 'up to ~0.5 s', 'mid_level': '0.5-3 s', 'high_level': '3 s and above', 'analysis_primitives': 'any'}
features per synchronization module: Counter({'events': 5, 'correlation': 3, 'recurrence': 2, 'phase': 1, 'temporal': 1})
classes in pyeyesweb.analysis_primitives.synchronization: 12
moved to low_level: [('FilterContour', 'low_level', 'pyeyesweb.low_level.shape'), ('Directness', 'low_level', 'pyeyesweb.low_level.directness'), ('TrajectoryNonPlanarity', 'low_level', 'pyeyesweb.low_level.non_planarity')]
dir(pyeyesweb): ['Layer', 'SeriesBuffer', 'Timescale', 'analysis_primitives', 'catalog', 'catalog_table', 'data_models', 'high_level', 'low_level', 'mid_level', 'physical_signals', 'skeletons']
pyeyesweb.__all__: ['Layer', 'Timescale', 'catalog', 'catalog_table']
hasattr base/utils: True True | listed in dir: False
| Feature | Timescale | EyesWeb block |
|---|---|---|
| `EnsembleDominance` | 3 s and above |  |
with an EyesWeb block: 47 | without (lab features): ['BoundingBoxFilledArea', 'SpectralArcLength', 'LogDimensionlessJerk', 'Harmonicity', 'SubmovementCount', 'CurvatureDispersion', 'Equilibrium', 'DirectionChange', 'Suddenness', 'SuddennessImpulsivity', 'EnsembleDominance', 'MultiScaleEntropy', 'PhaseLockingValue']
catalog entries are classes of a FeatureInfo: FeatureInfo ['name', 'layer', 'timescale', 'eyesweb_block', 'module', 'summary', 'cls']
exported by a layer package but not catalog features: {'physical_signals': ['MassSpringModel', 'HUMANOID_JOINTS', 'HUMANOID_BONES', 'SynchronizedWindow', 'TimeWindowSynchronizer'], 'low_level': ['average_curvature_3d'], 'mid_level': [], 'high_level': [], 'analysis_primitives': []}
```


**Status.** corrected vs plan: counts (11/22/7/1/19, the plan header said 12/20/8/1/19), synchronization has 12 classes, `base`/`utils` reachable but unlisted.

---

## 14. Live and structural parameters

**Statement.** *Live*: applied in place, the state is kept. *Structural*: it sizes or shapes the state; the state restarts and the next result's `reason`
contains `"parameters changed: state reset"` (once). A bad new value raises at the setter and nothing changes. `window` and `hop` of a windowed feature are
neither: the newest samples are kept (a window that grew reports `WARMING_UP` until it is full again); `CurvatureVelocityCorrelation` restarts its filters when its `window` changes. The classification
is decided per parameter from the original block (read in `Execute()` is live, in `Init()` structural; uncertain means structural). The source of truth is now the
**test tables** (`tests/unit_tests/test_live_parameters*.py`: `LIVE`, `STRUCTURAL`, `INVALID`, checked by `tests/_support/live_param_suite.py`), because
`examples/scratch/live_parameters_classification.md` is git-ignored and goes away with the scratch folder. Table generated from them:

Run `i14_live_table`:

```python
import collections, glob, importlib, os, sys
import pyeyesweb as pew

tests = r"<workspace>/PyEyesWeb/tests"
sys.path[:0] = [tests + "/_support", tests + "/unit_tests"]
table = collections.defaultdict(lambda: {"live": set(), "structural": set()})
for path in sorted(glob.glob(tests + "/unit_tests/test_live_parameters*.py")):
    module = importlib.import_module(os.path.basename(path)[:-3])
    for kind, rows in (("live", getattr(module, "LIVE", [])), ("structural", getattr(module, "STRUCTURAL", []))):
        for factory, attribute, *_ in rows:
            table[type(factory()).__name__][kind].add(attribute)

print(f"{'feature':32s} live | structural")
for info in pew.catalog():
    row = table.get(info.name)
    if row:
        print(f"{info.name:32s} {', '.join(sorted(row['live'])) or '-'} | {', '.join(sorted(row['structural'])) or '-'}")
print("catalog features with no row in the live-parameter tests:", [info.name for info in pew.catalog() if info.name not in table])
```

Output:

```text
feature                          live | structural
SilhouetteCentroids              add_intermediate_centroids, parts | silhouette
SilhouetteBodyParts              arm_percentage, parts | -
Videogram                        - | mode, window
HitCellDetector                  x_max | -
Kinematics                       movement_threshold | filter_polyorder, output_type
KineticEnergy                    weights | input_mode
BoundingBoxFilledArea            epsilon | -
PointsDensity                    distance_type | -
Symmetry                         aggregation, reference_point | -
SpectralArcLength                amplitude_threshold, maximum_cutoff_frequency, minimum_cutoff_frequency, sampling_rate | -
LogDimensionlessJerk             input_mode, sampling_rate | -
Harmonicity                      sampling_rate | -
SubmovementCount                 prominence_factor, sampling_rate | -
CurvatureVelocityCorrelation     upper_limit | filter_window_length
Equilibrium                      margin | -
DirectionChange                  epsilon | -
FilterContour                    gaussian_sigma | -
ConvexHull                       integer_coordinates | -
BodyPartsFromCurvature           minimum_distance | -
TrajectoryNonPlanarity           radius | -
GestureSegmenter                 firing_threshold | filter_window_length
MotionDuration                   sampling_rate | -
SuddennessImpulsivity            direction_change_epsilon | -
ContractionImpulsivity           motion_threshold, peak_threshold, sampling_rate | -
PositionDependingPotentials      gaussian_sigma_x | potential_type
RegionDependingPotentials        parts | potential_type
SampleEntropy                    relative_tolerance, tolerance | -
CoarseGraining                   - | factor
Rarity                           alpha, measure | window
BinaryPulsesRegularity           threshold | -
MultiScaleEntropy                tolerance | -
Periodicity                      threshold | -
ScalarPeakDetector               threshold | window
PhaseLockingValue                low_frequency | -
GeneralisedAutoCorrelation       epsilon | output_type, tau_spread
EventSynchronization             tau | reset_every_buffer
EventSynchronizationMECS         kernel | number_of_event_classes, tau
NonlinearInterdependence         neighbours | -
SequenceDetector                 inter_event_time | sequence
RecurrencePlot                   epsilon | -
CrossRecurrencePlot              epsilon | -
TemporalSynchronization          thresholds | number_of_inputs
catalog features with no row in the live-parameter tests: ['HumanoidSimulator', 'HumanoidOrientations', 'GenericModelOrientations', 'GenericModelSimulator', 'GenericModelPredictor', 'GenericModelEstimator', 'PointsPredictor', 'EllipsoidSphericity', 'TriangleSymmetry', 'CurvatureDispersion', 'ContourCurvature', 'MotionNoiseDetector', 'Directness', 'Suddenness', 'EnsembleDominance', 'CorrelationsMatrix', 'PartialRecurrenceSynchronization', 'SpikeSynchronization']
```


Humanoid and generic models (`test_live_parameters_humanoid.py`, a different table layout): every tested block parameter is live (`damping`, `viscosity`, `gravity`,
`length_forces`, `rotation_forces`, `integration_step`, `reference_direction`, `floor_position`, `ground_interaction`, `use_input_lengths`, the predictor's `prediction_interval`,
`damping_factor`, `viscosity_factor`, `mode`, the estimator's costs and steps, `sampling_rate`), except `GenericModelEstimator.seed`, replacing the `model` by one of another
topology, and `HumanoidOrientations.reference_direction`, which are structural. The features without a row in the table are listed on the last line above; the
tests of the sync and the other areas cover their parameters in the other files.

Demonstration with the public API (live setter, structural setter, `window` change):

Run `i20_behaviours_b`:

```python
import numpy as np
from pyeyesweb.low_level import Kinematics, SpectralArcLength
from pyeyesweb.mid_level import SuddennessImpulsivity

# Window and hop change on a running feature keep the newest samples; a structural parameter restarts the state
feature = SpectralArcLength(window=10, hop=1, sampling_rate=100.0)
values = np.abs(np.sin(np.linspace(0, 6, 30))) + 0.5
for value in values[:15]:
    feature.process(float(value))
feature.window = 12
print("after window 10 -> 12 at sample 15:", feature.process(float(values[15])).status.name, "(buffer kept, window not full yet)" )

kinematics = Kinematics(sampling_rate=100.0, filter_window_length=15)
for i in range(3):
    kinematics.process((i * 0.01, 0, 0))
kinematics.movement_threshold = 0.1                          # live
print("live:", repr(kinematics.process((0.04, 0, 0)).reason))
kinematics.filter_window_length = 9                          # structural
print("structural:", repr(kinematics.process((0.05, 0, 0)).reason), "| next:", repr(kinematics.process((0.06, 0, 0)).reason))

# Parameters are read back; the state of a result is a snapshot
print(Kinematics(output_type=["velocity", "acceleration"]).outputs)

# An invalid construction names the public class and what is missing
for build in (lambda: SuddennessImpulsivity(), lambda: SpectralArcLength(window=5, sampling_rate=100.0)):
    try:
        build()
    except Exception as error:
        print(type(error).__name__, ":", str(error)[:140])
```

Output:

```text
after window 10 -> 12 at sample 15: WARMING_UP (buffer kept, window not full yet)
live: ''
structural: 'parameters changed: state reset' | next: ''
Schema(Output('velocity', unit='m/s'), Output('acceleration', unit='m/s^2'))
TypeError : SuddennessImpulsivity() missing required argument(s): window (the number of samples in each analysis window)
ValueError : SpectralArcLength: window must be >= 10 (got 5)
```


**Status.** verified (the rows come from the passing test suite; the demo above runs the same mechanism). Corrected: window/hop are a third kind.

---

## 15. Removed features

**Statement.** None of these names exists any more in any public module (verified by import below). Wording of the retirement notes is a maintainer
input; the reasons are those of the maintainer's decisions (`PORTING_STATUS.md` "Removed blocks", private).

Blocks removed from core, bindings and Python together: `SkeletonManipulator`; OpenNI and the legacy device presets (`input_type`, `skeleton_mode`; use
`skeleton=`); the `KineticEnergy` Bones algorithm (`algorithm`); `EventSynchronizationMECS` v1 (the class is now the former v2 only, no `version`);
`EventSynchronizationRealTime`; `TauEstimator`; `ScalarBinarySyncDetector`; the trajectory datatype and its blocks (`TrajectoryBuilder`,
`GetKinematicalFeatures`, the `Trajectory` input mode of `Kinematics`, `NumericDerivative`; `Directness` and `TrajectoryNonPlanarity` stay on plain `(n, D)` point arrays,
row 0 newest) and the `GeometricTrajectory3D` transforms (`rotation_matrix`, `rotate_x/y/z`, `rotate`, `scale`, `translate`, `rescale_in_range`, `remap_axis`,
`convert_on_2d`); `NoPreparationDetector` and `NoPreparationDetector2`; `StatisticalMoment` (simple measures; use numpy/scipy); `Clusterability` (Hopkins statistic);
`CannyEdgeDetector` (use OpenCV `cv2.Canny`); `Lightness` (its formula is not a valid lightness measure, research redesign deferred); `ZeroCross` (count sign changes with
`numpy`). The complete old-name to new-name table, with 1.x and development names, is in the migration section below.

**Evidence.** The removal notes of `PORTING_STATUS.md` (private) and `OPEN_POINTS.md` section 6; the code below.

Run `i15_removed`:

```python
import importlib
import pyeyesweb as pew

REMOVED = """SlidingWindow StaticFeature DynamicFeature BaseFeature FeatureResult TSVReader SpeedSmoothness Smoothness HistogramRarity
Synchronization MultiScaleEntropyDominance GeometricSymmetry SymmetryIndex3D Impulsivity Lightness Clusterability StatisticalMoment ZeroCross
CannyEdgeDetector SkeletonManipulator NoPreparationDetector NoPreparationDetector2 TauEstimator ScalarBinarySyncDetector
EventSynchronizationRealTime GetKinematicalFeatures AverageCurvature Curvature VelocityKineticEnergy EllipsoidFitSphericity
TrajectoryBuilder Trajectory KinematicalFeatures NumericDerivative KineticEnergyIndex PeriodicityIndex ImpulsivityIndex RarityIndex
SmoothnessIndex TriangleSymmetryIndex TrajectoryFeatures TICKS_PER_SECOND TimeMode SpikeES PARS MECS rotation_matrix rotate_x rotate scale translate""".split()
MODULES = [importlib.import_module(name) for name in (
    "pyeyesweb", "pyeyesweb.data_models", "pyeyesweb.physical_signals", "pyeyesweb.low_level", "pyeyesweb.mid_level",
    "pyeyesweb.high_level", "pyeyesweb.analysis_primitives", "pyeyesweb.analysis_primitives.synchronization", "pyeyesweb.skeletons")]
print("still importable:", [name for name in REMOVED if any(hasattr(module, name) for module in MODULES)])
for path in ("pyeyesweb.utils.tsv_reader", "pyeyesweb.data_models.sliding_window", "pyeyesweb.utils.math_utils", "pyeyesweb.utils.signal_processing", "pyeyesweb.low_level.smoothness_old"):
    try:
        importlib.import_module(path)
        print(path, "imports")
    except ImportError as error:
        print(path, "->", type(error).__name__, str(error)[:70])
import pyeyesweb.utils.validators as validators
print("pyeyesweb.utils holds only:", [n for n in dir(importlib.import_module("pyeyesweb.utils")) if not n.startswith("_")], "+ validators")
print("data_models.__all__:", importlib.import_module("pyeyesweb.data_models").__all__)

# the old method names on the feature classes
OLD_METHODS = "compute process_window process_series process_points process_axes push_trajectory process_trajectory process_samples to_tensor".split()
print("old methods still on a catalog class:", {info.name: [m for m in OLD_METHODS if hasattr(info.cls, m)] for info in pew.catalog() if any(hasattr(info.cls, m) for m in OLD_METHODS)})
print("is_valid is kept on Result:", hasattr(importlib.import_module("pyeyesweb.data_models").Result, "is_valid"))

# the old names of the keyword arguments
import inspect
OLD = "rate_hz time_mode t ts window_size window_length data_memory n_inputs cells_x cells_y std_dev_x std_dev_y filter_params ges_dur frames skeleton_mode input_type output_type_".split()
hits = {}
for info in pew.catalog():
    for name in inspect.signature(info.cls).parameters:
        if name in OLD or name.startswith("fix_") or name.startswith("use_cust"):
            hits.setdefault(name, []).append(info.name)
print("old parameter spellings still in a signature:", hits)
```

Output:

```text
still importable: []
pyeyesweb.utils.tsv_reader -> ModuleNotFoundError No module named 'pyeyesweb.utils.tsv_reader'
pyeyesweb.data_models.sliding_window -> ModuleNotFoundError No module named 'pyeyesweb.data_models.sliding_window'
pyeyesweb.utils.math_utils -> ModuleNotFoundError No module named 'pyeyesweb.utils.math_utils'
pyeyesweb.utils.signal_processing -> ModuleNotFoundError No module named 'pyeyesweb.utils.signal_processing'
pyeyesweb.low_level.smoothness_old -> ModuleNotFoundError No module named 'pyeyesweb.low_level.smoothness_old'
pyeyesweb.utils holds only: ['validators'] + validators
data_models.__all__: ['Status', 'Output', 'Schema', 'Result', 'Recorder', 'OutputsMixin', 'Input', 'InputKind', 'Inputs', 'Skeleton', 'Feature', 'WindowedFeature']
old methods still on a catalog class: {'EllipsoidSphericity': ['process_axes']}
is_valid is kept on Result: True
old parameter spellings still in a signature: {'use_custom_amplitude': ['PositionDependingPotentials'], 'use_custom_distance': ['PositionDependingPotentials']}
```


**Status.** verified (absence). The plan's list is complete; additions: `Impulsivity`, `GeometricSymmetry`, `SymmetryIndex3D`, `MultiScaleEntropyDominance`, `Smoothness` (1.x and dev), `VelocityKineticEnergy`,
`EllipsoidFitSphericity`, the `pyeyesweb.utils` helper modules, `StaticFeature`/`DynamicFeature`/`BaseFeature`/`FeatureResult` (all in the migration table).

---

## 16. Fidelity policy

**Statement.** A port reproduces the original block (formulas, order of operations that matters, defaults, edge cases); hangs, crashes and undefined behaviour are not reproduced.
A correction of a defect needs a maintainer decision; once decided, the corrected behaviour is the behaviour (**no flag**: `fix_*` parameters were all resolved and removed). Pages
mark such a behaviour as **"Corrected in the core"** with a one-line description. Lab features (13, listed in item 13) have no EyesWeb original and are tested by behaviour.
The source of the corrections is `PORTING_STATUS.md` "Corrected in the core (no flag)" in the private repository (63 entries, for ScalarPeakDetector, BodyPartsFromCurvature, ConvexHull,
MotionNoiseDetector (former GestureSegmenter), EnsembleDominance, Rarity, CurvatureVelocityCorrelation, SampleEntropy, Symmetry (ratio), the potentials, the event
synchronization family, the recurrence plots, SequenceDetector, SpikeSynchronization, TemporalSynchronization, SuddennessImpulsivity/DirectionChange/Suddenness, the humanoid blocks, the
synchronizer and the imaging blocks): **a page writer takes the one-line text from that file, it cannot be verified from this repository.** What can be verified by running:
no signature carries a `fix_`/`legacy`/`compat` flag, and one correction is observable from outside (SampleEntropy tolerance relative to the signal).

**Evidence.** DEV 322-335; `base/core_feature.py` (nothing reads a compatibility flag).

Run `i16_fidelity`:

```python
import inspect
import numpy as np
import pyeyesweb as pew
from pyeyesweb.analysis_primitives import SampleEntropy

flags = [(info.name, name) for info in pew.catalog() for name in inspect.signature(info.cls).parameters
         if name.startswith(("fix_", "legacy", "compat", "eyesweb_")) or "compat" in name]
print("fix_/legacy/compat parameters in the catalog:", flags)
print("parameter names containing 'bug' or 'faithful':", [(info.name, name) for info in pew.catalog() for name in inspect.signature(info.cls).parameters if "bug" in name or "faithful" in name])

# one of the corrections, observable from outside: the default tolerance of SampleEntropy is relative to the signal
# (the original's absolute 0.3 matched nothing on a signal of another scale and gave infinite entropies)
signal = np.random.default_rng(0).normal(size=1000) * 500.0
feature = SampleEntropy(window=200, hop=100, embedding_dimension=3)
print(inspect.signature(SampleEntropy).parameters["tolerance"], inspect.signature(SampleEntropy).parameters["relative_tolerance"])
print("scale 500:", feature.run(signal).sample_entropy[-1], "| finite:", bool(np.isfinite(feature.run(signal).sample_entropy[-1]).all()))
```

Output:

```text
fix_/legacy/compat parameters in the catalog: []
parameter names containing 'bug' or 'faithful': []
tolerance: float | None = None relative_tolerance: float = 0.2
scale 500: [2.14014154 2.12606486 2.21995283] | finite: True
```


**Status.** verified (policy and absence of flags); the list of corrections is a private input.

---

## 17. Install and core

**Statement.**

- The compiled core is the module `eyesweb_core` (a binary build; the C++ is closed source and never described or quoted). The docstring of `pyeyesweb/_core.py` says it is part of the
  `pyeyesweb` wheel (module `pyeyesweb._eyesweb_core`) and installed with `pip install pyeyesweb` (WP5: the earlier statement of a separate `eyesweb-core` wheel dependency is not what the code says;
  maintainer to confirm). **PyPI today (checked 2026-10-15): `pyeyesweb` 1.1.1 is the latest release (the 1.x API, no core); there is no `eyesweb-core` project.** `pyeyesweb._core`
  loads it (`from pyeyesweb import _eyesweb_core`, else `eyesweb_core`; during development the folder `EYESWEB_CORE_PATH` is put first on `sys.path`, and the
  import fails if `eyesweb_core` was already loaded from somewhere else).
- `REQUIRED_CORE = (2, 0)` (major, minor of `eyesweb_core.__version__`). Another version, or a module without a version, raises `ImportError`: *"pyeyesweb needs eyesweb_core 2.0.x, but
  <file> is version 1.9.3 (build abc1234). Rebuild or reinstall the core."*, or for a module without a version *"... is a module without a version (a stale or foreign build). Rebuild
  or reinstall the core."* No core at all: *"pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a
  local build of eyesweb_core."* (text changed after the first version of the sheet). A development path that conflicts with an already loaded core: *"EYESWEB_CORE_PATH is <path>, but eyesweb_core was already loaded from <file>."* Runs here: core 2.0.0, build `dbaf21c`.
- `import pyeyesweb`, `pyeyesweb.data_models`, `Layer`/`Timescale` need **no core**; `catalog()` and every layer package (`low_level`, ...) do.
- **Not yet true (packaging, work package E, is last): `pip install pyeyesweb` does not give a 2.0 install.** `pyproject.toml` still says version `1.1.1`, a setuptools build whose metadata the setuptools of the venv rejects (`project.license` as a string: `pip install -e .` fails in WP5, so the development install is `PYTHONPATH` + `EYESWEB_CORE_PATH`), and dependencies
  `numpy`, `scipy`, `scikit-learn`, `tqdm` (lines 7 and 49-54); the library itself imports only numpy (no scipy, sklearn or tqdm import in `pyeyesweb/`; pandas only inside
  `Recorder.to_frame`). Install pages must say what is decided (wheel `eyesweb-core`, first release `2.0.0a1`) and be flagged until WP E lands; today's working install is a development
  build plus `EYESWEB_CORE_PATH`.

**Evidence.** `_core.py:13` (`REQUIRED_CORE`), `:18-36` (import and version check); `pyproject.toml:7,49-54`; DEV 212-215, ALPHA_REVIEW section 5.

Run `i17_core_version`:

```python
import os, subprocess, sys
from pathlib import Path

repo = r"<workspace>/PyEyesWeb"
here = Path(__file__).resolve().parent.parent       # a folder holding stand-in "cores"

def attempt(label, core_dir, code="import pyeyesweb._core"):
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "EYESWEB_CORE_PATH")}
    env["PYTHONPATH"] = repo
    if core_dir:
        env["EYESWEB_CORE_PATH"] = str(core_dir)
    done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    last = done.stderr.strip().splitlines()[-1] if done.stderr.strip() else "(imported without error)"
    print(f"{label}:\n  {last}")

attempt("core with version 1.9.3 (REQUIRED_CORE is 2.0)", here / "fake_old")
attempt("module without __version__", here / "fake_noversion")
attempt("EYESWEB_CORE_PATH without any core", here / "fake_empty")
attempt("no core anywhere", None)

attempt("import pyeyesweb, data_models, Layer without any core", None, "import pyeyesweb, pyeyesweb.data_models; print('imported', pyeyesweb.Layer.LOW_LEVEL)")
attempt("catalog() without any core", None, "import pyeyesweb; pyeyesweb.catalog()")
attempt("import pyeyesweb.low_level without any core", None, "import pyeyesweb.low_level")

from pyeyesweb import _core
print("required:", _core.REQUIRED_CORE, "| loaded:", _core.core.__version__, "| build:", _core.core.__build__, "| module:", _core.core.__name__)
```

Output:

```text
core with version 1.9.3 (REQUIRED_CORE is 2.0):
  ImportError: pyeyesweb needs eyesweb_core 2.0.x, but <scratch>/fake_old/eyesweb_core/__init__.py is version 1.9.3 (build abc1234). Rebuild or reinstall the core.
module without __version__:
  ImportError: pyeyesweb needs eyesweb_core 2.0.x, but <scratch>/fake_noversion/eyesweb_core/__init__.py is a module without a version (a stale or foreign build). Rebuild or reinstall the core.
EYESWEB_CORE_PATH without any core:
  ImportError: pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a local build of eyesweb_core.
no core anywhere:
  ImportError: pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a local build of eyesweb_core.
import pyeyesweb, data_models, Layer without any core:
  (imported without error)
catalog() without any core:
  ImportError: pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a local build of eyesweb_core.
import pyeyesweb.low_level without any core:
  ImportError: pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a local build of eyesweb_core.
required: (2, 0) | loaded: 2.0.0 | build: dbaf21c | module: eyesweb_core
```


**Status.** corrected vs plan: the dependency statement is not yet true; `ImportError` texts verified (four cases, run in subprocesses with stand-in "cores" for a wrong version, no version, an empty path and no core).

---

## 18. Migration: removed and renamed public names

For `CHANGELOG.md` (2.0.0 entry), the migration guide (WP8) and the "Removed features" page. Sources: `DEVELOPMENT_SPEC.md` "Contract changes of work package A-D"
(DEV 104-229), `ALPHA_REVIEW.md` (U5-U26, Q-items), `PORTING_STATUS.md` "Removed blocks" and "Python wrapper names" (private), the released 1.1.1 tree
(`git show main:pyeyesweb/...`), the 2.0.0 development entries of `CHANGELOG.md`, and the names used by `docs/_legacy` and `examples/*.ipynb`
(`SlidingWindow`, `StaticFeature`, `SpeedSmoothness`, `HistogramRarity`, `GeometricSymmetry`, `Lightness`, `StatisticalMoment`, `Synchronization`, `rate_hz`,
`dims=3`, `.compute`, `.process_points`, `.to_tensor`, `input_type`, `joint_pairs`, ...). **"1.x"** is the released 1.1.1; **"dev"** is any unreleased 2.0
development state (the notebooks and `docs/_legacy` describe it). Absence of every removed name is verified in item 15 (run `i15_removed`).
Rows marked *(reason: maintainer)* take their wording from the maintainer's decision recorded in the private `PORTING_STATUS.md`.

### 18.1 Call contract and data model

| Old | From | New | Reason |
|---|---|---|---|
| `SlidingWindow(max_length, n_signals, n_dims)`, `.append`, `.to_tensor`, `.to_flat_array`, `.is_full`, `.max_length` | 1.x, dev | removed (2026-10-14). Windowed features buffer themselves: `window`, `hop`; a whole recording goes to `run` | one call contract; the buffer lives in the core |
| `BaseFeature`, `StaticFeature`, `DynamicFeature` | 1.x | `Feature`, `WindowedFeature` in `pyeyesweb.data_models`; frame features have no window | one base for the single contract (DEV 49-77) |
| `feature(sliding_window)` (`__call__`) and `feature.compute(array)` | 1.x | `feature.process(*sample, timestamp=None)` for one sample or frame, `feature.run(*recording, timestamps=None, reset=True)` for a recording | the dual API is replaced by one contract |
| `process_window(series)`, `process_series`, `push_trajectory`, `process_trajectory` | dev | `process(...)`; `Kinematics.from_series()` takes a series; `_process_window` is private and is never API | |
| `EllipsoidSphericity.process_points(points)` | dev | `EllipsoidSphericity().process(points)`; `process_axes(first_axis, second_axis, third_axis)` is the former `process(a, b, c)` | one `process` per feature |
| `FeatureResult` and the per-feature result dataclasses | 1.x | `Result`, immutable, with a subclass `<Feature>Result` generated from `feature.outputs` (`Schema`) | outputs are declared before data, immutable, same keys on every call |
| `result.is_valid`, `FeatureResult(is_valid=False)` | 1.x | `result.ok`, `result.status`, `result.reason`; `is_valid` remains as an alias of `ok` | four statuses say why there is no output |
| `None` for an unavailable value (`Optional[...]` fields) | 1.x | `NaN`, `0`, `False` plus `result.valid[name]`; array shapes no longer change between calls | |
| `result.to_flat_dict(prefix)` (dropped `None` fields) | 1.x | `to_flat_dict(prefix="", meta=True)`: the same keys on every call, plus integer `status` and `timestamp` | stable keys for logging |
| `Result.t`, `process(*x, t=None)`, `run(*X, ts=None)`, `creation_time` (100 ns ticks) | dev | `Result.timestamp`, `process(..., timestamp=None)`, `run(..., timestamps=None)`, seconds, `NaN` when unknown | one time rule |
| `rate_hz` (default 50.0 in the four smoothness metrics, 25.0 in `CurvatureVelocityCorrelation`) | 1.x, dev | `sampling_rate` (Hz), default `None` everywhere; the five window metrics require it | no hidden rate (ALPHA U11) |
| `time_mode`, `TimeMode`, `TICKS_PER_SECOND` | dev | removed; the wrapper derives the step from `timestamp` or `sampling_rate` | the core never sees timestamps or tick modes |
| `fix_*` boolean flags | dev | removed; the corrected behaviour is the only behaviour ("Corrected in the core") | fidelity policy (DEV 322-335) |
| Enum parameters (`KineticEnergyInputMode.VELOCITY`, `MECSMode`, ...) | dev | lower-case strings (`input_mode="velocity"`, `method="ratio"`), plus `from_*` constructors for `input_mode` | choices are strings (DEV 246-264) |
| groups of bool switches (14 in `SilhouetteCentroids`, 6 in `SilhouetteBodyParts`, 4 in `RegionDependingPotentials`) | dev | `parts=[...]` | one validated sequence |
| `Status` as a bare `IntEnum` printing `'0'` | dev | `str(Status.OK)` is `"OK"`; `int(Status.OK)` is still 0 | |
| the helpers `result`, `no_output`, `finite_result`, `INPUTS`, `OUTPUTS` on the feature classes | dev | private (`_result`, `_no_output`, `_finite_result`, `_INPUTS`, `_OUTPUTS`) | tab completion shows only the contract |
| top-level `pyeyesweb.Smoothness`, `pyeyesweb.Synchronization`; the package `pyeyesweb.eyesweb`; the aliases `KineticEnergyIndex`, `PeriodicityIndex`, `ImpulsivityIndex`, `RarityIndex`, `SmoothnessIndex`, `TriangleSymmetryIndex`, `TrajectoryFeatures` | 1.x, dev | removed; features live in the layer packages (`pyeyesweb.low_level.KineticEnergy`, ...) | layer packages follow the conceptual model |
| `pyeyesweb.utils.math_utils` (`compute_sparc`, `compute_ldlj`, `compute_jerk_rms`, `compute_sample_entropy`, `compute_harmonicity_index`, `compute_submovement_count`, `compute_eyesweb_smoothness_and_fluidity`, `normalize_signal`, `extract_velocity_from_position`), `pyeyesweb.utils.signal_processing` (`bandpass_filter`, `compute_hilbert_phases`, `apply_savgol_filter`, `validate_filter_params`) | 1.x | removed; `pyeyesweb.utils` is internal (only `validators`) | the maths is in the core behind the features |
| `TSVReader` (`pyeyesweb.utils.tsv_reader`) | 1.x | removed (2026-10-15). A `pyeyesweb.datasets` helper is planned (TEACHING_PLAN) and **does not exist in the code today** | loading data is not part of the library *(reason: maintainer)* |

### 18.2 Features of 1.x

| Old (1.x) | New | What changed |
|---|---|---|
| `Smoothness(metrics=[...])` | `SpectralArcLength`, `LogDimensionlessJerk`, `Harmonicity`, `SubmovementCount` (`low_level`) | one class per metric, each taking the signal it is defined on (a speed profile or an acceleration: compute it with `Kinematics`). Outputs: `sparc` to `spectral_arc_length`; `ldlj_v` and `ldlj_a` to `log_dimensionless_jerk` with `input_mode="velocity"` or `"acceleration"`; `harmonicity`; `n_submovements` to `submovement_count`. Parameters: `rate_hz` to `sampling_rate` (required); `sparc_amplitude_threshold` to `amplitude_threshold`; `sparc_min_fc`, `sparc_max_fc` to `minimum_cutoff_frequency`, `maximum_cutoff_frequency`. `use_filter` (Butterworth + `filtfilt`) is gone: numbers at the former defaults differ; `min_speed_threshold` was already unused. **`jerk_rms` and `samp_en` removed**: use `Kinematics(output_type="jerk")` and `SampleEntropy` |
| `Synchronization(filter_params=...)` | `PhaseLockingValue(window, hop, low_frequency, high_frequency, sampling_rate)` | output `plv` to `phase_locking_value`; a filter band needs `sampling_rate`; the `pyeyesweb.analysis_primitives.synchronization` package now has 12 classes |
| `Rarity(alpha)` | `Rarity(method="information"\|"mode_distance", number_of_inputs, measure="rarity"\|"contrast", window, bins, hop, alpha)` | the EyesWeb block replaces the 1.x implementation (they compute different things); `HistogramRarity` (dev) is `method="mode_distance"`; the old `type=` is `measure=` |
| `MultiScaleEntropyDominance(m, r, max_scale, min_points, methods=[...])` | `MultiScaleEntropy` (one complexity index per participant: `embedding_dimension`, `tolerance`, `max_scale`, `minimum_points`) and `EnsembleDominance` (`high_level`: takes the complexity indices, outputs `dominance_score`, `leader_index`, `leader_complexity`) | split in two features; sample entropy now comes from the EyesWeb block, values differ from 1.x by O(1/N) |
| `KineticEnergy(weights, labels)`; result `total_energy`, `component_energy`, `joints` | `KineticEnergy(labels` or `skeleton, weights=dict, input_mode, reference_point, sampling_rate)`; output `kinetic_energy` | the per-joint and per-component outputs are gone (only the total remains); `weights` is a mapping label to weight; `VelocityKineticEnergy` (dev) is `KineticEnergy.from_velocity` |
| `GeometricSymmetry(joint_pairs, center_of_symmetry)`; result `pairs` | `Symmetry(method="reflection", pairs=names, reference_point=...)` (`skeleton=` or `labels=`); output `pair_symmetry`, one value per pair (an array, replacing the `pairs` dict) | joint names instead of indices (`center_of_symmetry` index becomes `reference_point`, `None` = barycentre); `SymmetryIndex3D` (dev) is `Symmetry(method="ratio")`, the default method, with output `symmetry` (`output_dims="components"` gives three values) |
| `Equilibrium(left_foot_idx, right_foot_idx, barycenter_idx, margin_mm=100, y_weight, axes)`; result `value`, `angle` | `Equilibrium(margin=0.1, y_weight, units)` with three inputs `left_foot`, `right_foot`, `barycenter` (each `(x, y)`); outputs `equilibrium`, `angle` | no joint indices (pass the three points); margin in metres (0.1 m is the former 100 mm) |
| `DirectionChange(epsilon, num_subsamples, metrics)` | `DirectionChange(window, hop, epsilon, number_of_subsamples, metrics)` | `window` and `hop` are parameters of the feature; one trajectory per call |
| `Suddenness(algo="new")` | `Suddenness(window, hop, dims, method="constrained"\|"quantile")` | `algo="new"` is `method="constrained"` (the default); the other algorithm is `"quantile"`; one `(dims,)` point per call (`dims` 2 or 3), a `(signals, dims)` frame is rejected: average markers beforehand |
| `Impulsivity(direction_change_epsilon, suddenness_algo)`; result `impulsivity_index`, `direction_change_val`, `is_sudden` | `SuddennessImpulsivity(window, hop, dims, direction_change_epsilon, method)`; output `impulsivity_index` only | the intermediate values are gone; the EyesWeb `ImpulsivityIndex` is the new `ContractionImpulsivity` |
| `BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity` (shared `ContractionExpansionResult`: `contraction_index`, `sphericity`, `points_density`) | same names; outputs `contraction_index`; `sphericity`, `axis_ratio`, `radii`; `density`, `centroid` | each feature declares its own outputs; `PointsDensity` is the EyesWeb one (a superset) |

### 18.3 Features with no 2.0 counterpart (removed)

| Old | From | Replacement | Reason |
|---|---|---|---|
| `Lightness` | 1.x | none (research redesign deferred) | its formula (rarity of the horizontal energy share) is not a valid lightness measure *(maintainer, 2026-10-13)* |
| `Clusterability` (Hopkins statistic) | 1.x | none | removed to reduce the code surface (2026-10-11) *(maintainer)* |
| `StatisticalMoment` | 1.x | `numpy` / `scipy.stats` (`mean`, `std`, `skew`, `kurtosis`) | simple measures, already available elsewhere (e.g. in TouchDesigner) *(maintainer)* |
| `ZeroCross` | dev | `numpy`: count the sign changes (`np.diff(np.sign(x))`) | replaceable by a one-liner (2026-10-14) *(maintainer)* |
| `CannyEdgeDetector` | dev | OpenCV `cv2.Canny` | replaceable, nothing else used it (2026-10-14) *(maintainer)* |
| `SkeletonManipulator`, OpenNI and the legacy device presets (`input_type`, `skeleton_mode`), the `KineticEnergy` Bones `algorithm` | dev | `skeleton=` with a preset or your own `Skeleton` | not used anywhere (2026-10-10 and 11) *(maintainer)* |
| `NoPreparationDetector`, `NoPreparationDetector2` | dev | none | removed to reduce the code surface (2026-10-11) *(maintainer)* |
| MECS Algorithm v1, `EventSynchronizationRealTime`, `TauEstimator`, `ScalarBinarySyncDetector` | dev | `EventSynchronizationMECS` is the former v2 only (no `version`) | never compiled by the current EyesWeb project (or only by an old one) *(maintainer)* |
| trajectory datatype and blocks (`Trajectory`, `TrajectoryBuilder`, `GetKinematicalFeatures`, `KinematicalFeatures`, `TrajectoryFeatures` (length), `NumericDerivative`, the `Trajectory` input mode of `Kinematics`) | dev | `Kinematics` on plain arrays (`from_point`, `from_series`); `Directness` and `TrajectoryNonPlanarity` take `(n, D)` point arrays, row 0 newest | the datatype was not needed on plain arrays *(maintainer, 2026-10-11)* |
| `GeometricTrajectory3D` transforms: `rotation_matrix`, `rotate_x`, `rotate_y`, `rotate_z`, `rotate`, `scale`, `translate`, `rescale_in_range`, `remap_axis`, `convert_on_2d` | dev | `numpy` | same decision |
| `EllipsoidFitSphericity` | dev | `EllipsoidSphericity().process(points)`; `axis_ratio` is the former value | merged |

### 18.4 Renamed within the 2.0 development (names a developer of the 2.0 branch or an EyesWeb user may know)

| EyesWeb block or dev name | Python name | Note |
|---|---|---|
| `KineticEnergyIndex` | `KineticEnergy` | |
| `PeriodicityIndex` | `Periodicity` | |
| `ImpulsivityIndex` | `ContractionImpulsivity` | `ges_dur` is `gesture_duration`, `frames` is `sampling_rate` |
| `RarityIndex`, `HistogramRarity` | `Rarity(method="information"\|"mode_distance")` | |
| `SmoothnessIndex` (dev `Smoothness`) | `CurvatureVelocityCorrelation` | |
| `GetKinematicalFeatures`, core `TrajectoryFeatures` | `Kinematics` | |
| `AverageCurvature` (dev, renamed 2026-10-11) | `TrajectoryNonPlanarity` | it measures the distance from local best-fit planes, not a curvature; for a trajectory's curvature use `Kinematics(output_type="curvature")` |
| `Curvature` (dev) | `ContourCurvature` | tells it from the trajectory curvature |
| `SymmetryIndex3D`, `GeometricSymmetry` | `Symmetry(method="ratio"\|"reflection")` | |
| `TriangleSymmetryIndex` | `TriangleSymmetry` | output `symmetry` is 1 minus the EyesWeb asymmetry |
| the old `GestureSegmenter` reading skeletons (`skeleton_mode`) | `MotionNoiseDetector` (skeleton in, noise flag out); `GestureSegmenter` now takes the intensity | |
| `PARS` | `PartialRecurrenceSynchronization` | |
| `EventSynchronizationInterdependence` | `NonlinearInterdependence` | outputs `xy`, `yx` are `first_to_second_interdependence`, `second_to_first_interdependence` |
| `SpikeES` | `SpikeSynchronization` | |
| `CentroidsCalc`, `BlobSubRegions`, `VideoGram` | `SilhouetteCentroids`, `SilhouetteBodyParts`, `Videogram` | on full-frame masks |
| `HumanoidOrientationsExtractor`, `GenericModelOrientationsExtractor` | `HumanoidOrientations`, `GenericModelOrientations` | `joint_map` names your labels |
| `MassSpringModel`, `TimeWindowSynchronizer` | `pyeyesweb.physical_signals.MassSpringModel`, `.TimeWindowSynchronizer` (and `SynchronizedWindow`) | not catalog features |

### 18.5 Parameter, input and output spellings (package B and C)

The list below is not hand-written: it is the table of forbidden synonyms that `tests/unit_tests/test_naming.py` enforces over every parameter, input and output of the
catalog, joined with where the new spelling is used (generated by running the code, `t18_renames`). Most of the old spellings existed only in the development states
(1.x had `rate_hz`, `num_subsamples`, `joint_pairs`, `center_of_symmetry`, `algo`, `filter_params`, `plv`, `margin_mm`); the column "still declared"
must read "no" everywhere.

| Old spelling | New spelling | Still declared anywhere | New spelling used by |
|---|---|---|---|
| `n_inputs` | `number_of_inputs` | no | CorrelationsMatrix (parameter), EventSynchronizationMECS (parameter), Rarity (parameter), SpikeSynchronization (parameter), ... (5) |
| `input_number` | `number_of_inputs` | no | CorrelationsMatrix (parameter), EventSynchronizationMECS (parameter), Rarity (parameter), SpikeSynchronization (parameter), ... (5) |
| `time_series_number` | `number_of_inputs` | no | CorrelationsMatrix (parameter), EventSynchronizationMECS (parameter), Rarity (parameter), SpikeSynchronization (parameter), ... (5) |
| `number_of_input_trains` | `number_of_inputs` | no | CorrelationsMatrix (parameter), EventSynchronizationMECS (parameter), Rarity (parameter), SpikeSynchronization (parameter), ... (5) |
| `event_class_number` | `number_of_event_classes` | no | EventSynchronizationMECS (parameter) |
| `points_number` | `number_of_points` | no | BodyPartsFromCurvature (parameter) |
| `num_of_regions` | `number_of_regions` | no | RegionDependingPotentials (parameter) |
| `num_subsamples` | `number_of_subsamples` | no | DirectionChange (parameter) |
| `window_size` | `window` | no | BinaryPulsesRegularity (parameter), CoarseGraining (parameter), CorrelationsMatrix (parameter), CrossRecurrencePlot (parameter), ... (28) |
| `window_length` | `window` | no | BinaryPulsesRegularity (parameter), CoarseGraining (parameter), CorrelationsMatrix (parameter), CrossRecurrencePlot (parameter), ... (28) |
| `length` | `window` | no | BinaryPulsesRegularity (parameter), CoarseGraining (parameter), CorrelationsMatrix (parameter), CrossRecurrencePlot (parameter), ... (28) |
| `buffer_length` | `window` | no | BinaryPulsesRegularity (parameter), CoarseGraining (parameter), CorrelationsMatrix (parameter), CrossRecurrencePlot (parameter), ... (28) |
| `data_memory` | `window` | no | BinaryPulsesRegularity (parameter), CoarseGraining (parameter), CorrelationsMatrix (parameter), CrossRecurrencePlot (parameter), ... (28) |
| `cells_x` | `cells_along_x` | no | HitCellDetector (parameter), PositionDependingPotentials (parameter), RegionDependingPotentials (parameter) |
| `cells_y` | `cells_along_y` | no | HitCellDetector (parameter), PositionDependingPotentials (parameter), RegionDependingPotentials (parameter) |
| `sigma_value` | `gaussian_sigma` | no | EventSynchronizationMECS (parameter), FilterContour (parameter) |
| `std_dev_x` | `gaussian_sigma_x` | no | PositionDependingPotentials (parameter) |
| `std_dev_y` | `gaussian_sigma_y` | no | PositionDependingPotentials (parameter) |
| `rho` | `gaussian_correlation` | no | PositionDependingPotentials (parameter) |
| `ges_dur` | `gesture_duration` | no | ContractionImpulsivity (output), ContractionImpulsivity (parameter) |
| `frames` | `sampling_rate` | no | ContractionImpulsivity (parameter), CurvatureDispersion (parameter), CurvatureVelocityCorrelation (parameter), GenericModelEstimator (parameter), ... (16) |
| `use_cust_ampl` | `use_custom_amplitude` | no | PositionDependingPotentials (parameter) |
| `cust_ampl` | `custom_amplitude` | no | PositionDependingPotentials (parameter) |
| `use_cust_dist` | `use_custom_distance` | no | PositionDependingPotentials (parameter) |
| `cust_dist` | `custom_distance` | no | PositionDependingPotentials (parameter) |
| `reg_init_values` | `region_initial_values` | no | RegionDependingPotentials (parameter) |
| `ref_dir` | `reference_direction` | no | GenericModelEstimator (parameter), GenericModelPredictor (parameter), GenericModelSimulator (parameter), HumanoidOrientations (parameter), ... (5) |
| `cog` | `center_of_gravity` | no | (not a declared name) |
| `filter_params` | `low_frequency, high_frequency` | no | PhaseLockingValue (parameter) |
| `algorithm` | `method` | no | Periodicity (parameter), Rarity (parameter), Suddenness (parameter), SuddennessImpulsivity (parameter), ... (5) |
| `algo` | `method` | no | Periodicity (parameter), Rarity (parameter), Suddenness (parameter), SuddennessImpulsivity (parameter), ... (5) |
| `type` | `measure` | no | Rarity (parameter) |
| `couples` | `pairs` | no | Symmetry (parameter) |
| `joint_pairs` | `pairs` | no | Symmetry (parameter) |
| `center_of_symmetry` | `reference_point` | no | KineticEnergy (parameter), Symmetry (parameter) |
| `sqom` | `quantity_of_motion` | no | ContractionImpulsivity (input) |
| `ci` | `contraction_index` | no | BoundingBoxFilledArea (output), ContractionImpulsivity (input) |
| `cpr` | `correlations_matrix` | no | CorrelationsMatrix (output), PartialRecurrenceSynchronization (input) |
| `ts1` | `first_signal` | no | EventSynchronization (input), NonlinearInterdependence (input), PhaseLockingValue (input) |
| `ts2` | `second_signal` | no | EventSynchronization (input), NonlinearInterdependence (input), PhaseLockingValue (input) |
| `x` | `first_signal` | no | EventSynchronization (input), NonlinearInterdependence (input), PhaseLockingValue (input) |
| `y` | `second_signal` | no | EventSynchronization (input), NonlinearInterdependence (input), PhaseLockingValue (input) |
| `plv` | `phase_locking_value` | no | PhaseLockingValue (output) |
| `xy` | `first_to_second_interdependence` | no | NonlinearInterdependence (output) |
| `yx` | `second_to_first_interdependence` | no | NonlinearInterdependence (output) |
| `value` | `equilibrium` | no | Equilibrium (output) |
| `matrix` | `a specific name` | no | (not a declared name) |
| `sequences` | `sequence_count` | no | SequenceDetector (output) |
| `plot` | `recurrence_matrix` | no | RecurrencePlot (output) |
| `synchronisation` | `synchronization` | no | EventSynchronization (output), EventSynchronizationMECS (output), TemporalSynchronization (input) |


Other renames of the same packages: `Equilibrium` margin `margin_mm` to `margin` (metres); `Symmetry` takes `labels`/`skeleton`, `pairs` and `reference_point` for both methods; `PhaseLockingValue`
takes `low_frequency`, `high_frequency`, `sampling_rate` instead of `filter_params`; `RecurrencePlot` / `CrossRecurrencePlot` `multiple_epsilons=None` is `epsilon` for each of the `window` samples;
`MultiScaleEntropy` defaults to `window=3000`; a boolean output is always `is_<something>` (`is_sudden`, `is_peak`, `is_gesturing`, ...); the Savitzky-Golay parameters are always
`filter_window_length`, `filter_polyorder`; feature names have no `Get` prefix and no `Index` suffix; `Kinematics` keeps the modes `tangential` / `components`; a core enum member `COMPONENT` is spelled `"components"`.

---

## 19. Behaviours a reader would not guess

Each row is verified by the run block named in the last column (the code and the pasted output are in the item above, or just below the table).

| # | Behaviour | Verified by |
|---|---|---|
| B1 | An `INVALID_INPUT` result has **every output empty** (NaN, 0, False) and `valid` all `False`, whatever the feature computed; the explanation is only in `reason`. | `i03_status` |
| B2 | A rejected sample (NaN, infinity, missing joint, non-increasing timestamp) is **not buffered and moves nothing**: the next valid call behaves as if it never happened. **Exception: an overflow** ("the result is not finite") is detected after the state advanced; the next valid call can be `INVALID_INPUT` too. | `i03b_invalid_state`, `i03c_overflow_state` |
| B3 | `latest` stays `None` until the first `OK` result (not "the last result") and is untouched by `WARMING_UP`, `NO_OUTPUT`, `INVALID_INPUT`; `reset()` clears it. | `i01b_latest`, `i01_contract` |
| B4 | The **first timed call** (first call, after `reset()`, after a call without timestamp) has step `1 / sampling_rate`, else 1 s: epoch timestamps never become a step. | `i06_time` |
| B5 | Without `sampling_rate`, even a first call **with** a timestamp says "no time given: per-sample derivatives". | `i06_time` |
| B6 | The "must increase" check exists in 9 classes only (the "must be finite" check is central since H); the five window metrics need `sampling_rate` but **ignore `timestamp`** (it is only copied to `result.timestamp`). | `i06b_rate_required`, `i06c_window_timestamps` |
| B7 | A NaN or infinite `timestamp` is `INVALID_INPUT` "non-finite timestamp" in every feature (was `ValueError` in the 9 timed classes; changed in H). | `i06_time` |
| B8 | `WARMING_UP` says `"k of N samples"`; the first full window is `OK` at call `N`; with `hop > 1`, calls between windows are `NO_OUTPUT` (`"between windows"`). | `i03_status`, `i01b_latest` |
| B9 | `run()` starts from a fresh state by default (it calls `reset()`); `run(..., reset=False)` continues; a second `run()` does not carry the window over. | `i20_behaviours_a` |
| B10 | `timestamp` is keyword-only: `process(frame, 0.0)` is read as a second input and raises `ValueError` ("takes 1 input(s)"). | `i01_contract` |
| B11 | `feature.parameters` is read-only, omits `skeleton` (it is resolved into `labels`/`weights`), and a setter validates like the constructor and leaves the feature unchanged on error. | `i01_contract`, `i05_errors` |
| B12 | `units="mm"` scales the **parameters** (thresholds are written in metres whatever `units` says) and renames the output units (`mm/s`), never the data: `parameters` reads the value back unscaled. | `i08_units` |
| B13 | `qualisys_sport`, `mediapipe`, `openpose` run without error but with **uniform kinetic-energy weights of 1.0**; `Symmetry(method="ratio")` on the two presets without a reference raises `ValueError` asking for `reference_point=` (S4, fixed in H). | `i11b_skeleton_override`, `x3_symmetry_ratio_reference` |
| B14 | A dict frame lacking a weighted joint is `INVALID_INPUT`, one with an unknown key **raises**; an array with the wrong number of rows raises. | `i05_errors` |
| B15 | `dims=None` is inferred at the first frame, forgotten by `reset()`, and a later frame of another size raises; this exists in four classes only. | `i12_dims` |
| B16 | A value that was not produced is never `None`, for scalar, vector, matrix, variable-size and image outputs; labelled outputs (3 of them) hold a dict that can be empty. Checked on 417 results (`OK`, `WARMING_UP`, `NO_OUTPUT`, `INVALID_INPUT`) of all 60 features, including shapes. | `i21_never_none` |
| B17 | Finite data can still be `INVALID_INPUT` ("the result is not finite") when the arithmetic overflows (1e300). | `i20_behaviours_a` |
| B18 | NaN is **data** for the humanoid and ensemble features: one NaN joint is a dropout (`OK`), one NaN complexity index is a participant without one; infinity and all-NaN frames are still `INVALID_INPUT`. | `i20_behaviours_a` |
| B19 | Images: a `bool` array is a 0/1 mask; any other numeric array must hold whole numbers in 0-255 (`3.0` is fine, `0.5` and `300` raise); a wrong rank raises; images never enter `to_numpy()` / `to_frame()`. | `i20_behaviours_a`, `i04b_recorder_images` |
| B20 | `EventSynchronization` (and `...MECS`): `hop=None` is `window`, and any other `hop` raises ("change both with configure()"). | `i07_windows` |
| B21 | `MultiScaleEntropy` needs `window >= max_scale * minimum_points` (3000 by default) and the error says so. | `i07_windows` |
| B22 | A variant feature refuses the parameters of another variant (`Symmetry(method="reflection", aggregation=...)` is a `TypeError`). | `i09_choices` |
| B23 | Changing `window` or `hop` keeps the newest samples (a grown window warms up again); a structural parameter restarts the state and says so exactly once in `reason`. | `i20_behaviours_b` |
| B24 | `Output.unit` text follows the parameters (`frames` becomes `s` with a rate; `units=` names the length unit). | `i08c_unit_strings` |
| B25 | `import pyeyesweb`, `pyeyesweb.data_models`, `Layer` work without the core; `catalog()` and every layer package raise `ImportError`. | `i17_core_version` |
| B26 | `rec[3]` rebuilds a `Result` with `reason` and `valid`; `to_numpy()` has the fixed outputs only; `Recorder` has no `to_array()`. | `i04_recorder` |
| B27 | `EllipsoidSphericity.process_axes(...)` is a second public entry point (the faithful EyesWeb input): it does its own validity check, produces only `sphericity`, and does **not** update `latest`. | `i01c_process_axes` |
| B28 | The enums reachable from the public modules are `Layer`, `Timescale`, `InputKind`, `Status`; no parameter takes an enum. | `i09_choices` |

Additional run blocks for B1-B28 not shown above:

Run `i20_behaviours_a`:

```python
import numpy as np
from pyeyesweb.high_level import EnsembleDominance
from pyeyesweb.low_level import KineticEnergy, SpectralArcLength
from pyeyesweb.physical_signals import HumanoidSimulator, Videogram

# run() starts from a fresh state unless reset=False
feature = SpectralArcLength(window=10, sampling_rate=100.0)
signal = np.abs(np.sin(np.linspace(0, 3, 14))) + 0.5
feature.run(signal[:7])
fresh = feature.run(signal[7:])
feature.run(signal[:7])
continued = feature.run(signal[7:], reset=False)
print("run() again, default (state forgotten):", [fresh[i].status.name for i in range(len(fresh))])
print("run(reset=False) (state kept):         ", [continued[i].status.name for i in range(len(continued))])

# a finite input whose result overflows is INVALID_INPUT, not a plausible number
energy = KineticEnergy(labels=["a"], weights={"a": 1.0})
energy.process({"a": (0.0, 0.0, 0.0)}, timestamp=0.0)
huge = energy.process({"a": (1e300, 0.0, 0.0)}, timestamp=1.0)
print("1e300:", huge.status.name, repr(huge.reason), huge.kinetic_energy)

# NaN is data (a dropout) for the humanoid and ensemble features; infinity is not
simulator = HumanoidSimulator(sampling_rate=25.0)
from pyeyesweb._core import core
from pyeyesweb.physical_signals import HUMANOID_JOINTS
positions = core.humanoid.HumanoidSimulator().positions()
pose = np.array([positions[name] for name in HUMANOID_JOINTS]) / 1000.0
dropout = pose.copy(); dropout[3] = np.nan
infinite = pose.copy(); infinite[3] = np.inf
print("humanoid, one NaN joint:", simulator.process(dropout).status.name, "| one inf joint:", simulator.process(infinite).status.name,
      "| all NaN:", simulator.process(np.full_like(pose, np.nan)).status.name)
ensemble = EnsembleDominance()
print("ensemble with a NaN complexity index:", ensemble.inputs)
out = ensemble.process(np.array([1.0, np.nan, 3.0]))
print(out.status.name, out.dominance_score, out.leader_index)

# images: a bool array is a 0/1 mask, other numbers must be whole 0-255 values, a wrong rank raises
video = Videogram(window=3)
for label, image in (("bool mask", np.ones((4, 4), dtype=bool)), ("float 0.5", np.full((4, 4), 0.5)), ("float 3.0", np.full((4, 4), 3.0)),
                     ("300", np.full((4, 4), 300)), ("rank 1", np.ones(4, dtype=np.uint8))):
    try:
        print(label, "->", video.process(image).status.name)
    except ValueError as error:
        print(label, "-> ValueError:", str(error)[:110])
```

Output:

```text
run() again, default (state forgotten): ['WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP', 'WARMING_UP']
run(reset=False) (state kept):          ['WARMING_UP', 'WARMING_UP', 'OK', 'OK', 'OK', 'OK', 'OK']
1e300: INVALID_INPUT 'the result is not finite' nan
humanoid, one NaN joint: OK | one inf joint: INVALID_INPUT | all NaN: INVALID_INPUT
ensemble with a NaN complexity index: Inputs(complexity_index: sample (?) - complexity index of each participant)
OK [0.66666667        nan 0.        ] 0
bool mask -> OK
float 0.5 -> ValueError: Videogram: input 'frame' expects whole-number pixel values in 0-255, got float64 values from 0.5 to 0.5
float 3.0 -> OK
300 -> ValueError: Videogram: input 'frame' expects whole-number pixel values in 0-255, got int64 values from 300 to 300
rank 1 -> ValueError: Videogram: input 'frame' expects image of shape (any, any, any), got shape (4,)
```


Run `i21_never_none`:

```python
import sys
import numpy as np
from pyeyesweb.data_models import InputKind, Status

tests = r"<workspace>/PyEyesWeb/tests"
sys.path[:0] = [tests + "/unit_tests", tests + "/_support"]
from test_contract_all_features import NAMES, factory_and_recordings    # builds every catalog feature and a recording for it

def none_inside(value):
    if value is None:
        return True
    if isinstance(value, dict):
        return any(none_inside(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(none_inside(item) for item in value)
    return False

counts, problems = {status.name: 0 for status in Status}, []
for name in NAMES:
    factory, recordings = factory_and_recordings(name)
    feature = factory()
    declared = list(feature.inputs)
    calls = [[recording[i] for recording in recordings] for i in range(min(6, len(recordings[0])))]
    poisoned = [np.array(sample, dtype=float) if kind.kind is not InputKind.IMAGE else sample for sample, kind in zip(calls[0], declared)]
    if declared[0].kind is not InputKind.IMAGE:
        poisoned[0] = np.full_like(poisoned[0], np.nan)
        calls.append(poisoned)
    for sample in calls:
        result = feature.process(*sample)
        counts[result.status.name] += 1
        for output in feature.outputs:
            value = result[output.name]
            if none_inside(value):
                problems.append(f"{name}.{output.name}: None in a {result.status.name} result")
            elif not output.labelled and output.shape is not None and None not in output.shape and np.shape(value) != tuple(output.shape):
                problems.append(f"{name}.{output.name}: shape {np.shape(value)} != declared {output.shape} ({result.status.name})")
            if result.status is Status.INVALID_INPUT and any(result.valid.values()):
                problems.append(f"{name}: INVALID_INPUT with a valid output")
print("labelled outputs (a dict label -> value, possibly empty):", sum(o.labelled for n in NAMES for o in factory_and_recordings(n)[0]().outputs), "outputs")
print(len(NAMES), "features;", sum(counts.values()), "results checked:", counts)
print("problems:", problems or "none")
```

Output:

```text
labelled outputs (a dict label -> value, possibly empty): 3 outputs
60 features; 417 results checked: {'OK': 211, 'WARMING_UP': 142, 'NO_OUTPUT': 6, 'INVALID_INPUT': 58}
problems: none
```


---

## 20. Suspected bugs and inconsistencies

Found while verifying. Items marked "fixed in H" were fixed in work package H (see `DEVELOPMENT_SPEC.md`, "Contract changes of work package H"); the others are unchanged. Each has the snippet that reproduces it (run output below). "Decision" means the maintainer already decided and the
item is listed only because a page writer will stumble over it.

| # | What | Where |
|---|---|---|
| S1 | **Fixed in H.** `KineticEnergy.run` now builds its `Recorder` from the feature (`Recorder.from_arrays(self, ...)`): `Recorder(KineticEnergy, ...)` with `KineticEnergyResult` rows, as every other `run` (catalog-wide test). Was: `Recorder(schema, ...)` and plain `Result` rows. | `low_level/energy.py:90`; `data_models/recorder.py:47,97`; run `x1_recorder_repr` |
| S2 | **Fixed in H.** `Result` docstring says seconds. | `data_models/results.py:300` |
| S3 | **Fixed in H.** `HumanoidSimulator.process` docstring says the unit of `units`. | `physical_signals/humanoid.py:289` |
| S4 | **Fixed in H.** `Symmetry(method="ratio", skeleton=...)` with a preset that defines no reference joint (`mediapipe`, `qualisys_sport`) raises `ValueError` at construction naming the preset and asking for `reference_point=` (the alternative `reference_type="barycenter"` of the first fix was removed in I-a); the presets are not filled. The core skips the translation when the label is absent, which is what used to happen silently. An explicit `reference_point=` works. | `x3_symmetry_ratio_reference` |
| S5 | **Fixed in H.** `KineticEnergy(weights=[1.0])` raises `ValueError` ("weights has 1 value, the skeleton has 3 joints"; without labels: "weights must be a mapping ... or a sequence with one weight per label"); a sequence of the right length is accepted as one weight per label. No other feature takes `weights`; `MotionNoiseDetector`, `PointsDensity`, `PointsPredictor` take `labels` only. (A malformed `pairs` of `Symmetry` still shows the raw core error: not in scope.) | run `x2_weights_list` |
| S6 | **By design, documented in H.** An overflow `INVALID_INPUT` is detected after the block advanced and the core cannot undo it, so the next valid call can be `INVALID_INPUT` too (`KineticEnergy` position mode, windowed features until the sample leaves the window). The other rejections change nothing. Pinned by `test_an_overflow_has_advanced_the_state_of_the_block`; run `i03c_overflow_state` still shows it. | run `i03c_overflow_state` |
| S7 | **Fixed in H.** A NaN or infinite `timestamp` is `INVALID_INPUT` "non-finite timestamp" in every feature (one check in `Feature._input_problem`), nothing changes; was `ValueError` in the 9 timed classes and unchecked elsewhere. A decreasing timestamp is still checked only by the 9 timed classes (the window metrics ignore `timestamp`). | runs `i06_time`, `i06c_window_timestamps` |
| S8 | **Fixed in H.** The constructor error of `window`/`hop` names the class (`SpectralArcLength: window must be >= 1 ...`). | `data_models/feature.py:228-231` vs `base/core_feature.py`; run `i05_errors` |
| S9 | Stale words: *Fixed in H:* `pyeyesweb/__init__.py:9`, `DEVELOPMENT_SPEC.md` (`MotionNoiseDetector`; the order of the `SilhouetteBodyParts` parts). *Open:* private `PORTING_STATUS.md` still places `Directness` in `mid_level` and `TimeWindowSynchronizer` in `pyeyesweb.utils`. | files named |
| S10 | **Fixed in H** (the typo): layer 4 reads "qualities communicated" in `Layer.HIGH_LEVEL.title`, `pyeyesweb/__init__.py`, `high_level/__init__.py`. Still open: the fifth layer, `analysis_primitives`, has no number. | `catalog.py:52`, `high_level/__init__.py:1` |
| S11 | `TrajectoryNonPlanarity` defaults (`radius=100.0`, `nan_value=999.0`) look like millimetres but `units` defaults to `"m"` (a 100 m neighbourhood). *Decision*: kept in package C (ALPHA_REVIEW U10); still a trap for data in metres. | run `x5_defaults` |
| S12 | `EllipsoidSphericity.process_axes` is a public entry point outside the contract (documented in its docstring); it bypasses the central input check and `latest`. *Probably by design.* | `low_level/contraction.py:168`; run `i01c_process_axes` |
| S13 | `to_frame()` of a feature with image-only outputs (`Videogram`) has no value columns (`schema.size` is 0): correct but surprising; page writers should say so. | run `i04b_recorder_images` |
| S14 | 18 catalog docstrings still mention the private `_process_window` and `Parameters` sections are missing in 36 (from the WP0 docstring audit): WP4 work, listed for completeness. | `docstring_audit.md` (WP0) |

Run `x1_recorder_repr`:

```python
import numpy as np
from pyeyesweb.low_level import KineticEnergy, Kinematics

frames = np.random.default_rng(0).normal(size=(4, 25, 3))
energy = KineticEnergy(skeleton="kinect_v2", sampling_rate=100.0)
print(repr(energy.run(frames)), "|", type(energy.run(frames)[0]).__name__)         # KineticEnergy.run builds the Recorder in C++
print(repr(Kinematics(sampling_rate=100.0).run(np.arange(4.0)[:, None] * [[0.1, 0.0, 0.0]])), "|",
      type(Kinematics(sampling_rate=100.0).run(np.arange(4.0)[:, None] * [[0.1, 0.0, 0.0]])[0]).__name__)
print("process():", type(energy.process(frames[0])).__name__)
```

Output:

```text
Recorder(KineticEnergy, rows=4, columns=['kinetic_energy'], status={'OK': 4}) | KineticEnergyResult
Recorder(Kinematics, rows=4, columns=['velocity'], status={'OK': 4}) | KinematicsResult
process(): KineticEnergyResult
```


Run `x2_weights_list`:

```python
from pyeyesweb.low_level import KineticEnergy

for labels, weights in ((["a"], {"a": 1.0}), (["a"], [1.0]), (["a", "b", "c"], [1.0]), (None, [1.0]), (["a"], 1.0)):
    try:
        KineticEnergy(labels=labels, weights=weights)
        print(repr(weights), "with", labels, "accepted")
    except Exception as error:
        print(repr(weights), "with", labels, "->", type(error).__name__, "|", str(error))
```

Output:

```text
{'a': 1.0} with ['a'] accepted
[1.0] with ['a'] accepted
[1.0] with ['a', 'b', 'c'] -> ValueError | KineticEnergy: weights has 1 value, the skeleton has 3 joints
[1.0] with None -> ValueError | KineticEnergy: weights must be a mapping joint -> weight, or a sequence with one weight per label (given with labels= or skeleton=), got list
1.0 with ['a'] -> ValueError | KineticEnergy: weights must be a mapping joint -> weight, or a sequence with one weight per label (given with labels= or skeleton=), got float
```


Run `x3_symmetry_ratio_reference`:

```python
import numpy as np
from pyeyesweb.low_level import Symmetry
from pyeyesweb.skeletons import get_skeleton

for preset in ("kinect_v2", "mediapipe", "qualisys_sport", "openpose"):
    for method in ("reflection", "ratio"):
        try:
            feature = Symmetry(skeleton=preset, method=method)
        except ValueError as error:
            print(f"{preset:15s} {method:10s} ValueError: {error}")
            continue
        parameters = {name: feature.parameters.get(name) for name in ("reference_point", "reference_type") if name in feature.parameters}
        frame = np.random.default_rng(0).normal(size=(len(get_skeleton(preset).joints), 3))
        print(f"{preset:15s} {method:10s} {parameters} -> {feature.process(frame).status.name}")
joint = get_skeleton("mediapipe").joints[0]
print(f"mediapipe ratio with reference_point={joint!r}:", Symmetry(skeleton="mediapipe", reference_point=joint).parameters["reference_point"])
```

Output:

```text
kinect_v2       reflection {'reference_point': 'SpineShoulder'} -> OK
kinect_v2       ratio      {'reference_point': 'SpineShoulder', 'reference_type': 'label'} -> OK
mediapipe       reflection {'reference_point': None} -> OK
mediapipe       ratio      ValueError: Symmetry(method='ratio'): the skeleton 'mediapipe' defines no reference joint; pass reference_point= (a joint of the skeleton)
qualisys_sport  reflection {'reference_point': None} -> OK
qualisys_sport  ratio      ValueError: Symmetry(method='ratio'): the skeleton 'qualisys_sport' defines no reference joint; pass reference_point= (a joint of the skeleton)
openpose        reflection {'reference_point': 'Neck'} -> OK
openpose        ratio      {'reference_point': 'Neck', 'reference_type': 'label'} -> OK
mediapipe ratio with reference_point='nose': nose
```


Run `x5_defaults`:

```python
from pyeyesweb.low_level import TrajectoryNonPlanarity

feature = TrajectoryNonPlanarity()
print({name: feature.parameters[name] for name in ("radius", "nan_value", "nan_fraction", "units")}, "| unit-scaled:", TrajectoryNonPlanarity._unit_params)
print(feature.outputs, TrajectoryNonPlanarity(units="mm").parameters["radius"])
```

Output:

```text
{'radius': 100.0, 'nan_value': 999.0, 'nan_fraction': 0.5, 'units': 'm'} | unit-scaled: {'radius': 1}
Schema(Output('curvature_radius', unit='m')) 100.0
```


---

## 21. Changes after the first version of the sheet (work packages H and I), verified in WP5

Each row was checked against the code on 2026-10-15 (state `a8402dd`). Items of H that touch items 4 to 6, 11 and 17 were edited in place above.

| # | Change | Verified by |
|---|---|---|
| C1 | `MotionNoiseDetector.is_noisy`: `True` means noisy (random, jumpy motion); `False` for a still body, uniform motion and the first 14 frames. `GestureSegmenter`'s `noise` input means *judged to be noise* (blocks a start), so a pipeline feeds it `is_noisy` directly. | `c1_noisy` |
| C2 | `Suddenness.gamma` has no unit (dimensionless). `CurvatureVelocityCorrelation.velocity` and `velocity_std` are per second in both modes (`differentiate` False and True give the same values; unit `<length>/s`). | `c2_gamma_velocity`, `i08c_unit_strings` |
| C3 | `SpikeSynchronization(mode="timings")` is public: input `spike_times`, a matrix `(number_of_inputs, window)` (`window` = spikes per train), one result per matrix (`OK`, no warm-up); times must be > 0 and increasing within a train (`INVALID_INPUT` otherwise); another shape is a `ValueError`. `run` takes `(T, number_of_inputs, window)`. | `c3_spikes` |
| C4 | `MassSpringModel.to_xml()` round trip: `from_xml_string(model.to_xml()).to_xml()` equals the first text. | `c4_xml_symmetry` |
| C5 | `Symmetry(method="ratio")`: `reference_type` accepts only `"label"` (`"barycenter"` and `"point"` raise `ValueError` at construction); a preset without a reference joint asks for `reference_point=` only. | `c4_xml_symmetry`, `x3_symmetry_ratio_reference` |
| C6 | `KineticEnergy(weights=<sequence>)` is one weight per label; `run` gives `Recorder(<Feature>, ...)` for every feature; a non-finite timestamp is `INVALID_INPUT` everywhere. | `c4_xml_symmetry`, `x2_weights_list`, `i04_recorder`, `i06_time` |
| C7 | `SlidingWindow` and `pyeyesweb.utils.tsv_reader` are gone; layer placement and counts (`Directness`, `TrajectoryNonPlanarity` low-level; 11/22/7/1/19). | `c4_xml_symmetry`, `i13_catalog` |

### C1

`is_noisy` and the `noise` input of the segmenter.

Run `c1_noisy`:

```python
import numpy as np
from pyeyesweb.low_level import MotionNoiseDetector
from pyeyesweb.mid_level import GestureSegmenter

rng = np.random.default_rng(0)
def flags(frames):
    detector = MotionNoiseDetector(labels=["a", "b"], sampling_rate=100.0)
    return [bool(detector.process({"a": f[0], "b": f[1]}).is_noisy) for f in frames][-3:]

still = np.zeros((40, 2, 3))
uniform = np.cumsum(np.full((40, 2, 3), 0.001), axis=0)
jumpy = rng.normal(scale=0.05, size=(40, 2, 3))
print("still:", flags(still), "| uniform motion:", flags(uniform), "| random jumps:", flags(jumpy))
print("GestureSegmenter inputs:", GestureSegmenter().inputs.names)
```

Output:

```text
still: [False, False, False] | uniform motion: [False, False, False] | random jumps: [True, True, True]
GestureSegmenter inputs: ('intensity', 'noise')
```

### C2

`gamma` and the velocity of the curvature-velocity correlation.

Run `c2_gamma_velocity`:

```python
import numpy as np
from pyeyesweb.mid_level import Suddenness
from pyeyesweb.low_level import CurvatureVelocityCorrelation

print("Suddenness gamma unit:", repr(Suddenness(window=20).outputs["gamma"].unit), "(dimensionless)")

t = np.linspace(0, 2 * np.pi, 100, endpoint=False)
ellipse = np.c_[np.cos(t), 0.5 * np.sin(t)]
for differentiate in (False, True):
    feature = CurvatureVelocityCorrelation(window=100, hop=100, sampling_rate=100.0, differentiate=differentiate)
    velocity = feature.run(ellipse)[99].velocity
    print(f"differentiate={differentiate}: velocity[[0, 50, 99]] = {np.round(velocity[[0, 50, 99]], 3)}, unit {feature.outputs['velocity'].unit}")
```

Output:

```text
Suddenness gamma unit: '' (dimensionless)
differentiate=False: velocity[[0, 50, 99]] = [0.    3.563 3.726], unit <length>/s
differentiate=True: velocity[[0, 50, 99]] = [0.    3.563 3.726], unit <length>/s
```

### C3

The `timings` mode of `SpikeSynchronization`.

Run `c3_spikes`:

```python
import numpy as np
from pyeyesweb.analysis_primitives import SpikeSynchronization

feature = SpikeSynchronization(mode="timings", number_of_inputs=3, window=4)
print(feature.inputs)
trains = np.array([[0.1, 0.5, 0.9, 1.3], [0.12, 0.52, 0.88, 1.33], [0.2, 0.6, 1.0, 1.4]])
result = feature.process(trains)
print(result.status.name, result.reason == "", {name: np.round(value, 3).tolist() for name, value in result.to_dict().items()})
print(feature.run(np.stack([trains, trains])))
try:
    feature.process(trains[:, :3])
except ValueError as error:
    print("ValueError:", error)
bad = trains.copy(); bad[0, 1] = 0.05
print(feature.process(bad).status.name, repr(feature.process(bad).reason))
```

Output:

```text
Inputs(spike_times: matrix (3, 4) - spike times, one row per train, increasing and > 0)
OK True {'degree': 1.0, 'distance': 0.0, 'profile': []}
Recorder(SpikeSynchronization, rows=2, columns=['degree', 'distance', 'profile'], status={'OK': 2})
ValueError: SpikeSynchronization: input 'spike_times' expects matrix of shape (3, 4), got shape (3, 3)
INVALID_INPUT 'spike times must increase within each train'
```

### C4 to C7

XML round trip, `reference_type`, weights as a sequence, removed names.

Run `c4_xml_symmetry`:

```python
import re
from pyeyesweb.physical_signals import MassSpringModel
from pyeyesweb.low_level import Symmetry, KineticEnergy

model = MassSpringModel(name="rod")
model.add_mass("root", 1e10)
model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0, 0.5, 0.25)
first = model.to_xml()
second = MassSpringModel.from_xml_string(first).to_xml()
print("round trip identical:", first == second)
print(re.findall(r'[Dd]amping\w*="[^"]*"', first))

for kwargs in ({"reference_type": "barycenter"}, {"reference_type": "point"}, {"reference_type": "label"}):
    try:
        feature = Symmetry(skeleton="kinect_v2", method="ratio", **kwargs)
        print(kwargs, "->", feature.parameters["reference_type"], feature.parameters["reference_point"])
    except ValueError as error:
        print(kwargs, "-> ValueError:", error)
print("weights as a sequence:", dict(KineticEnergy(labels=["a", "b"], weights=[1.0, 2.0]).parameters["weights"]))

import importlib
for name in ("pyeyesweb.data_models.SlidingWindow", "pyeyesweb.utils.tsv_reader", "pyeyesweb.data_models.sliding_window"):
    module, _, attribute = name.rpartition(".")
    try:
        target = importlib.import_module(module)
        print(name, "->", "present" if hasattr(target, attribute) else "absent")
    except ImportError:
        print(name, "-> absent (no such module)")
```

Output:

```text
round trip identical: True
['Damping="0.5"', 'Damping="0.25"']
{'reference_type': 'barycenter'} -> ValueError: Symmetry(method='ratio'): reference_type='barycenter' is not supported: the core does not translate the frame for it (the original block did nothing); only 'label' is
{'reference_type': 'point'} -> ValueError: Symmetry(method='ratio'): reference_type='point' is not supported: the core does not translate the frame for it (the original block did nothing); only 'label' is
{'reference_type': 'label'} -> label SpineShoulder
weights as a sequence: {'a': 1.0, 'b': 2.0}
pyeyesweb.data_models.SlidingWindow -> absent
pyeyesweb.utils.tsv_reader -> absent
pyeyesweb.data_models.sliding_window -> absent
```

---

## Appendix: how this sheet was produced

Every snippet was run with the environment of the header (WP5 re-ran all of them with a small script that extracts the `Run` blocks of this file and compares the pasted output; the snippets of section 21 were added then); the generating script (kept outside the repository) substituted the real output. The script, the snippets and the
raw outputs are in the session scratchpad; the sheet is the record. After any change to a feature contract, re-run the snippets and update this file in the same commit; where
a page and this sheet disagree, the page is fixed (the sheet follows the code).
