# Inputs

Every feature declares what one call receives, and it does so before any data arrives. The declaration is
`feature.inputs`, the counterpart of the declared outputs described in {doc}`results`. It makes it possible to shape and
validate data without trial and error, and every call is checked against it.

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy, Kinematics
>>> Kinematics(sampling_rate=100.0).inputs
Inputs(point: sample (?) - position of the point (or value of the signal))
>>> KineticEnergy(skeleton="kinect_v2").inputs
Inputs(skeleton: points (25, 3) - joint positions or velocities)
```

Each entry is an {py:class}`~pyeyesweb.data_models.Input`: a name, a kind, a shape (`?` where the size is set by a
parameter or by the data), the labels of the rows or channels when the feature was given them, and a unit. A feature with
several inputs lists them in the order of the positional arguments of `process`.

## Four kinds of input

| Kind | One call to `process` receives | `run` receives |
|---|---|---|
| `SAMPLE` | a number, or a vector of `C` channel values (a scalar signal has `C = 1`); an event train is a stream in which a non-zero value is an event | `(T, C)`, or `(T,)` for one channel |
| `POINTS` | one frame of `N` labelled points of dimension `D`, an `(N, D)` array | `(T, N, D)` |
| `MATRIX` | one `(R, C)` matrix, for example the output of another feature | `(T, R, C)` |
| `IMAGE` | one 8-bit image, `(H, W)` or `(H, W, C)` | `(T, H, W)` or `(T, H, W, C)`, or a list of images |

`T` is the number of samples in time. The kinds are the members of {py:class}`~pyeyesweb.data_models.InputKind`, one of the
four enumerations that are part of the public interface (the others are `Layer`, `Timescale` and `Status`).

```{doctest}
>>> from pyeyesweb.analysis_primitives import PartialRecurrenceSynchronization
>>> from pyeyesweb.physical_signals import Videogram
>>> [feature.inputs[0].kind.name for feature in (Kinematics(), KineticEnergy(skeleton="kinect_v2"), PartialRecurrenceSynchronization(), Videogram())]
['SAMPLE', 'POINTS', 'MATRIX', 'IMAGE']
```

The values are used as floating-point numbers: an integer array is accepted and converted.

## Shape errors and data problems

Two different things can be wrong with a call, and they are reported differently.

- A **shape or kind error** is a programming mistake: a sample of the wrong size, a frame with the wrong number of points or
  the wrong dimension, an image of the wrong rank. It raises `ValueError`, which names the feature and the input.
- A **data problem** is something that happens to real recordings: NaN or infinity, an empty frame, a joint that a dict frame
  does not contain, a timestamp that goes back. It does not raise. The call returns a result with status
  `INVALID_INPUT` and a `reason` (see {doc}`results`).

```{doctest}
>>> energy = KineticEnergy(labels=["head", "hand"], weights=[1.0, 2.0], sampling_rate=100.0)
>>> energy.process(np.zeros((3, 3)))
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: input 'skeleton' expects points of shape (2, 3), one row per label (2 labels), got shape (3, 3)
>>> result = energy.process(np.full((2, 3), np.nan))
>>> result.status.name, result.reason
('INVALID_INPUT', 'NaN or infinite values')
```

An empty frame (no points) is not a shape error either; it reaches the feature, which reports `INVALID_INPUT`.

## Several inputs

A feature that takes several signals receives them as positional arguments, in the order of `inputs`. Time is never one of
them: `timestamp` (and `timestamps` in `run`) is keyword-only.

```{doctest}
>>> from pyeyesweb.low_level import Equilibrium
>>> balance = Equilibrium()
>>> balance.inputs.names
('left_foot', 'right_foot', 'barycenter')
>>> balance.process((-0.1, 0.0), (0.1, 0.0), (0.0, 0.5), timestamp=0.0).status.name
'OK'
>>> balance.process((-0.1, 0.0), (0.1, 0.0), (0.0, 0.5), 0.0)
Traceback (most recent call last):
  ...
