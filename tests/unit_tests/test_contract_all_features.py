"""Every feature of `catalog()` goes through the shared contract suite (`contract_suite.check_feature_contract`).

For each catalog feature a synthetic recording is built and the suite checks that `process` and `run` agree, that
`reset` restores the state, that chunked runs add up, time and wrong-shape handling.

* A feature that can be built with no argument and driven by random data of its declared `inputs` needs no entry.
* A feature that needs constructor arguments (labels, window, model...) or particular data (positive intensities,
  event trains, contours, ...) has an entry `name -> (factory, data)` in `OVERRIDES`: `factory()` builds a fresh
  feature and `data()` returns the recordings, one per input, time on the first axis.
* A feature that cannot be driven by the suite is in `NOT_COVERED` with the reason.

A new catalog feature with neither a default that works nor an entry fails `test_contract`; the second test fails when
the table and the catalog disagree.
"""

import math

import numpy as np
import pytest

from contract_suite import check_feature_contract
from humanoid_inputs import CHAIN_XML, MASSES, REFERENCE, forearm
from imaging_inputs import silhouette

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb import catalog  # noqa: E402
from pyeyesweb.analysis_primitives import (  # noqa: E402
    BinaryPulsesRegularity, CoarseGraining, MultiScaleEntropy, Periodicity, Rarity, SampleEntropy
)
from pyeyesweb.analysis_primitives.synchronization import (  # noqa: E402
    CorrelationsMatrix, CrossRecurrencePlot, EventSynchronization, EventSynchronizationMECS, GeneralisedAutoCorrelation,
    NonlinearInterdependence, PhaseLockingValue, RecurrencePlot, SpikeSynchronization,
    TemporalSynchronization
)
from pyeyesweb.data_models import InputKind  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    BodyPartsFromCurvature, CurvatureDispersion, CurvatureVelocityCorrelation, DirectionChange, Harmonicity, Kinematics, KineticEnergy,
    LogDimensionlessJerk, MotionNoiseDetector, SpectralArcLength, SubmovementCount, Symmetry
)
from pyeyesweb.mid_level import (  # noqa: E402
    GestureSegmenter, PositionDependingPotentials, RegionDependingPotentials, Suddenness, SuddennessImpulsivity
)
from pyeyesweb.physical_signals import (  # noqa: E402
    GenericModelEstimator, GenericModelOrientations, GenericModelPredictor, GenericModelSimulator, HitCellDetector,
    HumanoidOrientations, HumanoidSimulator, MassSpringModel, PointsPredictor,
    SilhouetteCentroids, Videogram
)

FRAME_COUNT = 40
LABELS = ["torso", "left_hip", "right_hip"]
MODEL = MassSpringModel.from_xml_string(CHAIN_XML)
MILLIMETRES = dict(sampling_rate=25.0, units="mm")


def _random(seed):
    return np.random.default_rng(seed)


def from_inputs(feature, seed=0):
    """A recording per declared input, generated from its kind and shape (free sizes get a small default)."""
    rng = _random(seed)
    recordings = []
    for declared in feature.inputs:
        want = declared._wanted()
        if declared.kind is InputKind.SAMPLE:
            shape = (FRAME_COUNT,) if want == (1,) else (FRAME_COUNT, want[0] or 2)
            recordings.append(rng.uniform(0.5, 2.0, size=shape))
        elif declared.kind is InputKind.IMAGE:
            channels = (want[2] or 3,) if len(want) > 2 else ()
            recordings.append(rng.integers(0, 256, size=(10, 12, 16, *channels)).astype(np.uint8))
        else:
            rows, columns = (want + (None, None))[:2]
            recordings.append(rng.standard_normal((FRAME_COUNT, rows or 4, columns or 3)))
    return tuple(recordings)


def _walk(frames, dims, seed):
    return np.cumsum(_random(seed).standard_normal((frames, dims)), axis=0)


def _contours():
    angles = np.linspace(0, 2 * math.pi, 8, endpoint=False)
    circle = np.stack([np.cos(angles), np.sin(angles)], axis=1)
    return (np.round(10 * (circle + 0.1 * _random(1).standard_normal((12, 8, 2)))),)


def _signal():
    return (np.sin(2 * np.pi * np.arange(160) / 10) + 0.05 * _random(2).standard_normal(160),)


def _speed():
    return (np.abs(_random(3).standard_normal(120)) + 1.0,)


def _pulses():
    pulses = (_random(4).random(80) < 0.3).astype(float)
    pulses[::4] = 1.0
    return (pulses,)


def _moving_body():
    return (np.stack([silhouette(shift=2 * step) for step in range(8)]),)


def _signals_with_phase():
    time = np.arange(80) / 20.0
    return np.stack([np.sin(2 * np.pi * time), np.sin(2 * np.pi * time + 0.7), _random(5).standard_normal(80)], axis=1)


