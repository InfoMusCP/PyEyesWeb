"""Output contract of the space features (EyesWeb SpaceAnalysis blocks): HitCellDetector and the potentials.

Schemas known before data, fixed shapes from the grid and region parameters, statuses of the no-output paths,
parameter-dependent schemas and a Recorder over a few steps. The numerical behaviour is tested in C++
(tests/space). Skipped without the compiled core (pyeyesweb._eyesweb_core, or eyesweb_core in EYESWEB_CORE_PATH).
"""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb._core import core  # noqa: E402
from pyeyesweb.data_models.recorder import Recorder  # noqa: E402
from pyeyesweb.data_models.results import Result, Schema, Status  # noqa: E402
from pyeyesweb.mid_level import PositionDependingPotentials, RegionDependingPotentials  # noqa: E402
from pyeyesweb.physical_signals import HitCellDetector  # noqa: E402

MASK = np.array([[0, 0, 1, 2]])


def assert_contract(block, result):
    assert isinstance(block.outputs, Schema) and isinstance(result, Result)
    assert result.schema is block.outputs
    assert set(result.valid) == set(block.outputs.names)
    for output in block.outputs:
        value = getattr(result, output.name)
        if output.fixed:
            assert np.shape(value) == output.shape
        dtype = {float: np.floating, int: np.integer, bool: np.bool_}[output.kind]
        assert np.issubdtype(np.asarray(value).dtype, dtype)
    assert result.to_array().shape == (block.outputs.size,)


# ------------------------------------------------------------------------------------------ HitCellDetector

def test_hit_cell_detector_contract_and_values():
    detector = HitCellDetector(cells_x=4, cells_y=4, x_max=2.0, y_max=2.0)
    assert detector.outputs.names == ("cells",) and detector.outputs["cells"].shape == (None, 2)
    result = detector.process([(0.1, 1.9), (1.6, 0.6), (5, 5)])
    assert_contract(detector, result)
    assert result.ok and result.cells.tolist() == [[3, 0], [1, 3], [3, 3]]
    assert detector.process(np.array([[1, 1]])).cells.tolist() == [[2, 2]]  # integer points
    empty = detector.process([])
    assert empty.ok and empty.cells.shape == (0, 2)  # EyesWeb outputs an empty list


def test_hit_cell_detector_unclipped_out_of_range_is_invalid_input():
    detector = HitCellDetector(clip_values=False)
    result = detector.process([(0.5, 0.5), (1.5, 0.5)])
    assert result.status is Status.INVALID_INPUT and result.reason and result.valid == {"cells": False}
    assert detector.process([(1.0, 1.0)]).cells.tolist() == [[9, 9]]  # the maximum falls in the last cell


# ------------------------------------------------------------------------------------------ PositionDependingPotentials

def test_position_potentials_schema_from_grid_and_statuses():
    default = PositionDependingPotentials()
    assert default.outputs["potential"].shape == (10, 10)
    assert default.process([(0, 0)]).potential.shape == (10, 10)

    block = PositionDependingPotentials(cells_along_x=3, cells_along_y=2, decrement_factor=0.5)
    assert block.outputs["potential"].shape == (2, 3) and block.outputs.size == 6
    result = block.process([(1, 2)])
    assert_contract(block, result)
    assert result.ok and result.potential[1, 2] == 1.0 and result.potential[0, 0] == -0.5
    assert result.to_array().tolist() == result.potential.ravel().tolist()  # row-major layout

    none = block.process([])
    assert none.status is Status.NO_OUTPUT and np.isnan(none.to_array()).all()
    bad = block.process([(5, 0)])
    assert bad.status is Status.INVALID_INPUT and bad.reason and bad.valid == {"potential": False}
    block.reset()
    assert (block.potential == 0).all()


@pytest.mark.parametrize("ptype", [count.lower() for count in core.space.PositionPotentialType.__members__])
def test_position_potentials_every_type_follows_the_contract(ptype):
    block = PositionDependingPotentials(cells_along_x=4, cells_along_y=3, potential_type=ptype)
    for cells in ([(0, 0)], [(1, 1), (2, 3)]):
        result = block.process(np.array(cells))
        assert_contract(block, result)
        assert result.ok and result.potential.shape == (3, 4)


def test_position_potentials_bounds_and_initialization():
    init = np.arange(4.0).reshape(2, 2)
    block = PositionDependingPotentials(cells_along_x=2, cells_along_y=2, initialization_matrix=init)
    assert block.process([(0, 0)]).potential.tolist() == [[1, 0], [1, 2]]
    with pytest.raises(ValueError):
        PositionDependingPotentials(cells_along_x=3, cells_along_y=2, initialization_matrix=init)
    strict = PositionDependingPotentials(cells_along_x=2, cells_along_y=2)
    assert strict.process([(0, 2), (0, 0)]).status is Status.INVALID_INPUT
    log = dict(cells_along_x=3, cells_along_y=1, potential_type="logarithmic",
               use_cust_dist=True, cust_dist=1.0)
    potential = PositionDependingPotentials(**log).process([(0, 0), (0, 2)]).potential
    assert potential.tolist() == [[1, 0, 1]]