ValueError: Equilibrium: takes 3 input(s) (left_foot, right_foot, barycenter), got 4
```

The last call shows what happens when a timestamp is passed as the fourth positional argument: it is read as a fourth input,
and the count is wrong.

## Labels and dict frames

A feature that works on named joints (such as {py:class}`~pyeyesweb.low_level.KineticEnergy`) is given `labels`: the names of
the rows, in the order of the arrays it will receive. A frame can then be passed either as an `(N, 3)` array in that order, or
as a dict `label -> (x, y, z)`, in any order.

Weights are optional: `KineticEnergy(labels=[...])` weighs every joint 1.0, `weights=` is a mapping or a sequence with one
weight per label, and a joint missing from an explicit mapping weighs 0 (it does not contribute).

```{doctest}
>>> KineticEnergy(labels=["head", "hand"]).parameters["weights"]
{'head': 1.0, 'hand': 1.0}
>>> energy = KineticEnergy(labels=["head", "hand"], weights=[1.0, 2.0], sampling_rate=100.0)
>>> energy.inputs
Inputs(skeleton: points (2, 3) - joint positions or velocities)
>>> energy.process({"hand": (0.0, 0.0, 0.0), "head": (0.0, 0.0, 0.0)}, timestamp=0.00).kinetic_energy
0.0
>>> energy.process(np.array([[0.0, 0.0, 0.0], [0.01, 0.0, 0.0]]), timestamp=0.01).kinetic_energy
1.0
```

The two kinds of error on a dict frame follow the rule above. A joint the feature needs that is missing is a data problem
(`INVALID_INPUT`, "missing joints: ..."), as a dropout in a recording would be. A key that is not one of the configured
labels is a configuration mistake, and raises `ValueError`:

```{doctest}
>>> energy.process({"head": (0.0, 0.0, 0.0)}, timestamp=0.02).reason
'missing joints: hand'
>>> energy.process({"head": (0, 0, 0), "hand": (0, 0, 0), "foot": (0, 0, 0)}, timestamp=0.03)
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: unknown joint names ['foot']; expected ['head', 'hand']
```

A recording of `T` frames of `N` labelled points is given to `run` as a `(T, N, 3)` array in the order of `labels`, or, for
the features that take dict frames, as a list of dict frames; the numbers are those of a loop of `process`. A feature that
takes no dict frames raises `ValueError` for a list of dicts.

```{doctest}
>>> recording = np.zeros((4, 2, 3))
>>> recording[:, 1, 0] = np.arange(4) * 0.01
>>> energy.run(recording)
Recorder(KineticEnergy, rows=4, columns=['kinetic_energy'], status={'OK': 4})
>>> frames = [{"head": (0.0, 0.0, 0.0), "hand": (0.01 * k, 0.0, 0.0)} for k in range(4)]
>>> energy.run(frames).kinetic_energy.tolist() == energy.run(recording).kinetic_energy.tolist()
True
```

## Skeletons

Instead of listing joints by hand, a feature that works on a body takes `skeleton=`, either the name of a preset or a
{py:class}`~pyeyesweb.data_models.Skeleton` that you build. A skeleton carries the joint names, optionally the symmetric
pairs, a reference joint and the weights of the joints. `skeleton=` is accepted by five classes:
{py:class}`~pyeyesweb.low_level.KineticEnergy` (joints and weights), {py:class}`~pyeyesweb.low_level.MotionNoiseDetector`,
{py:class}`~pyeyesweb.low_level.Symmetry` (joints, pairs and reference), {py:class}`~pyeyesweb.low_level.PointsDensity` and
{py:class}`~pyeyesweb.physical_signals.PointsPredictor`. An explicit `labels=`, `weights=` or `pairs=` always wins over the
skeleton, and a feature given no joint information at all raises `ValueError`. (`KineticEnergy(labels=[...])` alone is joint
information: it weighs every joint 1.0.)

The presets are in `pyeyesweb.skeletons` (see {doc}`../api/skeletons`). Names are case-insensitive, and `-` or a space counts as `_`.

```{doctest}
>>> from pyeyesweb import skeletons
>>> for name, skeleton in skeletons.SKELETONS.items():
...     print(f"{name:15s} {len(skeleton.joints):2d} joints, {len(skeleton.pairs):2d} pairs, reference {skeleton.reference}, missing: {skeleton.missing()}")
kinect_v2       25 joints, 10 pairs, reference SpineShoulder, missing: ()
qualisys_sport  41 joints, 18 pairs, reference None, missing: ('reference', 'weights')
mediapipe       33 joints, 16 pairs, reference None, missing: ('reference', 'weights')
openpose        25 joints, 11 pairs, reference Neck, missing: ('weights',)
>>> skeletons.get_skeleton("Kinect-V2").name
'kinect_v2'
```

```{note}
`Skeleton.missing()` and `skeletons.SKELETON_TODO` list the fields that a preset does not define. A missing weight becomes
1.0 for every joint. A missing reference joint is harmless for `Symmetry(method="reflection")`, which then reflects about the
barycentre, but `Symmetry(method="ratio")` needs one and raises `ValueError` at construction, asking for `reference_point=`.
```

```{doctest}
>>> skeletons.SKELETON_TODO
{'kinect_v2': (), 'qualisys_sport': ('reference', 'weights'), 'mediapipe': ('reference', 'weights'), 'openpose': ('weights',)}
>>> from pyeyesweb.low_level import Symmetry
>>> Symmetry(skeleton="mediapipe", method="ratio")
Traceback (most recent call last):
  ...