def _events(columns=None, seed=6):
    shape = (80,) if columns is None else (80, columns)
    return (_random(seed).random(shape) > 0.8).astype(float)


def _correlation_matrices():
    rng = _random(7)
    return (np.stack([np.corrcoef(rng.standard_normal((3, 10))) for _ in range(12)]),)


def _gesture_segmenter():
    return (np.abs(np.sin(np.arange(60) / 4)) + (np.arange(60) > 30), (np.arange(60) % 9 < 3).astype(float))


def _hits():
    return (_random(8).uniform(0, 0.99, size=(12, 3, 2)),)


def _cells():
    return (_random(9).integers(0, 3, size=(12, 4, 2)).astype(float),)


def _humanoid_control():
    frames = forearm(30)
    return frames, HumanoidOrientations().run(frames)["directions"]


def _chain(name):
    return (REFERENCE[name][:30],)


# name -> (factory, data); features not listed are built with no argument and driven by `from_inputs`
OVERRIDES = {
    "FilterContour": (None, _contours),
    "ContourCurvature": (None, _contours),
    "ConvexHull": (None, _contours),
    "BodyPartsFromCurvature": (lambda: BodyPartsFromCurvature(minimum_distance=1),
                               lambda: (_random(10).choice([-1.0, 1.0], size=(12, 8)), _contours()[0])),
    "HitCellDetector": (lambda: HitCellDetector(cells_x=4, cells_y=4, x_max=1.0, y_max=1.0), _hits),
    "HumanoidSimulator": (lambda: HumanoidSimulator(**MILLIMETRES), _humanoid_control),
    "HumanoidOrientations": (None, lambda: (forearm(30),)),
    "GenericModelOrientations": (lambda: GenericModelOrientations(MODEL), lambda: _chain("model_positions")),
    "GenericModelSimulator": (lambda: GenericModelSimulator(MODEL, **MILLIMETRES), lambda: _chain("bone_directions")),
    "GenericModelPredictor": (lambda: GenericModelPredictor(MODEL, **MILLIMETRES), lambda: _chain("bone_directions")),
    "GenericModelEstimator": (lambda: GenericModelEstimator(MODEL, **MILLIMETRES, estimate_masses=True),
                              lambda: _chain("model_positions")),
    "PointsPredictor": (lambda: PointsPredictor(labels=MASSES), lambda: _chain("model_positions")),
    "SilhouetteCentroids": (lambda: SilhouetteCentroids(filter_centroids=True, alpha=0.5), _moving_body),
    "SilhouetteBodyParts": (None, _moving_body),
    "Videogram": (lambda: Videogram(length=4), None),
    "Kinematics": (lambda: Kinematics(dims=2), lambda: (_walk(FRAME_COUNT, 2, 11),)),
    "KineticEnergy": (lambda: KineticEnergy(labels=LABELS, weights=dict.fromkeys(LABELS, 1.0)), lambda: (_walk(FRAME_COUNT * 3, 3, 12).reshape(FRAME_COUNT, 3, 3),)),
    "Symmetry": (lambda: Symmetry(couples=[("left_hip", "right_hip")], reference_point="torso", labels=LABELS), None),
    "SpectralArcLength": (lambda: SpectralArcLength(window=30, hop=7, sampling_rate=50.0), _speed),
    "LogDimensionlessJerk": (lambda: LogDimensionlessJerk(window=30, hop=7, sampling_rate=50.0), _speed),
    "Harmonicity": (lambda: Harmonicity(window=30, hop=7, sampling_rate=50.0), _speed),
    "SubmovementCount": (lambda: SubmovementCount(window=30, hop=7, sampling_rate=50.0), _speed),
    "CurvatureDispersion": (lambda: CurvatureDispersion(dims=3),
                            lambda: (np.gradient(_walk(80, 3, 13), axis=0),
                                     np.gradient(np.gradient(_walk(80, 3, 13), axis=0), axis=0))),
    "CurvatureVelocityCorrelation": (lambda: CurvatureVelocityCorrelation(window=40, hop=20),
                                     lambda: (_walk(120, 2, 14),)),
    "DirectionChange": (lambda: DirectionChange(window=10, hop=3), lambda: (_walk(60, 3, 15),)),
    "MotionNoiseDetector": (lambda: MotionNoiseDetector(labels=LABELS),
                            lambda: (np.cumsum(_random(16).standard_normal((FRAME_COUNT, 3, 3)) * 0.05, axis=0),)),
    "GestureSegmenter": (lambda: GestureSegmenter(filter_window_length=5, firing_threshold=0.5), _gesture_segmenter),
    "Suddenness": (lambda: Suddenness(window=20, hop=5, dims=3), lambda: (_walk(FRAME_COUNT, 3, 17),)),
    "SuddennessImpulsivity": (lambda: SuddennessImpulsivity(window=20, hop=5, dims=3), lambda: (_walk(FRAME_COUNT, 3, 17),)),
    "PositionDependingPotentials": (lambda: PositionDependingPotentials(cells_along_x=3, cells_along_y=3), _cells),
    "RegionDependingPotentials": (lambda: RegionDependingPotentials(cells_along_x=3, cells_along_y=3, num_of_regions=3), _cells),
    "EnsembleDominance": (None, lambda: (np.abs(_random(18).standard_normal((150, 2))),)),
    "SampleEntropy": (lambda: SampleEntropy(window=40, hop=10, embedding_dimension=2, tolerance=0.5),
                      lambda: (np.sin(np.arange(120) / 5.0) + 0.1 * _random(19).standard_normal(120),)),
    "CoarseGraining": (lambda: CoarseGraining(window=8, hop=4, factor=2), lambda: (_random(20).standard_normal((40, 2)),)),
    "Rarity": (lambda: Rarity(method="information"), lambda: (_random(21).standard_normal((30, 2)),)),
    "BinaryPulsesRegularity": (lambda: BinaryPulsesRegularity(window=12, hop=3, threshold=1), _pulses),
    "MultiScaleEntropy": (lambda: MultiScaleEntropy(window=100, hop=50, minimum_points=50, max_scale=2),
                          lambda: (_random(22).standard_normal((150, 2)),)),
    "Periodicity": (lambda: Periodicity(window=64, hop=16), _signal),
    "ScalarPeakDetector": (None, _signal),
    "PhaseLockingValue": (lambda: PhaseLockingValue(window=30, hop=10),
                          lambda: (_signals_with_phase()[:, 0], _signals_with_phase()[:, 1])),
    "CorrelationsMatrix": (lambda: CorrelationsMatrix(window=20, hop=5, n_inputs=3), lambda: (_signals_with_phase(),)),
    "PartialRecurrenceSynchronization": (None, _correlation_matrices),
    "GeneralisedAutoCorrelation": (lambda: GeneralisedAutoCorrelation(window=20, hop=10),
                                   lambda: (_signals_with_phase()[:, 0],)),
    "EventSynchronization": (lambda: EventSynchronization(window=20, hop=20), lambda: (_events(seed=6), _events(seed=7))),
    "EventSynchronizationMECS": (lambda: EventSynchronizationMECS(window=20, hop=20),
                                 lambda: (_events(3, seed=6), _events(3, seed=7))),
    "NonlinearInterdependence": (lambda: NonlinearInterdependence(window=30, hop=10),
                                 lambda: (_signals_with_phase()[:, 0], _signals_with_phase()[:, 2])),
    "SpikeSynchronization": (lambda: SpikeSynchronization(window=20, hop=10),
                             lambda: (np.where(_random(23).random((80, 2)) > 0.7, 1.0, -1.0),)),
    "SequenceDetector": (None, lambda: (_random(24).integers(0, 3, 80).astype(float),)),
    "TemporalSynchronization": (lambda: TemporalSynchronization(thresholds=[0.5, 0.5, 0.5]),
                                lambda: (np.abs(_signals_with_phase()),)),
    "RecurrencePlot": (lambda: RecurrencePlot(window=10, hop=5, epsilon=0.5), lambda: (_signals_with_phase()[:, :2],)),
    "CrossRecurrencePlot": (lambda: CrossRecurrencePlot(window=10, hop=5, epsilon=0.5),
                            lambda: (_signals_with_phase()[:, :2], _signals_with_phase()[:, 1:])),
}

# name -> why the contract suite cannot drive it
NOT_COVERED = {}

NAMES = [info.name for info in catalog() if info.name not in NOT_COVERED]


def factory_and_recordings(name):
    """A factory of fresh features of the catalog feature `name` and the recordings it is driven with (one per input)."""
    factory, data = OVERRIDES.get(name, (None, None))
    factory = factory or next(info.cls for info in catalog() if info.name == name)
    return factory, (data or (lambda: from_inputs(factory())))()


@pytest.mark.parametrize("name", NAMES)
def test_contract(name):
    factory, recordings = factory_and_recordings(name)
    check_feature_contract(factory, *recordings)


def test_every_catalog_feature_is_covered_or_excused():
    catalog_names = {info.name for info in catalog()}
    assert set(OVERRIDES) <= catalog_names, "an entry of OVERRIDES is not in the catalog"
    assert set(NOT_COVERED) <= catalog_names, "an entry of NOT_COVERED is not in the catalog"
    assert not set(OVERRIDES) & set(NOT_COVERED), "a feature is both covered and excused"
    assert all(NOT_COVERED.values()), "every NOT_COVERED entry needs a reason"
    assert catalog_names == set(NAMES) | set(NOT_COVERED)
