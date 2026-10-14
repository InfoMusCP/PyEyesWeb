"""Output contract of every PyEyesWeb feature: declared outputs, a status, fixed-layout results.

A feature **declares its outputs once** as a [Schema][pyeyesweb.data_models.results.Schema] (what it returns,
with which shape, component names and unit), available as `feature.outputs` as soon as the feature is built.
Each call returns a [Result][pyeyesweb.data_models.results.Result]: the same fields on every call, a
[Status][pyeyesweb.data_models.results.Status] saying whether the call produced output, and a per-output
validity mask. Missing values are `NaN` (or `0` / `False` for integer / boolean outputs), never `None`.

The schema drives everything else: flat column names (`schema.flat_names`), `result.to_array()` (one fixed
vector per call, e.g. one CHOP sample), `result.to_dict()` / `to_flat_dict()`, and the
[Recorder][pyeyesweb.data_models.recorder.Recorder] for offline analysis.
"""

import enum
import math
import types
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

__all__ = ["Status", "Output", "Schema", "Result"]

_NAN = float("nan")
_EMPTY: Mapping = types.MappingProxyType({})  # shared empty value of a labelled output

Shape = Tuple[Optional[int], ...]


class Status(enum.IntEnum):
    """Why a call produced (or did not produce) output. `IntEnum`: usable directly as a numeric column."""

    OK = 0
    """The call produced output."""
    WARMING_UP = 1
    """The window or internal state is still filling. Some outputs may already be valid (see `Result.valid`)."""
    NO_OUTPUT = 2
    """The feature emits only on some calls (event or phase change) and this was not one of them."""
    INVALID_INPUT = 3
    """The input cannot be processed (empty, too short, degenerate); `Result.reason` says why."""

    def __str__(self) -> str:
        return self.name


