"""pyeyesweb.datasets: locating, reading and standardising Qualisys recordings (no compiled core needed)."""

import json
import sys

import numpy as np
import pytest

from pyeyesweb import datasets
from pyeyesweb.datasets import QualisysTrial, load_qualisys_trial

MAPPING = {"Head": ["HeadFront", "HeadL"], "Left_Hand": ["LHand"], "Right_Hand": ["RHand"], "Pelvis": ["Waist", "Gone"]}


def _write_trial(folder, frames=300, rate=100):
    """A small Qualisys export: 4 markers, one lost for a few frames (0, 0, 0), time starting at 0."""
    (folder / "qualisys").mkdir(parents=True)
    names = ["HeadFront", "HeadL", "LHand", "RHand", "Waist"]
    t = np.arange(frames)
    data = {n: np.stack([np.sin(t / 20 + k), np.cos(t / 20 + k), 1000.0 + k + 0 * t], axis=1) for k, n in enumerate(names)}
    data["LHand"][10:13] = 0.0
    header = ["FILE_VERSION\t2.0.0", f"NO_OF_FRAMES\t{frames}", f"NO_OF_MARKERS\t{len(names)}", f"FREQUENCY\t{rate}",
              "MARKER_NAMES\t" + "\t".join(names), "Frame\tTime\t" + "\t".join(f"{n} {a}" for n in names for a in "XYZ")]
    rows = [f"{i + 1}\t{i / rate:.5f}\t" + "\t".join(f"{v:.3f}" for n in names for v in data[n][i]) for i in range(frames)]
    (folder / "qualisys" / "trial7.tsv").write_text("\n".join(header + rows) + "\n")
    (folder / "markers_mappings.json").write_text(json.dumps(MAPPING))
    return data


@pytest.fixture
def folder(tmp_path, monkeypatch):
    monkeypatch.setenv("PYEYESWEB_DATA", str(tmp_path))
    return tmp_path


def test_a_file_in_pyeyesweb_data_is_read_and_standardised(folder):
    raw = _write_trial(folder)
    trial = load_qualisys_trial(7)
    assert isinstance(trial, QualisysTrial) and trial.trial == 7 and trial.units == "mm" and trial.sampling_rate == 100.0
    assert trial.labels == tuple(MAPPING) and trial.positions.shape == (300, 4, 3)
    assert np.allclose(trial.joint("Head"), (raw["HeadFront"] + raw["HeadL"]) / 2, atol=1e-3)
    assert np.allclose(trial.joint("Pelvis"), raw["Waist"], atol=1e-3)            # an alias that is absent is ignored
    assert np.isfinite(trial.positions).all()
    assert trial.timestamps[1] == pytest.approx(0.01) and trial.duration == pytest.approx(3.0)


def test_lost_markers_are_interpolated_not_zero(folder):
    raw = _write_trial(folder)
    hand = load_qualisys_trial("trial7", standardize=False).joint("LHand")
    assert (hand[10:13] != 0).all()
    expected = np.linspace(raw["LHand"][9], raw["LHand"][13], 5)[1:-1]
    assert np.allclose(hand[10:13], expected, atol=1e-3)


def test_start_and_stop_are_seconds_of_the_recording_and_the_clock_restarts(folder):
    _write_trial(folder)
    part = load_qualisys_trial(7, start=1.0, stop=2.5)
    assert part.positions.shape[0] == 150 and part.offset == pytest.approx(1.0) and part.timestamps[0] == 0.0
    with pytest.raises(ValueError, match="no frame"):
        load_qualisys_trial(7, start=10.0)
    again = part.window(0.5, 1.0)
    assert again.positions.shape[0] == 50 and again.offset == pytest.approx(1.5)


def test_units_are_kept_and_converted_on_request(folder):
    _write_trial(folder)
    trial = load_qualisys_trial(7)
    metres = trial.to_units("m")
    assert metres.units == "m" and np.allclose(metres.positions, trial.positions / 1000)
    assert np.allclose(metres.to_units("mm").positions, trial.positions)
    with pytest.raises(ValueError, match="units"):
        trial.to_units("cm")


def test_the_skeleton_of_the_standard_joints_has_the_left_right_couples(folder):
    _write_trial(folder)
    skeleton = load_qualisys_trial(7).skeleton
    assert skeleton.joints == tuple(MAPPING) and skeleton.pairs == (("Left_Hand", "Right_Hand"),)
    with pytest.raises(ValueError, match="standardized"):
        load_qualisys_trial(7, standardize=False).skeleton
    with pytest.raises(KeyError, match="Elbow"):
        load_qualisys_trial(7).joint("Elbow")


def test_task_and_condition_come_from_the_trial_table(folder):
    _write_trial(folder)
    trial = load_qualisys_trial(7)
    assert (trial.task, trial.condition) == ("Clapping hands", "synchronized")
    assert 7 in datasets.available_trials()


def test_missing_data_without_a_host_says_so(folder, monkeypatch):
    monkeypatch.setattr(datasets, "_checkout_data_dir", lambda: folder / "nowhere")
    with pytest.raises(FileNotFoundError, match="not available online yet"):
        datasets.fetch_data_file("qualisys/trial7.tsv")


def test_a_download_without_pooch_names_the_optional_dependency(folder, monkeypatch):
    monkeypatch.setattr(datasets, "_checkout_data_dir", lambda: folder / "nowhere")
    monkeypatch.setattr(datasets, "BASE_URL", "https://example.invalid/data/")
    monkeypatch.setattr(datasets, "_registry", lambda: {"qualisys/trial7.tsv": "0" * 64})
    monkeypatch.setitem(sys.modules, "pooch", None)
    with pytest.raises(ImportError, match=r"pip install pyeyesweb\[datasets\]"):
        datasets.fetch_data_file("qualisys/trial7.tsv")


def test_a_file_that_is_not_a_qualisys_export_is_refused(folder):
    (folder / "qualisys").mkdir()
    (folder / "qualisys" / "trial3.tsv").write_text("a\tb\n1\t2\n")
    with pytest.raises(ValueError, match="not a Qualisys"):
        load_qualisys_trial(3)


def test_the_cache_directory_follows_the_environment(folder):
    assert datasets.cache_dir() == folder


@pytest.mark.skipif(not (datasets._checkout_data_dir() / "qualisys" / "trial7.tsv").exists(), reason="example data not in this checkout")
def test_the_repository_recording_loads_with_all_twenty_joints():
    trial = load_qualisys_trial(7, start=2.0, stop=7.0)
    assert trial.positions.shape == (500, 20, 3) and trial.labels[:3] == ("Head", "Neck", "Spine")
    assert np.isfinite(trial.positions).all() and trial.offset == pytest.approx(2.0)
    raw = load_qualisys_trial(7, standardize=False, stop=1.0)
    assert raw.positions.shape == (100, 41, 3)
