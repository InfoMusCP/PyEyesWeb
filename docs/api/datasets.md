# Datasets

The example recordings used by the tutorials. The module needs no compiled core; downloading needs the optional
dependency `pooch` (`pip install pyeyesweb[datasets]`). Reference for the objects below (generated from the docstrings).

```{eval-rst}
.. py:module:: pyeyesweb.datasets

.. currentmodule:: pyeyesweb.datasets

.. autosummary::
   :toctree: generated/
   :nosignatures:

   load_qualisys_trial
   QualisysTrial
   fetch_data_file
   available_trials
   cache_dir
```

## Data objects

```{eval-rst}
.. py:data:: QUALISYS_TRIALS
   :type: dict[int, tuple[str, str]]

   Trial number -> ``(task, condition)`` of the recorded session.

.. py:data:: BASE_URL
   :type: str | None

   URL of the folder that hosts the recordings; ``None`` until a host is chosen (the recordings are then read from a
   repository checkout or from the folder named by ``PYEYESWEB_DATA``).
```

## Where a file is looked for

1. the folder named by the environment variable `PYEYESWEB_DATA`, if set (it is also the download cache);
2. `examples/data` of a repository checkout;
3. the download cache, filled from `BASE_URL` with a SHA-256 check.

The recordings are Qualisys exports at 100 Hz with positions in millimetres; the loader keeps the millimetres and
records them in the `units` field of the result.
