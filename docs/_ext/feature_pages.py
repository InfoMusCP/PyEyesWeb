"""Generated API pages: one page per ``pyeyesweb.catalog()`` entry, plus the ``feature-table`` directive.

Data driven: names, layers, timescales, summaries, EyesWeb blocks, parameters, inputs and outputs all come from the
library; the only data kept here are ``docs/_data/families.yaml`` (family -> theory page), ``instantiation.yaml``
(minimum constructor arguments, WP0 audit) and ``wp4_waivers.yaml``. Any per-class failure raises: nothing is swallowed.
"""
from __future__ import annotations

import importlib
import inspect
import json
import re
import shutil
from pathlib import Path

import yaml
from docutils import utils
from docutils.parsers.rst import Directive
from docutils.parsers.rst import Parser as RSTParser
from numpydoc.docscrape import ClassDoc
from sphinx.util import logging

import pyeyesweb

logger = logging.getLogger(__name__)
DOCS = Path(__file__).resolve().parent.parent
GENERATED = "api/generated"


# --- data files --------------------------------------------------------------------------------------------------------
def _yaml(path):
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_families(path, entries):
    """Return ``{feature: family_key}`` and the family table; raise unless each catalog feature is assigned exactly once."""
    table = _yaml(path)
    owner = {}
    for key, family in table.items():
        for name in family["features"]:
            if name in owner:
                raise ValueError(f"families.yaml: {name} is assigned twice ({owner[name]}, {key})")
            owner[name] = key
    names = {info.name for info in entries}
    missing, unknown = sorted(names - set(owner)), sorted(set(owner) - names)
    if missing or unknown:
        raise ValueError(f"families.yaml does not match the catalog: no family for {missing}, not in the catalog {unknown}")
    for key, family in table.items():
        if not (DOCS / (family["doc"] + ".md")).exists() and not (DOCS / (family["doc"] + ".rst")).exists():
            raise ValueError(f"families.yaml: theory page {family['doc']} of family {key} does not exist")
    return owner, table


def _model():
    from pyeyesweb.physical_signals import MassSpringModel
    model = MassSpringModel()
    model.add_mass("a", 1.0, (0, 0, 0))
    model.add_mass("b", 1.0, (0.3, 0, 0))
    model.add_spring("s", "a", "b", 0.3, 100.0, (1, 0, 0), 10.0, 1.0, 1.0)
    return model


def instantiate(info, minimum):
    kwargs = {k: (_model() if v == "@mass_spring_model" else v) for k, v in (minimum.get(info.name) or {}).items()}
    try:
        return info.cls(**kwargs)
    except Exception as error:
        raise RuntimeError(f"feature_pages: cannot instantiate {info.name}({kwargs}): {error!r}; "
                           "fix docs/_data/instantiation.yaml") from error


# --- formatting --------------------------------------------------------------------------------------------------------
def _esc(text):
    """Escape plain text for reST."""
    text = re.sub(r"([\\*`|_<>])", r"\\\1", str(text)).replace("\n", " ")
    return re.sub(r"^(\(?[0-9A-Za-z#]{1,3}[.)]|[-+])", r"\\\1", text)  # a table cell must not start a list


def _lit(text):
    return "``" + str(text).replace("`", "'").replace("\n", " ") + "``"


def _type(annotation):
    if annotation is inspect.Parameter.empty:
        return ""
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation).replace("typing.", "").replace("collections.abc.", "")


def _shape(shape):
    if shape is None:
        return "variable"
    if isinstance(shape, int):
        shape = (shape,)
    dims = ["n" if s is None else str(s) for s in shape]
    return "scalar" if not dims else "(" + ", ".join(dims) + (",)" if len(dims) == 1 else ")")


def _table(header, rows, widths):
    out = [".. list-table::", "   :header-rows: 1", "   :widths: " + " ".join(map(str, widths)), ""]
    for row in [header] + rows:
        out.append("   * - " + row[0])
        out += ["     - " + cell for cell in row[1:]]
    return "\n".join(out) + "\n"


