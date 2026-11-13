"""Frozen reference of the skeleton pipeline of the EyesWeb block GestureSegmenter: `KineticEnergy` -> `GestureSegmenter`.

The block embedded the kinetic energy, a noise test and the segmentation. `KineticEnergy` + `GestureSegmenter`, run frame
by frame, must give for every frame what `tests/data/gesture_segmenter_reference.npz` froze: bit for bit, statuses and
reasons included, after `reset()` and after live parameter changes. The scenarios (Qualisys excerpts of
`motion_excerpts.npz` and synthetic edge cases: still, NaN / infinite frames, repeated timestamps, dict frames with
missing labels, weights that name a subset of the labels) are described in the file. The numbers are those of the current
composition, not of the block (see below).

Regenerated for the GestureSegmenter merge (2026-11-13, algorithm review): the Savitzky-Golay fit uses the newest
`filter_window_length` samples (warm-up `filter_window_length - 1` samples instead of 10); the noise test is not wired
(MotionNoiseDetector is held back from the first release; the `noise_threshold` of the scenarios is unused); the
durations of MotionDuration, merged in, are two more outputs.

Regenerated for work package I-a (2026-10-15): `is_noisy` is fed directly to the `noise` input (it used to be negated, which
blocked every smooth gesture); the reference was rebuilt with `tools/regenerate_gesture_segmenter_reference.py`.

Regenerated for work package A (2026-10-14): the first timed call has no previous timestamp (1 / `sampling_rate` or 1 s,
with the per-sample note), a repeated timestamp is `INVALID_INPUT`, a dict frame with a missing joint is `INVALID_INPUT`
("missing joints") and one with a joint that is not among the labels raises (those two frames left the dict scenario), a
rejected frame carries no per-sample note.

Needs the compiled core: found as pyeyesweb._eyesweb_core, or as eyesweb_core in EYESWEB_CORE_PATH; else skipped.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from floats import assert_same_floats  # noqa: E402
from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import KineticEnergy  # noqa: E402
from pyeyesweb.low_level.motion_noise import MotionNoiseDetector  # noqa: E402
from pyeyesweb.mid_level import GestureSegmenter  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
REFERENCE = np.load(DATA / "gesture_segmenter_reference.npz")
EXCERPTS = np.load(DATA / "motion_excerpts.npz")
SCENARIOS = json.loads(str(REFERENCE["meta"]))["scenarios"]
_OUTPUTS = ["kinetic_energy", "smoothed_kinetic_energy", "is_gesturing", "is_gesture_start", "is_gesture_end",
            "motion_duration", "pause_duration"]
MM_SQUARED = 1000.0 ** 2  # the old block scaled the energy threshold by the square of the unit factor
STATE_RESET, PER_SAMPLE = "parameters changed: state reset", "no time given: per-sample derivatives"


def _inputs(scenario):
    """The frames and the timestamps (or None) of a scenario."""
    source, kind = scenario["source"], scenario["ts"]
    if source == "dict":
        frames = scenario["dict_frames"]
    elif source.startswith("trial"):
        frames = EXCERPTS[source][:scenario.get("take", len(EXCERPTS[source]))]
    else:
        frames = REFERENCE["syn_" + source]
    if kind == "none":
        return frames, None
    if kind == "source":
        return frames, EXCERPTS[source + "_t"][:len(frames)]
    if kind in ("irregular", "repeated"):
        return frames, REFERENCE["ts_" + kind][:len(frames)]
    return frames, np.arange(len(frames)) / float(kind.split(":")[1])


def _reason(results):
    """The reason of the pipeline: the parts of the two reasons, the notes first and last as `CoreFeature.result` puts them."""
    parts = []
    for result in results:
        parts += [part for part in result.reason.split("; ") if part]
    ordered = [part for part in dict.fromkeys(parts) if part not in (STATE_RESET, PER_SAMPLE)]
    return "; ".join([p for p in (STATE_RESET,) if p in parts] + ordered + [p for p in (PER_SAMPLE,) if p in parts])


class _Composition:
    """The two features with the parameters the block had."""

    def __init__(self, scenario):
        params = scenario["params"]
        labels = list(EXCERPTS["names"]) if scenario["labels"] == "names" else scenario["labels"]
        labels = None if scenario["source"] == "dict" else labels
        weights = scenario["weights"]
        self.squared = MM_SQUARED if params.get("units") == "mm" else 1.0
        self.labels, self.weights = labels, weights
        self.energy = KineticEnergy(labels=labels, weights=weights)
        self.segmenter = GestureSegmenter(firing_threshold=params["firing_threshold"] * self.squared,
                                          filter_window_length=params["filter_window_length"])

    def apply(self, event):
        if event[0] == "reset":
            for feature in (self.energy, self.segmenter):
                feature.reset()
        elif event[1] == "firing_threshold":
            self.segmenter.firing_threshold = event[2] * self.squared
        elif event[1] == "noise_threshold":
            pass  # the noise test is not wired (held back)
        else:
            self.energy.weights = event[2]

    def process(self, frame, timestamp):
        """(status, reason, values, valid) of one frame, in the layout of the reference."""
        energy = self.energy.process(frame, timestamp=timestamp)
        values, valid = np.full(len(_OUTPUTS), np.nan), np.zeros(len(_OUTPUTS), dtype=bool)
        if energy.status is not Status.OK:
            return int(energy.status), energy.reason, values, valid
        segmented = self.segmenter.process(energy["kinetic_energy"], timestamp=timestamp)
        values[0], valid[0] = energy["kinetic_energy"], True
        for position, name in enumerate(("smoothed_intensity", "is_gesturing", "is_gesture_start", "is_gesture_end",
                                         "motion_duration", "pause_duration"), start=1):
            values[position], valid[position] = segmented[name], segmented.valid[name]
        return int(segmented.status), _reason((segmented, energy)), values, valid


def compute(scenario):
    """(status, reason, values, valid) of every frame of a scenario, as the reference stores them."""
    frames, timestamps = _inputs(scenario)
    composition = _Composition(scenario)
    events = {int(key): value for key, value in scenario.get("events", {}).items()}
    rows = []
    for index, frame in enumerate(frames):
        for event in events.get(index, []):
            composition.apply(event)
        rows.append(composition.process(frame, None if timestamps is None else float(timestamps[index])))
    return rows


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[scenario["name"] for scenario in SCENARIOS])
def test_composition_matches_the_frozen_reference(scenario):
    name = scenario["name"]
    frames, timestamps = _inputs(scenario)
    composition = _Composition(scenario)
    events = {int(key): value for key, value in scenario.get("events", {}).items()}
    for index, frame in enumerate(frames):
        for event in events.get(index, []):
            composition.apply(event)
        status, reason, values, valid = composition.process(frame, None if timestamps is None else float(timestamps[index]))
        where = f"{name}, frame {index}"
        assert status == REFERENCE[name + "_status"][index], where
        assert reason == REFERENCE[name + "_reason"][index], where
        assert np.array_equal(valid, REFERENCE[name + "_valid"][index]), where
        expected = np.where(valid, REFERENCE[name + "_values"][index], np.nan)
        assert_same_floats(np.where(valid, values, np.nan), expected, err_msg=where)


def test_the_reference_exercises_the_block():
    """The scenarios reach every state: starts and ends, durations, warm-up, invalid frames."""
    values = np.concatenate([REFERENCE[scenario["name"] + "_values"] for scenario in SCENARIOS])
    status = np.concatenate([REFERENCE[scenario["name"] + "_status"] for scenario in SCENARIOS])
    assert np.nansum(values[:, 3]) >= 5 and np.nansum(values[:, 4]) >= 3
    assert np.isfinite(values[:, 5]).sum() >= 3 and np.isfinite(values[:, 6]).sum() >= 3
    assert {int(Status.OK), int(Status.WARMING_UP), int(Status.INVALID_INPUT)} <= set(status.tolist())


def test_only_the_alphabetically_last_joint_name_decides_the_noise_flag():
    """Quirk of the original, kept: with several joints only the alphabetically last joint name counts, whatever the order
    of the labels, so the flag of a jumpy joint is lost when its name is not the last; a single joint is judged on its own."""
    jumps = np.random.default_rng(0).normal(scale=0.3, size=(60, 1, 3))
    still = np.zeros((60, 1, 3))
    flag = lambda labels, frames: np.asarray(MotionNoiseDetector(labels=labels, sampling_rate=50.0).run(frames)["is_noisy"])
    assert flag(["hand"], jumps)[-1]
    assert flag(["a", "b"], np.concatenate([jumps, still], axis=1))[-1] == False  # noqa: E712  jumpy "a", still "b"
    assert flag(["a", "b"], np.concatenate([still, jumps], axis=1))[-1]
    # the order of the labels does not matter: "b" decides although it is listed first
    assert flag(["b", "a"], np.concatenate([jumps, still], axis=1))[-1]
    assert flag(["b", "a"], np.concatenate([still, jumps], axis=1))[-1] == False  # noqa: E712


def test_a_plain_signal_is_segmented():
    signal = np.concatenate([np.zeros(15), np.ones(25), np.zeros(25)])
    plain = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal)
    assert plain["is_gesture_start"].sum() == 1 and plain["is_gesture_end"].sum() == 1
    assert (plain.status == int(Status.WARMING_UP)).sum() == 4
    assert np.nanmax(plain["motion_duration"]) == 25  # samples: the same smoothing on both edges
