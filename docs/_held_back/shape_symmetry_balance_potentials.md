<!-- Sections cut from docs/theory/shape_symmetry_balance.md for the early release (2026-11-13). -->

The hit cells feed {py:class}`~pyeyesweb.mid_level.PositionDependingPotentials`, which keeps one potential value per cell
and updates it at every call. With `potential_type="increment_decrement"` a hit cell gains `increment` and every other cell
loses `decrement`; with `"occupation_rates"` the value of a cell is the fraction of calls in which it was hit (optionally
over the last `window` calls); the `"polynomial"`, `"gaussian"` and `"logarithmic"` types have no memory and draw a field
centred on each hit cell. {py:class}`~pyeyesweb.mid_level.RegionDependingPotentials` does the same for regions, groups of
cells defined by a mask (for example the zones of a stage), with linear or exponential occupation rates. Both keep state:
`reset()` restores the initial potential. An empty list of hits has status `NO_OUTPUT` and does not update the potential.

```{doctest}
>>> from pyeyesweb.physical_signals import HitCellDetector
>>> from pyeyesweb.mid_level.space_occupation import PositionDependingPotentials
>>> detector = HitCellDetector(cells_along_x=4, cells_along_y=2)
>>> potentials = PositionDependingPotentials(cells_along_x=4, cells_along_y=2, potential_type="occupation_rates")
>>> path = [[0.1, 0.1], [0.1, 0.1], [0.4, 0.2], [0.9, 0.7]]       # a dancer who mostly stays on the left
>>> for point in path:
...     cells = detector.process([point]).cells
...     result = potentials.process(cells)
>>> result.potential
array([[50., 25.,  0.,  0.],
       [ 0.,  0.,  0., 25.]])
```

