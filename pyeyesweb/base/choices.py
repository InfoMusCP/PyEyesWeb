"""Choices given as a string, the way scikit-learn takes `algorithm="points"`."""

from typing import Any, Iterable

# Members of the core's enums that the library spells differently (the core is not touched).
_RENAMED = {"component": "components"}


def choice_name(member: Any) -> str:
    """The lower-case string that names the enum member `member` in the public API."""
    name = member.name.lower()
    return _RENAMED.get(name, name)


def coerce_choice(value: Any, names: Iterable[str], what: str) -> str:
    """`value` as one of the lower-case `names` (case-insensitive; `-` and spaces count as `_`).

    `what` names the parameter in the error, which lists the valid names.
    """
    names = list(names)
    if isinstance(value, str):
        key = value.strip().replace("-", "_").replace(" ", "_").lower()
        if key in names:
            return key
    options = ", ".join(repr(name) for name in names)
    raise ValueError(f"{what}: invalid value {value!r}; choose one of {options}")


def coerce_enums(value: Any, enum_cls: type, what: str) -> Any:
    """`value` as a member of `enum_cls`, or, given a list or tuple, as a list of them (a wrong element raises as `coerce_enum` does)."""
    if isinstance(value, (list, tuple)):
        return [coerce_enum(item, enum_cls, what) for item in value]
    return coerce_enum(value, enum_cls, what)


def coerce_enum(value: Any, enum_cls: type, what: str) -> Any:
    """`value` as a member of `enum_cls`: its name as a string, or a member (which is passed through)."""
    if isinstance(value, enum_cls):
        return value
    members = {choice_name(member): member for member in enum_cls.__members__.values()}
    return members[coerce_choice(value, members, what)]
