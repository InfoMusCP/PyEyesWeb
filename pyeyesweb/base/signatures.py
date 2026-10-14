"""Constructor signatures of the core-backed features, derived from the nanobind bindings of their blocks.

`core_signature(cls)` merges the explicit Python parameters of a feature's `__init__` with the parameters of the C++
block (names, defaults, type hints), so `inspect.signature(Feature)` shows every parameter a keyword can set. A choice
the core takes as an enum is typed `Literal["point", "time_series"]` (its default is the string too); one the core takes as a
sequence of enums is typed `Union[Literal[...], Sequence[Literal[...]]]`; an on/off enum is a `bool`.

`input_mode_factory` makes the classmethod constructors `from_*` of a feature whose input kind differs for the same quantity:
each shows the constructor's signature without `input_mode` and checks its keywords like the constructor does.
"""

import ast
import collections.abc
import difflib
import enum
import functools
import inspect
import re
import types
import typing
from typing import Any, Literal, Optional, Sequence, Union

import numpy as np

from pyeyesweb.base.choices import choice_name

_PLACEHOLDER = re.compile(r"\\(\d+)")  # nanobind writes a default as "\0", "\1"... and ships the values apart


class _CoreTypes:
    """The name `eyesweb_core` in an annotation of a nanobind signature: an enum of the core resolves to
    `Literal[names]`, any other core type to itself, so annotations are resolved by `typing.get_type_hints` against a
    fixed namespace."""

    def __init__(self, target: Any):
        self._target = target

    def __getattr__(self, name: str) -> Any:
        member = getattr(self._target, name)
        if hasattr(member, "__members__"):
            return Literal[tuple(choice_name(entry) for entry in member.__members__.values())]
        return member if isinstance(member, type) else _CoreTypes(member)


def _resolve_annotations(core: Any, sources: dict) -> dict:
    """`parameter -> annotation` for annotation texts `sources`, evaluated only against the names nanobind writes."""
    namespace = {"collections": collections, "np": np, "Union": Union, "Any": Any, "eyesweb_core": _CoreTypes(core)}
    return typing.get_type_hints(types.SimpleNamespace(__annotations__=sources), namespace)


def _nb_parameters(core: Any, core_class: Any, public: Optional[dict] = None) -> list:
    """The constructor parameters of `core_class` as keyword-only `inspect.Parameter`s (empty when the binding has none),
    under their public names (`public`: block name -> public name)."""
    signatures = getattr(core_class.__init__, "__nb_signature__", ())
    if not signatures:
        return []
    text, defaults = signatures[0][0], (signatures[0][2] if len(signatures[0]) > 2 else None) or ()
    text = re.sub(r"ndarray\[[^\]]*\]", "np.ndarray", _PLACEHOLDER.sub(r"__default_\1", text))
    tree = ast.parse(text.replace("def __init__", "def f") + ":\n pass")
    values = {f"__default_{index}": value for index, value in enumerate(defaults)}
    arguments = tree.body[0].args
    defaulted = dict(zip((argument.arg for argument in arguments.args[len(arguments.args) - len(arguments.defaults):]), arguments.defaults))
    hints = _resolve_annotations(core, {arg.arg: ast.unparse(arg.annotation) for arg in arguments.args[1:] if arg.annotation})
    parameters = []
    for arg in arguments.args[1:]:  # skip self
        annotation = hints.get(arg.arg, Any)
        if typing.get_origin(annotation) is collections.abc.Sequence and typing.get_origin(typing.get_args(annotation)[0]) is Literal:
            annotation = Union[typing.get_args(annotation)[0], annotation]  # one choice, or several
        default = inspect.Parameter.empty
        if arg.arg in defaulted:
            node = defaulted[arg.arg]
            default = values.get(node.id, Any) if isinstance(node, ast.Name) else ast.literal_eval(node)
            if isinstance(default, enum.Enum):
                default = choice_name(default)
            elif isinstance(default, list) and default and all(isinstance(item, enum.Enum) for item in default):
                names = [choice_name(item) for item in default]
                default = names[0] if len(names) == 1 else names
        parameters.append(inspect.Parameter((public or {}).get(arg.arg, arg.arg), inspect.Parameter.KEYWORD_ONLY, default=default,
                                            annotation=annotation))
    return parameters


