# Physical signals

Layer 1 of the conceptual model ({doc}`../theory/framework`) holds the signals that come from sensors and the virtual sensors
built on them. In PyEyesWeb a feature of this layer takes raw frames or a model and gives a signal again, so that the features
of the upper layers can work on cleaner or richer data: it simulates a body, extracts centroids or parts from an image, or
locates points in a grid. Its timescale is the frame: a value belongs to one call, not to a window. This page helps to choose
among the {{ n_physical_signals }} features of the layer; the layers are described in {doc}`../concepts/layers`.

```{feature-table} physical_signals
```

## Which feature for which problem

The features fall in three groups, one for each kind of input.

**You have a skeleton and want a cleaner or a forecast one.** The captured joints jitter and drop out; a mass-spring model
follows them and gives a smooth, articulated pose with constant bone lengths.

- {py:class}`~pyeyesweb.physical_signals.HumanoidSimulator` for the fixed 21-joint humanoid (the joints of the first Kinect
  SDK as EyesWeb names them). It is the choice for a body captured by any system whose joints you can map to those names (see
  {doc}`../howto/map_skeleton`).
- {py:class}`~pyeyesweb.physical_signals.HumanoidOrientations` when you need the posture itself, the direction of each bone in
  the frame of its parent, which does not depend on where the body is.
- {py:class}`~pyeyesweb.physical_signals.GenericModelSimulator`, {py:class}`~pyeyesweb.physical_signals.GenericModelOrientations`,
  {py:class}`~pyeyesweb.physical_signals.GenericModelPredictor` and
  {py:class}`~pyeyesweb.physical_signals.GenericModelEstimator` when the structure is not a human body (a limb, a puppet, an
  instrument) or you want to predict a movement or identify the parameters of a body. They take a `MassSpringModel`.
- {py:class}`~pyeyesweb.physical_signals.PointsPredictor` for the simplest forecast of any labelled points, a constant-velocity
  extrapolation one frame ahead, with no model.

Theory, assumptions and the units exception: {doc}`../theory/humanoid_models`.

**You have video and want the body without a skeleton.** The silhouette of a person is a binary mask.

- {py:class}`~pyeyesweb.physical_signals.SilhouetteCentroids` for 14 points of a body (centre of gravity, head, shoulders,
  elbows, hands, knees, feet), cheap enough to follow at the frame rate of a camera.
- {py:class}`~pyeyesweb.physical_signals.SilhouetteBodyParts` for the bounding box and the mask of six parts (head, trunk, arms,
  legs), when you want to analyse a part of the image, not a point.
- {py:class}`~pyeyesweb.physical_signals.Videogram` to summarise a long video in one image in which a movement is a visible
  trace, for inspection or for a visual feature of the movement over time.

Theory: {doc}`../theory/imaging`. The outline of a silhouette is measured by the contour features of layer 2.

**You have positions in a plane and want to know where they fall.** {py:class}`~pyeyesweb.physical_signals.HitCellDetector`
divides a rectangle into a grid and gives the cell of each point. It is the first step of the space-occupation features of
layer 3 ({doc}`mid_level`); its theory is in {doc}`../theory/shape_symmetry_balance`.

## A typical pipeline

A skeleton passes through the simulator and then to the features of layer 2. The simulator is driven by three captured frames,
with a joint missing in the second one (a dropout); it gives the 21 joints at every call, and the simulated joints, labelled like
the model, feed any feature that takes a labelled skeleton.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.physical_signals import HUMANOID_JOINTS, HumanoidSimulator
>>> from pyeyesweb.low_level import KineticEnergy
>>> simulator = HumanoidSimulator(sampling_rate=25.0)
>>> energy = KineticEnergy(labels=list(HUMANOID_JOINTS), weights={name: 1.0 for name in HUMANOID_JOINTS}, sampling_rate=25.0)
>>> tpose = simulator.process({"head": (0.0, 0.0, 0.0)}).joints
>>> frame = {name: tuple(point) for name, point in zip(HUMANOID_JOINTS, tpose)}
>>> second = {name: point for name, point in frame.items() if name != "left_hand"}    # dropout
>>> statuses = []
>>> for captured in (frame, second, frame):
...     simulated = simulator.process(captured)
...     statuses.append((simulated.status.name, bool(np.isfinite(simulated.joints).all())))
>>> statuses
[('OK', True), ('OK', True), ('OK', True)]
>>> energy.process(dict(zip(HUMANOID_JOINTS, simulated.joints))).status.name
'OK'
```

The other pipeline of the layer goes from an image to the measures of an outline: a mask, then
{py:class}`~pyeyesweb.physical_signals.SilhouetteCentroids` or the contour of the mask, then the contour features of
{doc}`low_level`.

## What to know before choosing

- The features of this layer do not wait for data: every valid call is `OK`, with no warm-up (see {doc}`../concepts/results`).
- Time is in seconds. The simulators, the predictor and the estimator advance their model by the time of the call
  ({doc}`../concepts/time_units_parameters`); the image features and `HitCellDetector` have no time axis.
- Units: `HumanoidSimulator` is the one feature of the library that converts data (its model is in millimetres and it converts at
  the boundary); the generic models do not. {doc}`../theory/humanoid_models` explains the difference.
- Image features take 8-bit images or masks and return pixel coordinates (see {doc}`../concepts/inputs`).

% TODO(WP7): gallery link
