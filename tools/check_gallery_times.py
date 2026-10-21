"""Fail when a tutorial of the gallery exceeds its run-time budget (60 s per script, 10 min in total).

Usage: python tools/check_gallery_times.py [docs/_build/html/sphinx-gallery/junit-results.xml] [--script 60] [--total 600]
The file is written by sphinx-gallery during the HTML build (``junit`` in docs/conf.py).
"""
import argparse
import sys
import xml.etree.ElementTree as ET


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("junit", nargs="?", default="docs/_build/html/sphinx-gallery/junit-results.xml")
    parser.add_argument("--script", type=float, default=60.0, help="budget of one script, seconds")
    parser.add_argument("--total", type=float, default=600.0, help="budget of the whole gallery, seconds")
    args = parser.parse_args(argv)
    cases = [(case.get("file"), float(case.get("time"))) for case in ET.parse(args.junit).getroot().iter("testcase")]
    if not cases:  # every script was reused from the cache of executed outputs (delete docs/tutorials for a clean run)
        print(f"{args.junit}: no tutorial was run in this build, nothing to check")
        return 0
    total = sum(time for _, time in cases)
    slow = [(name, time) for name, time in cases if time > args.script]
    for name, time in sorted(cases, key=lambda case: -case[1])[:3]:
        print(f"{time:6.1f} s  {name}")
    print(f"{total:6.1f} s  total, {len(cases)} scripts (budgets: {args.script:g} s per script, {args.total:g} s in total)")
    for name, time in slow:
        print(f"over budget: {name} took {time:.1f} s")
    if total > args.total:
        print(f"over budget: the gallery took {total:.1f} s")
    return 1 if slow or total > args.total else 0


if __name__ == "__main__":
    sys.exit(main())