def parameter_rows(cls):
    rows = []
    for name, p in inspect.signature(cls).parameters.items():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        default = "*required*" if p.default is inspect.Parameter.empty else _lit(repr(p.default))
        rows.append([_lit(name), default, _lit(_type(p.annotation)) if p.annotation is not p.empty else ""])
    return rows


def constructors(cls):
    return [n for n in dir(cls) if n.startswith("from_") and callable(getattr(cls, n))]


def public_class(info):
    module = importlib.import_module(info.layer.package)
    if getattr(module, info.name, None) is not info.cls:
        raise RuntimeError(f"feature_pages: {info.layer.package}.{info.name} is not the catalog class of {info.name}")
    return module


def render_page(info, family_key, families, feature):
    """The reST text of one feature page."""
    layer = info.layer
    public_class(info)
    family = families[family_key]
    title = info.name
    lines = [f".. _feature-{info.name}:", "", title, "=" * len(title), "", _esc(info.summary), "",
             f":bdg-primary:`{_esc(layer.title)}` :bdg-secondary:`timescale: {_esc(info.timescale.value)}`"
             + (f" :bdg-info:`EyesWeb: {_esc(info.eyesweb_block)}`" if info.eyesweb_block else ""), "",
             f"Layer: :doc:`{_esc(layer.title)} </api/{layer.value}>`. "
             f"Family: :doc:`{_esc(family['title'])} </{family['doc']}>`.", "",
             "Parameters", "----------", ""]
    rows = parameter_rows(info.cls)
    lines.append(_table(["Name", "Default", "Type"], rows, [30, 35, 35]) if rows else "No parameters.\n")
    lines += ["Inputs", "------", ""]
    rows = []
    for i in feature.inputs:
        extra = f"{len(i.labels)} labels" if i.labels else ""
        rows.append([_lit(i.name), _esc(i.kind.value) + (" (optional)" if i.optional else ""), _esc(_shape(i.shape)),
                     _esc(i.unit), _esc("; ".join(x for x in (i.doc, extra) if x))])
    lines.append(_table(["Name", "Kind", "Shape", "Unit", "Description"], rows, [18, 14, 12, 12, 44]))
    lines += ["Outputs", "-------", ""]
    rows = []
    for o in feature.outputs:
        kind = _type(o.kind)
        rows.append([_lit(o.name), _lit(kind), _esc(_shape(o.shape)), _esc(o.unit), _esc(o.doc)])
    lines.append(_table(["Name", "Kind", "Shape", "Unit", "Description"], rows, [18, 10, 12, 14, 46]))
    names = constructors(info.cls)
    lines += [".. py:currentmodule:: " + layer.package, ""]
    if names:
        lines += ["Alternative constructors", "------------------------", ""]
        lines += [f".. automethod:: {info.name}.{n}\n" for n in names]
    lines += ["Description", "-----------", "", f".. autoclass:: {info.name}", "   :no-members:", "   :no-special-members:", "",
              "", "..", "   Gallery back-references: sphinx-gallery writes api/generated/backreferences/<module>.<Class>.examples (the",
              "   thumbnails of the tutorials that use the class) and touches an empty one for every documented class, so the",
              "   include below never fails.", "",
              f".. include:: /{GENERATED}/backreferences/{layer.package}.{info.name}.examples", "",
              ".. raw:: html", "", '   <div class="clearer"></div>', ""]
    return "\n".join(lines)


