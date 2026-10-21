# API reference

The catalog holds {{ n_features }} features in four layers and the analysis primitives (see {doc}`/concepts/layers`). Every feature has one generated page with its parameters, inputs, outputs and description, built from the code and from `pyeyesweb.catalog()`.

| Layer | Features |
|---|---|
| {doc}`physical_signals` | {{ n_physical_signals }} |
| {doc}`low_level` | {{ n_low_level }} |
| {doc}`mid_level` | {{ n_mid_level }} |
| {doc}`high_level` | {{ n_high_level }} |
| {doc}`analysis_primitives` | {{ n_analysis_primitives }} |

The shared building blocks are in {doc}`data_models` and {doc}`skeletons`; the catalog itself is described in {doc}`catalog`.

```{toctree}
:maxdepth: 1

physical_signals
low_level
mid_level
high_level
analysis_primitives
data_models
skeletons
datasets
catalog
```
