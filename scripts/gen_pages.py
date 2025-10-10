# gen_pages.py
"""
Auto-generate API documentation pages with mkdocs-gen-files + mkdocstrings.
Generates individual module pages and an API landing page with intro text only.
Navigation is handled by SUMMARY.md + literate-nav sidebar.
"""

from pathlib import Path
import mkdocs_gen_files

# -------- SETTINGS --------
PACKAGE_NAME = "pyeyesweb"
SRC_DIR = Path("pyeyesweb")
API_DOCS_PATH = Path("API")
# --------------------------

nav = mkdocs_gen_files.Nav()

def format_module_name(name):
    return " ".join(part.capitalize() for part in name.split("_"))


# Generate individual module pages and build nav
for path in sorted(SRC_DIR.rglob("*.py")):
    module_path = path.relative_to(SRC_DIR).with_suffix("")
    doc_path = API_DOCS_PATH / path.relative_to(SRC_DIR).with_suffix(".md")
    module_name = ".".join(module_path.parts)

    # Skip empty __init__.py user_guide if desired
    if module_name.endswith("__init__"):
        continue

    # Add to literate-nav
    formatted_nav = tuple(format_module_name(part) for part in module_path.parts)
    nav[formatted_nav] = doc_path.relative_to(API_DOCS_PATH).as_posix()

    # Generate module page
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with mkdocs_gen_files.open(doc_path, "w") as f:
        f.write(f"# {format_module_name(module_path.name)}\n\n")
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