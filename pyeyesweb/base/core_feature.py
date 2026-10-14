"""Base classes of the features that wrap a block of the compiled core."""

import inspect
import math
import re
from abc import ABCMeta
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Tuple

from pyeyesweb.base.choices import coerce_choice, coerce_enum, coerce_enums
from pyeyesweb._core import core
from pyeyesweb.base.signatures import _nb_parameters, core_signature, factory_signature, unexpected_keyword
from pyeyesweb.data_models.feature import Feature
from pyeyesweb.data_models.results import Result

# Component names of 2D / 3D point outputs.
XYZ = ("x", "y", "z")
XY = ("x", "y")

# Names owned by the output contract; never forwarded to the C++ block.
_CONTRACT_NAMES = frozenset({"inputs", "outputs", "result", "no_output"})

# Factor of one metre in the data unit, for the `units` argument of the features with unit-sensitive parameters.
_UNIT_FACTORS = {"m": 1.0, "mm": 1000.0}

# Said by every result that has no time to derive from.
_PER_SAMPLE_NOTE = "no time given: per-sample derivatives"

# Said by the next result after a parameter change that made the block forget its state.
_STATE_RESET_NOTE = "parameters changed: state reset"

# A parameter name in a nanobind signature, e.g. "(self, name: type = ...".
_SIGNATURE_PARAM = re.compile(r"[(,]\s*(\w+)\s*:")

# A parameter annotated with a core type in a nanobind signature: "name: [container[]eyesweb_core.path.Type".
_SIGNATURE_CORE_TYPE = re.compile(r"[(,]\s*(\w+)\s*:\s*([\w.]+\[)?eyesweb_core\.([\w.]+)")


