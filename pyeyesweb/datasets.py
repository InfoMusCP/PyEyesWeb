"""Example recordings for the tutorials and the documentation.

The gallery and the how-to pages use motion-capture recordings of expressive movement (Qualisys, 41 markers, 100 Hz,
positions in millimetres; one performer, 2024 session, see :data:`QUALISYS_TRIALS`). This module finds a recording,
reads it and returns the positions as an array, with the names of the joints, the sampling rate and the unit. It does
not compute anything else: derived signals and figures belong to the code that uses them.

Where a file is looked for, in this order:

1. the directory named by the environment variable ``PYEYESWEB_DATA``, if set (it is also the download cache);
2. the ``examples/data`` folder of a repository checkout, so that the documentation builds offline from the repository;
3. the download cache (``PYEYESWEB_DATA``, else the user cache directory of the operating system), filled by
   downloading the file from :data:`BASE_URL` and checking its SHA-256 sum against the registry of the module.

Downloading needs the optional dependency `pooch <https://www.fatiando.org/pooch/>`__
(``pip install pyeyesweb[datasets]``); reading a local file does not. The recordings are not hosted online yet
(:data:`BASE_URL` is ``None``): outside a checkout and without ``PYEYESWEB_DATA`` the functions raise an error that says so.

Examples
--------
>>> from pyeyesweb.datasets import load_qualisys_trial
>>> trial = load_qualisys_trial(7, start=2.0, stop=7.0)      # clapping hands, seconds 2 to 7
>>> trial.positions.shape, trial.units, trial.sampling_rate
((500, 20, 3), 'mm', 100.0)
>>> trial.labels[:3]
('Head', 'Neck', 'Spine')
>>> trial.task, trial.condition
('Clapping hands', 'synchronized')
"""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

__all__ = ["BASE_URL", "QUALISYS_TRIALS", "QualisysTrial", "available_trials", "cache_dir", "fetch_data_file",
           "load_qualisys_trial"]

BASE_URL: str | None = None
"""URL of the folder that hosts the recordings (the registry names are appended to it). ``None``: not hosted yet.

TODO(maintainer): set it once the host is chosen (Zenodo, OSF or a GitHub release asset); the checksums of the files to
host are in ``pyeyesweb/_datasets_registry.py``, written by ``tools/trim_example_data.py``."""

#: Trial number -> (task, condition), from ``examples/data/README.md`` (session of 2024-03-26; trials 1, 2 and 9 are
#: test takes and are not listed).
QUALISYS_TRIALS: dict[int, tuple[str, str]] = {
    3: ("Open the window", "synchronized"), 4: ("Open the window", "unsynchronized"),
    5: ("Breathing arms", "synchronized"), 6: ("Breathing arms", "unsynchronized"),
    7: ("Clapping hands", "synchronized"), 8: ("Clapping hands", "unsynchronized"),
    10: ("Sumo squat, weight shift", "alternating symmetric / asymmetric"),
    11: ("Infinite gesture (figure eight)", "smooth"), 12: ("Infinite gesture (figure eight)", "not smooth"),
    13: ("Caress a delicate surface", "smooth"), 14: ("Caress a delicate surface", "not smooth"),
    15: ("Move a valuable object", "smooth"), 16: ("Move a valuable object", "not smooth (trembling)"),
    17: ("Hiding and catching attention", "contraction / expansion, facing front"),
    18: ("Hiding and catching attention", "contraction / expansion, turning"),
    19: ("Balance on tiptoes", "alternating balance / imbalance"),
    20: ("Lose balance on one leg", "impulsive"), 21: ("Hide an object on cue", "reactive, impulsive"),
    22: ("Be a balloon", "light"), 23: ("Hand like a falling leaf", "light"),
    24: ("Be a feather", "alternating light / heavy"), 25: ("Total body slow motion", "extremely slow"),
}



def __dir__():
    return sorted(__all__)


_UNIT_SCALE = {"mm": 1.0, "m": 1e-3}


# --------------------------------------------------------------------------------------------- locating the files
def cache_dir() -> Path:
    """Directory where downloaded recordings are stored.

    ``PYEYESWEB_DATA`` if the variable is set, else the user cache directory of the operating system (``pooch.os_cache``
    when pooch is installed, ``~/.cache/pyeyesweb`` otherwise). The directory is not created here.

    Returns
    -------
    pathlib.Path
        The cache directory (it may not exist yet).

    Examples
    --------
    >>> from pyeyesweb.datasets import cache_dir
    >>> cache_dir().name != ""
    True
    """
    if os.environ.get("PYEYESWEB_DATA"):
        return Path(os.environ["PYEYESWEB_DATA"]).expanduser()
    try:
        import pooch
        return Path(pooch.os_cache("pyeyesweb"))
    except ImportError:
        return Path.home() / ".cache" / "pyeyesweb"


