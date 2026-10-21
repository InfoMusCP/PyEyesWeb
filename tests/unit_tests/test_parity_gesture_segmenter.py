"""Parity of the split GestureSegmenter with the EyesWeb block it was cut from.

The block embedded the kinetic energy, the noise test and the segmentation. `KineticEnergy` + `MotionNoiseDetector` +
`GestureSegmenter` (see its docstring), run frame by frame, must give for every frame what the block gave: bit for bit,
statuses and reasons included, after `reset()` and after live parameter changes.

`tests/data/gesture_segmenter_reference.npz` freezes the outputs of the three features composed as in the block (before the split (Qualisys excerpts
of `motion_excerpts.npz` and synthetic edge cases: still, NaN / infinite frames, repeated timestamps, dict frames with
missing labels, weights that name a subset of the labels), together with the description of each scenario. Since I-a the
numbers are those of the current composition, not of the block (see below).

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
from pyeyesweb.low_level import MotionNoiseDetector  # noqa: E402
from pyeyesweb.mid_level import GestureSegmenter  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
REFERENCE = np.load(DATA / "gesture_segmenter_reference.npz")
EXCERPTS = np.load(DATA / "motion_excerpts.npz")
SCENARIOS = json.loads(str(REFERENCE["meta"]))["scenarios"]
_OUTPUTS = ["kinetic_energy", "smoothed_kinetic_energy", "noise", "is_gesturing", "is_gesture_start", "is_gesture_end"]
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
    """The reason the block gave: the parts of the three reasons, the notes first and last as `CoreFeature.result` puts them."""
    parts = []
    for result in results:
        parts += [part for part in result.reason.split("; ") if part]
    ordered = [part for part in dict.fromkeys(parts) if part not in (STATE_RESET, PER_SAMPLE)]
    return "; ".join([p for p in (STATE_RESET,) if p in parts] + ordered + [p for p in (PER_SAMPLE,) if p in parts])


class _Composition:
    """The three features with the parameters the block had."""

    def __init__(self, scenario):
        params = scenario["params"]
        labels = list(EXCERPTS["names"]) if scenario["labels"] == "names" else scenario["labels"]
        labels = None if scenario["source"] == "dict" else labels
        weights = scenario["weights"]
        self.squared = MM_SQUARED if params.get("units") == "mm" else 1.0
        self.labels, self.weights = labels, weights
        self.energy = KineticEnergy(labels=labels, weights=weights)
        # the block watched the weighted labels: when they are not all the columns, the detector gets those joints as a dict
        self.watches_all = labels is not None and set(labels) == set(weights)
        self.noise = MotionNoiseDetector(labels=labels if self.watches_all else sorted(weights),
                                         noise_threshold=params["noise_threshold"], units=params.get("units", "m"))
        self.segmenter = GestureSegmenter(firing_threshold=params["firing_threshold"] * self.squared,
                                          filter_window_length=params["filter_window_length"])

    def apply(self, event):
        if event[0] == "reset":
            for feature in (self.energy, self.noise, self.segmenter):
                feature.reset()
        elif event[1] == "firing_threshold":
            self.segmenter.firing_threshold = event[2] * self.squared
        elif event[1] == "noise_threshold":
            self.noise.noise_threshold = event[2]
        else:
            self.energy.weights = event[2]

    def process(self, frame, timestamp):
        """(status, reason, values, valid) of one frame, in the layout of the reference."""
        watched = frame if self.watches_all or isinstance(frame, dict) else {
            label: point for label, point in zip(self.labels, frame) if label in self.weights}
        energy, noise = self.energy.process(frame, timestamp=timestamp), self.noise.process(watched, timestamp=timestamp)
        values, valid = np.full(6, np.nan), np.zeros(6, dtype=bool)
        for upstream in (energy, noise):
            if upstream.status is not Status.OK:
                return int(upstream.status), upstream.reason, values, valid
        blocked = bool(noise["is_noisy"])  # is_noisy goes straight to the noise input of the segmenter
        segmented = self.segmenter.process(energy["kinetic_energy"], blocked, timestamp=timestamp)
        values[[0, 2]], valid[[0, 2]] = (energy["kinetic_energy"], blocked), True
        for position, name in ((1, "smoothed_intensity"), (3, "is_gesturing"), (4, "is_gesture_start"), (5, "is_gesture_end")):
            values[position], valid[position] = segmented[name], segmented.valid[name]
        return int(segmented.status), _reason((segmented, energy, noise)), values, valid


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
def test_composition_reproduces_the_block_bit_for_bit(scenario):
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
    """The scenarios reach every state: starts and ends, noise on and off, warm-up, invalid frames."""
    values = np.concatenate([REFERENCE[scenario["name"] + "_values"] for scenario in SCENARIOS])
    status = np.concatenate([REFERENCE[scenario["name"] + "_status"] for scenario in SCENARIOS])
    assert np.nansum(values[:, 4]) >= 5 and np.nansum(values[:, 5]) >= 3
    assert (values[:, 2] == 0).any() and (values[:, 2] == 1).any()
    assert {int(Status.OK), int(Status.WARMING_UP), int(Status.INVALID_INPUT)} <= set(status.tolist())


def test_a_jumpy_joint_blocks_the_segmenter_and_a_smooth_one_does_not():
    """Wiring: is_noisy goes directly to the noise input; the jumpy joint (the last one) blocks the starts while it jumps."""
    rng = np.random.default_rng(1)
    time = np.arange(120) / 50.0
    smooth = np.zeros((120, 2, 3))
    smooth[30:, 0, 0] = 0.5 * (1 - np.cos(2 * np.pi * (time[30:] - time[30]) / (time[-1] - time[30])))  # a smooth reach of "a"
    jumpy = smooth.copy()
    jumpy[30:60, 1] = rng.normal(scale=0.3, size=(30, 3))  # "b" jumps about for 30 frames
    ran = {}
    for name, frames in (("smooth", smooth), ("jumpy", jumpy)):
        energy = KineticEnergy(labels=["a", "b"], weights={"a": 1.0, "b": 1.0}, sampling_rate=50.0).run(frames)["kinetic_energy"]
        noise = np.asarray(MotionNoiseDetector(labels=["a", "b"], sampling_rate=50.0).run(frames)["is_noisy"], dtype=bool)
        starts = GestureSegmenter(firing_threshold=0.01, filter_window_length=5).run(energy, noise)["is_gesture_start"]
        ran[name] = (noise, np.flatnonzero(starts))
    assert not ran["smooth"][0].any() and len(ran["smooth"][1]) >= 1  # smooth motion is never noise: the gesture opens
    noise, starts = ran["jumpy"]
    assert noise[30:60].any() and not noise[:14].any()
    assert not noise[starts].any()  # no gesture starts while the motion is judged noise
    assert len(starts) >= 1 and starts[0] > ran["smooth"][1][0]  # blocked while jumpy, opens once the jumps are over


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


def test_a_plain_signal_is_segmented_without_a_noise_input():
    signal = np.concatenate([np.zeros(15), np.ones(25), np.zeros(25)])
    plain = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal)
    gated = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal, np.zeros(len(signal)))
    noisy = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal, np.ones(len(signal)))
    assert np.array_equal(plain.status, gated.status) and np.array_equal(plain["is_gesture_start"], gated["is_gesture_start"])
    assert plain["is_gesture_start"].sum() == 1 and plain["is_gesture_end"].sum() == 1
    assert noisy["is_gesture_start"].sum() == 0  # the flag blocks every start
    assert (plain.status == int(Status.WARMING_UP)).sum() == 10
