"""Readability rule: no one-character identifier in the package (`_` alone, an unused value, is allowed).

Checked with the AST: function and lambda arguments, assigned names, loop and comprehension targets, `except ... as`
names and import aliases. Attribute names and keyword names of calls are not identifiers of the package and are not scanned.
"""
import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "pyeyesweb"


def _short(name):
    return len(name.lstrip("_")) <= 1 and name != "_"


def _identifiers(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            yield node.arg, node.lineno, "argument"
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id, node.lineno, "variable"
        elif isinstance(node, ast.ExceptHandler) and node.name:
            yield node.name, node.lineno, "except name"
        elif isinstance(node, ast.alias) and node.asname:
            yield node.asname, getattr(node, "lineno", 0), "import alias"


def test_no_one_character_identifier_in_the_package():
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf8"), filename=str(path))
        offenders += [f"{path.relative_to(PACKAGE.parent).as_posix()}:{line}: {kind} `{name}`"
                      for name, line, kind in _identifiers(tree) if _short(name)]
    assert not offenders, "one-character identifiers (use a descriptive name):\n" + "\n".join(offenders)


def test_no_one_character_public_parameter_of_a_feature_or_of_the_core():
    """The same rule for what a user types: constructor parameters of the catalog features and every nanobind argument."""
    import inspect
    import types

    import pytest

    pytest.importorskip("pyeyesweb._core")
    from pyeyesweb import catalog
    from pyeyesweb._core import core
    from pyeyesweb.base.core_feature import _SIGNATURE_PARAM

    offenders = [f"{info.cls.__name__}({name})" for info in catalog() for name in inspect.signature(info.cls).parameters
                 if _short(name)]

    def walk(owner, path, seen):
        for attribute, member in vars(owner).items():
            if attribute.startswith("__") and attribute != "__init__":
                continue
            where = f"{path}.{attribute}"
            for signature in getattr(member, "__nb_signature__", ()):
                offenders.extend(f"{where}({name})" for name in _SIGNATURE_PARAM.findall(signature[0]) if _short(name))
            if isinstance(member, (type, types.ModuleType)) and id(member) not in seen:
                seen.add(id(member))
                walk(member, where, seen)

    walk(core, "core", set())
    assert not offenders, "one-character public parameters (use a descriptive name):\n" + "\n".join(sorted(set(offenders)))
