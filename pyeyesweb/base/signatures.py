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
import typing
from typing import Any, Literal, Optional, Union

import numpy as np

_PLACEHOLDER = re.compile(r"\\(\d+)")  # nanobind writes a default as "\0", "\1"... and ships the values apart
_CORE_TYPE = re.compile(r"eyesweb_core\.([\w.]+)")


def _choice(core: Any, path: str) -> Any:
    """The annotation of a core type: an enum becomes `Literal[names]`, anything else is kept."""
    target = core
    for part in path.split("."):
        target = getattr(target, part, None)
    if hasattr(target, "__members__"):
        return Literal[tuple(name.lower() for name in target.__members__)]
    return target if target is not None else Any


def _nb_parameters(core: Any, core_class: Any) -> list:
    """The constructor parameters of `core_class` as keyword-only `inspect.Parameter`s (empty when the binding has none)."""
    signatures = getattr(core_class.__init__, "__nb_signature__", ())
    if not signatures:
        return []
    text, defaults = signatures[0][0], (signatures[0][2] if len(signatures[0]) > 2 else None) or ()
    text = re.sub(r"ndarray\[[^\]]*\]", "np.ndarray", _PLACEHOLDER.sub(r"__default_\1", text))
    tree = ast.parse(text.replace("def __init__", "def f") + ":\n pass")
    scope = {"collections": collections, "np": np, "Union": Union, "Any": Any, "_choice": lambda parameter: _choice(core, parameter)}
    values = {f"__default_{index}": value for index, value in enumerate(defaults)}
    arguments = tree.body[0].args
    defaulted = dict(zip((argument.arg for argument in arguments.args[len(arguments.args) - len(arguments.defaults):]), arguments.defaults))
    parameters = []
    for arg in arguments.args[1:]:  # skip self
        annotation = Any
        if arg.annotation is not None:
            source = ast.unparse(arg.annotation)
            source = _CORE_TYPE.sub(lambda match: f'_choice("{match.group(1)}")', source)
            try:
                annotation = eval(source, scope)
            except Exception:
                annotation = Any
            if typing.get_origin(annotation) is collections.abc.Sequence and typing.get_origin(typing.get_args(annotation)[0]) is Literal:
                annotation = Union[typing.get_args(annotation)[0], annotation]  # one choice, or several
        default = inspect.Parameter.empty
        if arg.arg in defaulted:
            node = defaulted[arg.arg]
            default = values.get(node.id, Any) if isinstance(node, ast.Name) else ast.literal_eval(node)
            if isinstance(default, enum.Enum):
                default = default.name.lower()
            elif isinstance(default, list) and default and all(isinstance(item, enum.Enum) for item in default):
                names = [item.name.lower() for item in default]
                default = names[0] if len(names) == 1 else names
        parameters.append(inspect.Parameter(arg.arg, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=annotation))
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
    extra = [parameter for parameter in _nb_parameters(core, cls._core_class)
             if parameter.name not in known and parameter.name not in getattr(cls, "_hidden_params", ())]
    if getattr(cls, "_timed", False):  # time is `timestamp` or `sampling_rate` (Hz, int or float), never a mode
        extra = [parameter for parameter in extra if parameter.name != "sampling_rate"]
        extra.append(inspect.Parameter("sampling_rate", inspect.Parameter.KEYWORD_ONLY, default=None,
                                       annotation=Optional[float]))
    if getattr(cls, "_unit_params", None):  # lengths in metres (EyesWeb) or data in millimetres
        extra.append(inspect.Parameter("units", inspect.Parameter.KEYWORD_ONLY, default="m",
                                       annotation=Literal["m", "mm"]))
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


def input_mode_factory(value: str, parameter: str = "input_mode") -> Any:
    """Turns a stub (its docstring is the documentation) into the classmethod constructor `cls.from_<kind>(...)` that builds
    `cls(input_mode=value, ...)`. Its signature is the constructor's without `input_mode` (see `factory_signature`)."""
    def decorate(stub: Any) -> classmethod:
        @functools.wraps(stub)
        def factory(cls: type, *args: Any, **kwargs: Any) -> Any:
            signature = inspect.signature(getattr(cls, stub.__name__))
            if unknown := [name for name in kwargs if name not in signature.parameters]:
                raise unexpected_keyword(cls, unknown, signature, f"{cls.__name__}.{stub.__name__}")
            return cls(*args, **{parameter: value}, **kwargs)
        factory._input_mode_parameter = parameter
        return classmethod(factory)
    return decorate


def factory_signature(signature: inspect.Signature, parameter: str) -> inspect.Signature:
    """The signature of a `from_*` function (with its `cls`): the constructor's `signature` without `parameter`."""
    return inspect.Signature([inspect.Parameter("cls", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                              *(entry for entry in signature.parameters.values() if entry.name != parameter)])
