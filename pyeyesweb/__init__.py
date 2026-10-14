"""PyEyesWeb: movement analysis organised by the layers of the conceptual model.

    pyeyesweb.physical_signals     Layer 1: physical signals and virtual sensors
    pyeyesweb.low_level            Layer 2: low-level features
    pyeyesweb.mid_level            Layer 3: mid-level features
    pyeyesweb.high_level           Layer 4: qualities communication (social and interaction-level features)
    pyeyesweb.analysis_primitives  metrics applicable at any layer

`pyeyesweb.catalog()` lists every feature with its layer, timescale and origin. The layers need the compiled
EyesWeb core; `import pyeyesweb` itself, the data models (`pyeyesweb.data_models`) and the catalog types do not.
`SeriesBuffer` of the core is available here once it is installed (it is not in `__all__`: it needs the core).
`pyeyesweb.physical_signals` also holds `MassSpringModel` and `TimeWindowSynchronizer`; `pyeyesweb.skeletons` the lab
skeleton presets.
"""

from .catalog import Layer, Timescale, catalog, catalog_table

__all__ = ["Layer", "Timescale", "catalog", "catalog_table"]


_PUBLIC_MODULES = ("physical_signals", "low_level", "mid_level", "high_level", "analysis_primitives", "data_models", "skeletons")


def __dir__():
    return sorted([*__all__, "SeriesBuffer", *_PUBLIC_MODULES])


def __getattr__(name: str):
    if name == "SeriesBuffer":
        from ._core import core
        return getattr(core, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
