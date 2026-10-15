# Adding a feature

This page lists, in order, what a new feature needs. A feature that is not described, exported and tested through the catalog does
not exist as far as users and the documentation are concerned, so the steps are short and each one is checked by a test or by the
documentation build. Read {doc}`architecture` and {doc}`conventions` first.

A feature is either backed by a block of the compiled core (the usual case for an algorithm) or written in Python on the contract
alone. A new block in the core is added in the repository of the core, which is not part of this one; it must be exposed with a Python
binding that names every parameter descriptively and gives it a default, because the signature of the Python class is derived from
it. The steps below start from the point where the block can be imported.

## 1. Decide where it goes

The layer is the one whose timescale and meaning fit the feature, not the layer of its EyesWeb block. The placement rule is in the
docstring of {py:func}`pyeyesweb.catalog`.

- *Physical signals*: gives a signal again from raw frames or from a model (a body simulation, centroids of an image).
- *Low-level*: measures one frame, or a short window the feature buffers itself, including the shape of a contour and a path given as
  a list of points.
- *Mid-level*: needs a whole gesture.
- *High-level*: needs several people.
- *Analysis primitive*: takes any scalar, vector or event signal and knows nothing of bodies, skeletons or geometry.

Put the class in a module of the package of the layer (`pyeyesweb/low_level/directness.py` is a small example).

## 2. Write the class

1. Choose the base class: `CoreFeature` (or `FrameFeature`) for a block of the core, `WindowedFeature` for a feature on a window
   that it buffers, `VariantFeature` when one name covers several algorithms chosen by `method=`, or `Feature` for the contract
   alone.
2. Decorate it with `@describe(Layer.X, eyesweb="<block>")`. Give `timescale=` only when the feature differs from the default of its
   layer, and omit `eyesweb` for a feature of the laboratory. The catalog summary is the first line of the docstring.
3. Declare the outputs: `_OUTPUTS = Schema(Output(...))` for fixed outputs, or `_schema()` when they depend on the parameters (call
   `_outputs_changed()` from a setter that changes them). **Every numeric output has a unit** (`"<length>"`, `"<input>"`, `"s"`, ...);
   a dimensionless output is listed with its reason in `tests/unit_tests/test_units_all_features.py`. A boolean output is named
   `is_<something>`.
4. Declare the inputs: `_INPUTS = Inputs(Input(...))` or `_inputs()`. Do not check shapes yourself; the central check does it.
5. Implement `process` (or the private window hook of `WindowedFeature` for a window; it is never public). Return `self._result(...)` or
   `self._no_output(...)`. Do not check for NaN, missing joints or timestamps: the wrappers do.
6. Parameters: keyword-only after `window, hop` and after the joint arguments, each annotated, with the single public spelling of the
   concept, and `sampling_rate=None` as the default rate. Use `_unit_params`, `_timed`, `_rate_required`, `_core_names` and `_parts`
   where they apply instead of writing the logic again. Mark in the docstring which parameters are live and which structural; a
   structural parameter is one that sizes the state, and when in doubt it is structural.
7. Export the class in the `__init__` of the layer package and in its `__all__`.

## 3. Docstring checklist

The generated page is built from the docstring and fails to build when it does not cover the signature. Check each item
({doc}`conventions` describes them).

- [ ] One-sentence summary of at most 100 characters.
- [ ] What it measures, with the definition in mathematics and the notation of the theory pages.
- [ ] `Parameters`: every parameter of the signature, with type, default, unit, allowed strings and *(live)* or *(structural)*.
- [ ] `Notes`: inputs, outputs (unit and range, as in the schema), statuses and warm-up, EyesWeb origin, **Corrected in the core** if it
  applies, limits.
- [ ] `References`: keys of `docs/references.bib` only; add the entry to the file first, or write **[citation needed]**.
- [ ] `Examples`: at most ten lines, synthetic data, runs under `python -m pytest --doctest-modules pyeyesweb`.
- [ ] No mention of a private method, a removed class or an old parameter name.

## 4. Tests

Three kinds of tests are needed, and the first of them is nearly free.

1. **The catalog-wide suites** find the feature through `catalog()` and run on it without change: the contract suite (`process` and
   `run` agree, reset, chunked runs, wrong shape), the invariants (non-finite input, empty outputs, a rejected call changes nothing),
   the time rule, live validation of parameters, units, choices, naming and signatures. A feature that cannot be built with no
   arguments or driven by random data of its declared inputs needs an entry in `OVERRIDES` of
   `tests/unit_tests/test_contract_all_features.py` (a factory and a recording), or an entry in `NOT_COVERED` with the reason; the
   suite fails when the table and the catalog disagree. Every parameter also needs a row in the live-parameter tests
   (`test_live_parameters*.py`), live or structural, with a recording on which the check runs.
2. **Known answers**: inputs whose result follows from the definition, or whose ordering is certain.
3. **Error cases**: wrong shape, NaN, too short, an invalid parameter at construction and at the setter.

Frozen data are added to `tests/data` only with a description in its `README.md` and, if possible, a script in `tools/` that
regenerates them. `pytest -q` must pass with no numeric test edited ({doc}`conventions`).

## 5. Documentation

The documentation build uses the catalog, so most of the work is done by it.

1. **Family.** Add the class to exactly one family in `docs/_data/families.yaml`. A family names a theory page. The build fails when
   a catalog feature is in no family, in two, or when the file names a class that is not in the catalog.
2. **Instantiation.** The generated page needs an instance to read the inputs and outputs. A class that cannot be built with no
   arguments needs its smallest arguments in `docs/_data/instantiation.yaml` (for example `{window: 50}`); the build fails with the
   class name when it cannot build one.
3. **Theory and user guide.** Describe the feature on the theory page of its family, in the notation of
   {doc}`../theory/notation`, and link it from the user guide of its layer.
4. **Reference.** Add the references to `docs/references.bib`.
5. **Gallery.** Every feature should appear in a tutorial of the gallery in `examples/`, on data that run within the budget of the
   gallery. The check that every catalog feature appears in at least one tutorial is not automated yet; the "Examples using ..."
   block of the generated page is built from the tutorials that use it, so a feature that is in no tutorial has an empty one.
6. **Build.** Run the build and the doctest builder ({doc}`building_the_docs`); both must report no warning and no failure.

## 6. Before you say it is done

- The whole test suite passes, including the naming test and `--doctest-modules`.
- The documentation builds with warnings as errors, and the page of the new class has its parameters, inputs, outputs and units.
- Nothing in the change adds public API that the conventions forbid: enumerations as parameters, time-mode parameters, flags that switch a correction on or off,
  `**params` in a public signature, a public window hook, one-character names.
- For a port of an EyesWeb block: document every deviation from the original that changes numbers in the `Notes` of the docstring. A
  deviation needs a decision of the maintainers; once decided it is the behaviour of the core, with no flag ({doc}`porting_status`).
