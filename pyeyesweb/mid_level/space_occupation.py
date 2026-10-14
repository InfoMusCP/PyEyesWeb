"""Occupation of space over time: potentials of cells and regions (EyesWeb SpaceAnalysis).

`PositionDependingPotentials` and `RegionDependingPotentials` keep a potential over the grid of
`pyeyesweb.physical_signals.space` driven by the hit cells (per cell, or per region of a mask). A cell is `(i, j)` =
(row, column). Statuses: `OK` when the call produced output, `NO_OUTPUT` for an empty input list (EyesWeb outputs
nothing), `INVALID_INPUT` when EyesWeb rejects the call (a cell outside the grid, a region index out of range;
`result.reason` says why). Every `process(hits, *, timestamp=None)` takes the hits of one call and the timestamp in seconds
(`NaN` when not given).
"""

from typing import Any, Dict, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature, FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.base.inputs import points_input
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_space = core.space

# C++ defaults the schemas depend on.
_DEFAULT_CELLS = 10
_DEFAULT_REGIONS = 10


def _no_input(block: CoreFeature, timestamp: float) -> Result:
    return block.no_output(Status.NO_OUTPUT, "empty input list", timestamp)


_CELLS = points_input("cells", None, "hit cells (i, j) = (row, column)", dims=2)


@describe(Layer.MID_LEVEL, eyesweb="PositionDependingPotentials")
class PositionDependingPotentials(FrameFeature):
    """EyesWeb PositionDependingPotentials. `process(cells, *, timestamp=None)`, `cells` an `(N, 2)` array of integer `(i, j)`
    (`run` takes `(T, N, 2)`).

    Output `potential`: `(cells_along_y, cells_along_x)` matrix. `potential_type` selects increment/decrement,
    polynomial, occupation rates, Gaussian or logarithmic potentials (`PositionPotentialType`). `NO_OUTPUT` for an
    empty list, `INVALID_INPUT` for a rejected cell. `reset()` is both EyesWeb's Init() and its Reset trigger.
    """
    _core_class = _space.PositionDependingPotentials
    INPUTS = Inputs(_CELLS)

    def _schema(self) -> Schema:
        shape = (int(self._param("cells_along_y", _DEFAULT_CELLS)), int(self._param("cells_along_x", _DEFAULT_CELLS)))
        return Schema(Output("potential", shape, doc="potential of each cell (rows from y, columns from x)"))

    def _process(self, cells: Any, timestamp: Optional[float]) -> Result:
        try:
            raw = self._block.process(cells)
        except ValueError as exc:
            return self.no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        potential, error = raw
        if potential is None:
            return self.no_output(Status.INVALID_INPUT, error, timestamp) if error else _no_input(self, timestamp)
        return self.result(timestamp=timestamp, potential=potential)


@describe(Layer.MID_LEVEL, eyesweb="RegionDependingPotentials")
class RegionDependingPotentials(FrameFeature):
    """EyesWeb RegionDependingPotentials. `process(hits, *, timestamp=None)`.

    `hits`: an `(N, 2)` array of `(i, j)` cells (`input_kind=RegionInputKind.CELLS`, default; input `cells`) or `N`
    region indexes (`HIT_REGIONS`; input `regions`, a sample of `N` channels). `run` takes one such array per sample. `mask` gives the region of each cell (default all 0), `num_of_regions` the number of regions.
    Outputs, each declared only when its `output_*` parameter is on: `potential` `(cells_along_y, cells_along_x)`,
    `hit_regions` `(num_of_regions,)` int 0/1, `hit_region_indexes` `(n,)` int (one per input item), `region_values`
    `(num_of_regions,)`. `NO_OUTPUT` for an empty list; `INVALID_INPUT` when the compute is rejected (with region
    input, `hit_regions` / `hit_region_indexes` are still produced, as in EyesWeb, see `result.valid`).
    `reset()` is Init(); `trigger_reset()` is EyesWeb's Reset trigger: both restore the initial region values and clear
    the occupation counters.
    """
    _core_class = _space.RegionDependingPotentials

    _OUTPUT_FLAGS = (("potential", "output_potential_matrix", True), ("hit_regions", "output_hit_regions", False),
                     ("hit_region_indexes", "output_hit_region_indexes", False),
                     ("region_values", "output_region_values", False))

    def _schema(self) -> Schema:
        rows = int(self._param("cells_along_y", _DEFAULT_CELLS))
        cols = int(self._param("cells_along_x", _DEFAULT_CELLS))
        regions = int(self._param("num_of_regions", _DEFAULT_REGIONS))
        every = {
            "potential": Output("potential", (rows, cols), doc="value of the region of each cell"),
            "hit_regions": Output("hit_regions", regions, kind=int, doc="1 for each region hit by this call"),
            "hit_region_indexes": Output("hit_region_indexes", (None,), kind=int,
                                         doc="region of each input item, in input order"),
            "region_values": Output("region_values", regions, doc="value of each region"),
        }
        return Schema(*(every[name] for name, flag, default in self._OUTPUT_FLAGS if self._param(flag, default)))

    def _inputs(self) -> Inputs:
        if self._param("input_kind", _space.RegionInputKind.CELLS) == _space.RegionInputKind.CELLS:
            return Inputs(_CELLS)
        return Inputs(Input("regions", InputKind.SAMPLE, (None,), doc="indexes of the regions that were hit"))

    def _process(self, hits: Any, timestamp: Optional[float]) -> Result:
        try:
            raw = self._block.process(hits)
        except ValueError as exc:
            return self.no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: Dict[str, Any], timestamp: Optional[float]) -> Result:
        values = {name: raw[name] for name in self.outputs.names}
        if all(value is None for value in values.values()) and not raw["error"]:
            return _no_input(self, timestamp)
        if raw["error"]:
            return self.result(status=Status.INVALID_INPUT, reason=raw["error"], timestamp=timestamp, **values)
        return self.result(timestamp=timestamp, **values)

    def trigger_reset(self) -> None:
        """EyesWeb's Reset trigger parameter (differs from `reset()`, see the class docs)."""
        self._block.trigger_reset()


__all__ = ["PositionDependingPotentials", "RegionDependingPotentials"]