# ------------------------------------------------------------------------------------------ RegionDependingPotentials

def test_region_potentials_default_schema_is_potential_only():
    block = RegionDependingPotentials()
    assert block.outputs.names == ("potential",) and block.outputs["potential"].shape == (10, 10)
    result = block.process([(3, 4)])
    assert_contract(block, result)
    assert result.ok and result.potential[0, 0] == 1.0


def test_region_potentials_schema_follows_enabled_outputs():
    block = RegionDependingPotentials(cells_along_x=4, cells_along_y=1, mask=MASK, num_of_regions=4,
                                        output_potential_matrix=False, output_hit_regions=True,
                                        output_hit_region_indexes=True, output_region_values=True,
                                        decrement_factor=0.5)
    assert block.outputs.names == ("hit_regions", "hit_region_indexes", "region_values")
    assert block.outputs["hit_regions"].shape == (4,) and block.outputs["hit_regions"].kind is int
    assert block.outputs["hit_region_indexes"].shape == (None,) and block.outputs["region_values"].shape == (4,)
    assert block.outputs.size == 8  # hit_region_indexes is data-dependent, not part of to_array()
    result = block.process([(0, 0), (0, 3)])
    assert_contract(block, result)
    assert result.hit_regions.tolist() == [1, 0, 1, 0] and result.hit_region_indexes.tolist() == [0, 2]
    assert result.region_values.tolist() == [1, -0.5, 1, 0]  # region 3 has no cell: never updated
    with pytest.raises(ValueError):
        RegionDependingPotentials(output_potential_matrix=False)


def test_region_potentials_region_input_and_partial_outputs_on_error():
    block = RegionDependingPotentials(cells_along_x=4, cells_along_y=1, mask=MASK, num_of_regions=4,
                                        input_kind="hit_regions", output_hit_regions=True,
                                        output_hit_region_indexes=True)
    ok = block.process([1])
    assert ok.ok and ok.potential.tolist() == [[-1, -1, 1, -1]]
    bad = block.process([0, 9])
    assert bad.status is Status.INVALID_INPUT and bad.reason
    assert bad.valid == {"potential": False, "hit_regions": False, "hit_region_indexes": False}  # no numbers when invalid
    assert np.isnan(bad.potential).all() and not bad.hit_regions.any() and not bad.hit_region_indexes.size
    empty = block.process([])
    assert empty.status is Status.NO_OUTPUT and not any(empty.valid.values())


def test_region_potentials_reset_trigger():
    kw = dict(cells_along_x=4, cells_along_y=1, mask=MASK, num_of_regions=4, output_region_values=True,
              initialization_matrix=np.array([[1.0, 2, 3, 4]]))
    block = RegionDependingPotentials(**kw)
    assert block.region_values.tolist() == [2, 3, 4, 0]
    block.process([(0, 0)])
    block.trigger_reset()
    assert block.region_values.tolist() == [2, 3, 4, 0]  # the initial region values
    block.process([(0, 0)])
    block.reset()
    assert block.region_values.tolist() == [2, 3, 4, 0]
    with pytest.raises(ValueError):
        RegionDependingPotentials(reg_init_values=[0.0] * 10, initialization_matrix=np.zeros((10, 10)))


@pytest.mark.parametrize("ptype", [count.lower() for count in core.space.RegionPotentialType.__members__])
def test_region_potentials_every_type_with_a_recorder(ptype):
    block = RegionDependingPotentials(cells_along_x=4, cells_along_y=1, mask=MASK, num_of_regions=4,
                                        potential_type=ptype, output_hit_regions=True, output_region_values=True)
    rec = Recorder(block)
    for cells in ([(0, 0)], [(0, 2)], [], [(0, 3), (0, 1)]):
        rec.append(block.process(cells))
    assert len(rec) == 4
    assert rec.ok.tolist() == [True, True, False, True]
    assert rec["potential"].shape == (4, 1, 4) and rec["hit_regions"].shape == (4, 4)
    assert rec["region_values"].shape == (4, 4) and np.isnan(rec["region_values"][2]).all()
    assert rec.to_numpy().shape == (4, block.outputs.size)


def test_position_potentials_recorder():
    block = PositionDependingPotentials(cells_along_x=2, cells_along_y=2,
                                          potential_type="occupation_rates")
    rec = Recorder(block)
    for cells in ([(0, 0)], [(1, 1)], [(1, 1)]):
        rec.append(block.process(cells))
    assert rec["potential"].shape == (3, 2, 2)
    np.testing.assert_allclose(rec["potential"][-1], [[100 / 3, 0], [0, 200 / 3]])
    assert list(rec.to_frame().columns[2:]) == list(block.outputs.flat_names)
