"""Column-oriented storage of results, for offline analysis and logging.

Appending thousands of [Result][pyeyesweb.data_models.results.Result] objects to a list and converting them
afterwards is slow and awkward. A [Recorder][pyeyesweb.data_models.recorder.Recorder] knows the schema, so it
keeps one preallocated, growable NumPy column per output and hands back arrays or a DataFrame.
"""

from typing import Any, Callable, Dict, Iterable, List, Union

import numpy as np

from .results import Result, Schema, Status

__all__ = ["Recorder"]

_DTYPES = {float: np.float64, int: np.int64, bool: np.bool_}


def _signature(schema: Schema) -> tuple:
    """What a recorder needs of a schema to store its results: names, shapes, kinds."""
    return tuple((output.name, output.shape, output.kind, output.labelled) for output in schema)


class Recorder:
    """Records a stream of results as columns.

    Parameters
    ----------
    source : Schema or feature
        What is being recorded: a schema, or any object with an `outputs` schema (a feature).
    capacity : int, optional
        Initial number of rows; the columns double when full.

    Examples
    --------
    >>> rec = Recorder(feature)
    >>> for frame in frames:
    ...     rec.append(feature.process(frame))
    >>> rec.column("centroid").shape          # (n_frames, 3)
    >>> rec.to_frame()                        # pandas DataFrame, one column per flat name
    """

    def __init__(self, source: Union[Schema, Any], capacity: int = 1024):
        self.schema: Schema = source if isinstance(source, Schema) else source.outputs
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

    @classmethod
    def from_arrays(cls, source: Union[Schema, Any], columns: Dict[str, Any], timestamps: Any = None,
                    status: Any = None) -> "Recorder":
        """A recorder filled in one go from whole-recording arrays (the result of a batch `run`).

        `columns` maps every output name to an array `(n,) + shape`; outputs of variable size are not supported.
        `timestamps` (seconds) defaults to NaN and `status` to `Status.OK` for every row; every output counts as produced.
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
        return rec

    def __len__(self) -> int:
        return self._n

    def append(self, result: Result) -> None:
        """Add one result. It must come from a feature with the same schema."""
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
        missing = result._missing
        self._valid[row] = [name not in missing for name in self.schema.names]
        self._n += 1

    def extend(self, results: Iterable[Result]) -> None:
        """Add every result of an iterable."""
        for result in results:
            self.append(result)

    def run(self, process: Callable[[Any], Result], inputs: Iterable[Any]) -> "Recorder":
        """Call `process(x)` for each input and record the results. Returns the recorder."""
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
        """Status code of each row (`Status` values), shape `(n,)`."""
        return self._status[:self._n]

    @property
    def ok(self) -> np.ndarray:
        """Boolean mask of the rows whose status is `OK`."""
        return self._status[:self._n] == Status.OK

    @property
    def timestamps(self) -> np.ndarray:
        """Timestamp of each row (`NaN` where unknown), shape `(n,)`."""
        return self._timestamps[:self._n]

    @property
    def valid(self) -> Dict[str, np.ndarray]:
        """Per output, a boolean `(n,)` array: whether the output was produced in each row."""
        return {name: self._valid[:self._n, index] for index, name in enumerate(self.schema.names)}

    def column(self, name: str) -> Union[np.ndarray, List[Any]]:
        """All recorded values of an output: an array `(n,) + shape` for a fixed output, a list otherwise."""
        if name in self._columns:
            return self._columns[name][:self._n]
        return self._lists[name]

    def __getitem__(self, key: str) -> Union[np.ndarray, List[Any]]:
        """`rec["centroid"]` is `column("centroid")`; `rec["centroid_x"]` is one flat column, shape `(n,)`."""
        if key in self.schema:
            return self.column(key)
        index = self.schema.flat_index[key]
        if self._flat_cache is None or len(self._flat_cache) != self._n:
            self._flat_cache = self.to_numpy()
        return self._flat_cache[:, index]

    def to_numpy(self) -> np.ndarray:
        """The fixed outputs as a float64 matrix `(n, schema.size)`, columns in `schema.flat_names` order."""
        parts = [self._columns[output.name][:self._n].reshape(self._n, -1).astype(np.float64)
                 for output in self.schema.fixed_outputs]
        return np.concatenate(parts, axis=1) if parts else np.empty((self._n, 0))

    def to_frame(self, meta: bool = True):
        """A pandas DataFrame: one column per flat name, plus `status` and `timestamp` when `meta`.

        `status` holds the integer `Status` codes, as in `Result.to_flat_dict()`, so `frame.status == Status.OK`
        selects the rows that produced output.

        Raises `ImportError` if pandas is not installed.
        """
        import pandas as pd  # optional dependency

        frame = pd.DataFrame(self.to_numpy(), columns=list(self.schema.flat_names))
        if meta:
            frame.insert(0, "timestamp", self.timestamps)
            frame.insert(0, "status", self.status.astype(int))
        return frame