def core_signature(cls: Any, core: Any) -> Optional[inspect.Signature]:
    """The signature of `cls(...)`: its own `__init__` parameters, plus those of the block when it takes `**params`."""
    own = list(inspect.signature(cls.__init__).parameters.values())[1:]  # skip self
    if getattr(cls, "_unit_params", None):  # an explicit `units` parameter is a choice like the added one
        own = [parameter.replace(annotation=Literal["m", "mm"]) if parameter.name == "units" else parameter for parameter in own]
    if not any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in own):
        return inspect.Signature([parameter for parameter in own])
    named = [parameter for parameter in own if parameter.kind is not inspect.Parameter.VAR_KEYWORD]
    known = {parameter.name for parameter in named}
    extra = [parameter for parameter in _nb_parameters(core, cls._core_class, cls._public_names())
             if parameter.name not in known and parameter.name not in getattr(cls, "_hidden_params", ())]
    if getattr(cls, "_timed", False):  # time is `timestamp` or `sampling_rate` (Hz, int or float), never a mode
        extra = [parameter for parameter in extra if parameter.name != "sampling_rate"]
        extra.append(inspect.Parameter("sampling_rate", inspect.Parameter.KEYWORD_ONLY, default=None,
                                       annotation=Optional[float]))
    if getattr(cls, "_unit_params", None):  # lengths in metres (EyesWeb) or data in millimetres
        extra.append(inspect.Parameter("units", inspect.Parameter.KEYWORD_ONLY, default="m",
                                       annotation=Literal["m", "mm"]))
    if getattr(cls, "_parts", None):  # the choices that replace the block's bool switches
        extra.append(inspect.Parameter("parts", inspect.Parameter.KEYWORD_ONLY, default=cls._default_parts(),
                                       annotation=Sequence[Literal[tuple(cls._parts)]]))
    known |= {parameter.name for parameter in extra}
    # Python-only parameters the wrapper keeps out of the block (`_python_params`); only `dims` exists so far.
    extra += [inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=getattr(cls, "_DEFAULT_DIMENSION", None),
                                annotation=Optional[int])
              for name in getattr(cls, "_python_params", ()) if name not in known]
    return inspect.Signature(named + extra)


def unexpected_keyword(cls: type, names: Any, signature: Optional[inspect.Signature] = None, label: Optional[str] = None) -> TypeError:
    """The `TypeError` for keywords `cls` (or its factory `label`, with its `signature`) does not take: names the feature,
    suggests the closest valid parameter, lists them all."""
    valid = list((signature or getattr(cls, "__signature__", inspect.Signature())).parameters)
    messages = []
    for name in names:
        close = difflib.get_close_matches(name, valid, n=1)
        messages.append(f"'{name}'" + (f" (did you mean '{close[0]}'?)" if close else ""))
    return TypeError(f"{label or cls.__name__}() got unexpected keyword argument(s) {', '.join(messages)}; "
                     f"valid parameters: {', '.join(valid)}")


# What a required parameter means, for the error that names it.
_REQUIRED_HINTS = {"window": "the number of samples in each analysis window"}


def missing_arguments(cls: type, signature: inspect.Signature, args: Any, kwargs: Any) -> Optional[TypeError]:
    """The `TypeError` for the required parameters a call to `cls` leaves out, naming the public class and saying what
    `window` is (instead of Python's message about an internal `__init__`); `None` when nothing is missing."""
    try:
        given = signature.bind_partial(*args, **kwargs).arguments
    except TypeError:
        return None  # a wrong call: the constructor reports it
    missing = [name for name, parameter in signature.parameters.items() if parameter.default is parameter.empty
               and name not in given and parameter.kind not in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)]
    if not missing:
        return None
    return TypeError(f"{cls.__name__}() missing required argument(s): "
                     + ", ".join(f"{name} ({_REQUIRED_HINTS[name]})" if name in _REQUIRED_HINTS else name for name in missing))


class _InputModeFactory:
    """The constructor `cls.from_<kind>(...)`, built on each access for the class it is read from, so a subclass shows and
    checks its own parameters."""

    def __init__(self, stub: Any, value: str, parameter: str):
        functools.update_wrapper(self, stub)
        self.stub, self.value, self.parameter = stub, value, parameter

    def __get__(self, instance: Any, cls: Optional[type] = None) -> Any:
        cls = type(instance) if cls is None else cls
        signature = inspect.Signature([entry for entry in inspect.signature(cls).parameters.values() if entry.name != self.parameter])

        @functools.wraps(self.stub)
        def factory(*args: Any, **kwargs: Any) -> Any:
            if unknown := [name for name in kwargs if name not in signature.parameters]:
                raise unexpected_keyword(cls, unknown, signature, f"{cls.__name__}.{self.stub.__name__}")
            return cls(*args, **{self.parameter: self.value}, **kwargs)
        factory.__signature__ = signature
        return factory


def input_mode_factory(value: str, parameter: str = "input_mode") -> Any:
    """Turns a stub (its docstring is the documentation) into the constructor `cls.from_<kind>(...)` that builds
    `cls(input_mode=value, ...)`. Its signature is the constructor's of the class it is read from, without `input_mode`."""
    return lambda stub: _InputModeFactory(stub, value, parameter)
