"""Parity of the split GestureSegmenter with the EyesWeb block it was cut from.

The block embedded the kinetic energy, the noise test and the segmentation. `KineticEnergy` + `MotionNoiseDetector` +
`GestureSegmenter` (see its docstring), run frame by frame, must give for every frame what the block gave: bit for bit,
statuses and reasons included, after `reset()` and after live parameter changes.

`tests/data/gesture_segmenter_reference.npz` freezes the outputs of the block before the split (Qualisys excerpts
of `motion_excerpts.npz` and synthetic edge cases: still, NaN / infinite frames, repeated timestamps, dict frames with
missing labels, weights that name a subset of the labels), together with the description of each scenario.

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

from pyeyesweb.data_models.results import Status  # noqa: E402
from pyeyesweb.low_level import KineticEnergy  # noqa: E402
from pyeyesweb.low_level import MotionNoiseDetector  # noqa: E402
from pyeyesweb.mid_level import GestureSegmenter  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"
REFERENCE = np.load(DATA / "gesture_segmenter_reference.npz")
EXCERPTS = np.load(DATA / "motion_excerpts.npz")
SCENARIOS = json.loads(str(REFERENCE["meta"]))["scenarios"]
OUTPUTS = ["kinetic_energy", "smoothed_kinetic_energy", "noise", "is_gesturing", "is_gesture_start", "is_gesture_end"]
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
        segmented = self.segmenter.process(energy["kinetic_energy"], noise["is_noisy"], timestamp=timestamp)
        values[[0, 2]], valid[[0, 2]] = (energy["kinetic_energy"], noise["is_noisy"]), True
        for position, name in ((1, "smoothed_intensity"), (3, "is_gesturing"), (4, "is_gesture_start"), (5, "is_gesture_end")):
            values[position], valid[position] = segmented[name], segmented.valid[name]
        return int(segmented.status), _reason((segmented, energy, noise)), values, valid


def _bits(values):
    return np.where(np.isnan(values), np.nan, values).view(np.int64)


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
        assert np.array_equal(_bits(np.where(valid, values, np.nan)), _bits(expected)), (where, values, expected)


def test_the_reference_exercises_the_block():
    """The scenarios reach every state: starts and ends, noise on and off, warm-up, invalid frames."""
    values = np.concatenate([REFERENCE[scenario["name"] + "_values"] for scenario in SCENARIOS])
    status = np.concatenate([REFERENCE[scenario["name"] + "_status"] for scenario in SCENARIOS])
    assert np.nansum(values[:, 4]) > 20 and np.nansum(values[:, 5]) > 20
    assert (values[:, 2] == 0).any() and (values[:, 2] == 1).any()
    assert {int(Status.OK), int(Status.WARMING_UP), int(Status.INVALID_INPUT)} <= set(status.tolist())


def test_a_plain_signal_is_segmented_without_a_noise_input():
    signal = np.concatenate([np.zeros(15), np.ones(25), np.zeros(25)])
    plain = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal)
    gated = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal, np.zeros(len(signal)))
    noisy = GestureSegmenter(firing_threshold=0.5, filter_window_length=5).run(signal, np.ones(len(signal)))
    assert np.array_equal(plain.status, gated.status) and np.array_equal(plain["is_gesture_start"], gated["is_gesture_start"])
    assert plain["is_gesture_start"].sum() == 1 and plain["is_gesture_end"].sum() == 1
    assert noisy["is_gesture_start"].sum() == 0  # the flag blocks every start
    assert (plain.status == int(Status.WARMING_UP)).sum() == 10
