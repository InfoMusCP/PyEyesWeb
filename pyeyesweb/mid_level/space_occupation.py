"""Occupation of space over time: potentials of cells and of regions of a grid.

``PositionDependingPotentials`` and ``RegionDependingPotentials`` keep a potential over the grid of
``pyeyesweb.physical_signals.space``, driven by the cells that are hit (one value per cell, or one per region of a
mask). A cell is ``(i, j)`` = (row, column). Every ``process`` takes the hits of one call and an optional timestamp in
seconds.
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
    return block._no_output(Status.NO_OUTPUT, "empty input list", timestamp)


_CELLS = points_input("cells", None, "hit cells (i, j) = (row, column)", dims=2)


@describe(Layer.MID_LEVEL, eyesweb="PositionDependingPotentials")
class PositionDependingPotentials(FrameFeature):
    r"""Potential over a grid of cells driven by the cells that are hit, with memory of past hits.

    Keeps a potential value for each cell of a rectangular grid and updates it with the cells that are hit at every
    call, for instance the cells of the floor that a dancer occupies (``HitCellDetector``). It measures how space is
    used over time: a cell that is often occupied builds up potential, an unvisited one loses it, or a field centred on
    the occupied cells is drawn, depending on ``potential_type``. A cell is ``(i, j)`` = (row, column), and the
    potential matrix has shape ``(cells_along_y, cells_along_x)``. With :math:`h` the hit cells of a call and
    :math:`V_c` the potential of a cell :math:`c`:

    * ``"increment_decrement"``: for a single hit cell, :math:`V_c \leftarrow V_c + \text{increment}` for it and
      :math:`V_c \leftarrow V_c - \text{decrement}` for every other cell. For several cells every cell loses
      ``decrement`` and every hit cell gains ``decrement + increment``. The potential is not bounded.
    * ``"occupation_rates"``: :math:`V_c` is the fraction of the calls since the last reset in which :math:`c` was hit
      (in percent with ``in_percentage``); with ``on_window`` only the last ``window`` calls count.
    * ``"polynomial"``, ``"gaussian"``, ``"logarithmic"``: no memory; the matrix is recomputed at each call as the sum,
      over the hit cells, of a field centred on the cell, as follows (:math:`\Delta i, \Delta j` are the offsets from
      the hit cell and :math:`d` the distance to it, in cells).
    * Polynomial field: 1 at the hit cell and :math:`(\lvert \Delta i \rvert^p + \lvert \Delta j \rvert^p)^{-q/p}`
      elsewhere, with :math:`p` the ``norm_exponent`` and :math:`q` the ``decay_exponent``.
    * Gaussian field: :math:`A \exp\!\left(-\frac{u^2 - 2 \rho u v + v^2}{2 (1 - \rho^2)}\right)`, with :math:`u =
      \Delta i / \sigma_x` and :math:`v = \Delta j / \sigma_y` (``gaussian_sigma_x`` applies along the rows and
      ``gaussian_sigma_y`` along the columns), :math:`\rho` the ``gaussian_correlation`` and :math:`A = 1 / (2 \pi
      \sigma_x \sigma_y \sqrt{1 - \rho^2})`, unless a custom amplitude is set.
    * Logarithmic field: :math:`\frac{a}{\ln(s D + 1)} \ln \max\!\big(1,\, s (D + 1/s - d)\big)`, with :math:`a` the
      ``amplitude``, :math:`s` the ``log_scale`` and :math:`D` the distance from the hit cell to the farthest corner of
      the grid (or ``custom_distance``).

    Input: the hit cells of one call, an ``(N, 2)`` array of integer ``(i, j)``; ``process(frame, *, timestamp=None)``;
    ``run`` takes one such array per sample. ``reset()`` restores the initial potential.

    Parameters
    ----------
    cells_along_x : int, optional
        Number of columns of the grid. Defaults to ``10``. *(structural)*
    cells_along_y : int, optional
        Number of rows of the grid. Defaults to ``10``. *(structural)*
    potential_type : {"increment_decrement", "polynomial", "occupation_rates", "gaussian", "logarithmic"}, optional
        The rule that updates the potential. Defaults to ``"increment_decrement"``. *(structural)*
    initialization_matrix : numpy.ndarray, optional
        Initial potential, shape ``(cells_along_y, cells_along_x)``; ``None`` (default) starts from 0. *(structural)*
    increment_factor : float, optional
        Gain of a hit cell (``"increment_decrement"``). Defaults to ``1.0``. *(live)*
    decrement_factor : float, optional
        Loss of the other cells (``"increment_decrement"``). Defaults to ``1.0``. *(live)*
    norm_exponent : float, optional
        Exponent :math:`p` of the norm (``"polynomial"``). Defaults to ``2.0``. *(live)*
    decay_exponent : float, optional
        Exponent :math:`q` of the decay with distance (``"polynomial"``). Defaults to ``1.0``. *(live)*
    in_percentage : bool, optional
        Express the occupation rates in percent instead of as fractions (``"occupation_rates"``). Defaults to ``True``.
        *(live)*
    on_window : bool, optional
        Count only the last ``window`` calls (``"occupation_rates"``). Defaults to ``False``. *(structural for
        ``"occupation_rates"``)*
    window : int, optional
        Number of calls of the window of ``on_window``, at least 1; not a window of samples of a windowed feature.
        Defaults to ``250``. *(structural for ``"occupation_rates"``)*
    gaussian_sigma_x : float, optional
        Standard deviation of the Gaussian along the rows, in cells, positive (``"gaussian"``). Defaults to ``1.0``.
        *(live)*
    gaussian_sigma_y : float, optional
        Standard deviation of the Gaussian along the columns, in cells, positive (``"gaussian"``). Defaults to ``1.0``.
        *(live)*
    gaussian_correlation : float, optional
        Correlation :math:`\rho` between the two directions, in [-1, 1] (``"gaussian"``). Defaults to ``0.0``. *(live)*
    use_custom_amplitude : bool, optional
        Use ``custom_amplitude`` instead of the normalising amplitude of the Gaussian. Defaults to ``False``. *(live)*
    custom_amplitude : float, optional
        Amplitude of the Gaussian, not negative, when ``use_custom_amplitude`` is set. Defaults to ``1.0``. *(live)*
    amplitude : float, optional
        Amplitude :math:`a` of the logarithmic field, not negative (``"logarithmic"``). Defaults to ``1.0``. *(live)*
    log_scale : float, optional
        Scale :math:`s` of the logarithm, positive (``"logarithmic"``). Defaults to ``1.0``. *(live)*
    use_custom_distance : bool, optional
        Use ``custom_distance`` instead of the distance to the farthest corner (``"logarithmic"``). Defaults to
        ``False``. *(live)*
    custom_distance : float, optional
        Distance :math:`D`, in cells, positive, when ``use_custom_distance`` is set. Defaults to ``100.0``. *(live)*

    Notes
    -----
    **Outputs.** ``potential``: ``(cells_along_y, cells_along_x)`` matrix, dimensionless (a fraction or a percentage for
    the occupation rates).

    **Statuses.** ``NO_OUTPUT`` for an empty list of cells (the potential is not updated); ``INVALID_INPUT`` for a cell
    outside the grid (``result.reason`` says so).

    Corrected in the core: with several cells a cell outside the grid is rejected (it used to be accepted with a wrapped
    index), and the custom distance of the logarithmic potential is honoured with several cells.

    Examples
    --------
    >>> from pyeyesweb.mid_level import PositionDependingPotentials
    >>> potentials = PositionDependingPotentials(cells_along_x=3, cells_along_y=2)
    >>> _ = potentials.process([[0, 1]])
    >>> print(potentials.process([[0, 1]]).potential)
    [[-2.  2. -2.]
     [-2. -2. -2.]]
    """
    _core_class = _space.PositionDependingPotentials
    _core_names = {"window": "window_size", "gaussian_sigma_x": "std_dev_x", "gaussian_sigma_y": "std_dev_y",
                   "gaussian_correlation": "rho", "use_custom_amplitude": "use_cust_ampl",
                   "custom_amplitude": "cust_ampl", "use_custom_distance": "use_cust_dist", "custom_distance": "cust_dist"}
    _INPUTS = Inputs(_CELLS)

    def _schema(self) -> Schema:
        shape = (int(self._param("cells_along_y", _DEFAULT_CELLS)), int(self._param("cells_along_x", _DEFAULT_CELLS)))
        return Schema(Output("potential", shape, doc="potential of each cell (rows from y, columns from x)"))

    def _process(self, cells: Any, timestamp: Optional[float]) -> Result:
        try:
            raw = self._block.process(cells)
        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        potential, error = raw
        if potential is None:
            return self._no_output(Status.INVALID_INPUT, error, timestamp) if error else _no_input(self, timestamp)
        return self._result(timestamp=timestamp, potential=potential)


@describe(Layer.MID_LEVEL, eyesweb="RegionDependingPotentials")
class RegionDependingPotentials(FrameFeature):
    r"""One potential per region of a cell mask, driven by hit cells or hit regions.

    Groups the cells of a grid into regions with a mask and keeps one value per region, driven by the cells (or the
    regions) that are hit at every call, for instance the zones of a stage that a performer visits. A cell is ``(i, j)``
    = (row, column), and ``mask`` gives the region of each cell. With :math:`V_r` the value of a region :math:`r`:

    * ``"increment_decrement"``: :math:`V_r \leftarrow V_r + \text{increment}` for a region that is hit and :math:`V_r
      \leftarrow V_r - \text{decrement}` for every other region.
    * ``"occupation_rates_linear"``: :math:`V_r` is the fraction of the calls since the last reset in which the region
      was hit (in percent with ``in_percentage``).
    * ``"occupation_rates_exponential"``: :math:`V_r` rises towards ``max_value`` while the region is hit and decays
      towards 0 while it is not, with time constant :math:`\tau` (``time_constant``, in calls). With :math:`n` the
      number of consecutive calls in the current state (0 on the first one), :math:`V_r = (V_{max} - V_{miss}) (1 -
      e^{-n/\tau}) + V_{miss}` when hit and :math:`V_r = V_{hit} \, e^{-n/\tau}` when missed, where :math:`V_{miss}` and
      :math:`V_{hit}` are the last value reached in the other state.

    Input: ``process(frame, *, timestamp=None)``, ``frame`` an ``(N, 2)`` array of integer ``(i, j)`` cells
    (``input_kind="cells"``, the default; input ``cells``) or ``N`` region indices (``input_kind="hit_regions"``; input
    ``regions``); ``run`` takes one such array per sample. ``reset()`` restores the initial values and clears the
    occupation counters, and so does ``trigger_reset()``, the EyesWeb Reset trigger.

    Parameters
    ----------
    cells_along_x : int, optional
        Number of columns of the grid. Defaults to ``10``. *(structural)*
    cells_along_y : int, optional
        Number of rows of the grid. Defaults to ``10``. *(structural)*
    potential_type : {"increment_decrement", "occupation_rates_linear", "occupation_rates_exponential"}, optional
        The rule that updates the values of the regions. Defaults to ``"increment_decrement"``. *(structural)*
    input_kind : {"cells", "hit_regions"}, optional
        Whether the hits are cells or region indices. Defaults to ``"cells"``. *(structural)*
    mask : numpy.ndarray, optional
        Region index of each cell, shape ``(cells_along_y, cells_along_x)``, with values from 0 to ``number_of_regions -
        1``; ``None`` (default) puts every cell in region 0. A hit on a cell with another value is invalid. *(live)*
    number_of_regions : int, optional
        Number of regions. Defaults to ``10``. *(structural)*
    initialization_matrix : numpy.ndarray, optional
        Initial values given per cell, shape ``(cells_along_y, cells_along_x)``, mapped to the regions through the mask;
        exclusive with ``region_initial_values``. *(structural)*
    region_initial_values : sequence of float, optional
        Initial value of each region, ``number_of_regions`` values; exclusive with ``initialization_matrix``. ``None``
        (default) starts from 0. *(structural)*
    increment_factor : float, optional
        Gain of a hit region (``"increment_decrement"``). Defaults to ``1.0``. *(live)*
    decrement_factor : float, optional
        Loss of the other regions (``"increment_decrement"``). Defaults to ``1.0``. *(live)*
    in_percentage : bool, optional
        Express the occupation rates in percent instead of as fractions (``"occupation_rates_linear"``). Defaults to
        ``True``. *(live)*
    max_value : float, optional
        Level towards which a hit region rises (``"occupation_rates_exponential"``). Defaults to ``1.0``. *(live)*
    time_constant : float, optional
        Time constant :math:`\tau` of the rise and of the decay, in calls (``"occupation_rates_exponential"``); 0 is
        taken as 1. Defaults to ``1.0``. *(live)*
    parts : sequence of {"potential", "hit_regions", "hit_region_indexes", "region_values"}, optional
        The outputs to produce, by name; at least one. Read back as a tuple in the declaration order of the outputs.
        Defaults to ``("potential",)``. *(live)*

    Notes
    -----
    **Outputs**, each produced only when it is in ``parts``: ``potential``, ``(cells_along_y, cells_along_x)``, the
    value of the region of each cell; ``hit_regions``, ``(number_of_regions,)`` integers, 1 for each region hit by the
    call; ``hit_region_indexes``, ``(N,)`` integers, the region of each input item in input order; ``region_values``,
    ``(number_of_regions,)``, the value of each region. Values are dimensionless.

    **Statuses.** ``NO_OUTPUT`` for an empty list of hits; ``INVALID_INPUT`` for a cell outside the grid or a region
    index out of range (``result.reason`` says so; with region input, ``hit_regions`` and ``hit_region_indexes`` are
    still produced).

    Corrected in the core: the Reset trigger restores the initial values of the regions and clears the occupation
    counters (it used to pass other values and keep the counters); increment/decrement with several cells is computed as
    intended; mask values outside the range of the regions are invalid instead of reading outside the mask.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import RegionDependingPotentials
    >>> mask = np.array([[0, 0, 1], [0, 0, 1]])
    >>> potentials = RegionDependingPotentials(cells_along_x=3, cells_along_y=2, mask=mask, number_of_regions=2,
    ...                                        parts=("region_values",))
    >>> print(potentials.process([[0, 0], [1, 1]]).region_values)
    [ 1. -1.]
    """
    _core_class = _space.RegionDependingPotentials
    _core_names = {"number_of_regions": "num_of_regions", "region_initial_values": "reg_init_values"}

    _parts = {"potential": "output_potential_matrix", "hit_regions": "output_hit_regions",
              "hit_region_indexes": "output_hit_region_indexes", "region_values": "output_region_values"}

    def _schema(self) -> Schema:
        rows = int(self._param("cells_along_y", _DEFAULT_CELLS))
        cols = int(self._param("cells_along_x", _DEFAULT_CELLS))
        regions = int(self._param("number_of_regions", _DEFAULT_REGIONS))
        every = {
            "potential": Output("potential", (rows, cols), doc="value of the region of each cell"),
            "hit_regions": Output("hit_regions", regions, kind=int, doc="1 for each region hit by this call"),
            "hit_region_indexes": Output("hit_region_indexes", (None,), kind=int,
                                         doc="region of each input item, in input order"),
            "region_values": Output("region_values", regions, doc="value of each region"),
        }
        return Schema(*(every[name] for name in self._params["parts"]))

    def _inputs(self) -> Inputs:
        if self._param("input_kind", _space.RegionInputKind.CELLS) == _space.RegionInputKind.CELLS:
            return Inputs(_CELLS)
        return Inputs(Input("regions", InputKind.SAMPLE, (None,), doc="indexes of the regions that were hit"))

    def _process(self, hits: Any, timestamp: Optional[float]) -> Result:
        try:
            raw = self._block.process(hits)
        except ValueError as exc:
            return self._no_output(Status.INVALID_INPUT, str(exc), timestamp)
        return self._to_result(raw, timestamp)

    def _to_result(self, raw: Dict[str, Any], timestamp: Optional[float]) -> Result:
        values = {name: raw[name] for name in self.outputs.names}
        if all(value is None for value in values.values()) and not raw["error"]:
            return _no_input(self, timestamp)
        if raw["error"]:
            return self._result(status=Status.INVALID_INPUT, reason=raw["error"], timestamp=timestamp, **values)
        return self._result(timestamp=timestamp, **values)

    def trigger_reset(self) -> None:
        """The EyesWeb Reset trigger: restores the initial values and clears the occupation counters (as ``reset()``)."""
        self._block.trigger_reset()


__all__ = ["PositionDependingPotentials", "RegionDependingPotentials"]
