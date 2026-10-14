"""Edge cases of Recorder: empty recordings, validated metadata, whole-schema comparison, flat-column cache."""

import numpy as np
import pytest

from pyeyesweb.data_models import Output, Recorder, Schema, Status
from pyeyesweb.data_models.base import OutputsMixin


class Dummy(OutputsMixin):
    def __init__(self, *outputs):
        self._outputs = outputs

    def _schema(self):
        return Schema(*self._outputs)


SCHEMA = Schema(Output("a"), Output("v", components=("x", "y")))


def columns(count):
    return {"a": np.arange(count, dtype=float), "v": np.zeros((count, 2))}


def test_from_arrays_with_no_rows_accepts_append():
    rec = Recorder.from_arrays(SCHEMA, columns(0))
    assert len(rec) == 0
    feature = Dummy(*SCHEMA)
    rec.append(feature.result(a=1.0, v=[1, 2]))
    rec.append(feature.result(a=2.0, v=[3, 4]))
    assert len(rec) == 2 and rec["a"].tolist() == [1.0, 2.0]


def test_from_arrays_checks_t_and_status():
    with pytest.raises(ValueError, match="one entry per row"):
        Recorder.from_arrays(SCHEMA, columns(3), timestamps=[0.0, 1.0])
    with pytest.raises(ValueError, match="one entry per row"):
        Recorder.from_arrays(SCHEMA, columns(3), status=[0, 0])
    rec = Recorder.from_arrays(SCHEMA, columns(3), timestamps=[0.0, 1.0, 2.0], status=[0, 1, 0])
    assert rec.status.tolist() == [0, 1, 0] and rec.timestamps.tolist() == [0.0, 1.0, 2.0]
    assert Recorder.from_arrays(SCHEMA, columns(3), status=Status.WARMING_UP).status.tolist() == [1, 1, 1]


def test_append_compares_shapes_and_kinds():
    rec = Recorder(Dummy(Output("a")))
    with pytest.raises(ValueError, match="create a new Recorder"):
        rec.append(Dummy(Output("a", 3)).result(a=[1, 2, 3]))
    with pytest.raises(ValueError, match="create a new Recorder"):
        rec.append(Dummy(Output("a", kind=int)).result(a=1))
    rec.append(Dummy(Output("a")).result(a=1.0))
    assert len(rec) == 1


def test_flat_column_is_built_once_per_length(monkeypatch):
    rec = Recorder(SCHEMA)
    feature = Dummy(*SCHEMA)
    for index in range(3):
        rec.append(feature.result(a=float(index), v=[index, -index]))
    calls = []
    original = Recorder.to_numpy
    monkeypatch.setattr(Recorder, "to_numpy", lambda self: calls.append(1) or original(self))
    assert rec["v_x"].tolist() == [0, 1, 2] and rec["v_y"].tolist() == [0, -1, -2] and rec["a"].tolist() == [0, 1, 2]
    assert len(calls) == 1
    rec.append(feature.result(a=3.0, v=[3, -3]))
    assert rec["v_x"].tolist() == [0, 1, 2, 3]
    assert len(calls) == 2