class _SealedMeta(ABCMeta):
    """Marks an instance as sealed once its constructor returns: from then on only parameters can be assigned."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if (signature := cls.__dict__.get("__signature__")) is not None and not any(
                parameter.kind is parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
            if unknown := [name for name in kwargs if name not in signature.parameters]:
                raise unexpected_keyword(cls, unknown)
        instance = super().__call__(*args, **kwargs)
        instance.__dict__["_sealed"] = True
        return instance


def _choice_name(value: Any) -> Any:
    """An enum member as its lower-case name, anything else unchanged."""
    return value.name.lower() if isinstance(value, Enum) else value


def _scaled(value: Any, factor: float) -> Any:
    """A number, or each number of a sequence, times `factor`."""
    return tuple(item * factor for item in value) if isinstance(value, (list, tuple)) else value * factor


class CoreFeature(Feature, metaclass=_SealedMeta):
    """A feature that wraps one block of the compiled core (a port of an EyesWeb block or a PyEyesWeb analysis).

    Its outputs follow the PyEyesWeb result contract. Each subclass names its block in `_core_class`:

    * the constructor takes the block's parameters as keyword arguments (see the subclass); they are kept in
      `_params`;
    * `outputs` is the [Schema][pyeyesweb.data_models.results.Schema] of the block, known from the constructor
      parameters alone (e.g. `Symmetry` has a scalar or a 3-vector output depending on `output_type`);
    * `process(...)` runs the block once and returns a [Result][pyeyesweb.data_models.results.Result] whose
      `status` is `OK` when the call produced output, `WARMING_UP` while a window fills, `NO_OUTPUT` when the block
      only emits on some activations and `INVALID_INPUT` for an unusable input; `valid` tells which outputs were
      produced;
    * `reset()` restores the state the block has after construction (nothing to do for stateless blocks);
    * any other attribute of the C++ block (properties, presets, helpers) is available unchanged.

    Changing a parameter keeps the state of the block unless the parameter is structural (see
    `CONVENTIONS.md` of the core); then the next result carries "parameters changed: state reset" in its `reason`.

    `process` is not pure: blocks keep state between calls (previous frames, filter histories, counters), so
    results depend on the call sequence.

    Time. A feature with `_timed = True` has derivatives or a time step and takes one rule: the timestamps `timestamp` /
    `timestamps` (seconds) when given, else `sampling_rate` (Hz), else per-sample derivatives (every result then says so in
    its `reason`). The wrapper turns that into the time step in seconds the block takes (`_time_step`).

    Units. A feature with `_unit_params = {name: power}` takes `units="m"` (default, the EyesWeb numbers) or `"mm"`:
    the listed parameters are written in metres (as EyesWeb does) and multiplied by `1000 ** power` for data in
    millimetres (power 1 for a length or a speed, 2 for an area or an energy). Data and outputs are never rescaled.

    `_hidden_params` names block parameters the wrapper does not show: it keeps them at the block's default and takes a
    parameter of its own instead (`joint_map` for the joint names of the humanoid). A feature whose parameters can be changed by a property setter calls `_set_param(name, value)`. A feature that sets its parameters after `CoreFeature.__init__` runs declares
    `_lazy_block = True`, so nothing is built until first use. A block that is not just `_core_class(**params)`
    overrides `_build_block()`.
    """

    _core_class: ClassVar[Any] = None
    _lazy_block: ClassVar[bool] = False
    _timed: ClassVar[bool] = False
    _unit_params: ClassVar[dict] = {}
    _hidden_params: ClassVar[frozenset] = frozenset()  # block parameters the wrapper replaces by a parameter of its own

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """A feature backed by a block shows the parameters of its constructor: `inspect.signature(cls)` merges the
        Python parameters of its `__init__` with those of the block, read from the nanobind signature."""
        super().__init_subclass__(**kwargs)
        if cls._core_class is not None:
            cls.__signature__ = core_signature(cls, core)
            for member in vars(cls).values():  # the `from_*` constructors show the constructor's parameters but one
                if isinstance(member, classmethod) and hasattr(member.__func__, "_input_mode_parameter"):
                    member.__func__.__signature__ = factory_signature(cls.__signature__, member.__func__._input_mode_parameter)

    def __init__(self, **params: Any):
        if self._unit_params:
            params.setdefault("units", "m")
        if self._timed:
            params.setdefault("sampling_rate", None)
        self._params = self._coerce_choices(params)
        self._built = None
        self._state_lost_pending = False
        self._previous_t = 0.0
        if not self._lazy_block:
            self._block

    def _build_block(self, params: Optional[dict] = None) -> Any:
        """A block for `params` (default: the current parameters)."""
        return self._core_class(**self._block_params(self._params if params is None else params))

    def _block_params(self, params: dict) -> dict:
        """`params` as the core takes them: lengths scaled to the data unit, wrapper-only names left out."""
        core_names = self._core_params()  # `sampling_rate` stays here unless the block takes it
        out = {key: item for key, item in params.items()
               if key != "units" and not (key == "sampling_rate" and (item is None or key not in core_names))}
        for name, (_, is_sequence) in self._core_enums().items():  # one choice given where the block takes a list
            if is_sequence and name in out and not isinstance(out[name], list):
                out[name] = [out[name]]
        factor = _UNIT_FACTORS[params.get("units", "m")]
        if factor != 1.0:
            defaults = self._unit_defaults()
            for name, power in self._unit_params.items():
                value = out.get(name, defaults.get(name))  # a default is a length in metres too
                if value is not None:
                    out[name] = _scaled(value, factor ** power)
        return out

    @classmethod
    def _unit_defaults(cls) -> dict:
        """The block's defaults of the unit-sensitive parameters that are plain numbers, read once per class."""
        found = cls.__dict__.get("_unit_defaults_cache")
        if found is None:
            found = {parameter.name: parameter.default for parameter in _nb_parameters(core, cls._core_class)
                     if parameter.name in cls._unit_params and isinstance(parameter.default, (int, float, list, tuple))}
            cls._unit_defaults_cache = found
        return found

    def _time_step(self, timestamp: Optional[float]) -> float:
        """The time step in seconds of this call: the difference of the timestamp `timestamp` to the previous one (the first
        previous is 0; a zero step, e.g. a first timestamp of 0, counts as 1 s instead of dividing by zero), else
        `1 / sampling_rate`, else 1 (per sample)."""
        rate = self._params.get("sampling_rate")
        self._untimed = timestamp is None and rate is None
        if timestamp is None:
            self._previous_t = 0.0
            return 1.0 if rate is None else 1.0 / rate
        if not math.isfinite(timestamp):
            raise ValueError(f"timestamp must be a finite number of seconds, got {timestamp!r}")
        step, self._previous_t = timestamp - self._previous_t, timestamp
        return step or 1.0

    @property
    def _block(self) -> Any:
        """The C++ block, built on first use from the current parameters."""
        if self._built is None:
            self.__dict__["_building"] = True
            try:
                self._built = self._build_block()
            finally:
                self.__dict__["_building"] = False
        return self._built

    def _invalidate_block(self) -> None:
        """Drop the block: it is rebuilt from `_params` the next time it is used."""
        self._built = None

    def _set_param(self, name: str, value: Any) -> None:
        """Change a parameter of the block (its keyword in `_core_class`).

        A built block takes the new parameters over keeping its state (`adopt_params`), and forgets the state only
        for a structural parameter; a block without `adopt_params` is replaced. A value the core rejects raises and
        leaves the feature as it was. A block not built yet just stores the value.
        """
        params = {**self._params, **self._coerce_choices({name: value})}
        if self._built is not None:
            fresh = self._build_block(params)  # validates before anything changes
            adopt = getattr(self._built, "adopt_params", None)
            if adopt is None:
                self._built = fresh
            if adopt is None or adopt(fresh):
                self._state_lost()
        self._params = params
        self._outputs_changed()

    def _state_lost(self) -> None:
        """The block forgot its state: the next result says so."""
        self._state_lost_pending = True
        self._previous_t = 0.0

    def result(self, *, reason: str = "", **values: Any) -> Result:
        if self.__dict__.get("_untimed"):
            reason = f"{reason}; {_PER_SAMPLE_NOTE}" if reason else _PER_SAMPLE_NOTE
        if self._state_lost_pending:
            self._state_lost_pending = False
            reason = f"{_STATE_RESET_NOTE}; {reason}" if reason else _STATE_RESET_NOTE
        return super().result(reason=reason, **values)

    @classmethod
    def _core_params(cls) -> frozenset:
        """Names of the constructor parameters of `_core_class`, read once per class from its nanobind signature."""
        names = cls.__dict__.get("_core_params_cache")
        if names is None:
            signatures = getattr(cls._core_class.__init__, "__nb_signature__", ())
            names = frozenset(name for signature in signatures for name in _SIGNATURE_PARAM.findall(signature[0])) - cls._hidden_params
            cls._core_params_cache = names
        return names

    @classmethod
    def _core_enums(cls) -> dict:
        """The parameters of `_core_class` annotated with a core enum, `name -> (enum type, given as a sequence)`, resolved once per class."""
        enums = cls.__dict__.get("_core_enums_cache")
        if enums is None:
            enums = {}
            for signature in getattr(cls._core_class.__init__, "__nb_signature__", ()):
                for name, container, path in _SIGNATURE_CORE_TYPE.findall(signature[0]):
                    target = core
                    for part in path.split("."):
                        target = getattr(target, part, None)
                    if hasattr(target, "__members__"):
                        enums[name] = (target, bool(container))
            cls._core_enums_cache = enums
        return enums

    @classmethod
    def _core_bools(cls) -> frozenset:
        """Names of the `bool` parameters of `_core_class`, read once per class."""
        names = cls.__dict__.get("_core_bools_cache")
        if names is None:
            names = frozenset(parameter.name for parameter in _nb_parameters(core, cls._core_class) if parameter.annotation is bool)
            cls._core_bools_cache = names
        return names

    @classmethod
    def _coerce_choices(cls, params: dict) -> dict:
        """`params` with the choices given as strings turned into enum members (a list of them where the block takes
        one; a single choice stays single); a `bool` parameter must be a bool."""
        out = dict(params)
        if out.get("units", "m") not in _UNIT_FACTORS:
            raise ValueError(f"units must be one of {sorted(_UNIT_FACTORS)}, got {out['units']!r}")
        for name in cls._core_bools().intersection(out):
            if not isinstance(out[name], bool):
                raise TypeError(f"{name} must be True or False, got {out[name]!r}")
        for name, (enum_cls, is_sequence) in cls._core_enums().items():
            value = out.get(name)
            if value is not None:
                out[name] = coerce_enums(value, enum_cls, name) if is_sequence else coerce_enum(value, enum_cls, name)
        return out

    def _param(self, name: str, default: Any) -> Any:
        """A constructor parameter, or `default` (the C++ default) when it was not given.

        Used by `_schema()` for the parameters that fix the shape of an output; the default is stated once,
        next to the schema, and checked against the core by the unit tests.
        """
        return self._params.get(name, default)

    def reset(self) -> None:
        """Forget the state accumulated since construction."""
        self._previous_t = 0.0
        reset = getattr(self._built, "reset", None)
        if reset is not None:
            reset()

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or "_sealed" not in self.__dict__:
            super().__setattr__(name, value)
        elif name in self.__dict__ or hasattr(type(self), name):
            super().__setattr__(name, value)
            self._outputs_changed()  # the declarations may depend on it (dims, labels...)
        elif name in self._core_params() or name in self._params:
            self._set_param(name, value)
        else:
            raise AttributeError(f"{type(self).__name__} has no parameter '{name}'")

    def __getattr__(self, name: str) -> Any:
        # Only called for attributes not found on the wrapper, or after a property of the wrapper raised
        # AttributeError: running it again shows that error instead of hiding it.
        if hasattr(type(self), name):
            return object.__getattribute__(self, name)
        if name.startswith("_") or name in _CONTRACT_NAMES or self.__dict__.get("_building"):
            raise AttributeError(name)
        params = self.__dict__.get("_params")
        if params and name in params:
            value = params[name]  # a choice reads back as its string
            return [_choice_name(item) for item in value] if isinstance(value, list) else _choice_name(value)
        if hasattr(self._core_class, name):
            return getattr(self._block, name)
        raise AttributeError(f"{type(self).__name__} has no attribute '{name}'")

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


