# Installation

```{admonition} Pre-release
:class: note

This documentation describes PyEyesWeb 2.0, which has not been released yet. The package on PyPI today is the 1.x series,
which has a different and incompatible interface (it does not contain the compiled core and none of the code on these pages
runs with it). The commands under "Install a release" are those that will apply when the first 2.0 pre-release is
published; until then, follow "Development install".
```

## Requirements

- Python 3.10 or later (3.10, 3.11 and 3.12 are declared; the documentation is built with 3.11).
- NumPy. The features need nothing else.
- Optional: pandas for `to_frame()` of a {py:class}`~pyeyesweb.data_models.Recorder`, and matplotlib for the plots
  of the examples.
- A platform with the compiled EyesWeb core. The release is planned with binary packages for Windows, Linux and macOS; a
  development build has so far been used on Windows only.

PyEyesWeb is pure Python on top of a compiled core, which holds the numerical implementation of the EyesWeb blocks. The core
ships with the package: there is nothing to compile.

## Install a release

A pre-release is not installed by default; ask for it explicitly:

```bash
pip install --pre pyeyesweb
```

and, once a stable 2.0 exists, simply `pip install pyeyesweb`. Use a virtual environment (`python -m venv .venv`) as for
any scientific project.

## Development install

Until the packages are published, the library runs from a clone of the repository together with a development build of the
compiled core, which the maintainers provide as a folder holding the core module. Two things must be visible to Python: the
folder of the repository (the library), and the folder of the core, named by the environment variable
`EYESWEB_CORE_PATH`.

::::{tab-set}
:::{tab-item} Windows (PowerShell)
```powershell
git clone https://github.com/InfoMusCP/PyEyesWeb
$env:PYTHONPATH = "C:\path\to\PyEyesWeb"
$env:EYESWEB_CORE_PATH = "C:\path\to\core-build"
python -c "import pyeyesweb; print(len(pyeyesweb.catalog()))"
```
:::
:::{tab-item} Linux and macOS
```bash
git clone https://github.com/InfoMusCP/PyEyesWeb
export PYTHONPATH=/path/to/PyEyesWeb
export EYESWEB_CORE_PATH=/path/to/core-build
python -c "import pyeyesweb; print(len(pyeyesweb.catalog()))"
```
:::
::::

`EYESWEB_CORE_PATH` is put first on `sys.path` when the library loads its core. If a different copy of the core was already
imported from elsewhere, the library refuses to start rather than mix two builds.

## Check the installation

`import pyeyesweb` itself needs no core. `catalog()` does, because it imports every layer package: if it works, the
library and the core are both in place.

```{doctest}
>>> import pyeyesweb
>>> features = pyeyesweb.catalog()
>>> len(features)
60
>>> [info.name for info in features[:3]]
['HumanoidSimulator', 'HumanoidOrientations', 'GenericModelOrientations']
```

The catalog lists every feature with its layer and timescale (see {doc}`../concepts/layers`).

### The core version

The library and the core are versioned together. Every layer package checks, at import, that the core reports the major and
minor version the library was written for (2.0), and refuses to import otherwise. The version of the loaded core can be
read from an internal module meant for diagnosis:

```{doctest}
>>> from pyeyesweb._core import core, REQUIRED_CORE
>>> REQUIRED_CORE
(2, 0)
>>> core.__version__.split(".")[:2]
['2', '0']
```

The documentation footer shows the version of the core the pages were built with.

## Error messages at import

`ImportError` is the only exception raised while loading. It has one of four causes, each with its own text.

No core at all (the library cannot find the compiled module, and `EYESWEB_CORE_PATH` is unset or names a folder without it)
: ``pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). Install it with `pip install pyeyesweb`, or set EYESWEB_CORE_PATH to the folder of a local build of eyesweb_core.``
  Importing `pyeyesweb`, `pyeyesweb.data_models`, `Layer` and `Timescale` still works; `catalog()` and the layer packages
  (`low_level`, `mid_level`, ...) raise it.

A core of another version
: `pyeyesweb needs eyesweb_core 2.0.x, but <file> is version 1.9.3 (build abc1234). Rebuild or reinstall the core.`
  The version and build in the message are those of the module found. Install the core that matches the library.

A module named like the core, without a version
: `pyeyesweb needs eyesweb_core 2.0.x, but <file> is a module without a version (a stale or foreign build). Rebuild or reinstall the core.`

A development path that conflicts with a core already loaded
: `EYESWEB_CORE_PATH is <path>, but eyesweb_core was already loaded from <file>.`
  Remove the other copy from `PYTHONPATH`, or unset `EYESWEB_CORE_PATH`.

## Next

Continue with the {doc}`quickstart`.
