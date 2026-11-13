# Pages of the features held back from the early release

Not built (`exclude_patterns` in `docs/conf.py`). Each file is a theory page, or a section cut from one, of a feature that is
kept in the code but not released (`@describe(..., released=False)`). When a feature comes back, move its text back to
`docs/theory/` (the file name says where it came from) and add the feature to `docs/_data/families.yaml`.
