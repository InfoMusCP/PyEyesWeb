<!-- Sections cut from docs/concepts/time_units_parameters.md for the early release (2026-11-13). -->

### The humanoid model

The humanoid of `MassSpringSimulator` works internally in millimetres, because the body model of EyesWeb and its spring forces are defined in
that unit. It still follows the same rule: `units` declares the unit of your frames, of `gravity` and `floor_position`, and of
the output, and the wrapper converts at the boundary. A body run in metres and the same body run in millimetres give the same
motion, to rounding:

```{doctest}
>>> from pyeyesweb.physical_signals.humanoid import MassSpringSimulator
>>> pose = MassSpringSimulator(sampling_rate=25.0).process({"head": (0.0, 1.7, 0.0)}).joints      # metres
>>> in_metres = MassSpringSimulator(sampling_rate=25.0)
>>> in_millimetres = MassSpringSimulator(sampling_rate=25.0, units="mm")
>>> for step in range(5):
...     a = in_metres.process(pose + 0.001 * step).joints
...     b = in_millimetres.process(pose * 1000 + 1.0 * step).joints
>>> bool(np.allclose(a * 1000, b))
True
>>> in_millimetres.outputs
Schema(Output('joints', shape=(21, 3), unit='mm'), Output('directions', shape=(20, 3)))
```

A model of your own is different: it runs in its own unit, and `units` only names it, so `"m"` and `"mm"` give the same
numbers.

