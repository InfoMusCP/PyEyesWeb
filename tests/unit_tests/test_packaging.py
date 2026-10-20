"""Metadata of the package (``pyproject.toml``): a pure parse, no build and no network, so it runs everywhere."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # the `test` extra installs it for 3.10

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
PROJECT = PYPROJECT["project"]


def _name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[ ]", requirement, maxsplit=1)[0].lower().replace("_", "-")


def _required_core() -> tuple[int, int]:
    source = (ROOT / "pyeyesweb" / "_core.py").read_text(encoding="utf-8")
    match = re.search(r"^REQUIRED_CORE\s*=\s*\((\d+),\s*(\d+)\)", source, re.MULTILINE)
    assert match, "REQUIRED_CORE not found in pyeyesweb/_core.py"
    return int(match.group(1)), int(match.group(2))


def test_runtime_dependencies_are_numpy_and_the_core_only():
    assert sorted(_name(d) for d in PROJECT["dependencies"]) == ["eyesweb-core", "numpy"]


@pytest.mark.parametrize("forbidden", ["scipy", "scikit-learn", "tqdm", "pandas", "matplotlib", "pooch", "mediapipe", "opencv-python"])
def test_no_forbidden_runtime_dependency(forbidden):
    assert forbidden not in {_name(d) for d in PROJECT["dependencies"]}


def test_version_is_pep440_and_matches_the_core_pin():
    version = PROJECT["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+((a|b|rc)\d+)?", version), version
    assert tuple(int(p) for p in version.split(".")[:2]) == _required_core()
    pin = next(d for d in PROJECT["dependencies"] if _name(d) == "eyesweb-core")
    major, minor = _required_core()
    assert f"<{major}.{minor + 1}" in pin.replace(" ", "")
    # the lower bound must admit the core of this very release (2.0.0a1 sorts before 2.0)
    assert f">={version}" in pin.replace(" ", "") or f">={major}.{minor}" in pin.replace(" ", "")
    if re.search(r"(a|b|rc)\d+$", version):
        assert f">={version}" in pin.replace(" ", "")


def test_extras_exist():
    extras = PROJECT["optional-dependencies"]
    for name in ("test", "docs", "datasets", "dev"):
        assert name in extras, name
    assert "pytest" in {_name(d) for d in extras["test"]}
    assert "pooch" in {_name(d) for d in extras["datasets"]}
    assert "pooch" in {_name(d) for d in extras["docs"]}


def test_docs_extra_names_match_the_pinned_requirements():
    pinned = {_name(line) for line in (ROOT / "docs" / "requirements.txt").read_text(encoding="utf-8").splitlines()
              if line.strip() and not line.startswith("#")}
    assert {_name(d) for d in PROJECT["optional-dependencies"]["docs"]} == pinned


def test_python_requirement_and_classifiers():
    assert PROJECT["requires-python"] == ">=3.10"
    classifiers = PROJECT["classifiers"]
    for minor in (10, 11, 12, 13):
        assert f"Programming Language :: Python :: 3.{minor}" in classifiers
    assert "Development Status :: 3 - Alpha" in classifiers


def test_license_and_build_backend():
    assert PROJECT["license"] == "MIT"
    assert PROJECT["license-files"] == ["LICENSE.txt"] and (ROOT / "LICENSE.txt").is_file()
    requires = {_name(r): r for r in PYPROJECT["build-system"]["requires"]}
    assert PYPROJECT["build-system"]["build-backend"] == "setuptools.build_meta"
    assert int(re.search(r">=(\d+)", requires["setuptools"]).group(1)) >= 77  # SPDX license expressions


def test_only_the_library_is_packaged():
    find = PYPROJECT["tool"]["setuptools"]["packages"]["find"]
    assert find["include"] == ["pyeyesweb*"]