ValueError: Symmetry(method='ratio'): the skeleton 'mediapipe' defines no reference joint; pass reference_point= (a joint of the skeleton)
>>> Symmetry(skeleton="mediapipe", method="ratio", reference_point="nose").parameters["reference_point"]
'nose'
```

The joint names differ between presets (`L*`/`R*`, `*Left`/`*Right`, `left_*`/`right_*`) and are used exactly as the
preset spells them; they are not normalised. A frame given as a dict must use the preset's names; a frame given as an array
must have as many rows as the preset has joints.

### The reference joint of `Symmetry`

The reference joint is the origin to which `Symmetry` translates the whole frame (every joint minus that joint) before it
computes anything, so that only the posture counts, not where the body stands. It comes from `reference_point=` or, when
that is absent, from the skeleton (`Skeleton.reference`). With `method="ratio"` it is needed (`"neck"` is the default
without a skeleton); with `method="reflection"` a frame without a reference joint is reflected about its barycentre (the mean
position of the joints). The `"label"` rule is the only one the core implements, so there is no `reference_type` parameter:
to centre a ratio on something else, subtract that point from the frame yourself.

```{doctest}
>>> labels = ["neck", "left_hand", "right_hand", "foot"]
>>> frame = np.array([[0.0, 0.0, 0.0], [-1.0, 1.0, 0.0], [2.0, 1.0, 0.0], [5.0, 5.0, 5.0]])
>>> pairs = [("left_hand", "right_hand")]
>>> ratio = Symmetry(labels, pairs=pairs, reference_point="foot")
>>> bool(np.isclose(ratio.process(frame).symmetry, ratio.process(frame + 10.0).symmetry))
True
>>> mirror = Symmetry(labels, pairs=pairs, method="reflection")
>>> bool(np.isclose(mirror.process(frame).pair_symmetry[0], mirror.process(frame + 10.0).pair_symmetry[0]))
True
```

You can build a skeleton for your own marker set:

```{doctest}
>>> from pyeyesweb.data_models import Skeleton
>>> arm = Skeleton("arm", joints=("shoulder", "elbow", "hand"), reference="shoulder", weights={"shoulder": 4.0, "elbow": 2.0, "hand": 1.0})
>>> KineticEnergy(skeleton=arm, sampling_rate=100.0).parameters["weights"]
{'shoulder': 4.0, 'elbow': 2.0, 'hand': 1.0}
```

## Mapping your joint names to a model: `joint_map`

The humanoid and generic-model features of the physical-signals layer follow a captured skeleton with a body model. The model
has its own joint names (`pyeyesweb.physical_signals.HUMANOID_JOINTS`), and `joint_map` says which label of your data feeds
each model joint, as `model joint -> your label`. The names you leave out keep their own. Only these six classes take
`joint_map`: `HumanoidSimulator`, `HumanoidOrientations`, `GenericModelOrientations`, `GenericModelSimulator`,
`GenericModelPredictor` and `GenericModelEstimator`.

```{doctest}
>>> from pyeyesweb.physical_signals import HumanoidSimulator
>>> simulator = HumanoidSimulator(joint_map={"head": "Head", "neck": "Neck"}, sampling_rate=25.0)
>>> simulator.process({"Head": (0.0, 1.7, 0.0), "Neck": (0.0, 1.5, 0.0)}).joints.shape
(21, 3)
```

## Images

Image features take an 8-bit image per call, `(H, W)` for grayscale or `(H, W, C)` for colour. A mask is a `bool` array, read
as 0 and 1; a mask of a body (as the silhouette features take) counts every non-zero pixel as foreground. Any other numeric
array must hold whole numbers from 0 to 255 (the value `3.0` is accepted, `0.5` and `300` raise `ValueError`), and a wrong rank raises.

```{doctest}
>>> from pyeyesweb.physical_signals import SilhouetteCentroids
>>> silhouette = np.zeros((8, 8), dtype=bool)
>>> silhouette[2:6, 3:5] = True
>>> centroids = SilhouetteCentroids().process(silhouette)
>>> centroids.status.name
'OK'
>>> Videogram(window=3).process(np.full((4, 4), 0.5))
Traceback (most recent call last):
  ...
