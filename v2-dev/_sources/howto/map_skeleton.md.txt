# Map your marker set to a skeleton

A feature that works on a body has to know which row of a frame is which joint. A
{py:class}`~pyeyesweb.data_models.Skeleton` carries that knowledge: the names of the joints in the order of the rows, the pairs of
left and right joints, the joint used as origin, and a weight for each joint. This page shows how to describe the marker set of
your own capture system, how to use one of the presets of the library, and what the presets do and do not contain. The
concepts behind it are in {doc}`../concepts/inputs`; the generated reference is {doc}`../api/skeletons`.

## What a feature reads from a skeleton

Five classes take `skeleton=`. Each reads the fields of the skeleton that it needs and ignores the others.

| Class | Fields it reads |
|---|---|
| {py:class}`~pyeyesweb.low_level.KineticEnergy` | `joints` (the labels of the rows) and `weights` (the weight of each joint) |
| {py:class}`~pyeyesweb.low_level.MotionNoiseDetector` | `joints` |
| {py:class}`~pyeyesweb.low_level.Symmetry` | `joints`, `pairs` and, for `method="ratio"`, `reference` |
| {py:class}`~pyeyesweb.low_level.PointsDensity` | `joints` (names only; they do not enter the computation) |
| {py:class}`~pyeyesweb.physical_signals.PointsPredictor` | `joints` |

A value given explicitly to the feature (`labels=`, `weights=`, `pairs=`) always wins over the skeleton. A feature that needs
joints and receives none, neither through `skeleton=` nor through `labels=`, raises `ValueError` at construction. Other
features that work on a body do not take a skeleton: `Equilibrium` takes the points it needs as separate inputs, and the
humanoid features take a `joint_map` (see the last section).

## The presets

The library describes four capture systems in {py:mod}`pyeyesweb.skeletons`. A preset is selected by name; the name is
case-insensitive and `-` or a space counts as `_`.

```{doctest}
>>> from pyeyesweb import skeletons
>>> for name, skeleton in skeletons.SKELETONS.items():
...     print(f"{name:15s} {len(skeleton.joints):2d} joints, {len(skeleton.pairs):2d} pairs, reference {skeleton.reference}, missing {skeleton.missing()}")
kinect_v2       25 joints, 10 pairs, reference SpineShoulder, missing ()
qualisys_sport  41 joints, 18 pairs, reference None, missing ('reference', 'weights')
mediapipe       33 joints, 16 pairs, reference None, missing ('reference', 'weights')
openpose        25 joints, 11 pairs, reference Neck, missing ('weights',)
>>> skeletons.get_skeleton("Kinect-V2").name
'kinect_v2'
```

