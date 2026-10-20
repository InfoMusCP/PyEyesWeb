"""Prepare PyKinect2 for 64-bit Python 3.8+ (Kinect v2 / Kinect for Xbox One).

PyKinect2 has not been updated since 2018 and does not import on modern
Python/NumPy. This script, run once with the same Python you use for
``live_kinect_smoothness.py``:

1. upgrades ``comtypes`` if the installed one is the old Python-2 style
   release pulled in by PyKinect2 (SyntaxError "multiple exception types must
   be parenthesized");
2. patches the installed ``pykinect2`` package (a ``.orig`` backup of each
   file is kept, running it twice is harmless):
   * PyKinectV2.py: removes ``_check_version('')`` (incompatible with recent
     comtypes) and makes the ``tagSTATSTG`` size check valid on 64-bit;
   * PyKinectRuntime.py: ``time.clock()`` -> ``time.perf_counter()``
     (removed in Python 3.8), ``numpy.object`` -> ``object`` (removed in
     NumPy 1.24);
3. checks that ``pykinect2`` imports and that a Kinect runtime can be created.

Usage::

    python examples/setup_kinect_v2.py

Requirements: Windows, 64-bit Python, Kinect for Windows SDK 2.0, and
PyKinect2 installed (``pip install pykinect2`` or
``pip install git+https://github.com/Kinect/PyKinect2.git``).
"""

import importlib.util
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path


def step(msg):
    print(f"\n== {msg}")


def run(cmd):
    print("   $", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


def check_comtypes():
    step("comtypes")
    probe = run([sys.executable, "-c", "import comtypes, sys; print(comtypes.__version__)"])
    if probe.returncode == 0:
        version = probe.stdout.strip()
        major_minor = tuple(int(x) for x in re.findall(r"\d+", version)[:2])
        if major_minor >= (1, 2):
            print(f"   comtypes {version}: OK")
            return True
        print(f"   comtypes {version} is too old, upgrading...")
    else:
        print("   comtypes does not import (old Python 2 release), upgrading...")
    res = run([sys.executable, "-m", "pip", "install", "--upgrade", "comtypes>=1.2"])
    print("   " + (res.stdout.strip().splitlines() or [""])[-1])
    if res.returncode != 0:
        print(res.stderr)
        return False
    return True


def find_pykinect2():
    spec = importlib.util.find_spec("pykinect2")
    if spec is None or not spec.submodule_search_locations:
        return None
    return Path(list(spec.submodule_search_locations)[0])


def patch_file(path: Path, rules):
    text = path.read_text(encoding="latin-1")  # byte-preserving (files declare mbcs)
    new = text
    applied = []
    for desc, pattern, repl in rules:
        new, n = re.subn(pattern, repl, new, flags=re.MULTILINE)
        if n:
            applied.append(f"{desc} ({n}x)")
    if new == text:
        print(f"   {path.name}: already patched / nothing to do")
        return
    backup = path.with_suffix(path.suffix + ".orig")
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(new, encoding="latin-1")
    print(f"   {path.name}: " + "; ".join(applied))


V2_RULES = [
    ("removed _check_version",
     r"^(\s*)from comtypes import _check_version; _check_version\(''\)\s*$",
     r"\1# from comtypes import _check_version; _check_version('')  # patched by setup_kinect_v2.py"),
    ("64-bit tagSTATSTG size check",
     r"^assert sizeof\(tagSTATSTG\) == (?!\(72, 80\))[^,\n]+,",
     "assert sizeof(tagSTATSTG) in (72, 80),"),
]

RUNTIME_RULES = [
    ("time.clock -> time.perf_counter", r"\btime\.clock\(\)", "time.perf_counter()"),
    ("numpy.object -> object", r"\bnumpy\.object\b", "object"),
    ("numpy.float -> float", r"\bnumpy\.float\b(?!\d|_)", "float"),
]


def verify():
    step("import test")
    code = ("from pykinect2 import PyKinectV2, PyKinectRuntime; "
            "k = PyKinectRuntime.PyKinectRuntime(PyKinectV2.FrameSourceTypes_Body); "
            "print('Kinect runtime OK, max bodies:', k.max_body_count); k.close()")
    res = run([sys.executable, "-c", code])
    if res.returncode == 0:
        print("   " + res.stdout.strip())
        print("\nAll set. Start the live analysis with:\n"
              "   python examples/live_kinect_smoothness.py --joint right_hand")
        return True
    print(res.stderr.strip()[-2000:])
    print("\nThe import still fails: send this output to get help.")
    return False


def main():
    step("environment")
    bits = struct.calcsize("P") * 8
    print(f"   Python {sys.version.split()[0]} {bits}-bit on {sys.platform}")
    if sys.platform != "win32":
        sys.exit("Kinect v2 only works on Windows.")
    if bits != 64:
        print("   Warning: 32-bit Python; the tagSTATSTG patch is meant for 64-bit.")

    if not check_comtypes():
        sys.exit("Could not upgrade comtypes.")

    step("pykinect2")
    pkg = find_pykinect2()
    if pkg is None:
        sys.exit("pykinect2 is not installed. Run:\n"
                 "   pip install git+https://github.com/Kinect/PyKinect2.git")
    print(f"   found in {pkg}")
    patch_file(pkg / "PyKinectV2.py", V2_RULES)
    patch_file(pkg / "PyKinectRuntime.py", RUNTIME_RULES)

    sys.exit(0 if verify() else 1)


if __name__ == "__main__":
    main()