ValueError: Videogram: input 'frame' expects whole-number pixel values in 0-255, got float64 values from 0.5 to 0.5
```

Images never enter a `Recorder` table: `to_numpy()` and `to_frame()` hold the numeric outputs only, and the image outputs of a
recording are read from the `Result` of each row.

## One quantity in two forms: `from_*` constructors

Some features read the same quantity in two different forms: kinetic energy from positions or from velocities, kinematics
of a single point or of a whole series, the jerk measure from a speed profile or from an acceleration. The form is the
`input_mode` constructor parameter, and each form also has a constructor of its own that fixes it and makes the intent
explicit in the code. Exactly three classes have them (six constructors).

| Class | Constructors |
|---|---|
| {py:class}`~pyeyesweb.low_level.KineticEnergy` | `from_position`, `from_velocity` |
| {py:class}`~pyeyesweb.low_level.Kinematics` | `from_point`, `from_series` |
| {py:class}`~pyeyesweb.low_level.LogDimensionlessJerk` | `from_velocity`, `from_acceleration` |

```{doctest}
>>> positions = KineticEnergy.from_position(skeleton="kinect_v2", sampling_rate=100.0)
>>> velocities = KineticEnergy.from_velocity(skeleton="kinect_v2")
>>> positions.parameters["input_mode"], velocities.parameters["input_mode"]
('position', 'velocity')
>>> Kinematics.from_point(sampling_rate=100.0).inputs
Inputs(point: sample (?) - position of the point (or value of the signal))
>>> Kinematics.from_series(sampling_rate=100.0).inputs
Inputs(series: matrix (?, ?) - (D, N) series, newest sample last)
```

The two constructors of a class take the same parameters, and `input_mode` is not among them: it is what the constructor
sets. What differs is what the feature declares as its input, and how it reads it. `Kinematics.from_series` takes one
`(D, N)` series per call, `D` dimensions by `N` samples, with the newest sample last, instead of one point.

## The dimension of a signal: `dims`

Four classes (`Kinematics`, `CurvatureDispersion`, `Suddenness` and `SuddennessImpulsivity`) work on a point or signal of
any dimension. Their `dims` parameter defaults to `None`, which means "taken from the first frame". The inferred value is
fixed for the rest of the run, a later frame of another size raises `ValueError`, and `reset()` forgets it.

```{doctest}
>>> kinematics = Kinematics(sampling_rate=100.0)
>>> kinematics.parameters["dims"] is None
True
>>> result = kinematics.process((0.0, 0.0, 0.0))
>>> kinematics.parameters["dims"]
3
>>> kinematics.process((0.0, 0.0))
Traceback (most recent call last):
  ...
ValueError: Kinematics: input 'point' expects sample of shape (3,), got shape (2,)
>>> kinematics.reset()
>>> kinematics.parameters["dims"] is None
True
```
