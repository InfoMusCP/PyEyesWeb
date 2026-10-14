"""Live parameter validation on every feature of `catalog()`: a numeric parameter set to -1 on a built feature either is
accepted by design (`ACCEPTS_NEGATIVE`, with the reason) or raises `ValueError` and leaves the feature as it was, like the
constructor. The parameters are those of the signature of the feature (`inspect.signature`), so a new numeric parameter is
covered as soon as it exists.
"""

import inspect
import typing

import pytest

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from test_contract_all_features import NAMES, factory_and_recordings  # noqa: E402

# parameter name -> why a negative value is meaningful (or reported per call) for it
ACCEPTS_NEGATIVE = {
    "x_min": "origin of the grid: a coordinate, of any sign",
    "y_min": "origin of the grid: a coordinate, of any sign",
    "nan_value": "marker value that stands for NaN in the original output: any number",
    "noise_threshold": "variance threshold: a negative one never judges the motion as noise (the EyesWeb scenarios use -1)",
    "margin": "margin of the support polygon: a negative margin shrinks it (parity with the original)",
    "number_of_subsamples": "a negative count is reported per call as INVALID_INPUT, as the original does (parity test)",
    "gaussian_correlation": "correlation coefficient of the Gaussian field, in [-1, 1]",
    "increment_factor": "signed gain of the potential formula, not validated by EyesWeb",
    "decrement_factor": "signed gain of the potential formula, not validated by EyesWeb",
    "norm_exponent": "exponent of the polynomial field, not validated by EyesWeb",
    "decay_exponent": "exponent of the polynomial field, not validated by EyesWeb",
}


def _numeric(annotation):
    if annotation in (int, float):
        return True
    return typing.get_origin(annotation) is typing.Union and any(item in (int, float) for item in typing.get_args(annotation))


def _numeric_parameters(cls):
    return [parameter for parameter in inspect.signature(cls).parameters.values()
            if parameter.kind is not parameter.VAR_KEYWORD
            and (_numeric(parameter.annotation) or (parameter.annotation is inspect.Parameter.empty
                                                    and isinstance(parameter.default, (int, float))
                                                    and not isinstance(parameter.default, bool)))]


CASES = []
for name in NAMES:
    factory, _ = factory_and_recordings(name)
    CASES += [pytest.param(name, parameter.name, id=f"{name}.{parameter.name}")
              for parameter in _numeric_parameters(type(factory()))]


def _state(feature, parameter):
    try:
        shown = getattr(feature, parameter)
    except AttributeError:  # a parameter left at the core default is not stored
        shown = None
    return shown, dict(vars(feature).get("_params", {})), getattr(feature, "window", None), getattr(feature, "hop", None)


@pytest.mark.parametrize("name, parameter", CASES)
def test_a_negative_value_raises_and_changes_nothing_or_is_accepted_by_design(name, parameter):
    factory, recordings = factory_and_recordings(name)
    feature = factory()
    for index in range(min(len(recordings[0]), 5)):  # a running feature: its block is built and holds state
        feature.process(*(recording[index] for recording in recordings))
    before = _state(feature, parameter)
    if parameter in ACCEPTS_NEGATIVE:
        setattr(feature, parameter, -1)
        return
    with pytest.raises(ValueError):
        setattr(feature, parameter, -1)
    assert _state(feature, parameter) == before


def test_accepts_negative_names_only_existing_parameters():
    existing = {parameter.name for name in NAMES for parameter in _numeric_parameters(type(factory_and_recordings(name)[0]()))}
    assert set(ACCEPTS_NEGATIVE) <= existing
    assert all(ACCEPTS_NEGATIVE.values())
