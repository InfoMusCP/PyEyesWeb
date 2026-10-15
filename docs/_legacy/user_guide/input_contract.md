# Input contract

Every feature takes its input the same way, and says what that input is **before you give it any data**, just as it
says what it returns (see [Output contracts](output_contracts.md)).

```python
from pyeyesweb.low_level import SpeedSmoothness

feature = SpeedSmoothness(window=60, hop=5, rate_hz=50.0)

feature.inputs                    # Inputs(speed: sample (1) [units/s] - speed of the movement)
feature.outputs                   # what it returns

for speed in stream:              # streaming: one sample (frame) per call
    result = feature.process(speed, t=timestamp_seconds)

recording = feature.run(speeds)   # offline: a whole recording, returns a Recorder
recording.to_frame()
```

## The rules

1. **`feature.inputs` declares what one call receives.** Each input has a name, a kind, a shape, and the joint or
   channel labels when the feature was given them. It depends only on the constructor parameters.
2. **Two calls everywhere.**
   - `process(x, t=None)` takes one sample or frame and returns a `Result`. It keeps state between calls (previous
     frames, the window being filled).
   - `run(X, ts=None)` takes a whole recording, with time on the first axis, and returns a `Recorder` with one row per
     sample. Where the core has a batch loop it runs in C++ (`KineticEnergy`), otherwise it calls `process`. Both
     give the same numbers.
3. **`run` starts from a fresh state** (`reset=True`), so `run(recording)` always gives the same output for the same
   recording. Pass `reset=False` to continue from the previous call, e.g. to process a long recording in chunks.
   `feature.reset()` clears the state of a streaming feature.
4. **Time is optional and in seconds.** `t` (or `ts`, one per sample) is the timestamp; the result's `t` is `NaN` when
   it was not given. Nothing is stamped with the wall clock.
5. **Features that work on a window own their buffer.** They are configured with `window` and `hop` and receive
   samples:
   - `process` returns `WARMING_UP` until the first window is full and `NO_OUTPUT` between hops;
   - `process_window(series)` computes one complete `(channels, window)` window directly, for static analysis of a
     segment.
6. **Labelled inputs** (skeletons) take their joint names at construction, `KineticEnergy(labels=[...])`, and then
   `(N, 3)` arrays; a dict `label -> (x, y, z)` is accepted too. Arrays are much cheaper than dicts per frame.

## Input kinds

| Kind | One call receives | `run` receives |
|---|---|---|
| `SAMPLE` | a vector of `C` channel values (a scalar signal has `C = 1`) | `(T, C)` or `(T,)` |
| `POINTS` | one frame of `N` labelled points, an `(N, D)` array (a 2-D contour is `D = 2`) | `(T, N, D)` |
| `MATRIX` | one `(R, C)` matrix, e.g. the output of another feature | `(T, R, C)` |

**Events are samples.** A block that synchronises events takes event trains as `SAMPLE` streams in which a non-zero value
is an event (this is how the EyesWeb blocks read them), so they need no kind of their own.

**Several inputs.** A feature with more than one input (a pair of signals, `Impulsivity(sqom, ci)`) lists them in
`inputs` in call order and takes them as positional arguments: `process(x, y, t=None)`, `run(X, Y, ts=None)`. Every
input has the same number of samples in `run`.

**Static series.** Features whose EyesWeb block runs on a static series (correlations, recurrence plots, periodicity)
are windowed features: `process` takes samples, and `process_window(series)` is the EyesWeb Execute on one complete
`(channels, window)` series.

## Sharing data between features

`SlidingWindow` is a standalone circular buffer for the case where several features read the same stream. It is not
needed to call a feature: windowed features keep their own buffer.

## Writing a feature

Subclass `Feature` (or `WindowedFeature`), declare `INPUTS` or `_inputs()`, `OUTPUTS` or `_schema()`, and implement
`process` (or `process_window`). `run` and `reset` come with the base class; override `run` when a batch fast path
exists.

## Reproducibility caveats

`run` starts from a fresh state: `reset()` clears the whole state of every feature (`Rarity` and `GestureSegmenter` used
to keep their bin indices and speed windows, as EyesWeb does; the core now clears them).

## Status

Every feature follows the contract. Where a feature has an extra entry point it carries a genuinely different input:
`Kinematics.process_trajectory` (a `Trajectory` object), `EllipsoidSphericity.process_axes` (three axis lengths, the
EyesWeb input), and `process_window(series)` on windowed features (one complete window).