```{note}
`qualisys_sport`, `mediapipe` and `openpose` define the joints and the pairs of their device, and leave some fields empty,
which `Skeleton.missing()` and `skeletons.SKELETON_TODO` list: no weights, and for `qualisys_sport` and `mediapipe` no reference
joint either. What this means in practice:

- a missing `weights` becomes a weight of 1.0 for every joint;
- a missing `reference` is harmless for `Symmetry(method="reflection")`, which then reflects about the barycentre, but
  `Symmetry(method="ratio")` raises `ValueError` at construction and asks for `reference_point=`.

The joint names keep the spelling of each device (`L*` and `R*`, `*Left` and `*Right`, `left_*` and `right_*`) and are not
normalised. Use them as the preset spells them, or build your own skeleton.
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

A preset can be completed without editing the library, because a `Skeleton` is an immutable dataclass: make a copy with the
missing field filled with {py:func}`dataclasses.replace`. Which joint is the origin of a body is a decision about your analysis,
not a property of the system; the choice below is only an example.

```{doctest}
>>> import dataclasses
>>> mediapipe = skeletons.get_skeleton("mediapipe")
>>> mine = dataclasses.replace(mediapipe, name="mediapipe_hip", reference="left_hip")
>>> mine.missing()
('weights',)
>>> Symmetry(skeleton=mine, method="ratio").parameters["reference_point"]
'left_hip'
```

## A worked example: your own marker set

Suppose a system that tracks nine markers on the upper body and the pelvis, and delivers them in this order. The order of the
columns of your array is the order of the joints of the skeleton: it is the only link between the data and the names.

```{doctest}
>>> from pyeyesweb.data_models import Skeleton
>>> markers = ["pelvis", "chest", "head", "l_shoulder", "r_shoulder", "l_elbow", "r_elbow", "l_wrist", "r_wrist"]
```

Describe the fields in turn.

1. **`joints`**: the names, in the order of the columns. They must be unique.
2. **`pairs`**: the couples `(left, right)` of joints that mirror each other. Only the symmetry features use them.
3. **`reference`**: the joint taken as the origin of the body, for the ratio symmetry. It must be one of the joints.
4. **`weights`**: for the kinetic energy, a weight for each joint (for example the fraction of the body mass that the marker
   stands for). A joint that has no entry in a weights mapping weighs 0 (see below).

```{doctest}
>>> upper_body = Skeleton(
...     "upper_body",
...     joints=tuple(markers),
...     pairs=(("l_shoulder", "r_shoulder"), ("l_elbow", "r_elbow"), ("l_wrist", "r_wrist")),
...     reference="pelvis",
...     weights={"pelvis": 0.30, "chest": 0.25, "head": 0.08, "l_shoulder": 0.04, "r_shoulder": 0.04,
...              "l_elbow": 0.03, "r_elbow": 0.03, "l_wrist": 0.01, "r_wrist": 0.01},
... )
>>> upper_body.missing()
()
>>> upper_body.index("head")
2
```

`missing()` is empty: nothing is left to fill. Now give the skeleton to the features. The inputs they declare show the shape of a
frame, one row per joint, and `parameters` shows what they took from the skeleton.

```{doctest}
>>> from pyeyesweb.low_level import KineticEnergy, MotionNoiseDetector, PointsDensity
>>> energy = KineticEnergy(skeleton=upper_body, sampling_rate=100.0)
>>> energy.inputs
Inputs(skeleton: points (9, 3) - joint positions or velocities)
>>> energy.parameters["weights"]["head"]
0.08
>>> symmetry = Symmetry(skeleton=upper_body, method="ratio")
>>> symmetry.parameters["pairs"], symmetry.parameters["reference_point"]
([('l_shoulder', 'r_shoulder'), ('l_elbow', 'r_elbow'), ('l_wrist', 'r_wrist')], 'pelvis')
>>> PointsDensity(skeleton=upper_body).inputs
Inputs(points: points (9, 3) - points whose dispersion is measured)
>>> MotionNoiseDetector(skeleton=upper_body).inputs
Inputs(skeleton: points (9, 3) - joint positions)
```

A recording of this system is an array of shape `(frames, 9, 3)`; here a random walk stands in for the data. `run` takes the
whole array and `process` takes one frame, either as an array of shape `(9, 3)` or as a dict `joint -> (x, y, z)` in any order.

```{doctest}
>>> positions = np.cumsum(np.random.default_rng(0).normal(0.0, 0.002, size=(200, 9, 3)), axis=0)   # metres
>>> energy.run(positions)
Recorder(KineticEnergy, rows=200, columns=['kinetic_energy'], status={'OK': 200})
>>> frame = {name: positions[10, row] for row, name in enumerate(markers)}
>>> energy.process(frame, timestamp=0.0).status.name
'OK'
>>> symmetry.process(positions[0])
SymmetryResult(status=OK, symmetry=0.224588)
>>> Symmetry(skeleton=upper_body, method="reflection").process(positions[0])
SymmetryResult(status=OK, pair_symmetry=[0.1311, 0.39  , 0.1896])
```

The ratio method gives one number for the whole body; the reflection method gives one value per pair, in the order of `pairs`.

### When the recording has more markers than the skeleton

The rows of a frame must be exactly the joints of the skeleton. If the system exports more markers than you want to use, select
the columns first, with the indices of the names in the full list.

```{doctest}
>>> exported = markers + ["l_hip", "r_hip"]
>>> recording = np.zeros((50, len(exported), 3))
>>> columns = [exported.index(name) for name in upper_body.joints]
>>> selected = recording[:, columns]
>>> selected.shape
(50, 9, 3)
>>> energy.run(selected).status.tolist()[:3]
[0, 0, 0]
```

## What an explicit value changes

`labels=`, `weights=` and `pairs=` override the corresponding field of the skeleton. A `weights` mapping replaces the weights of
the skeleton as a whole, and a joint that is not in it weighs 0, as an unlisted joint does in EyesWeb; a sequence is read as one
weight per label.

```{doctest}
>>> only_pelvis = KineticEnergy(skeleton=upper_body, weights={"pelvis": 1.0}, sampling_rate=100.0)
>>> only_pelvis.parameters["weights"]
{'pelvis': 1.0}
>>> still = np.zeros((9, 3))
>>> moved_head = still.copy()
>>> moved_head[markers.index("head"), 0] = 0.1          # only the head moves, 0.1 m in 0.01 s
>>> _ = only_pelvis.process(still, timestamp=0.0)
>>> only_pelvis.process(moved_head, timestamp=0.01).kinetic_energy
0.0
>>> KineticEnergy(skeleton=upper_body, weights=[1.0, 2.0], sampling_rate=100.0)
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: weights has 2 values, the skeleton has 9 joints
```

The weights of a skeleton are used by `KineticEnergy` only. No other feature takes `weights`.

## Resolve a skeleton in your own code

{py:func}`pyeyesweb.skeletons.get_skeleton` returns a `Skeleton` from a name or from a skeleton, and
{py:func}`pyeyesweb.skeletons.with_skeleton` is the helper that the five classes use to turn `skeleton=` into their labels and
parameters, with explicit values winning. They are useful for a function of your own that accepts both forms.

```{doctest}
>>> labels, parameters = skeletons.with_skeleton("kinect_v2", None, {"pairs": ()}, lambda skeleton: {"pairs": skeleton.pairs})
>>> len(labels), parameters
(25, {'pairs': ()})
>>> skeletons.get_skeleton(upper_body) is upper_body
True
```

## Mapping to a body model: `joint_map`

The humanoid and generic-model features of the physical-signals layer do not take a skeleton. They follow a captured body with a
model that has its own joint names (`pyeyesweb.physical_signals.HUMANOID_JOINTS`, 21 names), and the parameter `joint_map`
says which label of your data feeds each model joint, as `model joint -> your label`. A joint you leave out keeps the model's
name. Six classes take `joint_map`: `HumanoidSimulator`, `HumanoidOrientations`, `GenericModelOrientations`,
`GenericModelSimulator`, `GenericModelPredictor` and `GenericModelEstimator`.

```{doctest}
>>> from pyeyesweb.physical_signals import HUMANOID_JOINTS, HumanoidSimulator
>>> HUMANOID_JOINTS[:4]
('head', 'left_ankle', 'left_elbow', 'left_foot')
>>> simulator = HumanoidSimulator(joint_map={"head": "Head", "neck": "Neck"}, sampling_rate=25.0)
>>> simulator.process({"Head": (0.0, 1.7, 0.0), "Neck": (0.0, 1.5, 0.0)}).joints.shape
(21, 3)
```

The simulator follows a body model and expects frames in the unit given by `units`; see
{doc}`../theory/humanoid_models` for what the model does and {doc}`../concepts/time_units_parameters` for the unit rule.

## What goes wrong, and how it is reported

A skeleton is checked when it is built, and a frame is checked when it is given. The errors name the feature and the offending
names.

```{doctest}
>>> Skeleton("bad", joints=("a", "a"))
Traceback (most recent call last):
  ...