def _checkout_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "data"


def _local_dirs() -> list[Path]:
    dirs = []
    if os.environ.get("PYEYESWEB_DATA"):
        dirs.append(cache_dir())
    dirs.append(_checkout_data_dir())
    if cache_dir() not in dirs:
        dirs.append(cache_dir())
    return dirs


def _registry() -> dict[str, str]:
    from ._datasets_registry import REGISTRY
    return REGISTRY


def fetch_data_file(name: str) -> Path:
    """Path of an example data file, downloading it first if it is not available locally.

    Parameters
    ----------
    name : str
        Path of the file relative to the data folder, with forward slashes, e.g. ``"qualisys/trial7.tsv"`` (a trimmed
        copy is ``"qualisys/trial7.tsv.gz"``) or
        ``"markers_mappings.json"``.

    Returns
    -------
    pathlib.Path
        An existing file. A local file (see the module description for the search order) is returned as it is, without
        any check; a downloaded file has been verified against its SHA-256 sum.

    Raises
    ------
    FileNotFoundError
        If the file is not local and cannot be downloaded: ``BASE_URL`` is ``None`` (data not available online yet) or the
        name is not in the registry.
    ImportError
        If a download is needed and the optional dependency pooch is not installed.

    Examples
    --------
    >>> from pyeyesweb.datasets import fetch_data_file
    >>> fetch_data_file("qualisys/trial7.tsv").name
    'trial7.tsv'
    """
    relative = str(name).replace("\\", "/").lstrip("/")
    for folder in _local_dirs():
        candidate = folder / relative
        if candidate.is_file():
            return candidate
    registry = _registry()
    if BASE_URL is None or relative not in registry:
        why = ("the example data are not available online yet (pyeyesweb.datasets.BASE_URL is None)" if BASE_URL is None
               else f"{relative!r} is not in the registry of the example data")
        raise FileNotFoundError(
            f"Example data file {relative!r} was not found locally ({', '.join(str(folder) for folder in _local_dirs())}) and {why}. "
            "Run from a checkout of the repository, or set the environment variable PYEYESWEB_DATA to a folder holding "
            "the files.")
    try:
        import pooch
    except ImportError as error:
        raise ImportError("Downloading the example data needs the optional dependency 'pooch': "
                          "pip install pyeyesweb[datasets]") from error
    store = pooch.create(path=cache_dir(), base_url=BASE_URL, registry={key: f"sha256:{digest}" for key, digest in registry.items()})
    return Path(store.fetch(relative))


def available_trials() -> tuple[int, ...]:
    """Numbers of the Qualisys trials that can be loaded now (local files, plus the registry once ``BASE_URL`` is set).

    Returns
    -------
    tuple of int
        Sorted trial numbers. Without a local copy and without a registry the tuple is empty.

    Examples
    --------
    >>> from pyeyesweb.datasets import available_trials
    >>> 7 in available_trials()
    True
    """
    found = set()
    names = [path.name for folder in _local_dirs() for path in (folder / "qualisys").glob("trial*.tsv*")]
    if BASE_URL is not None:                      # the files of the registry can be downloaded
        names += [Path(key).name for key in _registry() if key.startswith("qualisys/")]
    for name in names:
        digits = name[len("trial"):].split(".")[0]
        if name.startswith("trial") and name.endswith((".tsv", ".tsv.gz")) and digits.isdigit():
            found.add(int(digits))
    return tuple(sorted(found))


