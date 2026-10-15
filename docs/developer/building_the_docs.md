# Building the docs

The documentation is built with Sphinx, the PyData theme, MyST Markdown for the prose pages, numpydoc for the docstrings,
`sphinx-design` for cards and tabs, `sphinxcontrib-bibtex` for the references and `sphinx-gallery` for the tutorials. The
toolchain is pinned in `docs/requirements.txt` and is the `docs` extra of the package.

## What the build needs

The documentation imports the library and executes code, so the compiled core must be importable: an installed `eyesweb-core`
package, or a development build named by `EYESWEB_CORE_PATH` ({doc}`../getting_started/install`). If the core is missing, the build
stops at once with a message that says so; it never builds empty API pages. The build prints the version of the core in the footer
of every page, so that a page can be traced to the core it was built with.

## Build and check locally

From the repository root, with the core on the paths (on Windows the two paths are separated by `;`):

```bash
export EYESWEB_CORE_PATH=/path/to/eyesweb_core_build
export PYTHONPATH="$EYESWEB_CORE_PATH:$PWD"
python -m sphinx -b html -W --keep-going docs docs/_build/html
python -m sphinx -b doctest docs docs/_build/doctest
```

`docs/build.ps1` does the same on Windows. It looks for the core in `..\EyesWebCore\build\Release` next to the repository, or in
the folder given with `-Core`, sets `EYESWEB_CORE_PATH` and `PYTHONPATH`, builds with warnings as errors and opens the result;
with `-Live` it rebuilds and reloads in the browser on every save (it needs `sphinx-autobuild`).

```powershell
.\docs\build.ps1 -Core C:\path\to\core\build
```

The first command builds the site and turns every warning into an error (`-W`), reporting all of them (`--keep-going`). The second
is the **doctest builder**. It runs the code of the prose pages and compares its output with the output written in the page.

## Executed code in the pages

One mechanism for text and one for figures.

- A code block that shows behaviour is a `{doctest}` directive with `>>>` lines and the real output. The builder runs the blocks of a
  page in one namespace, in order, with NumPy imported as `np`, and with `ELLIPSIS` and `NORMALIZE_WHITESPACE` on. A block may carry
  `:skipif:` with an expression, as the pages that need the example recordings do. Shell commands and code that cannot run in the
  build are plain fenced blocks.
- A figure is a `{plot}` block, executed by the HTML build, inside an `{eval-rst}` block (the plot directive does not work in MyST
  syntax). A failing figure script is a warning, so `-W` fails.
- The `>>>` examples of the docstrings are not run by the Sphinx builder (they have the globals of their module); they are run by
  `python -m pytest --doctest-modules pyeyesweb`.

To refresh the output of a block after a change in the library, run the block, copy the real output into the page and run the
doctest builder again until it reports no failure. Do not write the output by hand.

## The gallery and its data

The tutorials are the numbered scripts `plot_NN_*.py` in the layer folders of `examples/` (`01_getting_started`,
`02_physical_signals`, ...), each folder with a `GALLERY_HEADER.rst`. `docs/conf.py` runs one gallery per folder, executes every
script on every build and **fails the build when a script raises** (`abort_on_example_error`). The text blocks of a script are
reStructuredText (sphinx-gallery does not read Markdown); the shared plotting functions are in `examples/helpers.py`. The overview
`tutorials/index.rst` is written by `conf.py` from `examples/GALLERY_HEADER.rst`. The gallery writes the run time of each script to
`sphinx-gallery/junit-results.xml` in the output folder.

The scripts read the example recordings through {py:mod}`pyeyesweb.datasets` ({doc}`../howto/load_data`), which looks for a file in
the folder named by `PYEYESWEB_DATA`, then in `examples/data` of a checkout. The recordings are large; `tools/trim_example_data.py`
writes smaller copies to `examples/data_trimmed` that keep only the frames and markers the tutorials read (same format, gzip
compressed, same time column, so `start=` and `stop=` mean the same in both), and the build can use them:

```bash
python tools/trim_example_data.py            # write examples/data_trimmed and print the sizes
export PYEYESWEB_DATA=$PWD/examples/data_trimmed
```

The same script writes the SHA-256 sums of the files to the registry of the module with `--write-registry`. Budgets, to be kept when
a tutorial is added: each script under 60 seconds and the whole gallery under 10 minutes; a script over budget is fixed by slicing
the data, not by dropping the figure.

## How the API pages are generated

The pages of the features are not written by hand. The local extension `docs/_ext/feature_pages.py`, at the start of the build,
reads `pyeyesweb.catalog()` and writes one page for each feature into `docs/api/generated/<layer>/<Name>.rst` (a folder that is not
in the repository). A page holds the title and the summary, the layer, the timescale and the EyesWeb block, the parameters
(from an instance of the class), the inputs and outputs with their units (from `inputs` and `outputs`), the `from_*` constructors, the
docstring through `autodoc`, a link to the theory page of the family and the tutorials that use the feature. Nothing about a feature
is written in the documentation source, so a page cannot drift from the code. The extension also provides the `feature-table`
directive used by the layer pages. It reads three files in `docs/_data/`:

| File | Content |
|---|---|
| `families.yaml` | the family of every feature, and the theory page of each family |
| `instantiation.yaml` | the smallest constructor arguments of the classes that cannot be built with none |
| `wp4_waivers.yaml` | classes whose docstring is allowed not to match the signature; the list can only shrink, and is empty |

The pages of the data models, the skeletons and the catalog types are `autosummary` pages written in `docs/api/`.

## What fails the build

Every item below is an error, not a warning, and a failure in the generator is raised, never skipped.

- any Sphinx warning, because of `-W`: a broken cross-reference, a malformed directive, a missing toctree entry, a figure script that
  fails;
- no importable core of the right version ({doc}`architecture`);
- a catalog feature that is in no family, in two, or a family that names a class that is not in the catalog or a theory page that
  does not exist;
- a class that cannot be instantiated for its page;
- a numpydoc `Parameters` section that lacks a name of the signature or documents one that is not in it (unless the class is in the
  waiver list, and a waiver that is no longer needed is an error too);
- a number of generated pages different from the number of features;
- a gallery script that raises;
- in the doctest build, a `{doctest}` block whose output differs.

Two checks that are planned and not automated yet: that every catalog feature appears in at least one tutorial, and that none of the
names of removed features appears outside the changelog and the porting status. Until then they are checked by a search before a
release.

## Tests of the generator

`tests/unit_tests/test_docs_feature_pages.py` tests the extension: the number of pages equals the number of features, the families
cover the catalog, and the data files agree with the code. It runs with the rest of the suite (`python -m pytest -q`).

## Continuous integration

`.github/workflows/docs.yml` builds the site on every push and pull request with `python -m sphinx -b html -W --keep-going docs
docs/_build/html` on Python 3.11, and deploys to GitHub Pages only from `main`. The workflow installs the package with the `docs`
extra, which brings the compiled core from its binary wheel. That wheel has not been published yet, so the workflow cannot succeed
until the packaging is done, and the documentation is built locally in the meantime as above. The tests run in
`.github/workflows/tests.yml` on three operating systems and Python 3.10 to 3.13; without the core they collect only the tests of the
pure Python data model.
