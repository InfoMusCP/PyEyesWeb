"""Trim the example recordings to what the tutorials need (TEACHING_PLAN section 5).

Reads ``examples/data/qualisys/trial*.tsv`` and writes smaller copies to ``examples/data_trimmed/`` (git-ignored for
now): the same Qualisys TSV format, gzip-compressed (``trial7.tsv.gz``; ``pyeyesweb.datasets`` reads both), only the frames between two times and only the markers that the
tutorials use (sensor data only: the video recordings of the sessions are private and not in the repository).
``examples/data`` is never modified. The result is a drop-in replacement for the data folder:
``PYEYESWEB_DATA=examples/data_trimmed`` makes ``pyeyesweb.datasets`` read the trimmed files.

    python tools/trim_example_data.py                 # write examples/data_trimmed/ and print the size table
    python tools/trim_example_data.py --dry-run       # only print the size table
    python tools/trim_example_data.py --write-registry   # also write the SHA-256 sums to pyeyesweb/_datasets_registry.py

Rules (the numbers are in ``PLAN`` below, one line per trial, with the script that needs it):

* time range: the frames the scripts read (``start`` inclusive, ``stop`` exclusive, seconds of the original recording).
  Time and frame columns keep their original values, so ``load_qualisys_trial(7, start=2, stop=17)`` selects the same
  frames in the full and in the trimmed file;
* markers: the ones named in ``markers_mappings.json`` (the 20 standard joints are built from them) for every trial, plus
  all 41 raw markers for the trials in ``RAW_MARKERS`` (scripts that use ``standardize=False``);
* values are copied as text, nothing is re-formatted, the file is gzipped with a fixed timestamp (reproducible sums); ``markers_mappings.json`` is copied as it is.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples" / "data"
TARGET = ROOT / "examples" / "data_trimmed"
REGISTRY = ROOT / "pyeyesweb" / "_datasets_registry.py"

# trial: (start, stop, scripts that read it); seconds of the original recording
PLAN = {
    3: (5, 21, "03 hit cells, 06 symmetry, 09 synchronization"),
    4: (5, 21, "06 symmetry, 09 synchronization"),
    5: (5, 21, "06 symmetry, 09 synchronization"),
    6: (5, 21, "06 symmetry, 09 synchronization"),
    7: (0, 21, "01 getting started, 02 the contract, 03 humanoid, 08 analysis primitives, 09 synchronization"),
    8: (5, 21, "06 symmetry, 09 synchronization"),
    10: (0, 16, "03 hit cells, 06 symmetry"),
    11: (0, 14, "05 smoothness, 08 entropy"),
    12: (0, 14, "05 smoothness, 08 entropy"),
    13: (0, 12, "05 smoothness, 06 contour"),
    14: (0, 12, "05 smoothness, 06 contour"),
    17: (0, 16, "06 contraction"),
    18: (0, 16, "03 hit cells (raw markers), 06 contraction"),
    19: (0, 16, "06 equilibrium"),
    20: (0, 24, "07 impulsivity, 08 rarity"),
    21: (0, 24, "05 energy, 07 segmentation and suddenness, 08 rarity"),
    22: (0, 24, "07 segmentation"),
    23: (0, 24, "07 suddenness"),
    24: (0, 24, "07, 08 rarity"),
    25: (0, 24, "05 energy (raw markers), 07 segmentation"),
}
RAW_MARKERS = {18, 25}


def trim(text: str, start: float, stop: float, keep: set[str] | None):
    """Return the trimmed TSV text of one trial, the number of frames kept and the markers kept."""
    lines = text.splitlines()
    top = next(i for i, line in enumerate(lines) if line.startswith("Frame\t"))
    columns = lines[top].split("\t")
    markers = [c[:-2].strip() for c in columns if c.endswith(" X")]
    wanted = [m for m in markers if keep is None or m in keep]
    pick = [0, 1] + [columns.index(f"{m} {a}") for m in wanted for a in "XYZ"]
    rate = float(next(line.split("\t")[1] for line in lines[:top] if line.startswith("FREQUENCY")))
    first, last = int(round(start * rate)), int(round(stop * rate))
    body = []
    for line in lines[top + 1:]:
        if not line.strip():
            continue
        cells = line.split("\t")
        if first <= int(round(float(cells[1]) * rate)) < last:
            body.append("\t".join(cells[i] for i in pick))
    header = []
    for line in lines[:top]:
        key = line.split("\t")[0]
        if key == "NO_OF_FRAMES":
            line = f"NO_OF_FRAMES\t{len(body)}"
        elif key == "NO_OF_MARKERS":
            line = f"NO_OF_MARKERS\t{len(wanted)}"
        elif key == "MARKER_NAMES":
            line = "MARKER_NAMES\t" + "\t".join(wanted)
        elif key == "TRAJECTORY_TYPES":
            line = "TRAJECTORY_TYPES\t" + "\t".join(["Measured"] * len(wanted))
        elif key == "DESCRIPTION":
            line = f"DESCRIPTION\ttrimmed copy, {start:g} s to {stop:g} s of the original recording"
        header.append(line)
    columns_out = [columns[0], columns[1]] + [f"{m} {a}" for m in wanted for a in "XYZ"]
    return "\n".join(header + ["\t".join(columns_out)] + body) + "\n", len(body), wanted


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print the size table, write nothing")
    parser.add_argument("--write-registry", action="store_true", help="write the SHA-256 sums to pyeyesweb/_datasets_registry.py")
    args = parser.parse_args()

    mapping = json.loads((SOURCE / "markers_mappings.json").read_text(encoding="utf-8"))
    standard = {alias for aliases in mapping.values() for alias in aliases}
    sums, total_in, total_out = {}, 0, 0
    print(f"{'trial':>5} {'window (s)':>11} {'markers':>8} {'frames':>7} {'original MB':>12} {'trimmed MB':>11}  needed by")
    for trial, (start, stop, why) in PLAN.items():
        source = SOURCE / "qualisys" / f"trial{trial}.tsv"
        text, frames, kept = trim(source.read_text(encoding="utf-8", errors="replace"), start, stop,
                                  None if trial in RAW_MARKERS else standard)
        data = gzip.compress(text.encode("utf-8"), 9, mtime=0)       # mtime=0: the same bytes (and sum) on every run
        total_in += source.stat().st_size
        total_out += len(data)
        sums[f"qualisys/trial{trial}.tsv.gz"] = hashlib.sha256(data).hexdigest()
        print(f"{trial:>5} {start:>5g}-{stop:<5g} {len(kept):>8} {frames:>7} {source.stat().st_size / 1e6:>12.2f} "
              f"{len(data) / 1e6:>11.2f}  {why}")
        if not args.dry_run:
            (TARGET / "qualisys").mkdir(parents=True, exist_ok=True)
            (TARGET / "qualisys" / (source.name + ".gz")).write_bytes(data)
    mapping_bytes = (SOURCE / "markers_mappings.json").read_bytes()
    sums["markers_mappings.json"] = hashlib.sha256(mapping_bytes).hexdigest()
    total_out += len(mapping_bytes)
    if not args.dry_run:
        TARGET.mkdir(exist_ok=True)
        (TARGET / "markers_mappings.json").write_bytes(mapping_bytes)
    print(f"{'total':>5} {'':>11} {'':>8} {'':>7} {total_in / 1e6:>12.2f} {total_out / 1e6:>11.2f}   (qualisys + mapping)")
    if args.write_registry and not args.dry_run:
        rows = "".join(f'    "{name}": "{digest}",\n' for name, digest in sorted(sums.items()))
        REGISTRY.write_text('"""SHA-256 sums of the example data files that can be downloaded (``pyeyesweb.datasets``).\n\n'
                            'Written by ``tools/trim_example_data.py --write-registry``: name relative to the data folder -> hex\n'
                            'digest of the trimmed file. The files are not hosted yet (``pyeyesweb.datasets.BASE_URL`` is None).\n'
                            '"""\n\nREGISTRY: dict[str, str] = {\n' + rows + "}\n", encoding="utf-8")
        print(f"registry written: {REGISTRY}")


if __name__ == "__main__":
    main()
