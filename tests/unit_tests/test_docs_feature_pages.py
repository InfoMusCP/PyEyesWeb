"""The documentation generator (docs/_ext/feature_pages.py): one page per catalog feature, families cover the catalog."""
import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("sphinx")
pytest.importorskip("numpydoc")
pytest.importorskip("yaml")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs" / "_ext"))

try:
    import pyeyesweb
    entries = pyeyesweb.catalog()
except ImportError:  # compiled core missing
    pytest.skip("the compiled EyesWeb core is not available", allow_module_level=True)

import feature_pages  # noqa: E402

DATA = ROOT / "docs" / "_data"


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated")
    feature_pages.generate(entries, out, DATA)
    return out


def test_one_page_per_catalog_feature(pages):
    written = sorted(pages.glob("*/*.rst"))
    assert len(written) == len(entries) == len({i.name for i in entries})
    for info in entries:
        assert (pages / info.layer.value / f"{info.name}.rst").exists()


def test_pages_name_the_class_and_every_output(pages):
    for info in entries:
        text = (pages / info.layer.value / f"{info.name}.rst").read_text(encoding="utf-8")
        assert info.name in text
        feature = feature_pages.instantiate(info, feature_pages._yaml(DATA / "instantiation.yaml"))
        for output in feature.outputs:
            assert output.name in text, f"{info.name}: output {output.name} missing from the page"


def test_wp4_todo_file(pages):
    import json
    todo = json.loads((pages / "_wp4_todo.json").read_text(encoding="utf-8"))
    assert todo["count"] == len(todo["classes"]) > 0


def test_families_cover_the_catalog_exactly():
    owner, families = feature_pages.load_families(DATA / "families.yaml", entries)
    assert set(owner) == {i.name for i in entries}
    assert sum(len(f["features"]) for f in families.values()) == len(entries)


def test_missing_family_raises(tmp_path):
    shutil.copy(DATA / "families.yaml", tmp_path / "families.yaml")
    text = (tmp_path / "families.yaml").read_text(encoding="utf-8").replace("Kinematics, ", "", 1)
    (tmp_path / "families.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Kinematics"):
        feature_pages.load_families(tmp_path / "families.yaml", entries)


def test_duplicate_family_raises(tmp_path):
    text = (DATA / "families.yaml").read_text(encoding="utf-8").replace("features: [EnsembleDominance]", "features: [EnsembleDominance, Kinematics]")
    (tmp_path / "families.yaml").write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="twice"):
        feature_pages.load_families(tmp_path / "families.yaml", entries)
