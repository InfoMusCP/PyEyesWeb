"""Access to the compiled EyesWeb core: C++ ports of the EyesWeb feature blocks.

The module comes from the `eyesweb_core` package, a binary wheel built from the private EyesWebCore repository (the C++
is closed source and not part of PyEyesWeb). During development a build of that repository on `sys.path` is used
instead (`EYESWEB_CORE_PATH`, normally `EyesWebCore/build/Release`).
"""

try:
    from pyeyesweb import _eyesweb_core as core  # type: ignore[attr-defined]
except ImportError:
    try:
        import eyesweb_core as core  # type: ignore[no-redef]
    except ImportError as error:
        raise ImportError(
            "pyeyesweb features need the compiled EyesWeb core (pyeyesweb._eyesweb_core). "
            "Install a pyeyesweb wheel that includes it, or put a development build of eyesweb_core on sys.path."
        ) from error


__all__ = ["core"]
