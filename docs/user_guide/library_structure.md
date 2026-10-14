# Library structure

PyEyesWeb is organised by the layers of the conceptual model (`site/assets/conceptual_model.png`), not by the
where the code came from.

| Package | Layer | Timescale | Content |
|---|---|---|---|
| `pyeyesweb.physical_signals` | 1 | frame, continuous | skeletons, trajectories, contours, space |
| `pyeyesweb.low_level` | 2 | up to ~0.5 s | kinematics, energy, shape, symmetry, smoothness |
| `pyeyesweb.mid_level` | 3 | 0.5-3 s | segments, suddenness, impulsivity, lightness, directness, space occupation |
| `pyeyesweb.high_level` | 4 | 3 s and above | reserved |
| `pyeyesweb.analysis_primitives` | all | any | metrics applicable to any movement feature at any layer: statistics, complexity, rarity, periodicity, clustering, signal events, synchronization |

The layers are a conceptual model, not a strict pipeline: one feature can appear at different layers depending on the
timescale it is computed over. The placement of the features that could sit in more than one layer is listed in
`STRUCTURE_REVIEW.md` for discussion.

## Names

Features are computed in C++ and wrapped; all of them follow the same call contract (see
[Input contract](input_contract.md) and [Output contracts](output_contracts.md)). Names are simple (`KineticEnergy`,
`Smoothness`, `Rarity`). Where two features share a concept but compute different things, the name says what is
computed: `Smoothness` (EyesWeb: curvature against velocity) and `SpeedSmoothness` (SPARC, LDLJ, harmonicity,
sub-movements of a speed profile); `Impulsivity` (contraction-index range over a gesture) and `SuddennessImpulsivity`
(direction change x suddenness); `Rarity` and `HistogramRarity` (to be merged).

`KineticEnergy` has an `input_mode` (positions, or velocities obtained with `Kinematics`) and `EllipsoidSphericity`
accepts a point cloud (`process_points`). Every feature class is defined in its layer module (`KineticEnergy` in
`pyeyesweb.low_level.energy`, `RecurrencePlot` in `pyeyesweb.analysis_primitives.synchronization.recurrence`) and
re-exported by its layer package, so `from pyeyesweb.low_level import KineticEnergy` works. The layer packages need the
compiled core: importing one without it raises an `ImportError` saying so, while `import pyeyesweb` and
`pyeyesweb.data_models` do not need it. `pyeyesweb.SeriesBuffer` comes from the core.

## Discovery

Every feature class carries `LAYER`, `TIMESCALE` and `EYESWEB_BLOCK` (the EyesWeb block it comes from, if any).

```python
import pyeyesweb
from pyeyesweb import Layer

for info in pyeyesweb.catalog(Layer.LOW_LEVEL):
    print(info.name, info.timescale.value, info.eyesweb_block)

print(pyeyesweb.catalog_table(Layer.MID_LEVEL))   # Markdown
```

The "Implemented in the library" tables of the layer pages are generated from this metadata by
`python tools/update_catalog_docs.py`.
