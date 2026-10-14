"""The output contract shared by every feature: [OutputsMixin][pyeyesweb.data_models.base.OutputsMixin] gives
`feature.outputs` and `feature.result(...)`. The call contract is in `feature.py`."""

import math
from typing import Any, ClassVar, Optional

import numpy as np

from .results import Output, Result, Schema, Status

_DTYPES = {float: np.float64, int: np.int64, bool: np.bool_}
_NO_MISSING: frozenset = frozenset()


def _coerce(output: Output, value: Any) -> Any:
    """Convert `value` to the declared type of `output`; raise `ValueError` on a shape mismatch."""
    if output.labelled:
        items = {}
        for label, item in value.items():
            array = np.array(item, dtype=_DTYPES[output.kind])
            _check_shape(output, array, label)
            array.flags.writeable = False
            items[str(label)] = array
        return items
    if not output.shape:
        return output.kind(value)
    array = np.array(value, dtype=_DTYPES[output.kind])  # copy: results never alias feature state
    _check_shape(output, array)
    array.flags.writeable = False
    return array


def _check_shape(output: Output, array: np.ndarray, label: Optional[str] = None) -> None:
    ok = array.ndim == len(output.shape) and all(expected is None or expected == actual for expected, actual in zip(output.shape, array.shape))
    if not ok:
        where = f"{output.name}[{label!r}]" if label is not None else output.name
        raise ValueError(f"output {where}: expected shape {output.shape}, got {array.shape}")


class OutputsMixin:
    """The output contract shared by every feature.

    A feature declares its outputs once, either as the class attribute `OUTPUTS` (when they do not depend on the
    parameters) or by overriding `_schema()` (when they do, e.g. a number of joints or a global/per-axis mode).
    It then builds every return value with `self.result(...)`:

        class Speed(Feature):
            OUTPUTS = Schema(Output("speed", unit="m/s"))

            def process(self, frame, *, timestamp=None):
                return self.result(speed=float(np.linalg.norm(frame)), timestamp=timestamp)

    `feature.outputs` is the [Schema][pyeyesweb.data_models.results.Schema], available before any data is seen.
    """

    OUTPUTS: ClassVar[Optional[Schema]] = None

    def _schema(self) -> Schema:
        """Build the outputs of this instance. Override when they depend on the parameters."""
        if self.OUTPUTS is None:
            raise NotImplementedError(f"{type(self).__name__} must define OUTPUTS or override _schema()")
        return self.OUTPUTS

    @property
    def outputs(self) -> Schema:
        """The declared outputs: names, shapes, component names, units. Fixed for the life of the feature."""
        schema = self.__dict__.get("_outputs_cache")
        if schema is None:
            schema = self.__dict__["_outputs_cache"] = self._schema()
        return schema

    def _outputs_changed(self) -> None:
        """Call after changing a parameter that the schema or the inputs depend on."""
        self.__dict__.pop("_outputs_cache", None)
        self.__dict__.pop("_inputs_cache", None)
        self.__dict__.pop("_result_type", None)

    def result(self, *, status: Status = Status.OK, reason: str = "", timestamp: Optional[float] = None,
               **values: Any) -> Result:
        """Build a result.

        Parameters
        ----------
        status : Status, optional
            `Status.OK` (default) when the call produced output.
        reason : str, optional
            Short explanation when `status` is not `OK`.
        timestamp : float, optional
            Timestamp of the input in seconds; `NaN` in the result when not given.
        **values
            The outputs produced by this call, by name. An output that is omitted (or `None`) counts as not
            produced: it holds the empty value (`NaN`, `0` or `False`) and `result.valid[name]` is `False`.

        Raises
        ------
        KeyError
            For a name that is not a declared output.
        ValueError
            For a value whose shape does not match the declaration.
        """
        schema = self.outputs
        result_type = self.__dict__.get("_result_type")
        if result_type is None:
            result_type = self.__dict__["_result_type"] = schema.result_type(type(self).__name__ + "Result")
        data = dict(schema.empty_values())
        produced = 0
        for name, value in values.items():
            output = schema[name]  # KeyError for an undeclared output
            if value is not None:
                data[name] = _coerce(output, value)
                produced += 1
        missing = _NO_MISSING if produced == len(data) else frozenset(
            key for key in data if values.get(key) is None)
        return result_type(schema, data, status, reason, math.nan if timestamp is None else timestamp, missing)

    def no_output(self, status: Status = Status.NO_OUTPUT, reason: str = "", timestamp: Optional[float] = None) -> Result:
        """A result in which no output was produced."""
        return self.result(status=status, reason=reason, timestamp=timestamp)
