"""Lazy access to the compiled ``eyw_core`` extension (C++ port of EyesWeb, nanobind).

``pyeyesweb.native`` can always be imported; the compiled module is only
required when a native feature is instantiated.  This keeps PyEyesWeb usable
(and its docs buildable) on machines where ``eyw_core`` is not installed.
"""

from types import ModuleType
from typing import Optional

_INSTALL_HINT = (
    "The native EyesWeb features need the compiled module 'eyw_core' "
    "(C++ port of EyesWeb with nanobind bindings).\n"
    "Install it from the EyesWeb sources, e.g.:\n"
    "    pip install <path-to>/EyesWeb4/_standalone/eyw_core\n"
    "(needs a C++17 compiler: Visual Studio 2019+ on Windows)."
)

_module: Optional[ModuleType] = None
_error: Optional[BaseException] = None


def _load() -> Optional[ModuleType]:
    global _module, _error
    if _module is None and _error is None:
        try:
            import eyw_core  # noqa: PLC0415
            _module = eyw_core
        except ImportError as exc:  # pragma: no cover - depends on the environment
            _error = exc
    return _module


def is_available() -> bool:
    """Return ``True`` when the compiled ``eyw_core`` module can be imported."""
    return _load() is not None


def eyw_core_version() -> Optional[str]:
    """Version of the installed ``eyw_core`` module, or ``None`` if missing."""
    mod = _load()
    return getattr(mod, "__version__", None) if mod is not None else None


def require() -> ModuleType:
    """Return the ``eyw_core`` module or raise an ``ImportError`` with install hints."""
    mod = _load()
    if mod is None:
        raise ImportError(_INSTALL_HINT) from _error
    return mod
