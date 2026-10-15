# Sphinx configuration of the PyEyesWeb documentation.
#
# Local build (from the PyEyesWeb root; the compiled core is a development build, see DOCS_PLAN.md section 4.5):
#   MSYS_NO_PATHCONV=1 PYTHONPATH="C:/Users/Nicola/Desktop/CP/EwbTD/EyesWebCore/build/Release;C:/Users/Nicola/Desktop/CP/EwbTD/PyEyesWeb" EYESWEB_CORE_PATH=C:/Users/Nicola/Desktop/CP/EwbTD/EyesWebCore/build/Release C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe -m sphinx -b html -W --keep-going docs docs/_build/html
# In CI the core comes from the eyesweb-core wheel (`pip install .[docs]`), no path variables are needed.

import doctest
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.abspath(".."))  # repository root: the library is imported, not installed
sys.path.insert(0, os.path.abspath("_ext"))

# --- the docs describe the library, so the compiled core must be importable: never build empty API pages ---------------
try:
    import pyeyesweb
    from pyeyesweb import _core
except ImportError as error:
    raise RuntimeError(
        "The documentation cannot be built: pyeyesweb could not load the compiled EyesWeb core.\n"
        "Install the eyesweb-core wheel (pip install .[docs]) or set EYESWEB_CORE_PATH to a development build of the core.\n"
        f"Original error: {error}"
    ) from error

core_version = _core.core.__version__
core_build = getattr(_core.core, "__build__", "unknown")

# --- project ---------------------------------------------------------------------------------------------------------
project = "PyEyesWeb"
author = "Casa Paganini - InfoMus"
copyright = f"{date.today().year}, {author}"
try:
    from importlib.metadata import version as _dist_version
    release = _dist_version("pyeyesweb")
except Exception:  # not installed (development tree): read it from pyproject.toml
    import tomllib
    with open(os.path.abspath("../pyproject.toml"), "rb") as _f:
        release = tomllib.load(_f)["project"]["version"]
version = ".".join(release.split(".")[:2])

# --- extensions ------------------------------------------------------------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "numpydoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",  # {doctest} blocks of the prose pages are executed and their output checked (see below)
    "matplotlib.sphinxext.plot_directive",  # {plot} blocks: figures of the prose pages rendered from code at build time
    "sphinx.ext.viewcode",  # Python source only (the repository is public Python)
    "sphinx.ext.githubpages",
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx_copybutton",
    "myst_parser",
    "sphinx_gallery.gen_gallery",  # the tutorials: examples/*/plot_NN_*.py (settings in sphinx_gallery_conf below)
    "feature_pages",  # docs/_ext/feature_pages.py: one page per catalog feature (DOCS_PLAN 4.2)
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "_legacy", "_snippets", "Thumbs.db", ".DS_Store"]  # _snippets: internal fact sheet (docs/_snippets/facts.md), never published

autosummary_generate = True
autodoc_typehints = "none"
numpydoc_show_class_members = False  # member tables come from autosummary templates (WP3)
numpydoc_class_members_toctree = False

# --- executed code in the prose pages (DOCS_PLAN WP5) ----------------------------------------------------------------------
# Text: {doctest} blocks, checked with `python -m sphinx -b doctest docs docs/_build/doctest`. Figures: {plot} blocks,
# executed by the HTML build (a failing figure script is a warning, so -W fails). No other code block is Python.
doctest_global_setup = """
import numpy as np
"""
doctest_default_flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
# The `>>>` examples of the docstrings (shown on the API pages) are run by `pytest --doctest-modules pyeyesweb`, which gives
# them the globals of their module; the Sphinx builder must not run them again: only the {doctest} directives are tested.
doctest_test_doctest_blocks = ""
plot_include_source = True
plot_apply_rcparams = True
plot_html_show_source_link = False
plot_html_show_formats = False
plot_formats = [("png", 110)]
plot_rcparams = {"figure.figsize": (6.4, 3.0), "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
                 "figure.dpi": 110, "savefig.bbox": "tight"}
# nitpicky = True  # TODO(WP9): once the page set is stable (DOCS_PLAN 4.1)

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

# --- references (docs/references.bib; any supported style is accepted, DOCS_PLAN 4.3) --------------------------------------
bibtex_bibfiles = ["references.bib"]
bibtex_default_style = "unsrt"
bibtex_reference_style = "label"  # numeric labels

# --- MyST (prose pages) ----------------------------------------------------------------------------------------------
myst_enable_extensions = ["colon_fence", "deflist", "dollarmath", "amsmath", "substitution"]
myst_heading_anchors = 3

_counts = {}
for _info in pyeyesweb.catalog():
    _counts[_info.layer.value] = _counts.get(_info.layer.value, 0) + 1
# Feature counts for the landing page, computed from catalog(): {{ n_low_level }} etc. in the Markdown.
myst_substitutions = {f"n_{layer}": str(n) for layer, n in _counts.items()}
myst_substitutions["n_features"] = str(sum(_counts.values()))
myst_substitutions["core_version"] = core_version

