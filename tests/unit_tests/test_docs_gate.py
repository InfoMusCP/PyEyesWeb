"""The documentation gate (docs/_ext/docs_gate.py): markers of open work, stale 1.x names, catalog coverage."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("sphinx")
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs" / "_ext"))

import docs_gate  # noqa: E402

DATA = docs_gate.load()


def _tree(tmp_path, files):
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    return sorted(files)


def test_the_repository_passes_the_gate():
    paths = docs_gate.files()
    assert docs_gate.check_markers(docs_gate.marker_counts(paths, DATA), DATA) == []
    assert docs_gate.stale_hits(paths, DATA) == []


def test_a_new_marker_fails(tmp_path):
    paths = _tree(tmp_path, {"docs/page.md": "A claim **[citation needed]**.\nTODO(WP9): a figure\n"})
    failures = docs_gate.check_markers(docs_gate.marker_counts(paths, DATA, tmp_path), {**DATA, "open": {}})
    assert len(failures) == 2 and all("a new marker" in f for f in failures)


def test_a_resolved_marker_asks_for_the_count_to_be_lowered(tmp_path):
    paths = _tree(tmp_path, {"docs/page.md": "A claim with its source.\n"})
    data = {**DATA, "open": {"docs/page.md": {r"\[citation needed\]": 1}}}
    (failure,) = docs_gate.check_markers(docs_gate.marker_counts(paths, data, tmp_path), data)
    assert "lower the count" in failure


def test_listed_markers_pass_a_draft_build_and_fail_a_release_build(tmp_path):
    paths = _tree(tmp_path, {"docs/page.md": "A claim **[citation needed]**.\n",
                             "docs/references.bib": "@misc{a, note = {DRAFT: check}}\n"})
    data = {**DATA, "open": {"docs/page.md": {r"\[citation needed\]": 1}, "docs/references.bib": {r"\bDRAFT\b": 1}}}
    counts = docs_gate.marker_counts(paths, data, tmp_path)
    assert docs_gate.check_markers(counts, data) == []
    assert "release build: 2 open markers" in docs_gate.check_markers(counts, data, release=True)[0]


def test_allowed_lines_and_api_names_are_not_markers(tmp_path):
    paths = _tree(tmp_path, {"docs/developer/conventions.md": "is marked **[citation needed]** until it is added.\n",
                             "docs/api/skeletons.md": "`SKELETON_TODO` lists what is missing.\n"})
    assert docs_gate.marker_counts(paths, DATA, tmp_path) == {}


def test_skipped_folders_are_not_scanned(tmp_path):
    paths = _tree(tmp_path, {"docs/_snippets/facts.md": "TODO SpeedSmoothness\n", "docs/api/generated/x.rst": "TODO\n"})
    assert docs_gate.marker_counts(paths, DATA, tmp_path) == {}
    assert docs_gate.stale_hits(paths, DATA, tmp_path) == []


def test_stale_names(tmp_path):
    paths = _tree(tmp_path, {
        "docs/page.md": "Use a SlidingWindow.\n",
        "docs/migration.md": "SlidingWindow was removed.\n",  # allowed file
        "examples/03_low_level/plot_05_motion.py": "x = SpeedSmoothness()\n",
        "examples/live_demo.py": "rate_hz = 30\n",  # not a tutorial
        "pyeyesweb/low_level/thing.py": '"""Module."""\nclass Thing:\n    """Wraps the TSVReader."""\n'
                                        '    def _process_window(self):\n        """_process_window is private."""\n',
        "pyeyesweb/utils/helper.py": '"""rate_hz is fine in an internal module."""\n',
    })
    hits = {(path, name) for path, name, _ in docs_gate.stale_hits(paths, DATA, tmp_path)}
    assert hits == {("docs/page.md", "SlidingWindow"), ("examples/03_low_level/plot_05_motion.py", "SpeedSmoothness"),
                    ("pyeyesweb/low_level/thing.py", "TSVReader")}


def test_coverage_reads_non_empty_back_references(tmp_path):
    entries = [SimpleNamespace(name="Used"), SimpleNamespace(name="Unused"), SimpleNamespace(name="Excused")]
    (tmp_path / "pyeyesweb.low_level.Used.examples").write_text("examples\n", encoding="utf-8")
    (tmp_path / "pyeyesweb.low_level.Unused.examples").write_text("", encoding="utf-8")  # sphinx-gallery touches it
    (tmp_path / "pyeyesweb.low_level.Used.process.examples").write_text("x\n", encoding="utf-8")
    data = {**DATA, "coverage_allowed": {"Excused": "no tutorial yet"}}
    assert docs_gate.uncovered(entries, tmp_path, data) == ["Unused"]
