# gen_pages.py
"""
Auto-generate API documentation pages with mkdocs-gen-files + mkdocstrings.
Generates individual module pages and an API landing page with intro text only.
Navigation is handled by SUMMARY.md + literate-nav sidebar.
"""

from pathlib import Path
import mkdocs_gen_files

# -------- SETTINGS --------
PACKAGE_NAME = "core"
SRC_DIR = Path("core")
API_DOCS_PATH = Path("API")
# --------------------------

nav = mkdocs_gen_files.Nav()

# Generate individual module pages and build nav
for path in sorted(SRC_DIR.rglob("*.py")):
    module_path = path.relative_to(SRC_DIR).with_suffix("")
    doc_path = API_DOCS_PATH / path.relative_to(SRC_DIR).with_suffix(".md")
    module_name = ".".join(module_path.parts)

    # Skip empty __init__.py modules if desired
    if module_name.endswith("__init__"):
        continue

    # Add to literate-nav
    nav[module_path.parts] = doc_path.relative_to(API_DOCS_PATH).as_posix()

    # Generate module page
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with mkdocs_gen_files.open(doc_path, "w") as f:
        print(f"::: {PACKAGE_NAME}.{module_name}", file=f)

    mkdocs_gen_files.set_edit_path(doc_path, path)

# Write SUMMARY.md for sidebar navigation
with mkdocs_gen_files.open(API_DOCS_PATH / "SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())

# Generate API landing page (intro text only)
with mkdocs_gen_files.open(API_DOCS_PATH / "index.md", "w") as f:
    f.write(
        f"# API Reference\n\n"
        f"This section contains the **automatically generated reference documentation** for the `{PACKAGE_NAME}` package.\n\n"
        f"You can browse the modules using the sidebar navigation.\n"
    )