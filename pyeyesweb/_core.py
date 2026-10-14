"""Access to the compiled EyesWeb core: C++ ports of the EyesWeb feature blocks.

The module comes from the `eyesweb_core` package, a binary wheel built from the private EyesWebCore repository (the C++
is closed source and not part of PyEyesWeb). During development a build of that repository is used instead: the folder
named by `EYESWEB_CORE_PATH` (normally `EyesWebCore/build/Release`) is put first on `sys.path`, and the import fails
if the module found is not the one in that folder. Whatever is loaded must report a compatible version.
"""

import os
import sys
from pathlib import Path

REQUIRED_CORE = (2, 0)  # (major, minor) of `eyesweb_core.__version__`; bump with EyesWebCore's CMake version

try:
    from pyeyesweb import _eyesweb_core as core  # type: ignore[attr-defined]
except ImportError:
    if development_path := os.environ.get("EYESWEB_CORE_PATH"):
        sys.path.insert(0, development_path)
    try:
        import eyesweb_core as core  # type: ignore[no-redef]
    except ImportError as error:
        raise ImportError(
            "pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). "
            "Install a pyeyesweb wheel that includes it, or set EYESWEB_CORE_PATH to a development build of eyesweb_core."
        ) from error
    if development_path and Path(development_path).resolve() not in Path(core.__file__).resolve().parents:
        raise ImportError(f"EYESWEB_CORE_PATH is {development_path}, but eyesweb_core was already loaded from {core.__file__}.")

_found = getattr(core, "__version__", None)
if _found is None or tuple(int(part) for part in _found.split(".")[:2]) != REQUIRED_CORE:
    raise ImportError(
        f"pyeyesweb needs eyesweb_core {REQUIRED_CORE[0]}.{REQUIRED_CORE[1]}.x, but {core.__file__} is "
        + (f"version {_found} (build {core.__build__})" if _found else "a module without a version (a stale or foreign build)")
        + ". Rebuild or reinstall the core.")

__all__ = ["core"]
