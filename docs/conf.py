# Sphinx configuration of the PyEyesWeb documentation.
#
# Local build (from the PyEyesWeb root; the compiled core is a development build, see DOCS_PLAN.md section 4.5):
#   MSYS_NO_PATHCONV=1 PYTHONPATH="C:/Users/Nicola/Desktop/CP/EwbTD/EyesWebCore/build/Release;C:/Users/Nicola/Desktop/CP/EwbTD/PyEyesWeb" EYESWEB_CORE_PATH=C:/Users/Nicola/Desktop/CP/EwbTD/EyesWebCore/build/Release C:/Users/Nicola/Desktop/CP/EwbTD/.venv/Scripts/python.exe -m sphinx -b html -W --keep-going docs docs/_build/html
# In CI the core comes from the eyesweb-core wheel (`pip install .[docs]`), no path variables are needed.

import os
import sys
from datetime import date

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
    "sphinx.ext.viewcode",  # Python source only (the repository is public Python)
    "sphinx.ext.githubpages",
    "sphinxcontrib.bibtex",
    "sphinx_design",
    "sphinx_copybutton",
    "myst_parser",
    # "sphinx_gallery.gen_gallery",  # TODO(WP7): enable together with sphinx_gallery_conf below
    "feature_pages",  # docs/_ext/feature_pages.py: one page per catalog feature (DOCS_PLAN 4.2)
]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "_legacy", "_snippets", "Thumbs.db", ".DS_Store"]  # _snippets: internal fact sheet (docs/_snippets/facts.md), never published

autosummary_generate = True
autodoc_typehints = "none"
numpydoc_show_class_members = False  # member tables come from autosummary templates (WP3)
numpydoc_class_members_toctree = False
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

# --- sphinx-gallery (TODO(WP7)): examples/ has no gallery scripts yet. Enable with the settings of TEACHING_PLAN.md section 1:
# sphinx_gallery_conf = {
#     "examples_dirs": "../examples", "gallery_dirs": "tutorials",
#     "filename_pattern": r"/\d\d_", "ignore_pattern": r"helpers\.py|build\.py",
#     "backreferences_dir": "api/generated/backreferences", "doc_module": ("pyeyesweb",),
#     "abort_on_example_error": True, "download_all_examples": True, "remove_config_comments": True,
# }
