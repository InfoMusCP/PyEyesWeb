"""Regenerate the "Implemented in the library" tables of the layer pages from `pyeyesweb.catalog()`.

Needs the compiled EyesWeb core (set EYESWEB_CORE_PATH to a development build), which the layer packages import.
    python tools/update_catalog_docs.py
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

from pyeyesweb import Layer, catalog_table  # noqa: E402

PAGES = {
    Layer.PHYSICAL_SIGNALS: "physical_signals/physical_signals.md",
    Layer.LOW_LEVEL: "low_level/low_level.md",
    Layer.MID_LEVEL: "mid_level/mid_level.md",
    Layer.ANALYSIS_PRIMITIVE: "analysis_primitives/analysis_primitives.md",
}
START, END = "<!-- catalog:start -->", "<!-- catalog:end -->"
BASE = ROOT / "docs" / "user_guide" / "theoretical_framework"

for layer, page in PAGES.items():
    path = BASE / page
    text = path.read_text(encoding="utf8")
    block = (f"{START}\n## Implemented in the library\n\n"
             f"Generated from `pyeyesweb.catalog(Layer.{layer.name})`; import from `{layer.package}`.\n\n"
             f"{catalog_table(layer)}\n{END}")
    if START in text:
        text = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf8")
    print("updated", path.relative_to(ROOT))
