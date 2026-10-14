"""Reusable checks of live parameter changes (see `EyesWebCore/CONVENTIONS.md`, "Changing parameters at run time").

A case is `(factory, attr, value, recording)`: `factory()` builds a feature, `attr = value` is the change, `recording` is a
list of what `process` receives, one item per call. Each area keeps its own table in `tests/unit_tests/test_live_parameters_<area>.py`:

    @pytest.mark.parametrize("factory, attr, value, recording", LIVE, ids=ids(LIVE))
    def test_live(factory, attr, value, recording):
        check_live(factory, attr, value, recording)
"""

import pytest

CHANGE_AT = 60  # the sample at which the parameter changes
NOTE = "parameters changed: state reset"


def ids(rows):
    return [f"{row[1]}-{index}" for index, row in enumerate(rows)]


def feed(feature, items):
    return [feature.process(*(item if isinstance(item, tuple) else (item,))) for item in items]


def check_live(factory, attr, value, recording, change_at=CHANGE_AT):
    """A LIVE parameter does not enter the state: changing it at sample k gives, from k on, what a feature built with the
    new value from the start gives, and the status sequence of an unchanged control; the state is not reset."""
    control, changed, fresh = factory(), factory(), factory()
    setattr(fresh, attr, value)
    feed(changed, recording[:change_at])
    setattr(changed, attr, value)
    expected = feed(control, recording)[change_at:]
    actual = feed(changed, recording[change_at:])
    assert [result.status for result in actual] == [result.status for result in expected]
    assert all(NOTE not in result.reason for result in actual)
    assert actual == feed(fresh, recording)[change_at:]


def check_structural(factory, attr, value, recording, change_at=CHANGE_AT):
    """A STRUCTURAL parameter (read by the original in Init()): the state restarts and the next result says so, once."""
    feature = factory()
    feed(feature, recording[:change_at])
    setattr(feature, attr, value)
    after = feed(feature, recording[change_at:])
    assert NOTE in after[0].reason
    assert all(NOTE not in result.reason for result in after[1:])


def check_invalid(factory, attr, value, recording, change_at=CHANGE_AT):
    """A value the core rejects raises at the setter, and the feature goes on as if nothing had happened."""
    feature, control = factory(), factory()
    feed(feature, recording[:change_at])
    feed(control, recording[:change_at])
    old = getattr(feature, attr)
    with pytest.raises(ValueError):
        setattr(feature, attr, value)
    assert getattr(feature, attr) == old
    assert feed(feature, recording[change_at:]) == feed(control, recording[change_at:])