# --- checks ------------------------------------------------------------------------------------------------------------
def docstring_report(entries, waivers):
    """Per class: does the numpydoc Parameters section exist, and does it cover the signature? Raise on a real mismatch."""
    report, failures, used = [], [], set()
    for info in entries:
        sig = {n for n, p in inspect.signature(info.cls).parameters.items() if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)}
        doc = ClassDoc(info.cls)
        documented = {part.strip() for p in doc["Parameters"] for part in p.name.split(",")}
        has = bool(doc["Parameters"])
        missing, extra = sorted(sig - documented), sorted(documented - sig)
        entry = {"name": info.name, "has_parameters_section": has, "missing": missing, "extra": extra,
                 "needs_wp4": (not has) or bool(missing or extra)}
        report.append(entry)
        if has and (missing or extra):
            if info.name in waivers:
                used.add(info.name)
            else:
                failures.append(f"{info.name}: Parameters section lacks {missing}, documents unknown {extra}")
    unused = sorted(set(waivers) - used)
    if unused:
        failures.append(f"wp4_waivers.yaml lists classes that no longer need a waiver: {unused}")
    if failures:
        raise RuntimeError("feature_pages: docstring Parameters do not match the signature:\n  " + "\n  ".join(failures))
    return report


def generate(entries, out_dir, data_dir):
    """Write one page per entry under ``out_dir/<layer>/<Name>.rst``; return the report (raises on any failure)."""
    out_dir, data_dir = Path(out_dir), Path(data_dir)
    owner, families = load_families(data_dir / "families.yaml", entries)
    minimum = _yaml(data_dir / "instantiation.yaml")
    waivers = _yaml(data_dir / "wp4_waivers.yaml") or []
    report = docstring_report(entries, waivers)
    for layer in {info.layer.value for info in entries}:
        shutil.rmtree(out_dir / layer, ignore_errors=True)
    for info in entries:
        target = out_dir / info.layer.value / f"{info.name}.rst"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(info, owner[info.name], families, instantiate(info, minimum)), encoding="utf-8")
    written = sorted(out_dir.glob("*/*.rst"))
    if len(written) != len(entries):
        raise RuntimeError(f"feature_pages: {len(written)} pages written for {len(entries)} catalog features")
    for info in entries:
        if not (out_dir / info.layer.value / f"{info.name}.rst").exists():
            raise RuntimeError(f"feature_pages: no page for {info.name}")
    (out_dir / "_wp4_todo.json").write_text(json.dumps(
        {"count": sum(r["needs_wp4"] for r in report), "classes": [r for r in report if r["needs_wp4"]]}, indent=1), encoding="utf-8")
    return report


# --- sphinx glue -------------------------------------------------------------------------------------------------------
class FeatureTable(Directive):
    """``.. feature-table:: <layer>``: feature, summary, timescale, family, link."""
    required_arguments = 1
    has_content = False

    def run(self):
        layer = self.arguments[0].strip()
        entries = [i for i in pyeyesweb.catalog() if i.layer.value == layer]
        if not entries:
            raise self.error(f"feature-table: no catalog feature in layer {layer!r}")
        owner, families = load_families(DOCS / "_data/families.yaml", pyeyesweb.catalog())
        rows = [[_lit(i.name), _esc(i.summary), _esc(i.timescale.value),
                 f":doc:`{_esc(families[owner[i.name]]['title'])} </{families[owner[i.name]]['doc']}>`",
                 f":doc:`API </{GENERATED}/{layer}/{i.name}>`"] for i in entries]
        text = _table(["Feature", "Summary", "Timescale", "Family", "Link"], rows, [20, 38, 10, 20, 12])
        # The table is reStructuredText whatever the page is written in: parse it with the RST parser, not with the state
        # machine of the page (on a MyST page that one reads Markdown and would print the list-table as a paragraph).
        document = utils.new_document(self.state.document.current_source, self.state.document.settings)
        RSTParser().parse(text, document)
        return document.children


def _builder_inited(app):
    entries = pyeyesweb.catalog()
    report = generate(entries, Path(app.srcdir) / GENERATED, DOCS / "_data")
    todo = sum(r["needs_wp4"] for r in report)
    logger.info("feature_pages: %d pages generated; docstring needs WP4: %d of %d (docs/api/generated/_wp4_todo.json)",
                len(entries), todo, len(entries))


def setup(app):
    app.add_directive("feature-table", FeatureTable)
    app.connect("builder-inited", _builder_inited)
    return {"version": "1.0", "parallel_read_safe": True}
