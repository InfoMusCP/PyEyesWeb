"""The features the catalog-wide suites check: `catalog()` plus the features held back from the release
(`@describe(..., released=False)`), which stay in the code and must keep the contract until they come back."""

import importlib
import inspect
import pkgutil

from pyeyesweb.catalog import FeatureInfo, Layer, _summary, catalog


def held_back():
    """The described feature classes that are not released, as catalog entries, in layer order."""
    entries = []
    for layer in Layer:
        package = importlib.import_module(layer.package)
        found = {}
        for module_info in pkgutil.walk_packages(package.__path__, prefix=f"{layer.package}."):
            if module_info.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            module = importlib.import_module(module_info.name)
            for name, obj in vars(module).items():
                if (inspect.isclass(obj) and obj.__module__ == module.__name__ and obj.__name__ == name
                        and getattr(obj, "LAYER", None) is layer and not getattr(obj, "RELEASED", True)):
                    found[name] = FeatureInfo(name, layer, obj.TIMESCALE, obj.EYESWEB_BLOCK, obj.__module__,
                                              _summary(obj), obj)
        entries.extend(found.values())
    return entries


def every_feature():
    """`catalog()` followed by the held-back features."""
    return catalog() + held_back()
