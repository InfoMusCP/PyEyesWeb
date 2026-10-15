Tutorials
=========

Ten tutorials take you from the first feature to a real-time loop. Each is a Python script that is executed when the
documentation is built, so the code and the output shown here are those of the current release. Each page ends with the
link to download the tutorial as a Jupyter notebook (``.ipynb``) or as a Python script (``.py``).

**Order.** Start with the two tutorials of *Getting started*; they introduce the objects and the rules that every other
tutorial uses. The tutorials by layer can then be read in any order, except that the later ones refer to the earlier ones
of the same layer.

**Running them yourself.**

.. code-block:: console

   pip install pyeyesweb[datasets] matplotlib pandas

A downloaded notebook installs these in its first cell and fetches ``helpers.py``, the few plotting functions the tutorials
share (it is next to the scripts in the repository, in ``examples/``). To run a script from a checkout of the repository,
put ``examples/`` on the Python path (``PYTHONPATH=examples``). The recordings are read by
:func:`pyeyesweb.datasets.load_qualisys_trial`.

**Data.** The recordings are motion-capture takes of one performer (Qualisys, 41 markers, 100 Hz, positions in
millimetres), made in the session of 2024-03-26: synchronized and unsynchronized gestures, smooth and jerky movements,
contraction and expansion, balance, impulsive and light movements. The tutorials use parts of them.

.. TODO(maintainer): licence and citation of the data (parked); add them here when decided.
