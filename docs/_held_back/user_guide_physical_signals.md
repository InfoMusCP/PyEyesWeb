<!-- Sections cut from docs/user_guide/physical_signals.md for the early release (2026-11-13). -->

**You have a skeleton and want a cleaner one.** The captured joints jitter and drop out; a mass-spring model
follows them and gives a smooth, articulated pose with constant bone lengths.

- {py:class}`~pyeyesweb.physical_signals.MassSpringSimulator`. With `model="humanoid"` (the default) it runs the fixed
  21-joint humanoid (the joints of the first Kinect SDK as EyesWeb names them), the choice for a body captured by any system
  whose joints you can map to those names (see {doc}`../howto/map_skeleton`). With `model=` a `MassSpringModel` it runs a
  structure that is not a human body (a limb, a puppet, an instrument). Its `directions` output is the posture itself, the
  direction of each bone, which does not depend on where the body is.

Theory, assumptions and the units exception: {doc}`../theory/humanoid_models`.

A skeleton passes through the simulator and then to the features of layer 2. The simulator is driven by three captured frames,
with a joint missing in the second one (a dropout); it gives the 21 joints at every call, and the simulated joints, labelled like
the model, feed any feature that takes a labelled skeleton.

```{doctest}
>>> import numpy as np
>>> from pyeyesweb.physical_signals.humanoid import HUMANOID_JOINTS, MassSpringSimulator
>>> from pyeyesweb.low_level import KineticEnergy
>>> simulator = MassSpringSimulator(sampling_rate=25.0)
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

