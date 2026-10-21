"""Base classes of the features that wrap a block of the compiled core."""

import functools
import inspect
import re
from contextlib import contextmanager
from numbers import Real
from abc import ABCMeta
from enum import Enum
from typing import Any, ClassVar, Literal, Optional, Tuple

from pyeyesweb.base.choices import choice_name, coerce_choice, coerce_enum, coerce_enums
from pyeyesweb._core import core
from pyeyesweb.base.signatures import _nb_parameters, core_signature, missing_arguments, unexpected_keyword
from pyeyesweb.data_models.feature import Feature
from pyeyesweb.data_models.results import Result

# Component names of 2D / 3D point outputs.
XYZ = ("x", "y", "z")
XY = ("x", "y")

# Names owned by the output contract; never forwarded to the C++ block.
_CONTRACT_NAMES = frozenset({"inputs", "outputs"})

# Factor of one metre in the data unit, for the `units` argument of the features with unit-sensitive parameters.
_UNIT_FACTORS = {"m": 1.0, "mm": 1000.0}

# Said by every result that has no time to derive from.
_PER_SAMPLE_NOTE = "no time given: per-sample derivatives"

# Said by the next result after a parameter change that made the block forget its state.
_STATE_RESET_NOTE = "parameters changed: state reset"

# Numeric parameters whose negative (or zero) values are meaningless, by name: a parameter of one of these names means
# the same in every feature, and the core validates only what EyesWeb validated (often only for the active mode).
# Checked whenever parameters are set, in the constructor and live. The parameters that take any sign by design
# (`x_min`, `gaussian_correlation`, `noise_threshold`...) are listed with the reason in `tests/unit_tests/test_live_validation_all_features.py`.
_POSITIVE_PARAMS = frozenset({
    "sampling_rate", "upper_limit", "window", "gaussian_sigma_x", "gaussian_sigma_y", "log_scale", "custom_distance",
    "time_constant", "gesture_duration", "number_of_points", "best_periods", "order", "low_frequency", "high_frequency"})
_NON_NEGATIVE_PARAMS = frozenset({
    "damping", "viscosity", "damping_factor", "viscosity_factor", "step_adaptation_factor", "seed", "arm_percentage",
    "legs_search", "legs_offset", "arms_min_threshold", "arms_max_threshold", "movement_threshold", "velocity_threshold",
    "standard_deviation_threshold", "y_weight", "epsilon", "minimum_distance", "direction_change_epsilon",
    "firing_threshold", "amplitude", "custom_amplitude", "max_value", "threshold", "inter_event_time", "max_steps"})

# A parameter name in a nanobind signature, e.g. "(self, name: type = ...".
_SIGNATURE_PARAM = re.compile(r"[(,]\s*(\w+)\s*:")

# A parameter annotated with a core type in a nanobind signature: "name: [container[]eyesweb_core.path.Type".
_SIGNATURE_CORE_TYPE = re.compile(r"[(,]\s*(\w+)\s*:\s*([\w.]+\[)?eyesweb_core\.([\w.]+)")

# An identifier of the core in a message: a word that has a capital inside (camelCase) or is a block name listed in `_core_names`.
_IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*\b")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _translating(method):
    """`method` (a `process` of a feature) with the names of the core in the errors it raises turned into public names."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._public_errors():
            return method(self, *args, **kwargs)

    return wrapper


class _SealedMeta(ABCMeta):
    """Marks an instance as sealed once its constructor returns: from then on only parameters can be assigned."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if (signature := cls.__dict__.get("__signature__")) is not None and not any(
                parameter.kind is parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
            if unknown := [name for name in kwargs if name not in signature.parameters]:
                raise unexpected_keyword(cls, unknown)
            if "_variants" not in cls.__dict__ and (error := missing_arguments(cls, signature, args, kwargs)):
                raise error
        instance = super().__call__(*args, **kwargs)
        instance.__dict__["_sealed"] = True
        return instance


