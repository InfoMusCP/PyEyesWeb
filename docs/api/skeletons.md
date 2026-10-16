# Skeletons

Reference for the objects below (generated from the docstrings).

```{eval-rst}
.. py:module:: pyeyesweb.skeletons

.. currentmodule:: pyeyesweb.skeletons

.. autosummary::
   :toctree: generated/
   :nosignatures:

   get_skeleton
   with_skeleton
```

## Presets

The data objects of the module (a constant has no docstring of its own, so they are listed here; each is a
{py:class}`~pyeyesweb.data_models.Skeleton`, or a dict of them).

| Object | What it is |
|---|---|
| `KINECT_V2` | Kinect v2 (SDK 2.0 joint names), 25 joints, with left/right pairs, reference joint `SpineShoulder` and the kinetic-energy weights of the EyesWeb table. |
| `QUALISYS_SPORT` | Qualisys "sport" marker set, 41 markers named as in the TSV files, with pairs; the reference joint and the weights are not filled yet. |
| `MEDIAPIPE` | MediaPipe Pose, 33 landmarks in the order of the model, with pairs; the reference joint and the weights are not filled yet. |
| `OPENPOSE` | OpenPose BODY_25, with pairs and reference joint `Neck`; the weights are not filled yet. |
| `SKELETONS` | Dict `name -> Skeleton` of the four presets above; what `get_skeleton` looks up. |
| `SKELETON_TODO` | Dict `name -> tuple of str` of what is still to fill in each preset (`Skeleton.missing()`). |
