"""The conceptual tree (layers, simple names, discovery metadata)."""

import importlib
import os
import pkgutil
import sys

import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

import pyeyesweb
from pyeyesweb import Layer, Timescale, catalog

try:
    import pyeyesweb._core  # noqa: F401
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

needs_core = pytest.mark.skipif(not HAS_CORE, reason="compiled EyesWeb core not available")


@pytest.mark.skipif(HAS_CORE, reason="only meaningful without the core")
def test_layers_raise_import_error_without_the_core():
    with pytest.raises(ImportError):
        from pyeyesweb.low_level import KineticEnergy  # noqa: F401


@needs_core
def test_catalog_lists_features():
    names = {entry.name for entry in catalog()}
    assert {"SpectralArcLength", "SubmovementCount", "Suddenness", "MotionNoiseDetector"} <= names
    assert len(catalog()) == 60  # 62 before CannyEdgeDetector, 61 before ZeroCross were dropped (2026-10-14)


@needs_core
def test_every_public_name_resolves_and_layer_matches_its_package():
    for layer in Layer:
        package = importlib.import_module(layer.package)
        for name in package.__all__:
            getattr(package, name)
    for info in catalog():
        assert info.cls.LAYER is info.layer
        assert isinstance(info.timescale, Timescale)


@needs_core
def test_features_with_an_eyesweb_block_name_it():
    from pyeyesweb import low_level, mid_level, analysis_primitives as ap

    assert low_level.KineticEnergy.EYESWEB_BLOCK and low_level.CurvatureVelocityCorrelation.EYESWEB_BLOCK
    assert ap.Rarity.EYESWEB_BLOCK and mid_level.ContractionImpulsivity.EYESWEB_BLOCK
    assert low_level.SpectralArcLength.EYESWEB_BLOCK is None


@needs_core
def test_layer_placements():
    from pyeyesweb import low_level, mid_level, physical_signals, analysis_primitives as ap

    assert low_level.Kinematics.LAYER is Layer.LOW_LEVEL
    assert low_level.MotionNoiseDetector.LAYER is Layer.LOW_LEVEL
    assert low_level.Directness.LAYER is Layer.LOW_LEVEL
    assert mid_level.PositionDependingPotentials.LAYER is Layer.MID_LEVEL
    assert low_level.FilterContour.LAYER is Layer.LOW_LEVEL
    assert low_level.TrajectoryNonPlanarity.LAYER is Layer.LOW_LEVEL
    assert not hasattr(physical_signals, "FilterContour")
    assert ap.Periodicity.LAYER is Layer.ANALYSIS_PRIMITIVE
    assert ap.synchronization.PartialRecurrenceSynchronization.LAYER is Layer.ANALYSIS_PRIMITIVE
    assert pyeyesweb.high_level.__all__ == ["EnsembleDominance"]
    assert pyeyesweb.high_level.EnsembleDominance.LAYER is Layer.HIGH_LEVEL
    assert not hasattr(ap, "EnsembleDominance")


@needs_core
def test_choices_are_strings_not_exported_enums():
    from pyeyesweb import low_level
    from pyeyesweb.low_level import KineticEnergy

    assert not hasattr(low_level, "KineticEnergyInputType")
    assert KineticEnergy.__module__ == "pyeyesweb.low_level.energy"


@needs_core
def test_every_public_feature_class_is_exported_by_its_package():
    import inspect

    for layer in Layer:
        package = importlib.import_module(layer.package)
        modules = [importlib.import_module(f"{layer.package}.{info.name}")
                   for info in pkgutil.iter_modules(package.__path__) if not info.name.startswith("_")]
        for module in modules:
            for name, obj in vars(module).items():
                if inspect.isclass(obj) and obj.__module__ == module.__name__ and not name.startswith("_")                         and hasattr(obj, "LAYER"):
                    assert name in package.__all__, f"{module.__name__}.{name} is missing from {layer.package}.__all__"
