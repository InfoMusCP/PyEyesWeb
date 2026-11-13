<!-- Sections cut from docs/howto/map_skeleton.md for the early release (2026-11-13). -->

## Mapping to a body model: `joint_map`

`MassSpringSimulator`, in the physical-signals layer, does not take a skeleton. It follows a captured body with a model that
has its own joint names (`pyeyesweb.physical_signals.HUMANOID_JOINTS`, 21 names, for the humanoid), and the parameter
`joint_map` says which label of your data feeds each model joint, as `model joint -> your label`. A joint you leave out keeps
the model's name. It is the only class that takes `joint_map`.

```{doctest}
>>> from pyeyesweb.physical_signals.humanoid import HUMANOID_JOINTS, MassSpringSimulator
>>> HUMANOID_JOINTS[:4]
('head', 'left_ankle', 'left_elbow', 'left_foot')
>>> simulator = MassSpringSimulator(joint_map={"head": "Head", "neck": "Neck"}, sampling_rate=25.0)
>>> simulator.process({"Head": (0.0, 1.7, 0.0), "Neck": (0.0, 1.5, 0.0)}).joints.shape
(21, 3)
```

The simulator follows a body model and expects frames in the unit given by `units`; see
{doc}`../theory/humanoid_models` for what the model does and {doc}`../concepts/time_units_parameters` for the unit rule.