# --- HTML ------------------------------------------------------------------------------------------------------------
html_theme = "pydata_sphinx_theme"
html_title = f"PyEyesWeb {release}"
html_static_path = ["_static", "assets"]  # assets/ is served so that the logo paths below resolve
html_css_files = ["custom.css"]
html_favicon = "assets/favicon-32x32.png"
html_theme_options = {
    # The PNG mark is dark grey on transparent: the dark variant is a light copy (docs/_static/eyesweb-logo-dark.png).
    "logo": {
        "text": "PyEyesWeb",
        "image_light": "eyesweb-logo.png",
        "image_dark": "eyesweb-logo-dark.png",
    },
    "icon_links": [
        {"name": "GitHub", "url": "https://github.com/InfoMusCP/PyEyesWeb", "icon": "fa-brands fa-github"},
    ],
    "navigation_with_keys": False,
    "show_toc_level": 2,
    "footer_start": ["copyright", "core_version"],
    "footer_end": ["sphinx-version", "theme-version"],
    # TODO(WP9): footer logos (cp-logo, eu-logo, resilence-logo) and version switcher (decision open).
}
html_sidebars = {"index": []}
html_context = {"core_version": core_version, "core_build": core_build}
templates_path = ["_templates"]

# --- sphinx-gallery: the tutorials (TEACHING_PLAN.md; conventions: DOCS_PLAN.md, "WP7 stage 1 conventions") --------------------
# The scripts of examples/ are run on every build; an error fails the build (abort_on_example_error). `import helpers` works
# because examples/ is put on sys.path here (a downloaded notebook fetches helpers.py, see first_notebook_cell).
sys.path.insert(0, os.path.abspath("../examples"))
from tutorial_reset import reset_tutorial_state  # noqa: E402  (docs/_ext)
_HELPERS_URL = "https://raw.githubusercontent.com/InfoMusCP/PyEyesWeb/main/examples/helpers.py"  # TODO(release): pin to the tag


_EXAMPLES = Path(os.path.abspath("../examples"))
# One sphinx-gallery per layer folder (examples/NN_name/ with a GALLERY_HEADER.rst and at least one plot_NN_*.py), not one
# gallery with sub-sections: sphinx-gallery would also pick up any other folder of examples/ that has a README (the
# git-ignored reviewer folder examples/scratch has one). tutorials/index.rst, the overview, is written below from
# examples/GALLERY_HEADER.rst plus a table of contents of the layer galleries.
_TUTORIAL_FOLDERS = sorted(folder.name for folder in _EXAMPLES.iterdir()
                           if re.fullmatch(r"\d\d_\w+", folder.name) and (folder / "GALLERY_HEADER.rst").is_file()
                           and any(folder.glob("plot_[0-9][0-9]_*.py")))


def _write_tutorials_overview(app, config):
    """tutorials/index.rst (generated, git-ignored): the text of examples/GALLERY_HEADER.rst and the list of the galleries."""
    target = Path(app.srcdir) / "tutorials"
    target.mkdir(exist_ok=True)
    text = (_EXAMPLES / "GALLERY_HEADER.rst").read_text(encoding="utf-8")
    contents = "".join(f"   {name}/index\n" for name in _TUTORIAL_FOLDERS)
    page = f".. _tutorials:\n\n{text}\n\n.. toctree::\n   :maxdepth: 1\n\n{contents}"
    (target / "index.rst").write_text(page, encoding="utf-8")


def setup(app):
    app.connect("config-inited", _write_tutorials_overview)


# sphinx-gallery replaces entries of its configuration by functions and classes while the build runs, which Sphinx cannot pickle
# for its config cache (only used to detect a changed configuration between two builds): the warning is of no use here.
suppress_warnings = ["config.cache"]

sphinx_gallery_conf = {
    "examples_dirs": [f"../examples/{name}" for name in _TUTORIAL_FOLDERS],  # one gallery per layer folder (see above)
    "gallery_dirs": [f"tutorials/{name}" for name in _TUTORIAL_FOLDERS],  # generated and git-ignored, like tutorials/index.rst
    "filename_pattern": r"[/\\]plot_\d\d_",  # only the numbered tutorials run: plot_01_first_feature.py, ...
    "ignore_pattern": r"^(?!plot_)",  # a file that is not a numbered tutorial is not a tutorial (helpers.py, ...)
    "within_subsection_order": "FileNameSortKey",
    "backreferences_dir": "api/generated/backreferences",  # "Examples using X" on the generated API pages (feature_pages.py)
    "doc_module": ("pyeyesweb",),
    "reference_url": {"pyeyesweb": None},  # links to the pages of this documentation
    "abort_on_example_error": True,
    "plot_gallery": True,
    "download_all_examples": True,
    "remove_config_comments": True,
    "capture_repr": ("_repr_html_", "__repr__"),
    "image_scrapers": ("matplotlib",),
    "thumbnail_size": (320, 240),
    "min_reported_time": 5,  # seconds: slower tutorials are listed in the build output
    "show_memory": False,
    "reset_modules": ("matplotlib", reset_tutorial_state),  # matplotlib's own reset, then ours (dpi, seed, print options)
    "reset_modules_order": "both",
    "expected_failing_examples": [],
    "run_stale_examples": False,
    "junit": "sphinx-gallery/junit-results.xml",  # under the HTML output folder: run time of each script, checked in CI
    "default_thumb_file": os.path.abspath("assets/eyesweb-logo.png"),  # card of a tutorial whose figures give no thumbnail
    # Only the downloaded notebook gets this first cell (never the HTML page): installation, inline figures, helpers.py.
    "first_notebook_cell": (
        "%pip install --quiet pyeyesweb[datasets] matplotlib pandas\n"
        "%matplotlib inline\n"
        "# helpers.py (the plotting functions of the tutorials) is fetched once, next to this notebook\n"
        "from pathlib import Path\n"
        "if not Path('helpers.py').exists():\n"
        "    import urllib.request\n"
        f"    urllib.request.urlretrieve('{_HELPERS_URL}', 'helpers.py')"
    ),
}
