"""Readability rule: no one-character identifier in the package (`_` alone, an unused value, is allowed).

Checked with the AST: function and lambda arguments, assigned names, loop and comprehension targets, `except ... as`
names and import aliases. Attribute names and keyword names of calls are not identifiers of the package and are not scanned.
"""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "pyeyesweb"


def _short(name):
    return len(name.lstrip("_")) <= 1 and name != "_"


def _identifiers(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            yield node.arg, node.lineno, "argument"
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id, node.lineno, "variable"
        elif isinstance(node, ast.ExceptHandler) and node.name:
            yield node.name, node.lineno, "except name"
        elif isinstance(node, ast.alias) and node.asname:
            yield node.asname, getattr(node, "lineno", 0), "import alias"


def test_no_one_character_identifier_in_the_package():
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf8"), filename=str(path))
        offenders += [f"{path.relative_to(PACKAGE.parent).as_posix()}:{line}: {kind} `{name}`"
                      for name, line, kind in _identifiers(tree) if _short(name)]
    assert not offenders, "one-character identifiers (use a descriptive name):\n" + "\n".join(offenders)


def test_no_one_character_public_parameter_of_a_feature_or_of_the_core():
    """The same rule for what a user types: constructor parameters of the catalog features and every nanobind argument."""
    import inspect
    import types

    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb import catalog
    from pyeyesweb._core import core
    from pyeyesweb.base.core_feature import _SIGNATURE_PARAM

    offenders = [f"{info.cls.__name__}({name})" for info in catalog() for name in inspect.signature(info.cls).parameters
                 if _short(name)]

    def walk(owner, path, seen):
        for attribute, member in vars(owner).items():
            if attribute.startswith("__") and attribute != "__init__":
                continue
            where = f"{path}.{attribute}"
            for signature in getattr(member, "__nb_signature__", ()):
                offenders.extend(f"{where}({name})" for name in _SIGNATURE_PARAM.findall(signature[0]) if _short(name))
            if isinstance(member, (type, types.ModuleType)) and id(member) not in seen:
                seen.add(id(member))
                walk(member, where, seen)

    walk(core, "core", set())
    assert not offenders, "one-character public parameters (use a descriptive name):\n" + "\n".join(sorted(set(offenders)))


# ------------------------------------------------------------------------------------ one spelling per concept

# spelling that is forbidden -> the one to use. Checked over the parameters, inputs and outputs of every catalog feature.
FORBIDDEN = {
    "n_inputs": "number_of_inputs", "input_number": "number_of_inputs", "time_series_number": "number_of_inputs",
    "number_of_input_trains": "number_of_inputs", "event_class_number": "number_of_event_classes",
    "points_number": "number_of_points", "num_of_regions": "number_of_regions", "num_subsamples": "number_of_subsamples",
    "window_size": "window", "window_length": "window", "length": "window", "buffer_length": "window",
    "data_memory": "window", "cells_x": "cells_along_x", "cells_y": "cells_along_y",
    "sigma_value": "gaussian_sigma", "std_dev_x": "gaussian_sigma_x", "std_dev_y": "gaussian_sigma_y",
    "rho": "gaussian_correlation", "ges_dur": "gesture_duration", "frames": "sampling_rate",
    "use_cust_ampl": "use_custom_amplitude", "cust_ampl": "custom_amplitude", "use_cust_dist": "use_custom_distance",
    "cust_dist": "custom_distance", "reg_init_values": "region_initial_values", "ref_dir": "reference_direction",
    "cog": "center_of_gravity", "filter_params": "low_frequency, high_frequency", "algorithm": "method",
    "algo": "method", "type": "measure", "couples": "pairs", "joint_pairs": "pairs",
    "center_of_symmetry": "reference_point", "sqom": "quantity_of_motion", "ci": "contraction_index",
    "cpr": "correlations_matrix", "ts1": "first_signal", "ts2": "second_signal", "x": "first_signal",
    "y": "second_signal", "plv": "phase_locking_value", "xy": "first_to_second_interdependence",
    "yx": "second_to_first_interdependence", "value": "equilibrium", "matrix": "a specific name",
    "sequences": "sequence_count", "plot": "recurrence_matrix", "synchronisation": "synchronization",
}


def _declared():
    """(feature, kind, name) for every parameter, input and output of the catalog."""
    import inspect

    import pytest

    pytest.importorskip("pyeyesweb._core")
    from test_contract_all_features import NAMES, factory_and_recordings

    from pyeyesweb import catalog
    names = []
    for info in catalog():
        names += [(info.name, "parameter", name) for name in inspect.signature(info.cls).parameters]
    for name in NAMES:
        feature = factory_and_recordings(name)[0]()
        names += [(name, "input", declared.name) for declared in feature.inputs]
        names += [(name, "output", declared.name) for declared in feature.outputs]
    return names


def test_no_forbidden_synonym_in_a_parameter_input_or_output_of_a_feature():
    offenders = [f"{feature} {kind} `{name}`: use {FORBIDDEN[name]}" for feature, kind, name in _declared() if name in FORBIDDEN]
    assert not offenders, "\n".join(offenders)


def test_a_boolean_output_is_named_is_something():
    import pytest

    pytest.importorskip("pyeyesweb._core")
    from test_contract_all_features import NAMES, factory_and_recordings
    offenders = [f"{name}.{declared.name}" for name in NAMES for declared in factory_and_recordings(name)[0]().outputs
                 if declared.kind is bool and not declared.name.startswith("is_")]
    assert not offenders, offenders


def test_sampling_rate_has_no_default_rate_anywhere():
    import inspect

    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb import catalog
    offenders = [info.name for info in catalog() if "sampling_rate" in inspect.signature(info.cls).parameters
                 and inspect.signature(info.cls).parameters["sampling_rate"].default is not None]
    assert not offenders, offenders


def test_window_is_missing_with_a_message_that_says_what_it_is():
    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb.analysis_primitives import CorrelationsMatrix
    with pytest.raises(TypeError, match=r"CorrelationsMatrix\(\) missing required argument.*window.*samples"):
        CorrelationsMatrix()


def test_a_parameter_left_at_its_default_reads_back_and_the_signature_is_honest():
    import inspect

    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb.analysis_primitives import Rarity
    assert Rarity().window == 50 and Rarity().measure == "rarity"
    parameters = inspect.signature(Rarity).parameters
    assert all(parameter.default is not parameter.empty for parameter in parameters.values())


def test_multi_scale_entropy_explains_its_minimum_window():
    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb.analysis_primitives import MultiScaleEntropy
    MultiScaleEntropy()
    with pytest.raises(ValueError, match=r"max_scale \* minimum_points = 6 \* 500"):
        MultiScaleEntropy(window=100)


def test_the_speed_profile_metrics_need_a_rate_and_accept_a_one_element_array():
    import numpy as np
    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb.low_level import Harmonicity
    with pytest.raises(ValueError, match="sampling_rate"):
        Harmonicity()
    feature = Harmonicity(window=10, sampling_rate=50.0)
    assert feature.process(np.array([1.0])).status.name == "WARMING_UP"
    assert len(feature.run(np.ones((12, 1)))) == 12
