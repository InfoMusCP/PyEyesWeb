<!-- Sections cut from docs/concepts/inputs.md for the early release (2026-11-13). -->

## Mapping your joint names to a model: `joint_map`

`MassSpringSimulator`, in the physical-signals layer, follows a captured skeleton with a body model. The model has its own
joint names (`pyeyesweb.physical_signals.HUMANOID_JOINTS` for the humanoid, the mass names for a model of your own), and
`joint_map` says which label of your data feeds each model joint, as `model joint -> your label`. The names you leave out keep
their own. It is the only class that takes `joint_map`.

```{doctest}
>>> from pyeyesweb.physical_signals.humanoid import MassSpringSimulator
>>> simulator = MassSpringSimulator(joint_map={"head": "Head", "neck": "Neck"}, sampling_rate=25.0)
>>> simulator.process({"Head": (0.0, 1.7, 0.0), "Neck": (0.0, 1.5, 0.0)}).joints.shape
(21, 3)
```