class Output:
    """Declaration of one output of a feature.

    Parameters
    ----------
    name : str
        Python identifier; the attribute name on results and the base of the flat names.
    shape : int or tuple of (int or None), optional
        Shape of the value; `()` for a scalar (default). `None` for a dimension whose size depends on the input.
        Inferred from `labels` and `components` when omitted.
    kind : {float, int, bool}, optional
        Element type. Missing values are `NaN` for `float`, `0` for `int`, `False` for `bool`.
    components : sequence of str, optional
        Names of the entries along the last axis, e.g. `("x", "y", "z")`.
    labels : sequence of str, optional
        Names of the entries along the first axis, e.g. joint names.
    unit : str, optional
        Unit of the values, for documentation, in terms of the data: `"<length>"` stands for the length unit of the data,
        `"<input>"` for the unit of the input; a feature with `units=` writes the unit it was given (`"mm/s"`). Empty when
        the value is dimensionless.
    doc : str, optional
        One-line description.
    labelled : bool, optional
        The value is a dict `label -> array(shape)` whose labels are only known at run time (a skeleton).
    """

    __slots__ = ("name", "shape", "kind", "axis_names", "unit", "doc", "labelled")

    def __init__(self, name: str, shape: Union[int, Shape, None] = None, *, kind: type = float,
                 components: Optional[Sequence[str]] = None, labels: Optional[Sequence[str]] = None,
                 unit: str = "", doc: str = "", labelled: bool = False):
        if not name.isidentifier():
            raise ValueError(f"output name {name!r} is not a valid identifier")
        if kind not in (float, int, bool):
            raise ValueError(f"output {name!r}: kind must be float, int or bool")
        if shape is None:
            shape = tuple(len(dimension) for dimension in (labels, components) if dimension is not None)
        elif isinstance(shape, int):
            shape = (shape,)
        shape = tuple(shape)
        if (labels is not None and not shape) or (components is not None and not shape):
            raise ValueError(f"output {name!r}: labels / components need an array shape")
        names: List[Optional[Tuple[str, ...]]] = [None] * len(shape)
        if labels is not None:
            names[0] = tuple(labels)
        if components is not None:
            names[-1] = tuple(components)
        for axis, (size, axis_names) in enumerate(zip(shape, names)):
            if axis_names is not None and size is not None and len(axis_names) != size:
                raise ValueError(f"output {name!r}: axis {axis} has {size} entries but {len(axis_names)} names")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "axis_names", tuple(names))
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "doc", doc)
        object.__setattr__(self, "labelled", labelled)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Output is immutable")

    @property
    def fixed(self) -> bool:
        """Whether the shape is known before any data is seen (no `None` size, not labelled at run time)."""
        return not self.labelled and all(size is not None for size in self.shape)

    @property
    def size(self) -> int:
        """Number of scalar entries of a fixed output."""
        if not self.fixed:
            raise ValueError(f"output {self.name!r} has a data-dependent size")
        return int(math.prod(self.shape))

    @property
    def flat_names(self) -> Tuple[str, ...]:
        """Names of the scalar entries of a fixed output, C order: `name`, `name_x`, `name_<label>_<component>`."""
        if not self.fixed:
            raise ValueError(f"output {self.name!r} has a data-dependent size")
        return tuple(_flat_names(self.name, self.shape, self.axis_names))

    def _empty(self) -> Any:
        """The value of this output when it was not produced (shared, read-only)."""
        if self.labelled:
            return _EMPTY
        if not self.shape:
            return _NAN if self.kind is float else self.kind()
        dtype = {float: np.float64, int: np.int64, bool: np.bool_}[self.kind]
        array = np.full(tuple(0 if extent is None else extent for extent in self.shape), _NAN if self.kind is float else 0,
                        dtype=dtype)
        array.flags.writeable = False
        return array

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly description."""
        return {"name": self.name, "shape": list(self.shape), "kind": self.kind.__name__,
                "axis_names": [list(names) if names else None for names in self.axis_names], "unit": self.unit, "doc": self.doc,
                "labelled": self.labelled}

    def __repr__(self) -> str:
        parts = [repr(self.name)]
        if self.shape:
            parts.append("shape=" + repr(self.shape))
        if self.kind is not float:
            parts.append(f"kind={self.kind.__name__}")
        if self.labelled:
            parts.append("labelled=True")
        if self.unit:
            parts.append(f"unit={self.unit!r}")
        return f"Output({', '.join(parts)})"


def _flat_names(prefix: str, shape: Shape, axis_names: Sequence[Optional[Tuple[str, ...]]]) -> Iterator[str]:
    if not shape:
        yield prefix
        return
    names = axis_names[0] or [str(index) for index in range(shape[0])]
    for sub in names:
        yield from _flat_names(f"{prefix}_{sub}", shape[1:], axis_names[1:])


class Schema:
    """The ordered outputs of a feature. Known before the feature is run; fixed for the life of the feature.

    Examples
    --------
    >>> s = Schema(Output("centroid", components=("x", "y", "z")), Output("density"))
    >>> s.flat_names
    ('centroid_x', 'centroid_y', 'centroid_z', 'density')
    """

    def __init__(self, *outputs: Output):
        names = [output.name for output in outputs]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate output names in {names}")
        self._outputs: Tuple[Output, ...] = tuple(outputs)
        self._by_name = {output.name: output for output in outputs}
        self._empty_cache: Optional[Dict[str, Any]] = None
        self._flat: Optional[Tuple[str, ...]] = None
        self._flat_index: Optional[Dict[str, int]] = None
        self._layout: Optional[Tuple[Tuple[str, int, int, bool], ...]] = None
        self._types: Dict[str, type] = {}

    # -- container protocol
    def __iter__(self) -> Iterator[Output]:
        return iter(self._outputs)

    def __len__(self) -> int:
        return len(self._outputs)

    def __getitem__(self, name: str) -> Output:
        return self._by_name[name]

    def __contains__(self, name: object) -> bool:
        return name in self._by_name

    def select(self, names: Iterable[str]) -> "Schema":
        """A schema with only the outputs called `names`, in declaration order (a catalogue narrowed to a choice)."""
        wanted = set(names)
        unknown = wanted - set(self._by_name)
        if unknown:
            raise KeyError(f"unknown outputs {sorted(unknown)}; available: {list(self._by_name)}")
        return Schema(*(output for output in self._outputs if output.name in wanted))

    @property
    def names(self) -> Tuple[str, ...]:
        """Output names, in declaration order."""
        return tuple(self._by_name)

    @property
    def fixed_outputs(self) -> Tuple[Output, ...]:
        """The outputs whose shape is known in advance; they make up `flat_names` / `to_array()`."""
        return tuple(output for output in self._outputs if output.fixed)

    @property
    def variable_outputs(self) -> Tuple[Output, ...]:
        """The outputs whose size depends on the data (variable-length or labelled at run time)."""
        return tuple(output for output in self._outputs if not output.fixed)

    @property
    def flat_names(self) -> Tuple[str, ...]:
        """Names of the scalar columns of the fixed outputs, in `to_array()` order."""
        if self._flat is None:
            self._flat = tuple(name for output in self.fixed_outputs for name in output.flat_names)
        return self._flat

    @property
    def size(self) -> int:
        """Length of `to_array()`."""
        return len(self.flat_names)

    @property
    def flat_index(self) -> Dict[str, int]:
        """Position of each flat name in `to_array()`."""
        if self._flat_index is None:
            self._flat_index = {name: index for index, name in enumerate(self.flat_names)}
        return self._flat_index

    @property
    def layout(self) -> Tuple[Tuple[str, int, int, bool], ...]:
        """`(output name, offset, size, is_scalar)` of each fixed output in `to_array()`."""
        if self._layout is None:
            offset, rows = 0, []
            for output in self.fixed_outputs:
                rows.append((output.name, offset, output.size, not output.shape))
                offset += output.size
            self._layout = tuple(rows)
        return self._layout

    @property
    def is_fixed(self) -> bool:
        """Whether every output has a fixed shape (a complete, constant flat layout)."""
        return not self.variable_outputs

    def empty_values(self) -> Dict[str, Any]:
        """The value of every output when nothing was produced. Shared: do not modify."""
        if self._empty_cache is None:
            self._empty_cache = {output.name: output._empty() for output in self._outputs}
        return self._empty_cache

    def describe(self) -> str:
        """A readable table of the outputs."""
        rows = [("output", "shape", "type", "unit", "description")]
        for output in self._outputs:
            shape = "dict[label] of " + str(output.shape) if output.labelled else str(tuple("N" if extent is None else extent for extent in output.shape))
            rows.append((output.name, shape, output.kind.__name__, output.unit, output.doc))
        widths = [max(len(row[column]) for row in rows) for column in range(5)]
        return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)

    def to_dict(self) -> Dict[str, Any]:
        """JSON-friendly description of the schema."""
        return {"outputs": [output.to_dict() for output in self._outputs], "flat_names": list(self.flat_names)}

    def result_type(self, name: str = "Result") -> type:
        """The `Result` subclass for this schema (one read-only attribute per output); created once per name."""
        if name not in self._types:
            namespace = {"__slots__": ()}
            for output_name in self._by_name:
                namespace[output_name] = property(lambda self, key=output_name: self._values[key])
            self._types[name] = type(name, (Result,), namespace)
        return self._types[name]

    def __repr__(self) -> str:
        return "Schema(" + ", ".join(repr(output) for output in self._outputs) + ")"


class Result:
    """What a feature returns: the values of its declared outputs for one call.

    Attributes
    ----------
    status : Status
        Whether this call produced output, and if not, why.
    reason : str
        Short explanation when `status` is not `OK`.
    timestamp : float
        Timestamp of the input (seconds or ticks, as supplied by the feature); `NaN` when unknown.
    valid : dict of str to bool
        Per-output flag: `False` where an output was not produced this call (its value is the empty value).

    The outputs are read-only attributes named as in `schema` (`result.kinetic_energy`) and also available
    as `result["kinetic_energy"]`. `result["centroid_x"]` reads one scalar by its flat name.
    Results are immutable; array values are read-only.
    """

    __slots__ = ("_schema", "_values", "status", "reason", "timestamp", "_missing")

    def __init__(self, schema: Schema, values: Dict[str, Any], status: Status = Status.OK, reason: str = "",
                 timestamp: float = _NAN, missing: frozenset = frozenset()):
        object.__setattr__(self, "_schema", schema)
        object.__setattr__(self, "_values", values)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "_missing", missing)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{type(self).__name__} is immutable")

    @property
    def schema(self) -> Schema:
        """The schema of the feature that produced this result."""
        return self._schema

    @property
    def ok(self) -> bool:
        """`status is Status.OK`."""
        return self.status is Status.OK

    @property
    def is_valid(self) -> bool:
        """Alias of `ok`, kept for the 1.x API."""
        return self.status is Status.OK

    @property
    def valid(self) -> Dict[str, bool]:
        """Per-output validity: whether each output was produced by this call."""
        return {name: name not in self._missing for name in self._schema.names}

    def with_time(self, timestamp: Optional[float]) -> "Result":
        """A copy with timestamp `timestamp` in seconds (`NaN` when `timestamp` is `None`)."""
        return type(self)(self._schema, self._values, self.status, self.reason, math.nan if timestamp is None else timestamp,
                          self._missing)

    # -- export
    def to_dict(self) -> Dict[str, Any]:
        """`output name -> value`: floats / ints / bools, NumPy arrays, or dicts of arrays. Same keys every call."""
        return dict(self._values)

    def to_array(self) -> np.ndarray:
        """The fixed outputs as one float64 vector, in `schema.flat_names` order; missing values are `NaN`.

        Variable-size outputs are not included (use `to_dict()` or `to_flat_dict()`).
        """
        out = np.empty(self._schema.size)
        values = self._values
        for name, offset, size, scalar in self._schema.layout:
            if scalar:
                out[offset] = values[name]
            else:
                out[offset:offset + size] = values[name].ravel()
        return out

    def to_flat_dict(self, prefix: str = "", meta: bool = True) -> Dict[str, Any]:
        """One scalar per key, ready for a log row or one channel per value.

        The keys of fixed outputs are those of `schema.flat_names`, identical on every call. Variable-size outputs
        are expanded by the sizes and labels they have in this result. `meta` adds `status` (its integer code)
        and `timestamp`.
        """
        flat: Dict[str, Any] = {}
        if meta:
            flat[_join(prefix, "status")] = int(self.status)
            flat[_join(prefix, "timestamp")] = self.timestamp
        for output in self._schema:
            _flatten(_join(prefix, output.name), self._values[output.name], output, flat)
        return flat

    def __getitem__(self, key: str) -> Any:
        if key in self._values:
            return self._values[key]
        index = self._schema.flat_index.get(key)
        if index is None:
            raise KeyError(key)
        return float(self.to_array()[index])

    def __iter__(self) -> Iterator[str]:
        return iter(self._schema.names)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Result) or self.status != other.status or self._schema.names != other._schema.names:
            return False
        return all(_same(self._values[name], other._values[name]) for name in self._schema.names)

    __hash__ = None  # type: ignore[assignment]

    def __dir__(self) -> List[str]:
        return sorted(set(super().__dir__()) | set(self._schema.names))

    def __repr__(self) -> str:
        shown = ", ".join(f"{name}={_short(self._values[name])}" for name in self._schema.names)
        reason = f", reason={self.reason!r}" if self.reason else ""
        return f"{type(self).__name__}(status={self.status.name}{reason}, {shown})"


def _join(prefix: str, key: str) -> str:
    return f"{prefix}_{key}" if prefix else key


def _fit_names(shape: Sequence[int], axis_names: Sequence[Optional[Tuple[str, ...]]]) -> List[Optional[Tuple[str, ...]]]:
    """Axis names applied to an actual shape: the first `size` names of an axis whose declared names are enough
    (`("x", "y", "z", "w")` on an axis of 3 gives x, y, z), indices otherwise."""
    return [names[:size] if names is not None and size <= len(names) else None
            for size, names in zip(shape, axis_names)]


def _flatten(key: str, value: Any, output: Output, out: Dict[str, Any]) -> None:
    if output.labelled:
        for label, item in value.items():
            shape = np.shape(item)
            for suffix, element in zip(_flat_names("", shape, _fit_names(shape, output.axis_names)), np.ravel(item)):
                out[f"{key}_{label}{suffix}"] = float(element)
        return
    if not output.shape:
        out[key] = value
        return
    array = np.asarray(value)
    for name, element in zip(_flat_names(key, array.shape, _fit_names(array.shape, output.axis_names)), array.ravel()):
        out[name] = element.item()


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, dict):
        return isinstance(right, dict) and left.keys() == right.keys() and all(_same(left[key], right[key]) for key in left)
    try:
        return bool(np.array_equal(left, right, equal_nan=True))
    except TypeError:
        return bool(np.array_equal(left, right))


def _short(value: Any) -> str:
    if isinstance(value, np.ndarray):
        return np.array2string(value, precision=4, threshold=6, edgeitems=2, separator=", ", suppress_small=True)
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key!r}: {_short(item)}" for key, item in list(value.items())[:3]) + (", ..." if len(value) > 3 else "") + "}"
    return repr(value)
