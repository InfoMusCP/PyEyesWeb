# Building the docs

To be written (WP8).

## Building and checking

The documentation imports the library, so the compiled core must be importable (an installed package, or `EYESWEB_CORE_PATH`
and `PYTHONPATH` for a development build, see {doc}`../getting_started/install`). From the repository root:

```bash
python -m sphinx -b html -W --keep-going docs docs/_build/html
python -m sphinx -b doctest docs docs/_build/doctest
```

The first command builds the site and turns every warning into an error. The second runs the code of the prose pages and
checks its output: the code blocks of the Getting started and Concepts pages are `{doctest}` directives, and the figures
are `{plot}` blocks executed by the HTML build (inside a `{eval-rst}` block, because the plot directive does not work in
MyST syntax). The `>>>` examples of the docstrings are not run by the Sphinx builder; they are tested with
`python -m pytest --doctest-modules pyeyesweb`.

To refresh the printed output of a `{doctest}` block after a change in the library, run the block, copy the real output
into the page, and run the doctest builder again until it reports no failure.