# --------------------------------------------------------------------------------------------- reading Qualisys files
def _read_tsv(path: Path):
    """Time (s), raw positions (T, M, 3) in mm, marker names and sampling rate of a Qualisys TSV export (private)."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
        header, rate = [], 100.0
        for line in handle:
            if line.startswith("Frame\t"):
                columns = line.rstrip("\r\n").split("\t")
                break
            header.append(line)
            if line.startswith("FREQUENCY"):
                rate = float(line.split("\t")[1])
        else:
            raise ValueError(f"{path}: not a Qualisys TSV file (no 'Frame' header row)")
        table = np.genfromtxt(handle, delimiter="\t", dtype=float, filling_values=np.nan, ndmin=2)
    names = [column[:-2].strip() for column in columns if column.endswith(" X")]
    index = {column: position for position, column in enumerate(columns)}
    positions = np.stack([table[:, [index[f"{name} {axis}"] for name in names]] for axis in "XYZ"], axis=-1)
    return table[:, index["Time"]], positions, names, rate


def _fill_lost_markers(positions: np.ndarray) -> np.ndarray:
    """A marker lost by the system is exported as (0, 0, 0): treat it as missing, interpolate linearly, hold the ends."""
    positions = positions.copy()
    positions[np.all(positions == 0.0, axis=-1)] = np.nan
    frames = np.arange(len(positions))
    for marker in range(positions.shape[1]):
        for axis in range(3):
            column = positions[:, marker, axis]
            good = np.isfinite(column)
            if good.any() and not good.all():
                column[~good] = np.interp(frames[~good], frames[good], column[good])
    return positions


def _standardize(positions: np.ndarray, names: list[str]):
    """Average the markers of each standard joint (``markers_mappings.json``): 20 joints from the 41 markers."""
    with open(fetch_data_file("markers_mappings.json"), "r", encoding="utf-8") as handle:
        mapping = json.load(handle)
    position_of = {name: position for position, name in enumerate(names)}
    joints = []
    for aliases in mapping.values():
        present = [position_of[alias] for alias in aliases if alias in position_of]
        joints.append(positions[:, present, :].mean(axis=1) if present else np.full_like(positions[:, 0, :], np.nan))
    return np.stack(joints, axis=1), list(mapping)


def _find_trial_file(stem: str) -> Path:
    """``qualisys/<stem>.tsv.gz`` (a trimmed copy) is preferred to ``qualisys/<stem>.tsv`` (the full export)."""
    try:
        return fetch_data_file(f"qualisys/{stem}.tsv.gz")
    except FileNotFoundError:
        return fetch_data_file(f"qualisys/{stem}.tsv")


@dataclass(frozen=True)
class QualisysTrial:
    """One motion-capture trial.

    Attributes
    ----------
    trial : int
        Trial number (see :data:`QUALISYS_TRIALS`).
    positions : numpy.ndarray
        Shape ``(frames, joints, 3)``, in ``units``.
    labels : tuple of str
        Names of the joints (or of the markers), in the order of the second axis of ``positions``.
    sampling_rate : float
        Frames per second (Hz).
    units : {"mm", "m"}
        Unit of ``positions``. Qualisys exports millimetres and the loader keeps them; see :meth:`to_units`.
    offset : float
        Time in the original recording of the first frame returned, in seconds.
    standardized : bool
        ``True`` for the 20 standard joints, ``False`` for the 41 raw markers.
    """

    trial: int
    positions: np.ndarray
    labels: tuple
    sampling_rate: float = 100.0
    units: str = "mm"
    offset: float = 0.0
    standardized: bool = True

    @property
    def task(self) -> str:
        """Name of the task performed (``"?"`` for a trial number that is not in :data:`QUALISYS_TRIALS`)."""
        return QUALISYS_TRIALS.get(self.trial, ("?", "?"))[0]

    @property
    def condition(self) -> str:
        """Condition of the take, e.g. ``"synchronized"`` (``"?"`` if unknown)."""
        return QUALISYS_TRIALS.get(self.trial, ("?", "?"))[1]

    @property
    def timestamps(self) -> np.ndarray:
        """Time of each frame in seconds, starting at 0 for the first frame returned."""
        return np.arange(len(self.positions)) / self.sampling_rate

    @property
    def duration(self) -> float:
        """Length of the trial in seconds."""
        return len(self.positions) / self.sampling_rate

    def joint(self, name: str) -> np.ndarray:
        """Positions ``(frames, 3)`` of one joint or marker, in ``units``. Raises ``KeyError`` for an unknown name."""
        if name not in self.labels:
            raise KeyError(f"{name!r} is not one of the labels: {', '.join(self.labels)}")
        return self.positions[:, self.labels.index(name), :]

    def window(self, start: float = 0.0, stop: float | None = None) -> "QualisysTrial":
        """The part of the trial between two times in seconds (``stop=None``: to the end), counted from its first frame."""
        first = int(round(start * self.sampling_rate))
        last = None if stop is None else int(round(stop * self.sampling_rate))
        return replace(self, positions=self.positions[first:last], offset=self.offset + first / self.sampling_rate)

    def to_units(self, units: str) -> "QualisysTrial":
        """A copy with ``positions`` converted to ``"m"`` or ``"mm"``. Features take metres by default (``units="m"``)."""
        if units not in _UNIT_SCALE:
            raise ValueError(f"units must be 'm' or 'mm', got {units!r}")
        factor = _UNIT_SCALE[units] / _UNIT_SCALE[self.units]
        return replace(self, positions=self.positions * factor, units=units)

    @property
    def skeleton(self):
        """The :class:`~pyeyesweb.data_models.Skeleton` of the 20 standard joints, to pass as ``skeleton=``.

        Uniform weights, reference ``Pelvis``, couples ``Left_*`` / ``Right_*``. Only for ``standardized=True`` trials.
        """
        if not self.standardized:
            raise ValueError("only the standardized trial (20 joints) has a skeleton; load it with standardize=True")
        from .skeletons import Skeleton
        right_of = {label: "Right_" + label[len("Left_"):] for label in self.labels if label.startswith("Left_")}
        pairs = tuple((left, right) for left, right in right_of.items() if right in self.labels)
        return Skeleton(name="standard20", joints=tuple(self.labels), pairs=pairs, reference="Pelvis",
                        weights=dict.fromkeys(self.labels, 1.0))


def load_qualisys_trial(trial: int | str, *, standardize: bool = True, start: float | None = None,
                        stop: float | None = None) -> QualisysTrial:
    """Load one Qualisys recording of the example session.

    Lost markers (exported as 0, 0, 0) are interpolated linearly over time. With ``standardize=True`` the markers are
    averaged into the 20 standard joints of ``markers_mappings.json`` (``Head``, ``Neck``, ``Spine``, ``Pelvis``, then
    left and right shoulder, elbow, wrist, hand, hip, knee, ankle, foot); otherwise the 41 raw markers are returned.
    Positions stay in millimetres, as exported.

    Parameters
    ----------
    trial : int or str
        Trial number (``7``) or file stem (``"trial7"``).
    standardize : bool, default True
        20 standard joints (True) or raw markers (False).
    start, stop : float, optional
        Keep the frames from ``start`` up to (not including) ``stop``, in seconds of the original recording. A trimmed copy
        of a recording (see ``tools/trim_example_data.py``) holds only a part: asking for a time it does not hold raises
        ``ValueError``. The returned ``timestamps`` start at 0; ``offset`` keeps the original start time.

    Returns
    -------
    QualisysTrial
        The positions, joint names, timestamps, sampling rate and unit of the recording.

    Raises
    ------
    FileNotFoundError
        If the recording is not available (see :func:`fetch_data_file`).
    ValueError
        If the requested times select no frame.

    Examples
    --------
    >>> from pyeyesweb.datasets import load_qualisys_trial
    >>> trial = load_qualisys_trial(11, start=1.0, stop=3.0)
    >>> trial.positions.shape
    (200, 20, 3)
    >>> trial.timestamps[[0, -1]], trial.offset
    (array([0.  , 1.99]), 1.0)
    >>> hand = trial.to_units("m").joint("Right_Hand")           # (200, 3), metres
    >>> hand.shape
    (200, 3)
    """
    stem = f"trial{int(trial)}" if not isinstance(trial, str) else trial.removesuffix(".tsv")
    number = int(stem[len("trial"):]) if stem[len("trial"):].isdigit() else -1
    time, raw, names, rate = _read_tsv(_find_trial_file(stem))
    raw = _fill_lost_markers(raw)
    if standardize:
        raw, names = _standardize(raw, names)
    frame = np.rint(time * rate).astype(int)
    keep = np.ones(len(frame), dtype=bool)
    if start is not None:
        keep &= frame >= int(round(start * rate))
    if stop is not None:
        keep &= frame < int(round(stop * rate))
    if not keep.any():
        raise ValueError(f"{stem}: no frame between {start} s and {stop} s; the file holds "
                         f"{frame[0] / rate:g} s to {(frame[-1] + 1) / rate:g} s of the recording")
    first = frame[keep][0]
    return QualisysTrial(trial=number, positions=raw[keep], labels=tuple(names), sampling_rate=rate, units="mm",
                         offset=float(first / rate), standardized=standardize)