def check_range(name: str, value: Any) -> None:
    """Raise `ValueError` for a number that is meaningless for the parameter `name` (see `_POSITIVE_PARAMS`); anything that
    is not a number (None, a choice, a sequence) is left to the core."""
    if isinstance(value, Real) and not isinstance(value, bool):
        if name in _POSITIVE_PARAMS and not value > 0:
            raise ValueError(f"{name} must be positive, got {value!r}")
        if name in _NON_NEGATIVE_PARAMS and not value >= 0:
            raise ValueError(f"{name} must not be negative, got {value!r}")


def require_rate(owner: str, rate: Optional[float]) -> None:
    """Raise `ValueError` for a feature that has no time axis of its own and so cannot go without `sampling_rate`."""
    if rate is None:
        raise ValueError(f"{owner} needs sampling_rate (Hz): the window it works on carries no time of its own")


def _choice_name(value: Any) -> Any:
    """An enum member as its lower-case name, anything else unchanged."""
    return choice_name(value) if isinstance(value, Enum) else value


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
    docs/howto/realtime_live_parameters.md); then the next result carries "parameters changed: state reset" in its `reason`.

    `process` is not pure: blocks keep state between calls (previous frames, filter histories, counters), so
    results depend on the call sequence.

    Time. A feature with `_timed = True` has derivatives or a time step and takes one rule: the timestamps `timestamp` /
    `timestamps` (seconds) when given, else `sampling_rate` (Hz), else per-sample derivatives (every result then says so in
    its `reason`). The wrapper turns that into the time step in seconds the block takes (`_time_step`): the difference
    of two timestamps; `1 / sampling_rate` or 1 s when there is no previous timestamp (the first call, or after a
    call without timestamp); a timestamp that does not increase is `INVALID_INPUT` ("non-increasing timestamp") and
    changes nothing.

    Units. A feature with `_unit_params = {name: power}` takes `units="m"` (default, the EyesWeb numbers) or `"mm"`:
    the listed parameters are written in metres (as EyesWeb does) and multiplied by `1000 ** power` for data in
    millimetres (power 1 for a length or a speed, 2 for an area or an energy). Data and outputs are never rescaled.

    `_core_names` maps the public name of a parameter to its name in the block, where the library spells out an abbreviation
    of the core (`{"gesture_duration": "ges_dur"}`); everything public (signature, setters, `_params`) uses the public name.
    `_hidden_params` names block parameters the wrapper does not show: it keeps them at the block's default and takes a
    parameter of its own instead (`joint_map` for the joint names of the humanoid). A feature whose parameters can be changed by a property setter calls `_set_param(name, value)`. A feature that sets its parameters after `CoreFeature.__init__` runs declares
    `_lazy_block = True`, so nothing is built until first use. A block that is not just `_core_class(**params)`
    overrides `_build_block()`.
    """

    _core_class: ClassVar[Any] = None
    _lazy_block: ClassVar[bool] = False
    _timed: ClassVar[bool] = False
    _rate_required: ClassVar[bool] = False  # a feature on windows, with no time step: it takes `sampling_rate` or raises
    _unit_params: ClassVar[dict] = {}
    _hidden_params: ClassVar[frozenset] = frozenset()  # block parameters the wrapper replaces by a parameter of its own
    _core_names: ClassVar[dict] = {}  # public parameter name -> name in the block, for the names the library spells out
    _parts: ClassVar[dict] = {}  # `parts=` choices -> the bool parameter of the block that switches each one on

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """A feature backed by a block shows the parameters of its constructor: `inspect.signature(cls)` merges the
        Python parameters of its `__init__` with those of the block, read from the nanobind signature."""
        super().__init_subclass__(**kwargs)
        if cls._parts:
            cls._hidden_params = cls._hidden_params | frozenset(cls._parts.values())
        if cls._core_class is not None:
            cls.__signature__ = core_signature(cls, core)
        for name in ("process", "_process_window"):  # an error of the block names the parameters as the user does
            method = cls.__dict__.get(name)
            if callable(method) and not getattr(method, "__isabstractmethod__", False):
                setattr(cls, name, _translating(method))

    def __init__(self, **params: Any):
        if self._unit_params:
            params.setdefault("units", "m")
        if self._timed:
            params.setdefault("sampling_rate", None)
        if self._parts:
            params.setdefault("parts", type(self).__signature__.parameters["parts"].default)
        self._params = self._coerce_choices(params)
        self._built = None
        self._state_lost_pending = False
        self._previous_t = None
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
        if "parts" in out:  # the chosen parts switch on their block parameters, the others off
            chosen = out.pop("parts")
            out.update({flag: part in chosen for part, flag in self._parts.items()})
        factor = _UNIT_FACTORS[params.get("units", "m")]
        if factor != 1.0:
            defaults = self._unit_defaults()
            for name, power in self._unit_params.items():
                value = out.get(name, defaults.get(name))  # a default is a length in metres too
                if value is not None:
                    out[name] = _scaled(value, factor ** power)
        return {self._core_names.get(name, name): value for name, value in out.items()}

    @classmethod
    def _public_names(cls) -> dict:
        """Block parameter name -> public name (the inverse of `_core_names`)."""
        return {name: public for public, name in cls._core_names.items()}

    @classmethod
    def _unit_defaults(cls) -> dict:
        """The block's defaults of the unit-sensitive parameters that are plain numbers, read once per class."""
        found = cls.__dict__.get("_unit_defaults_cache")
        if found is None:
            found = {parameter.name: parameter.default for parameter in _nb_parameters(core, cls._core_class, cls._public_names())
                     if parameter.name in cls._unit_params and isinstance(parameter.default, (int, float, list, tuple))}
            cls._unit_defaults_cache = found
        return found

    def _time_step(self, timestamp: Optional[float]) -> float:
        """The time step in seconds of this call: the difference of the timestamp `timestamp` to the previous one, else
        `1 / sampling_rate`, else 1 (per sample). With no previous timestamp (the first call, a call after one without
        timestamp, after `reset()`) the step is `1 / sampling_rate` or 1: an absolute time is not a step. A timestamp
        that does not increase never gets here (`_input_problem`)."""
        rate = self._params.get("sampling_rate")
        previous, self._previous_t = self._previous_t, timestamp
        self._untimed = rate is None and (timestamp is None or previous is None)
        if timestamp is None or previous is None:
            return 1.0 if rate is None else 1.0 / rate
        return timestamp - previous

    def _input_problem(self, sample: Any, timestamp: Optional[float]) -> str:
        self._untimed = False  # a rejected call is not a per-sample step: the note of the previous call is stale
        if reason := super()._input_problem(sample, timestamp):
            return reason
        previous = self.__dict__.get("_previous_t")
        return "non-increasing timestamp" if self._timed and timestamp is not None and previous is not None and timestamp <= previous else ""

    @contextmanager
    def _public_errors(self):
        """Inside, an error of the core that names a parameter by its core name (`amplitudeThreshold`, `ges_dur`) is
        re-raised, same type, with its public name (`amplitude_threshold`, `gesture_duration`). Only the identifiers of the
        message that are public parameters of this feature are touched: the reverse of `_core_names`, else camelCase to snake_case."""
        try:
            yield
        except (ValueError, TypeError, RuntimeError) as error:
            if error.args and isinstance(error.args[0], str):
                shown = inspect.signature(type(self)).parameters
                renamed = self._public_names()

                def public(match: "re.Match") -> str:
                    word = match.group()
                    snake = _CAMEL_BOUNDARY.sub("_", word).lower()
                    name = renamed.get(word) or renamed.get(snake) or snake  # the core says `nInputs` for `n_inputs`
                    return name if name in shown and name != word else word

                error.args = (_IDENTIFIER.sub(public, error.args[0]),) + error.args[1:]
            raise

    @property
    def _block(self) -> Any:
        """The C++ block, built on first use from the current parameters."""
        if self._built is None:
            self.__dict__["_building"] = True
            try:
                with self._public_errors():
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
            with self._public_errors():
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
        self._previous_t = None

    def _result(self, *, reason: str = "", **values: Any) -> Result:
        if self.__dict__.get("_untimed"):
            reason = f"{reason}; {_PER_SAMPLE_NOTE}" if reason else _PER_SAMPLE_NOTE
        if self._state_lost_pending:
            self._state_lost_pending = False
            reason = f"{_STATE_RESET_NOTE}; {reason}" if reason else _STATE_RESET_NOTE
        return super()._result(reason=reason, **values)

    @classmethod
    def _core_params(cls) -> frozenset:
        """Names of the constructor parameters of `_core_class`, read once per class from its nanobind signature."""
        names = cls.__dict__.get("_core_params_cache")
        if names is None:
            signatures = getattr(cls._core_class.__init__, "__nb_signature__", ())
            names = frozenset(cls._public_names().get(name, name) for signature in signatures
                              for name in _SIGNATURE_PARAM.findall(signature[0])) - cls._hidden_params
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
                        enums[cls._public_names().get(name, name)] = (target, bool(container))
            cls._core_enums_cache = enums
        return enums

    @classmethod
    def _default_parts(cls) -> tuple:
        """The parts whose block parameter is on by default, in declaration order."""
        defaults = {parameter.name: parameter.default for parameter in _nb_parameters(core, cls._core_class, cls._public_names())}
        return tuple(part for part, flag in cls._parts.items() if defaults[flag])

    @classmethod
    def _core_bools(cls) -> frozenset:
        """Names of the `bool` parameters of `_core_class`, read once per class."""
        names = cls.__dict__.get("_core_bools_cache")
        if names is None:
            names = frozenset(parameter.name for parameter in _nb_parameters(core, cls._core_class, cls._public_names())
                              if parameter.annotation is bool)
            cls._core_bools_cache = names
        return names

    @classmethod
    def _coerce_choices(cls, params: dict) -> dict:
        """`params` with the choices given as strings turned into enum members (a list of them where the block takes
        one; a single choice stays single); a `bool` parameter must be a bool."""
        out = dict(params)
        if cls._rate_required:
            require_rate(cls.__name__, out.get("sampling_rate", 0))
        for name, value in out.items():
            check_range(name, value)
        if out.get("units", "m") not in _UNIT_FACTORS:
            raise ValueError(f"units must be one of {sorted(_UNIT_FACTORS)}, got {out['units']!r}")
        for name in cls._core_bools().intersection(out):
            if not isinstance(out[name], bool):
                raise TypeError(f"{name} must be True or False, got {out[name]!r}")
        if "parts" in out:
            chosen = [out["parts"]] if isinstance(out["parts"], str) else out["parts"]
            chosen = {coerce_choice(part, cls._parts, "parts") for part in chosen}
            out["parts"] = tuple(part for part in cls._parts if part in chosen)
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
        """Forget the state accumulated since construction. A reset is not a parameter change: no note follows it."""
        self._previous_t = None
        self._state_lost_pending = False
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
        shown = inspect.signature(type(self)).parameters.get(name)
        if name in self._core_params() and shown is not None and shown.default is not shown.empty:
            return shown.default  # a parameter left at its default reads back as that default
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
            for _, source in sorted(public._variants.items(), key=lambda entry: entry[0] != default):  # the default's first
                for parameter in source.__signature__.parameters.values():
                    merged.setdefault(parameter.name, parameter)
            shared = set.intersection(*(set(source.__signature__.parameters) for source in public._variants.values()))
            merged = [parameter if parameter.name in shared else parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY)
                      for parameter in merged.values()]  # a parameter of only some of the methods is never positional
            public.__signature__ = inspect.Signature(sorted(merged, key=lambda entry: entry.kind))

    def __new__(cls, *args: Any, **params: Any):
        if "_variants" in cls.__dict__:
            keyword, default = cls._SWITCH
            choice = params.get(keyword, default)
            cls = cls._variants[coerce_choice(f"v{choice}" if type(choice) is int else choice, cls._variants, keyword)]
            if foreign := [name for name in params if name not in cls.__signature__.parameters]:
                raise TypeError(f"{keyword}={cls._variant!r} does not take {', '.join(foreign)}")
        return super().__new__(cls)
