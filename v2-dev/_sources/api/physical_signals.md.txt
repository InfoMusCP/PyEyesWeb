# Layer 1: physical signals

Generated from `pyeyesweb.catalog()`: {{ n_physical_signals }} features. Each entry links to its API page (parameters, inputs, outputs, description) and to the theory page of its family.

```{feature-table} physical_signals
```

## Supporting classes

Not features (they are not in the catalog): the model the generic-model features run on, and the stream plumbing that
aligns several sources in time.

```{eval-rst}
.. currentmodule:: pyeyesweb.physical_signals

.. autosummary::
   :toctree: generated/
   :nosignatures:

   MassSpringModel
   TimeWindowSynchronizer
   SynchronizedWindow
```

```{toctree}
:hidden:
:glob:

generated/physical_signals/*
```
