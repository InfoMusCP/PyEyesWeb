"""`feature.parameters` of every catalog feature: a read-only snapshot of the constructor parameters (as `get_params`)."""

import inspect

import pytest

from test_contract_all_features import NAMES, factory_and_recordings


@pytest.mark.parametrize("name", NAMES)
def test_parameters_are_the_constructor_parameters_read_only(name):
    feature = factory_and_recordings(name)[0]()
    shown = [parameter for parameter in inspect.signature(type(feature)).parameters.values()
             if parameter.kind not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)]
    parameters = feature.parameters
    assert [parameter.name for parameter in shown if parameter.name not in parameters] in ([], ["skeleton"])  # resolved into labels, weights, pairs
    assert list(parameters) == [parameter.name for parameter in shown if parameter.name in parameters]
    with pytest.raises(TypeError):
        parameters["window"] = 1
    for parameter in shown:
        if parameter.name in parameters and parameter.default is not parameter.empty and not hasattr(parameter.default, "__len__"):
            assert parameters[parameter.name] == getattr(feature, parameter.name)
