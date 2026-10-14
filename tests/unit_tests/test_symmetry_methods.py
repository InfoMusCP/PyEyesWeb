"""`Symmetry`: one feature, two methods (RATIO = EyesWeb SymmetryIndex-3D, REFLECTION = mirror reflection of pairs).
Needs the compiled core (EYESWEB_CORE_PATH)."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reference"))

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from contract_suite import check_feature_contract  # noqa: E402
from symmetry_reference import GeometricSymmetryReference  # noqa: E402
import pyeyesweb  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import Symmetry  # noqa: E402
from pyeyesweb.low_level import symmetry as module  # noqa: E402

RNG = np.random.default_rng(3)
CLOUDS = RNG.standard_normal((20, 8, 3))
SKELETONS = RNG.standard_normal((20, 3, 3))
LABELS = ["torso", "left_hip", "right_hip"]
RATIO = dict(couples=[("left_hip", "right_hip")], reference_point="torso")  # the default input type is custom
PAIRS = [(0, 1), (2, 3)]


def test_default_method_is_ratio():
    feature = Symmetry(**RATIO, labels=LABELS)
    assert feature.method == "ratio"
    assert list(feature.outputs.names) == ["symmetry"]


def test_contract_of_both_methods():
    check_feature_contract(lambda: Symmetry(**RATIO, labels=LABELS), SKELETONS)
    check_feature_contract(lambda: Symmetry(method="reflection", joint_pairs=PAIRS), CLOUDS)


@pytest.mark.parametrize("output_type", ["global", "components"])
def test_a_frame_with_a_missing_joint_is_invalid_input_without_numbers(output_type):
    """A dict frame that lacks a joint of a couple is INVALID_INPUT ("missing joints", central label check) with an empty
    index of the declared shape; a complete frame is as before."""
    feature = Symmetry(labels=["a", "b", "c", "d"], couples=[("a", "b"), ("c", "d")], reference_point="neck",
                       output_type=output_type)
    for frame, missing in (({"a": (1, 2, 3), "c": (0, 1, 1)}, "b, d"), ({"a": (1, 2, 3), "b": (1, -2, 3), "c": (0, 1, 1)}, "d")):
        result = feature.process(frame)
        assert result.status == Status.INVALID_INPUT and result.reason == f"missing joints: {missing}"
        assert np.isnan(result.symmetry).all() and np.shape(result.symmetry) == feature.outputs["symmetry"].shape
    complete = feature.process({"a": (1, 2, 3), "b": (1, -2, 3), "c": (0, 1, 1), "d": (0, 1, 1)})
    assert complete.status == Status.OK and np.any(complete.symmetry > 0)


def test_schemas_differ_per_method():
    ratio = Symmetry(**RATIO, labels=LABELS)
    reflection = Symmetry(method="reflection", joint_pairs=PAIRS)
    assert list(ratio.outputs.names) == ["symmetry"]
    assert list(reflection.outputs.names) == ["pair_symmetry"]
    assert ratio.outputs["symmetry"].shape == ()
    assert reflection.outputs["pair_symmetry"].shape == (2,)


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="method: invalid value"):
        Symmetry(method="mirror")


@pytest.mark.parametrize("method,params", [
    ("ratio", {"joint_pairs": PAIRS}),
    ("ratio", {"center_of_symmetry": 1}),
    ("reflection", {"joint_pairs": PAIRS, "output_type": "components"}),
    ("reflection", {"joint_pairs": PAIRS, "labels": LABELS}),
    ("reflection", {}),
])
def test_parameter_of_the_wrong_method_raises(method, params):
    with pytest.raises((TypeError, ValueError)):
        Symmetry(method=method, **params)


def test_results_equal_the_implementations():
    ratio = Symmetry(**RATIO, labels=LABELS, output_type="components")
    direct = module._RatioSymmetry(**RATIO, labels=LABELS, output_type="components")
    np.testing.assert_array_equal(ratio.process(SKELETONS[0]).symmetry, direct.process(SKELETONS[0]).symmetry)
    reflection = Symmetry(method="reflection", joint_pairs=PAIRS, center_of_symmetry=4)
    direct = module._ReflectionSymmetry(joint_pairs=PAIRS, center_of_symmetry=4)
    np.testing.assert_array_equal(reflection.process(CLOUDS[0]).pair_symmetry, direct.process(CLOUDS[0]).pair_symmetry)


def test_reflection_equals_the_reference():
    new = Symmetry(method="reflection", joint_pairs=PAIRS).process(CLOUDS[0])
    ref = GeometricSymmetryReference(PAIRS).compute(CLOUDS[0])
    np.testing.assert_allclose(new.pair_symmetry, ref["pair_error"], rtol=1e-9, atol=1e-9)


def test_catalog_lists_one_symmetry_and_no_private_implementation():
    names = [info.name for info in pyeyesweb.catalog()]
    assert names.count("Symmetry") == 1
    assert not {"SymmetryIndex3D", "GeometricSymmetry", "_RatioSymmetry", "_ReflectionSymmetry"} & set(names)
    assert not {"_RatioSymmetry", "_ReflectionSymmetry"} & set(module.__all__)
