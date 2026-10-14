"""What tab completion shows: the public names only, the helpers of the output contract private."""

import pytest

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

import pyeyesweb  # noqa: E402
from pyeyesweb import analysis_primitives, data_models, high_level, low_level, mid_level, physical_signals, skeletons  # noqa: E402
from pyeyesweb.physical_signals import GenericModelSimulator  # noqa: E402


def test_the_package_lists_its_public_modules_and_names_only():
    shown = dir(pyeyesweb)
    assert not {"_core", "base", "utils"} & set(shown)
    assert {"catalog", "Layer", "SeriesBuffer", "low_level", "data_models", "skeletons"} <= set(shown)


@pytest.mark.parametrize("package", [physical_signals, low_level, mid_level, high_level, data_models, skeletons])
def test_a_package_lists_its_exports_not_its_submodules_or_imports(package):
    assert dir(package) == sorted(package.__all__)


def test_analysis_primitives_list_their_exports_and_the_synchronization_package():
    assert dir(analysis_primitives) == sorted([*analysis_primitives.__all__, "synchronization"])


def test_the_stream_synchronizer_and_the_model_are_public_in_physical_signals():
    assert {"TimeWindowSynchronizer", "SynchronizedWindow", "MassSpringModel"} <= set(physical_signals.__all__)


def test_the_helpers_of_the_output_contract_are_private():
    shown = dir(low_level.Kinematics(dims=2))
    assert not {"result", "no_output", "finite_result", "INPUTS", "OUTPUTS"} & set(shown) and "parameters" in shown


def test_the_model_error_names_the_ways_to_build_one():
    with pytest.raises(TypeError, match="MassSpringModel.from_xml_file"):
        GenericModelSimulator(None)
