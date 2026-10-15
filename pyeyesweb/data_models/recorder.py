"""Column-oriented storage of results, for offline analysis and logging.

Appending thousands of :class:`~pyeyesweb.data_models.Result` objects to a list and converting them afterwards is slow
and awkward. A :class:`Recorder` knows the schema, so it keeps one preallocated, growable NumPy column per output and
hands back arrays or a DataFrame.
"""

from typing import Any, Callable, Dict, Iterable, List, Union

import numpy as np

from .base import _coerce
from .results import Result, Schema, Status

__all__ = ["Recorder"]

_DTYPES = {float: np.float64, int: np.int64, bool: np.bool_}


def _signature(schema: Schema) -> tuple:
    """What a recorder needs of a schema to store its results: names, shapes, kinds."""
    return tuple((output.name, output.shape, output.kind, output.labelled) for output in schema)


class Recorder:
    """Records a stream of results as columns, one row per call.

    A recorder is what ``Feature.run`` returns, and can be filled by hand with :meth:`append`. It stores, per row, the
    values of every output, the status, the reason, the timestamp (seconds) and the per-output validity.

    Parameters
    ----------
    source : Schema or feature
        What is being recorded: a schema, or any object with an ``outputs`` schema (a feature).
    capacity : int, optional
        Initial number of rows (default 1024); the columns double when full.

    Attributes
    ----------
    schema : Schema
        The schema of the recorded outputs.
    status : numpy.ndarray of int
        Status code of each row (the values of :class:`Status`), shape ``(n,)``.
    ok : numpy.ndarray of bool
        Mask of the rows whose status is ``OK``.
    timestamps : numpy.ndarray of float
        Timestamp of each row in seconds, ``NaN`` where unknown, shape ``(n,)``.
    valid : dict of str to numpy.ndarray
        Per output, a boolean ``(n,)`` array: whether the output was produced in each row.

    Notes
    -----
    ``len(rec)`` is the number of rows. ``rec["speed"]`` and ``rec.speed`` are the column of an output (an array of
    shape ``(n,) + shape`` for a fixed output, a list for a variable-size or image output); ``rec["position_x"]``
    is one flat column of shape ``(n,)``. ``rec[3]`` and ``rec[-1]`` are single rows as a :class:`Result` (``IndexError``
    out of range); ``rec[2:5]`` is a *list* of results.

    Only the fixed outputs enter :meth:`to_numpy` and :meth:`to_frame`; an image or labelled output stays in
    :meth:`column`. There is no ``Recorder.to_array`` (that name belongs to ``Result.to_array``).

    Examples
    --------
    >>> from pyeyesweb.data_models import Output, Recorder, Schema
    >>> schema = Schema(Output("speed", unit="m/s"), Output("direction", components=("x", "y")))
    >>> make = schema.result_type("DemoResult")
    >>> rec = Recorder(schema)
    >>> for index in range(3):
    ...     rec.append(make(schema, {"speed": 1.0 + index, "direction": [0.6, 0.8]}, timestamp=0.01 * index))
    >>> len(rec), rec.speed.tolist(), rec["direction"].shape, rec["direction_y"].tolist()
    (3, [1.0, 2.0, 3.0], (3, 2), [0.8, 0.8, 0.8])
    >>> rec[-1].speed, len(rec[0:2]), bool(rec.ok.all()), rec.timestamps.tolist()
    (3.0, 2, True, [0.0, 0.01, 0.02])
    >>> rec.to_numpy().shape, list(rec.to_frame().columns)
    ((3, 3), ['status', 'timestamp', 'speed', 'direction_x', 'direction_y'])
    """

    def __init__(self, source: Union[Schema, Any], capacity: int = 1024):
        self.schema: Schema = source if isinstance(source, Schema) else source.outputs
        self._feature = None if isinstance(source, Schema) else type(source).__name__
        self._signature = _signature(self.schema)
        self._flat_cache = None
        self._n = 0
        self._capacity = max(int(capacity), 1)
        self._columns: Dict[str, np.ndarray] = {}
        self._lists: Dict[str, List[Any]] = {}
        for output in self.schema:
            if output.fixed:
                self._columns[output.name] = np.empty((self._capacity,) + tuple(output.shape),
                                                      dtype=_DTYPES[output.kind])
            else:
                self._lists[output.name] = []
        self._status = np.empty(self._capacity, dtype=np.int8)
        self._timestamps = np.empty(self._capacity, dtype=np.float64)
        self._valid = np.empty((self._capacity, len(self.schema)), dtype=np.bool_)
        self._reasons: List[str] = []

    @classmethod
    def from_arrays(cls, source: Union[Schema, Any], columns: Dict[str, Any], timestamps: Any = None,
                    status: Any = None) -> "Recorder":
        """A recorder filled in one go from whole-recording arrays (the result of a batch ``run``).

        Parameters
        ----------
        source : Schema or feature
            As for the constructor.
        columns : dict of str to array-like
            Every output name mapped to an array of shape ``(n,) + shape``; outputs of variable size are not
            supported (``ValueError``).
        timestamps : array-like, optional
            Timestamps in seconds, one per row; ``NaN`` for every row when omitted.
        status : int or array-like, optional
            A status code per row, or one for all rows; ``Status.OK`` when omitted. Every output counts as produced.
        """
        rec = cls(source, capacity=1)
        names = [output.name for output in rec.schema]
        if rec._lists or set(columns) != set(names):
            raise ValueError(f"columns must be exactly the fixed outputs {names}")
        row_count = len(np.asarray(columns[names[0]]))
        for name in names:
            array = np.asarray(columns[name], dtype=rec._columns[name].dtype)
            if array.shape != (row_count,) + rec._columns[name].shape[1:]:
                raise ValueError(f"column {name!r} has shape {array.shape}, expected {(row_count,) + rec._columns[name].shape[1:]}")
            rec._columns[name] = array
        status = np.asarray(0 if status is None else status)
        timestamps = np.full(row_count, np.nan) if timestamps is None else np.array(timestamps, dtype=np.float64)
        if status.shape not in ((), (row_count,)) or timestamps.shape != (row_count,):
            raise ValueError(f"timestamps and status must have one entry per row ({row_count}), got timestamps {timestamps.shape} and status {status.shape}")
        rec._capacity = rec._n = row_count
        rec._status = np.broadcast_to(status, (row_count,)).astype(np.int8)
        rec._timestamps = timestamps
        rec._valid = np.ones((row_count, len(names)), dtype=np.bool_)
        rec._reasons = [""] * row_count
        return rec

    def __len__(self) -> int:
        return self._n

    def __repr__(self) -> str:
        counts = np.bincount(self.status, minlength=len(Status))
        status = {Status(code).name: int(count) for code, count in enumerate(counts) if count}
        return f"Recorder({self._feature or 'schema'}, rows={self._n}, columns={list(self.schema.names)}, status={status})"

    def append(self, result: Result) -> None:
        """Add one result. It must come from a feature with the same schema (``ValueError`` otherwise)."""
        if result.schema is not self.schema and _signature(result.schema) != self._signature:
            raise ValueError("result does not match the recorder's schema: the feature's outputs changed since this "
                             "Recorder was created: create a new Recorder")
        if self._n == self._capacity:
            self._grow()
        row = self._n
        values = result._values
        for name, column in self._columns.items():
            column[row] = values[name]
        for name, items in self._lists.items():
            items.append(values[name])
        self._status[row] = result.status
        self._timestamps[row] = result.timestamp
        self._reasons.append(result.reason)
        missing = result._missing
        self._valid[row] = [name not in missing for name in self.schema.names]
        self._n += 1

    def extend(self, results: Iterable[Result]) -> None:
        """Add every result of an iterable."""
        for result in results:
            self.append(result)

    def run(self, process: Callable[[Any], Result], inputs: Iterable[Any]) -> "Recorder":
        """Call ``process(x)`` for each input and record the results. Returns the recorder."""
        for item in inputs:
            self.append(process(item))
        return self

    def _grow(self) -> None:
        self._capacity = max(self._capacity * 2, 1)
        for name, column in self._columns.items():
            grown = np.empty((self._capacity,) + column.shape[1:], dtype=column.dtype)
            grown[:self._n] = column[:self._n]
            self._columns[name] = grown
        for attr in ("_status", "_timestamps", "_valid"):
            old = getattr(self, attr)
            grown = np.empty((self._capacity,) + old.shape[1:], dtype=old.dtype)
            grown[:self._n] = old[:self._n]
            setattr(self, attr, grown)

    # -- access
    @property
    def status(self) -> np.ndarray:
        """Status code of each row (:class:`Status` values), shape ``(n,)``."""
        return self._status[:self._n]

    @property
    def ok(self) -> np.ndarray:
        """Boolean mask of the rows whose status is ``OK``."""
        return self._status[:self._n] == Status.OK

    @property
    def timestamps(self) -> np.ndarray:
        """Timestamp of each row in seconds (``NaN`` where unknown), shape ``(n,)``."""
        return self._timestamps[:self._n]

    @property
    def valid(self) -> Dict[str, np.ndarray]:
        """Per output, a boolean ``(n,)`` array: whether the output was produced in each row."""
        return {name: self._valid[:self._n, index] for index, name in enumerate(self.schema.names)}

    def column(self, name: str) -> Union[np.ndarray, List[Any]]:
        """All recorded values of an output: an array ``(n,) + shape`` for a fixed output, a list otherwise."""
        if name in self._columns:
            return self._columns[name][:self._n]
        return self._lists[name]

    def __getitem__(self, key: Union[str, int, slice]) -> Any:
        """``rec["speed"]`` is ``column("speed")``; ``rec["position_x"]`` is one flat column, shape ``(n,)``; ``rec[3]``
        is row 3 as a :class:`Result` (negative counts from the end, ``IndexError`` out of range); ``rec[2:5]`` is a
        list of results."""
        if isinstance(key, slice):
            return [self._row(row) for row in range(*key.indices(self._n))]
        if isinstance(key, (int, np.integer)):
            if not -self._n <= key < self._n:
                raise IndexError(f"row {key} out of range for a recorder of {self._n} rows")
            return self._row(int(key) % self._n)
        if key in self.schema:
            return self.column(key)
        index = self.schema.flat_index[key]
        if self._flat_cache is None or len(self._flat_cache) != self._n:
            self._flat_cache = self.to_numpy()
        return self._flat_cache[:, index]

    def _row(self, row: int) -> Result:
        """Row ``row`` as the ``Result`` that was appended."""
        values = {output.name: _coerce(output, self.column(output.name)[row]) for output in self.schema}
        missing = frozenset(name for name, valid in zip(self.schema.names, self._valid[row]) if not valid)
        result_type = self.schema.result_type((self._feature or "") + "Result")
        return result_type(self.schema, values, Status(int(self._status[row])), self._reasons[row], float(self._timestamps[row]),
                           missing)

    def __getattr__(self, name: str) -> Union[np.ndarray, List[Any]]:
        """``rec.speed`` is ``rec["speed"]`` (an output or a flat name)."""
        if not name.startswith("_") and "schema" in self.__dict__ and (
                name in self.schema or name in self.schema.flat_index):
            return self[name]
        raise AttributeError(f"{type(self).__name__} has no attribute {name!r}")

    def __dir__(self) -> List[str]:
        return sorted(set(super().__dir__()) | set(self.schema.names))

    def to_numpy(self) -> np.ndarray:
        """The fixed outputs as a float64 matrix ``(n, schema.size)``, columns in ``schema.flat_names`` order."""
        parts = [self._columns[output.name][:self._n].reshape(self._n, -1).astype(np.float64)
                 for output in self.schema.fixed_outputs]
        return np.concatenate(parts, axis=1) if parts else np.empty((self._n, 0))

    def to_frame(self, meta: bool = True):
        """A pandas DataFrame: one column per flat name, plus ``status`` and ``timestamp`` when ``meta``.

        Parameters
        ----------
        meta : bool, optional
            Add the columns ``status`` (the :class:`Status` names, ``"OK"``, ``"WARMING_UP"``, ...: ``frame.status ==
            "OK"`` selects the rows that produced output) and ``timestamp`` (seconds), in front. Default ``True``.

        Raises
        ------
        ImportError
            If pandas is not installed.
        """
        import pandas as pd  # optional dependency

        frame = pd.DataFrame(self.to_numpy(), columns=list(self.schema.flat_names))
        if meta:
            frame.insert(0, "timestamp", self.timestamps)
            frame.insert(0, "status", [Status(code).name for code in self.status])
        return frame
