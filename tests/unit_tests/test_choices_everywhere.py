"""Every choice parameter of every feature is a `Literal` of strings (name, any case, `-` / space for `_`), or a bool when
it is on/off; an enum member of the core is still taken silently."""

import inspect
import typing

import pytest

pytest.importorskip("pyeyesweb._core")

from pyeyesweb import catalog  # noqa: E402
from pyeyesweb.base.choices import choice_name  # noqa: E402


# The parameters that pick the variant: only the public class dispatches on them.
SELECTORS = ("method",)


def _choice_parameters():
    rows = []
    for info in catalog():
        variants = info.cls._variants.values() if "_variants" in info.cls.__dict__ else []
        for cls in variants:
            _rows(rows, cls, skip=SELECTORS)
        _rows(rows, info.cls, only=SELECTORS if variants else None)
    return rows


def _rows(rows, cls, skip=(), only=None):
    try:
        parameters = inspect.signature(cls).parameters
    except (TypeError, ValueError):
        return
    enums = cls._core_enums() if hasattr(cls, "_core_enums") and cls._core_class is not None else {}
    for name, parameter in parameters.items():
        if name in skip or (only is not None and name not in only):
            continue
        annotation = parameter.annotation
        if typing.get_origin(annotation) is typing.Union and name in enums:  # one choice, or a list of them
            annotation = typing.get_args(annotation)[0]
        if typing.get_origin(annotation) is typing.Literal and (name in enums or only is not None):
            options = list(typing.get_args(annotation))
        elif parameter.annotation is bool and name in enums:
            options = [True, False]
        else:
            continue
        rows.append(pytest.param(cls, name, options, id=f"{cls.__name__}.{name}"))


def _model():
    from pyeyesweb.physical_signals import MassSpringModel

    model = MassSpringModel()
    model.add_mass("root", 1e10)
    model.add_mass("tip", 1.0, (1.0, 0.0, 0.0))
    model.add_spring("rod", "root", "tip", 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    return model


def _build(cls, **params):
    required = {name: 32 for name, parameter in inspect.signature(cls).parameters.items()
                if parameter.default is parameter.empty and parameter.kind is parameter.POSITIONAL_OR_KEYWORD and name == "window"}
    if "skeleton" in inspect.signature(cls).parameters:  # the joint features refuse to be built without joints
        params.setdefault("skeleton", "kinect_v2")
    if getattr(cls, "_rate_required", False):  # no default rate
        params.setdefault("sampling_rate", 50.0)
    if "model" in inspect.signature(cls).parameters:  # the mass-spring features need a model to follow
        params.setdefault("model", _model())
    try:
        return cls(**required, **params)
    except Exception as error:  # a combination that is invalid for the feature itself is not a choices problem
        if any(text in str(error) for text in ("choose one of", "invalid value", "True or False")):
            raise
        return None


def _spellings(option):
    return [option] if isinstance(option, bool) else [option, option.upper(), option.replace("_", "-")]


def test_the_catalog_has_choice_parameters():
    assert len(_choice_parameters()) >= 27


@pytest.mark.parametrize("cls, name, options", _choice_parameters())
def test_signature_is_literal_with_a_default_among_the_options(cls, name, options):
    default = inspect.signature(cls).parameters[name].default
    assert default is inspect.Parameter.empty or default in options
    assert all(isinstance(option, bool) for option in options) or all(option == option.lower() for option in options)


@pytest.mark.parametrize("cls, name, options", _choice_parameters())
def test_every_option_is_accepted_in_every_spelling(cls, name, options):
    for option in options:
        reference = _build(cls, **{name: option})
        for text in _spellings(option):
            assert (_build(cls, **{name: text}) is None) == (reference is None), f"{cls.__name__}({name}={text!r})"


@pytest.mark.parametrize("cls, name, options", [
    choice for choice in _choice_parameters() if choice.values[1] in getattr(choice.values[0], "_core_enums", dict)() and choice.values[2][0] is not True])
def test_an_enum_member_is_still_taken(cls, name, options):
    enum_cls = cls._core_enums()[name][0]
    for member in enum_cls.__members__.values():
        assert (_build(cls, **{name: member}) is None) == (_build(cls, **{name: choice_name(member)}) is None)


@pytest.mark.parametrize("cls, name, options", _choice_parameters())
def test_a_wrong_string_names_the_options(cls, name, options):
    with pytest.raises((ValueError, TypeError)) as error:
        _build(cls, **{name: "no_such_choice"})
    assert "no_such_choice" in str(error.value)
    if not isinstance(options[0], bool):
        assert all(repr(option) in str(error.value) for option in options)


@pytest.mark.parametrize("cls, name, options", _choice_parameters())
def test_the_setter_accepts_strings_too(cls, name, options):
    feature = _build(cls)
    if feature is None:
        pytest.skip("the feature needs required arguments")
    try:
        setattr(feature, name, options[-1])
    except AttributeError:
        assert name in SELECTORS, "only the variant selectors are fixed after construction"
    except (ValueError, TypeError) as error:
        assert "choose one of" not in str(error) and "invalid value" not in str(error) and "True or False" not in str(error), error
