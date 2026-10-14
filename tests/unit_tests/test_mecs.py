"""Output contract of EventSynchronizationMECS (EyesWeb MECS Algorithm v2); the numerics are tested in C++."""
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb.analysis_primitives.synchronization import EventSynchronizationMECS  # noqa: E402
from pyeyesweb.data_models.results import Result, Schema, Status  # noqa: E402


def check(block, result, size):
    assert isinstance(block.outputs, Schema) and isinstance(result, Result)
    assert result.status == Status.OK
    assert block.outputs.names == ("synchronization", "events")
    assert block.outputs["synchronization"].shape == (size,) and block.outputs["events"].shape == (size,)
    assert result.synchronization.shape == (size,) and result.events.shape == (size,)
    assert np.issubdtype(result.synchronization.dtype, np.floating)


@pytest.mark.parametrize("classes", [3, 2])
def test_one_output_per_event_class(classes):
    block = EventSynchronizationMECS(window=4, event_class_number=classes)
    series = np.zeros((classes, 4))
    series[0, 0] = 1
    check(block, block._process_window(series, series), classes)


def test_there_is_no_version_selector_and_no_set_mode():
    for name in ("version", "mode", "event_sets", "sequence_time"):
        with pytest.raises(TypeError):
            EventSynchronizationMECS(window=4, **{name: 1})