class FrameFeature(CoreFeature):
    """A core block with one input, one frame per call: `process(frame, *, timestamp=None)`.

    The frame goes to the block unchanged; subclasses declare `inputs` and turn the block's raw output into a
    `Result` in `_to_result(raw, timestamp)`. `timestamp` is the timestamp in seconds, `NaN` when not given. The block is stateless
    or keeps its own state (`reset()` restores it).
    """

    def process(self, frame: Any, *, timestamp: Optional[float] = None) -> Result:
        return self._process(frame, timestamp)

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        return self._to_result(self._block.process(frame), timestamp)

    def _to_result(self, raw: Any, timestamp: float) -> Result:
        raise NotImplementedError


class VariantFeature:
    """Mixin of a feature that merges several blocks: the public class is `Feature(..., <keyword>=choice)`, and the
    choice picks a variant, a subclass declared `class V(Feature, variant=<member>)` with its own `_core_class`.

    The public class names the keyword and its default string in `_SWITCH = (keyword, default)` and holds
    `_variants = {}`, keyed by the choices (lower-case strings); a parameter that only another variant takes is a `TypeError` naming the choice. Each
    variant's `__init__` accepts the keyword itself (and ignores it). `inspect.signature(Feature)` is the union of the variants'.
    """

    _SWITCH: ClassVar[Tuple[str, str]]
    _variants: ClassVar[dict]

    def __init_subclass__(cls, variant: Any = None, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if variant is not None:
            cls._variant = variant
            public = next(base for base in cls.__mro__ if "_variants" in base.__dict__)
            public._variants[variant] = cls
            keyword, default = public._SWITCH
            merged = {keyword: inspect.Parameter(keyword, inspect.Parameter.KEYWORD_ONLY, default=default,
                                                 annotation=Literal[tuple(public._variants)])}
            for source in public._variants.values():
                for parameter in source.__signature__.parameters.values():
                    merged.setdefault(parameter.name, parameter)
            public.__signature__ = inspect.Signature(sorted(merged.values(), key=lambda entry: entry.kind))

    def __new__(cls, *args: Any, **params: Any):
        if "_variants" in cls.__dict__:
            keyword, default = cls._SWITCH
            choice = params.get(keyword, default)
            cls = cls._variants[coerce_choice(f"v{choice}" if type(choice) is int else choice, cls._variants, keyword)]
            if foreign := [name for name in params if name not in cls.__signature__.parameters]:
                raise TypeError(f"{keyword}={cls._variant!r} does not take {', '.join(foreign)}")
        return super().__new__(cls)
