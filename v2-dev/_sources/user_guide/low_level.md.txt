# Low-level features

Layer 2 describes a movement fragment: a single frame or a short window of up to about half a second. The values are time
series at the rate of the input, and they are the quantities most analyses start from: how fast a point moves, how much energy
a body spends, how contracted, symmetric or balanced a posture is, how smooth a speed profile is, what shape an outline has. The
layer has {{ n_low_level }} features; this page helps to choose among them and shows how they chain. The background is in
{doc}`../concepts/layers` and {doc}`../theory/framework`.

```{feature-table} low_level
```

## Which feature for which question

**How does a point move?** {py:class}`~pyeyesweb.low_level.Kinematics` gives the velocity, acceleration, jerk, curvature or
direction of a point from a Savitzky-Golay fit, and is the usual first step: its speed feeds the smoothness metrics. For the
energy of a whole body use {py:class}`~pyeyesweb.low_level.KineticEnergy`, the weighted kinetic energy of the joints of a
skeleton. {py:class}`~pyeyesweb.low_level.DirectionChange` measures the sharp turns of a path in a window,
{py:class}`~pyeyesweb.low_level.Directness` how straight a path is, and
{py:class}`~pyeyesweb.low_level.TrajectoryNonPlanarity` how far a 3D path leaves its best-fit planes.
{py:class}`~pyeyesweb.low_level.MotionNoiseDetector` tells whether the motion of a skeleton is random. Theory:
{doc}`../theory/kinematics_energy`.

**How smooth is it?** Start from a speed profile and pick the metric that suits the question.
{py:class}`~pyeyesweb.low_level.SpectralArcLength` and {py:class}`~pyeyesweb.low_level.LogDimensionlessJerk` are the two
established metrics {cite}`balasubramanian2015smoothness`; {py:class}`~pyeyesweb.low_level.SubmovementCount` counts the
speed peaks, {py:class}`~pyeyesweb.low_level.Harmonicity` compares a profile with a single bell-shaped peak, and
{py:class}`~pyeyesweb.low_level.CurvatureDispersion` and {py:class}`~pyeyesweb.low_level.CurvatureVelocityCorrelation`
work on the vectors of the movement. Theory: {doc}`../theory/smoothness`.

**How is the posture shaped?** {py:class}`~pyeyesweb.low_level.BoundingBoxFilledArea`,
{py:class}`~pyeyesweb.low_level.EllipsoidSphericity` and {py:class}`~pyeyesweb.low_level.PointsDensity` measure
contraction and expansion; {py:class}`~pyeyesweb.low_level.Symmetry` and {py:class}`~pyeyesweb.low_level.TriangleSymmetry`
the left/right symmetry; {py:class}`~pyeyesweb.low_level.Equilibrium` the balance of the barycentre between the feet.
Theory: {doc}`../theory/shape_symmetry_balance`.

**What shape is an outline?** {py:class}`~pyeyesweb.low_level.FilterContour`, {py:class}`~pyeyesweb.low_level.ContourCurvature`,
{py:class}`~pyeyesweb.low_level.ConvexHull` and {py:class}`~pyeyesweb.low_level.BodyPartsFromCurvature` work on the closed
contour of a silhouette, one frame at a time. Theory: {doc}`../theory/imaging`.

## Frame features and window features

A **frame feature** gives a value for each call (for example `KineticEnergy`, `Symmetry`, the contour features). A **window
feature** buffers the newest `window` samples itself and gives its first value when the window is full, with the status
`WARMING_UP` before (the smoothness metrics, `DirectionChange`, `CurvatureVelocityCorrelation`). `window` is a number of samples
and `hop` the stride between two values (see {doc}`../concepts/results`). Whatever the length of the window, the quantity
measured is that of a movement fragment; for longer spans use layer 3.

## A typical pipeline

A point makes a smooth reach, its speed is measured, and a smoothness metric summarises the speed. The reach is the
minimum-jerk profile $x = 0.4\,(10 s^3 - 15 s^4 + 6 s^5)$, with $s$ the fraction of the movement time elapsed.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.low_level import Kinematics, SpectralArcLength
>>> rate = 50.0
>>> time = np.arange(0.0, 4.0, 1.0 / rate)
>>> s = np.clip((time - 1.0) / 2.0, 0.0, 1.0)
>>> x = 0.4 * (10 * s**3 - 15 * s**4 + 6 * s**5)                  # a 0.4 m reach between 1 s and 3 s
>>> position = np.column_stack([x, np.zeros_like(x), np.zeros_like(x)])
>>> speed = Kinematics(dims=3, sampling_rate=rate).run(position).velocity
>>> round(float(speed.max()), 2)
0.37
>>> arc = SpectralArcLength(window=100, sampling_rate=rate).run(speed)
>>> arc
Recorder(SpectralArcLength, rows=200, columns=['spectral_arc_length'], status={'OK': 101, 'WARMING_UP': 99})
>>> round(float(arc.spectral_arc_length[-1]), 2)
-1.63
```

Each step is a feature and the output of one is the input of the next. For a complete skeleton, `KineticEnergy` replaces
`Kinematics` and gives a single intensity for the whole body, which is what the segmentation of {doc}`mid_level` takes.
Compute the speed once and give the same array to as many metrics as you need.

## What to know before choosing

- Give `sampling_rate` (or timestamps) to every feature that has a time in it; otherwise the values are per sample and the
  `reason` of the result says so ({doc}`../concepts/time_units_parameters`).
- A feature with `skeleton=` or `labels=` and `joint_map=` reads a labelled skeleton; the presets and the mapping are in
  {doc}`../howto/map_skeleton`.
- To run a whole recording through a feature, use `run`; it gives the same numbers as a loop of `process`.

Hands-on: see {ref}`sphx_glr_tutorials_03_low_level_plot_05_motion.py` (motion) and {ref}`sphx_glr_tutorials_03_low_level_plot_06_shape.py` (shape).