ValueError: skeleton 'bad': repeated joint names
>>> Skeleton("bad", joints=("a", "b"), pairs=(("a", "c"),))
Traceback (most recent call last):
  ...
ValueError: skeleton 'bad': names that are not joints: ['c']
>>> Skeleton("bad", joints=("a", "b"), reference="z")
Traceback (most recent call last):
  ...
ValueError: skeleton 'bad': names that are not joints: ['z']
>>> skeletons.get_skeleton("kinect")
Traceback (most recent call last):
  ...
ValueError: skeleton: invalid value 'kinect'; choose one of 'kinect_v2', 'qualisys_sport', 'mediapipe', 'openpose' (or a Skeleton)
>>> KineticEnergy()
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: no joints given; pass skeleton= (e.g. 'kinect_v2') or your own weights= / pairs=
>>> Symmetry(skeleton=upper_body, pairs=[("l_hand", "r_hand")])
Traceback (most recent call last):
  ...
ValueError: Symmetry: names that are not among the labels: ['l_hand', 'r_hand']
>>> energy.process(np.zeros((8, 3)))
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: input 'skeleton' expects points of shape (9, 3), one row per label (9 labels), got shape (8, 3)
>>> energy.process({**frame, "foot": (0.0, 0.0, 0.0)}, timestamp=0.01)
Traceback (most recent call last):
  ...
ValueError: KineticEnergy: unknown joint names ['foot']; expected ['pelvis', 'chest', 'head', 'l_shoulder', 'r_shoulder', 'l_elbow', 'r_elbow', 'l_wrist', 'r_wrist']
>>> without_head = {name: value for name, value in frame.items() if name != "head"}
>>> energy.process(without_head, timestamp=0.02).reason
'missing joints: head'
```

| Situation | Reported as |
|---|---|
| a name repeated in `joints`, or a name in `pairs`, `reference` or `weights` that is not a joint | `ValueError` when the `Skeleton` is built |
| a preset name that does not exist | `ValueError` listing the presets |
| a feature that needs joints and gets none | `ValueError` at construction |
| `weights=` with a different number of values than there are labels | `ValueError` at construction |
| an array frame with another number of rows than joints | `ValueError` naming the expected shape |
| a key of a dict frame that is not a joint of the skeleton | `ValueError` naming the unknown names |
| a joint that the feature needs is missing from a dict frame | result with status `INVALID_INPUT` and `reason` "missing joints: ..." |
| `Symmetry(method="ratio")` on a skeleton with no reference | `ValueError` asking for `reference_point=` |

The distinction follows the error policy of the library: a configuration mistake raises, a gap in the data (a dropped marker)
is reported in the result and leaves the state of the feature unchanged ({doc}`../concepts/results`).
