"""The documentation gate (DOCS_PLAN.md 11.2): markers of open work, names of the 1.x library, catalog coverage.

The data are in ``docs/_data/gate.yaml``. The marker and stale-name checks run when the builder starts and the coverage check
when the build has finished (it reads the back-references written by sphinx-gallery); each raises on a failure, so ``-W`` is
not needed to see it. ``PYEYESWEB_DOCS_RELEASE=1`` (or ``docs_gate_release = True``) makes open markers an error too.
Only files tracked by git are scanned when the tree is a git checkout (work in progress that is not committed never fails
the gate).
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path

import yaml
from sphinx.errors import ExtensionError
from sphinx.util import logging

logger = logging.getLogger(__name__)
DOCS = Path(__file__).resolve().parent.parent
ROOT = DOCS.parent
_SKIPPED = ("docs/_snippets/", "docs/_build/", "docs/api/generated/", "docs/tutorials/")


def load(path=DOCS / "_data" / "gate.yaml"):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def files(root=ROOT):
    """Repository-relative paths (``/`` separators) of the tracked files, or of every file outside a git checkout."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
        return sorted(line for line in out.splitlines() if line and (Path(root) / line).is_file())
    except (OSError, subprocess.CalledProcessError):
        return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file() and ".git" not in p.parts)


def _doc_sources(paths):
    return [p for p in paths if p.startswith("docs/") and p.endswith((".md", ".rst")) and not p.startswith(_SKIPPED)]


# --- markers -------------------------------------------------------------------------------------------------------------
def marker_counts(paths, data, root=ROOT):
    """``{path: {marker: count}}`` over the prose pages, ``docs/conf.py``, the CSS files and (for ``DRAFT``) the bibliography."""
    scanned = _doc_sources(paths) + [p for p in paths if p == "docs/conf.py" or
                                     (p.startswith("docs/_static/") and p.endswith(".css"))]
    allowed = data.get("allowed") or []
    counts = {}
    for path in scanned:
        for line in (Path(root) / path).read_text(encoding="utf-8").splitlines():
            if any(a["path"] == path and a["contains"] in line for a in allowed):
                continue
            for marker in data["markers"]:
                n = len(re.findall(marker, line))
                if n:
                    counts.setdefault(path, {}).setdefault(marker, 0)
                    counts[path][marker] += n
    bib = "docs/references.bib"
    if bib in paths:
        n = len(re.findall(data["draft_marker"], (Path(root) / bib).read_text(encoding="utf-8")))
        if n:
            counts[bib] = {data["draft_marker"]: n}
    return counts


def check_markers(counts, data, release=False):
    """Failures: a count that differs from ``open`` of gate.yaml, and in a release build any open marker at all."""
    expected = data.get("open") or {}
    failures = []
    for path in sorted(set(counts) | set(expected)):
        for marker in sorted(set(counts.get(path, {})) | set(expected.get(path) or {})):
            found, listed = counts.get(path, {}).get(marker, 0), (expected.get(path) or {}).get(marker, 0)
            if found > listed:
                failures.append(f"{path}: {found} x {marker}, {listed} listed as open in docs/_data/gate.yaml (a new marker)")
            elif found < listed:
                failures.append(f"{path}: {found} x {marker}, {listed} listed as open: lower the count in docs/_data/gate.yaml")
    if release and counts:
        total = sum(sum(per.values()) for per in counts.values())
        failures.append(f"release build: {total} open markers in {len(counts)} files (docs/_data/gate.yaml, 'open')")
    return failures


# --- stale names ---------------------------------------------------------------------------------------------------------
def public_docstrings(source):
    """The docstrings of a module, of its public classes and functions and of their public methods."""
    tree = ast.parse(source)
    found = [ast.get_docstring(tree, clean=False) or ""]

    def visit(node):
        for child in node.body:
            if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                found.append(ast.get_docstring(child, clean=False) or "")
                if isinstance(child, ast.ClassDef):
                    visit(child)
    visit(tree)
    return found


def _public_module(path):
    """A module of the documented API: not private, not ``pyeyesweb.base`` or ``pyeyesweb.utils`` (internal, facts.md 13)."""
    if path.startswith(("pyeyesweb/base/", "pyeyesweb/utils/")):
        return False
    return path.startswith("pyeyesweb/") and path.endswith(".py") and not any(
        part.startswith("_") and part != "__init__.py" for part in path.split("/"))


def stale_hits(paths, data, root=ROOT):
    """``[(path, name, line)]`` for every stale name in the published text."""
    allowed, sources = set(data.get("stale_allowed") or []), set(_doc_sources(paths))
    texts = []
    for path in paths:
        if path in allowed:
            continue
        if path in sources or path == "README.md" or path == "examples/helpers.py" or (
                path.startswith("examples/") and re.search(r"/plot_[^/]*\.py$", path)):
            texts.append((path, (Path(root) / path).read_text(encoding="utf-8")))
        elif _public_module(path):
            texts += [(path, doc) for doc in public_docstrings((Path(root) / path).read_text(encoding="utf-8"))]
    hits = []
    for path, text in texts:
        for line in text.splitlines():
            hits += [(path, name, line.strip()) for name in data["stale_names"] if re.search(name, line)]
    return hits


# --- catalog coverage ----------------------------------------------------------------------------------------------------
def uncovered(entries, backreferences, data):
    """Catalog names with no non-empty ``<module>.<Name>.examples`` file and no reason in ``coverage_allowed``."""
    allowed = data.get("coverage_allowed") or {}
    used = {p.name[:-len(".examples")].rsplit(".", 1)[-1]
            for p in Path(backreferences).glob("*.examples") if p.read_text(encoding="utf-8").strip()}
    return sorted(info.name for info in entries if info.name not in used and info.name not in allowed)


# --- Sphinx --------------------------------------------------------------------------------------------------------------
def _release(app):
    return app.config.docs_gate_release or os.environ.get("PYEYESWEB_DOCS_RELEASE", "") not in ("", "0")


def _builder_inited(app):
    data, paths = load(), files()
    failures = check_markers(marker_counts(paths, data), data, release=_release(app))
    failures += [f"{path}: stale name {name!r} in: {line}" for path, name, line in stale_hits(paths, data)]
    if failures:
        raise ExtensionError("docs_gate:\n  " + "\n  ".join(failures))
    open_count = sum(sum((per or {}).values()) for per in (data.get("open") or {}).values())
    logger.info(f"docs_gate: markers and stale names checked ({open_count} open markers listed in docs/_data/gate.yaml)")


def _build_finished(app, exception):
    if exception is not None or app.builder.name not in ("html", "dirhtml"):
        return
    gallery = getattr(app.config, "sphinx_gallery_conf", {}) or {}
    if str(gallery.get("plot_gallery", True)).lower() in ("false", "0", "no", ""):
        logger.warning("docs_gate: the gallery was not executed, catalog coverage not checked")
        return
    import pyeyesweb
    missing = uncovered(pyeyesweb.catalog(), Path(app.srcdir) / gallery["backreferences_dir"], load())
    if missing:
        raise ExtensionError("docs_gate: catalog features used by no tutorial (add them to a script or to "
                             f"coverage_allowed in docs/_data/gate.yaml with a reason): {missing}")
    logger.info("docs_gate: every catalog feature is used by a tutorial")


def setup(app):
    app.add_config_value("docs_gate_release", False, "env")
    app.connect("builder-inited", _builder_inited)
    app.connect("build-finished", _build_finished)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
