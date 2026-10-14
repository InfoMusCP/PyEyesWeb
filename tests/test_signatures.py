"""Every core-backed feature shows its constructor parameters, and a misspelled keyword is a clean TypeError."""

import collections.abc
import enum
import inspect
import typing

import pytest

pytest.importorskip("pyeyesweb._core")

from pyeyesweb import catalog  # noqa: E402
from pyeyesweb.base.core_feature import _SIGNATURE_PARAM, CoreFeature  # noqa: E402

FEATURES = [info.cls for info in catalog()]
# A merged feature (`VariantFeature`) wraps one block per variant.
CORE_FEATURES = [variant for cls in FEATURES if issubclass(cls, CoreFeature) for variant in (cls._variants.values() if "_variants" in cls.__dict__ else [cls])]

# A block parameter the wrapper deliberately does not take under that name: Equilibrium folds the two axis indices
# into `axes`, BoundingBoxFilledArea fixes `epsilon`.
WRAPPED = {"Equilibrium": {"axis_x", "axis_y"}, "BoundingBoxFilledArea": {"epsilon"}}


def _ids(classes):
    return [cls.__name__ for cls in classes]


def _nb_defaults(cls):
    """`name -> default` of the block's binding, straight from the nanobind signature."""
    text, _doc, defaults = cls._core_class.__init__.__nb_signature__[0][:3]
    names = _SIGNATURE_PARAM.findall(text)
    defaults = defaults or ()
    return dict(zip(names[len(names) - len(defaults):], defaults))  # a block may take required arguments (`model`) first


@pytest.mark.parametrize("cls", FEATURES, ids=_ids(FEATURES))
def test_signature_has_no_bare_var_keyword(cls):
    parameters = inspect.signature(cls).parameters.values()
    assert not any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters)
    assert not any(parameter.kind is parameter.VAR_POSITIONAL for parameter in parameters)


@pytest.mark.parametrize("cls", CORE_FEATURES, ids=_ids(CORE_FEATURES))
def test_signature_lists_every_block_parameter(cls):
    missing = cls._core_params() - set(inspect.signature(cls).parameters) - WRAPPED.get(cls.__name__, set())
    assert not missing


@pytest.mark.parametrize("cls", CORE_FEATURES, ids=_ids(CORE_FEATURES))
def test_signature_defaults_are_the_block_defaults(cls):
    parameters = inspect.signature(cls).parameters
    for name, default in _nb_defaults(cls).items():
        if name in parameters and name not in cls.__init__.__code__.co_varnames:
            # A timed feature has no rate until the user gives one (the block's 30 Hz is never used).
            expected = None if name == "sampling_rate" and cls._timed else default
            if isinstance(expected, enum.Enum):  # a choice is its string, an on/off choice a bool
                expected = expected.name in ("ON", "YES") if parameters[name].annotation is bool else expected.name.lower()
            elif isinstance(expected, list) and expected and all(isinstance(item, enum.Enum) for item in expected):  # a list of choices: its names, one name when it is a single one
                expected = [item.name.lower() for item in expected]
                expected = expected[0] if len(expected) == 1 else expected
            assert parameters[name].default == expected, name


@pytest.mark.parametrize("cls", CORE_FEATURES, ids=_ids(CORE_FEATURES))
def test_typo_is_a_type_error_with_a_suggestion(cls):
    names = [name for name in inspect.signature(cls).parameters if name in cls._core_params()]
    typo = (names[0] + "x") if names else "bogus"
    required = {name: 1 for name, parameter in inspect.signature(cls).parameters.items() if parameter.default is parameter.empty}
    with pytest.raises(TypeError) as error:
        cls(**required, **{typo: 1})
    message = str(error.value)
    assert cls.__name__ in message and typo in message
    if names:
        assert f"did you mean '{names[0]}'" in message


@pytest.mark.parametrize("cls", CORE_FEATURES, ids=_ids(CORE_FEATURES))
def test_a_choice_is_a_literal_of_strings_or_a_bool(cls):
    parameters = inspect.signature(cls).parameters
    for name in cls._core_enums().keys() & parameters.keys():
        annotation = parameters[name].annotation
        if annotation is bool:
            continue
        if typing.get_origin(annotation) is typing.Union:  # one choice, or a sequence of them
            annotation, sequence = typing.get_args(annotation)
            assert typing.get_origin(sequence) is collections.abc.Sequence and typing.get_args(sequence) == (annotation,), name
        options = typing.get_args(annotation)
        assert typing.get_origin(annotation) is typing.Literal and options, name
        assert all(isinstance(option, str) and option == option.lower() for option in options), name


FACTORIES = [(cls, name, member.__func__) for cls in CORE_FEATURES for name, member in vars(cls).items()
             if isinstance(member, classmethod) and hasattr(member.__func__, "_input_mode_parameter")]
FACTORY_IDS = [f"{cls.__name__}.{name}" for cls, name, _ in FACTORIES]


def test_the_input_mode_features_have_their_factories():
    assert {identifier for identifier in FACTORY_IDS} == {
        "KineticEnergy.from_position", "KineticEnergy.from_velocity", "Kinematics.from_point", "Kinematics.from_series",
        "LogDimensionlessJerk.from_velocity", "LogDimensionlessJerk.from_acceleration"}


@pytest.mark.parametrize("cls, name, function", FACTORIES, ids=FACTORY_IDS)
def test_a_factory_shows_the_constructor_signature_without_the_input_mode(cls, name, function):
    constructor = inspect.signature(cls).parameters
    shown = inspect.signature(getattr(cls, name)).parameters
    assert list(shown) == [parameter for parameter in constructor if parameter != function._input_mode_parameter]
    assert all(shown[parameter] == constructor[parameter] for parameter in shown)  # defaults and annotations included
    assert function.__doc__


@pytest.mark.parametrize("cls, name, function", FACTORIES, ids=FACTORY_IDS)
def test_a_factory_builds_the_constructor_with_its_input_mode(cls, name, function):
    feature = getattr(cls, name)(**({"skeleton": "kinect_v2"} if cls.__name__ == "KineticEnergy" else {}))
    assert isinstance(feature, cls)
    assert name == f"from_{feature.input_mode}" or (cls.__name__ == "Kinematics" and feature.input_mode == "time_series")


@pytest.mark.parametrize("cls, name, function", FACTORIES, ids=FACTORY_IDS)
def test_a_factory_typo_is_a_type_error_with_a_suggestion(cls, name, function):
    valid = [parameter for parameter in inspect.signature(getattr(cls, name)).parameters if parameter in cls._core_params()]
    with pytest.raises(TypeError) as error:
        getattr(cls, name)(**{valid[0] + "x": 1})
    assert f"{cls.__name__}.{name}()" in str(error.value) and f"did you mean '{valid[0]}'" in str(error.value)
    with pytest.raises(TypeError, match="input_mode"):  # the mode is the factory's, not a keyword
        getattr(cls, name)(input_mode="point")
