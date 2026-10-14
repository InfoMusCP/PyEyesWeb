"""Output contract of the features that wrap a block of the compiled core.

Checks, for every block, that `block.outputs` is a Schema known before any data, that each call returns a Result of
that schema whose fixed outputs have exactly the declared shape and dtype, that the no-output paths carry the
documented status / valid mask, that parameter-dependent schemas match what the core produces, and that the
constructor defaults the schemas rely on match the C++ defaults. The numerical behaviour of each block is tested in
C++ alongside the core.

The compiled core is found as pyeyesweb._eyesweb_core, or as eyesweb_core in the directory named by the
EYESWEB_CORE_PATH environment variable. Without it these tests are skipped.
"""
import math
import os
import sys

import numpy as np
import pytest

if os.environ.get("EYESWEB_CORE_PATH"):
    sys.path.insert(0, os.environ["EYESWEB_CORE_PATH"])

pytest.importorskip("pyeyesweb._core", exc_type=ImportError)

from pyeyesweb._core import core  # noqa: E402
from pyeyesweb.analysis_primitives import (  # noqa: E402
    CoarseGraining, Periodicity, Rarity, SampleEntropy, ScalarPeakDetector
)
from pyeyesweb.analysis_primitives.synchronization import (  # noqa: E402
    CorrelationsMatrix, EventSynchronization, NonlinearInterdependence, EventSynchronizationMECS,
    GeneralisedAutoCorrelation, PartialRecurrenceSynchronization, SequenceDetector, SpikeSynchronization,
    TemporalSynchronization
)
from pyeyesweb.data_models.recorder import Recorder  # noqa: E402
from pyeyesweb.data_models.results import Result, Schema, Status  # noqa: E402
from pyeyesweb.low_level import (  # noqa: E402
    BodyPartsFromCurvature, ContourCurvature, EllipsoidSphericity, Kinematics, KineticEnergy, PointsDensity, CurvatureVelocityCorrelation,
    Symmetry, TriangleSymmetry
)
from pyeyesweb.low_level import MotionNoiseDetector  # noqa: E402
from pyeyesweb.mid_level import ContractionImpulsivity, GestureSegmenter, MotionDuration  # noqa: E402
from pyeyesweb.physical_signals import FilterContour  # noqa: E402

DTYPES = {float: np.floating, int: np.integer, bool: np.bool_}

EVENTS = np.zeros(40)
EVENTS[[5, 15, 25]] = 1
SQUARE = [(0, 0), (1, 0), (1, 1), (0, 1)]
RNG = np.random.default_rng(0)
signal_a, signal_b = RNG.standard_normal(50), RNG.standard_normal(50)
SKELETON = {"torso": (0, 0, 0), "left_hip": (-1, 0, 0), "right_hip": (1, 0, 0)}
RATIO = dict(couples=[("left_hip", "right_hip")], reference_point="torso")  # the default input type is custom
SINE = np.sin(np.arange(60) / 3.0)
PERIODIC = np.tile([3.0, -1, 0, 2, -4], 10)
CIRCLE = [(math.cos(angle), math.sin(angle)) for angle in np.linspace(0, 2 * math.pi, 8, endpoint=False)]

# name -> (block factory, call on the block). Every block, constructed with typical parameters, run once.
CASES = {
    "KineticEnergy": (lambda: KineticEnergy(weights={"head": 1.0}), lambda block: block.process({"head": (0, 0, 0)})),
    "Periodicity": (lambda: Periodicity(window=len(PERIODIC)), lambda block: block._process_window(PERIODIC)),
    "ContractionImpulsivity": (lambda: ContractionImpulsivity(), lambda block: block.process(0.5, 0.5)),
    "MotionDuration": (lambda: MotionDuration(continuous_output=True), lambda block: block.process(1.0)),
    "CoarseGraining": (lambda: CoarseGraining(window=4), lambda block: block._process_window(np.array([[1.0, 3, 5, 7]]))),
    "Rarity": (lambda: Rarity(method="information"), lambda block: block.process([0.1, 0.9])),
    "SampleEntropy": (lambda: SampleEntropy(window=len(SINE), embedding_dimension=2, tolerance=0.5), lambda block: block._process_window(SINE)),
    "CurvatureVelocityCorrelation": (lambda: CurvatureVelocityCorrelation(window=40), lambda block: block._process_window(
        np.vstack([np.cos(np.arange(40) / 10), np.sin(np.arange(40) / 10)]))),
    "GestureSegmenter": (lambda: GestureSegmenter(filter_window_length=5), lambda block: block.process(0.5)),
    "MotionNoiseDetector": (lambda: MotionNoiseDetector(labels=["head"]),
                            lambda block: block.process({"head": (0, 0, 0)}, timestamp=0.0)),
    "Symmetry": (lambda: Symmetry(**RATIO), lambda block: block.process(SKELETON)),
    "PointsDensity": (lambda: PointsDensity(), lambda block: block.process({"a": (0, 0, 0), "b": (2, 0, 0)})),
    "TriangleSymmetry": (lambda: TriangleSymmetry(), lambda block: block.process((0, 1), (-1, 0), (1, 0))),
    "EllipsoidSphericity": (lambda: EllipsoidSphericity(), lambda block: block.process_axes(1, 2, 3)),
    "ContourCurvature": (lambda: ContourCurvature(), lambda block: block.process(SQUARE)),
    "FilterContour": (lambda: FilterContour(), lambda block: block.process(SQUARE + [(0.5, 1.5)])),
    "BodyPartsFromCurvature": (lambda: BodyPartsFromCurvature(minimum_distance=1), lambda block: block.process(
        [1.0, -1, 1, -1, 1, -1, 1, -1], CIRCLE)),
    "Kinematics": (lambda: Kinematics(dims=2), lambda block: block.process([0.0, 1.0])),
    "CorrelationsMatrix": (lambda: CorrelationsMatrix(window=50, n_inputs=2),
                           lambda block: block._process_window(np.stack([signal_a, signal_b]))),
    "PartialRecurrenceSynchronization": (lambda: PartialRecurrenceSynchronization(), lambda block: block.process(np.eye(2))),
    "GeneralisedAutoCorrelation": (lambda: GeneralisedAutoCorrelation(window=50),
                                   lambda block: block._process_window(signal_a[None])),
    "EventSynchronization": (lambda: EventSynchronization(window=40),
                             lambda block: block._process_window(EVENTS[None], EVENTS[None])),
    "EventSynchronizationMECS": (lambda: EventSynchronizationMECS(window=40, hop=40),
                                   lambda block: block._process_window(*[np.vstack([EVENTS] * 3)] * 2)),
    "SpikeSynchronization": (lambda: SpikeSynchronization(window=40), lambda block: block._process_window(np.where(EVENTS > 0, 1.0, -1.0)[None] * [[1], [1]])),
    "NonlinearInterdependence": (lambda: NonlinearInterdependence(window=50),
                                            lambda block: block._process_window(signal_a[None], signal_b[None])),
    "SequenceDetector": (lambda: SequenceDetector(), lambda block: block.process(1)),
    "TemporalSynchronization": (lambda: TemporalSynchronization(thresholds=[1, 1, 1]),
                                lambda block: block.process([2, 0.5, 0])),
    "ScalarPeakDetector": (lambda: ScalarPeakDetector(), lambda block: block.process(1.0)),
}


def run(name):
    make, call = CASES[name]
    block = make()
    return block, call(block)


def assert_fixed_shapes(schema, result):
    """Every fixed output has exactly its declared shape and dtype; the flat forms follow the schema."""
    values = result.to_dict()
    assert list(values) == list(schema.names)
    for output in schema:
        value = values[output.name]
        if output.labelled:
            assert isinstance(value, dict)
            continue
        if not output.shape:
            assert isinstance(value, output.kind), output.name
            continue
        assert isinstance(value, np.ndarray) and not value.flags.writeable
        assert np.issubdtype(value.dtype, DTYPES[output.kind])
        assert value.ndim == len(output.shape)
        if output.fixed:
            assert value.shape == output.shape, output.name
    assert result.to_array().shape == (schema.size,)
    flat = result.to_flat_dict(meta=False)
    fixed_keys = [key for key in flat if key in set(schema.flat_names)]
    assert fixed_keys == list(schema.flat_names)


# ------------------------------------------------------------------------------------------ (a), (b) every block

@pytest.mark.parametrize("name", sorted(CASES))
def test_every_block_follows_the_contract(name):
    block, result = run(name)
    assert isinstance(block.outputs, Schema) and isinstance(result, Result)
    assert result.schema is block.outputs
    assert block.outputs is block.outputs  # built once
    for output in block.outputs:
        assert hasattr(result, output.name)
    assert set(result.valid) == set(block.outputs.names)
    assert_fixed_shapes(block.outputs, result)
    assert block.outputs.flat_names == tuple(key for key in result.to_flat_dict(meta=False)
                                             if key in set(block.outputs.flat_names))
    # a fresh block exposes its schema before any data
    assert CASES[name][0]().outputs.names == block.outputs.names


def test_outputs_and_result_are_not_shadowed_by_the_core_block():
    block = KineticEnergy(weights={"head": 1.0})
    assert block.outputs is not block._block and callable(block.result) and callable(block.no_output)


# ------------------------------------------------------------------------------------------ numeric / status

def test_scalar_results_are_named_after_the_feature():
    key = KineticEnergy(weights={"hand": 2.0},
                                  sampling_rate=2)
    first = key.process({"hand": (0, 0, 0)}, timestamp=2.0)
    second = key.process({"hand": (1, 0, 0)})
    assert first.status is Status.OK and first.kinetic_energy == 0.0
    assert first.timestamp == pytest.approx(2.0)
    assert second.kinetic_energy == pytest.approx(4.0) and math.isnan(second.timestamp)
    flat = second.to_flat_dict("ke")
    assert list(flat) == ["ke_status", "ke_timestamp", "ke_kinetic_energy"]
    assert flat["ke_status"] == 0 and math.isnan(flat["ke_timestamp"]) and flat["ke_kinetic_energy"] == pytest.approx(4.0)


# ------------------------------------------------------------------------------------------ (c) no-output paths

def test_coarse_graining_skipped_activation():
    cg = CoarseGraining(window=4, factor=2)
    assert cg._process_window(np.array([[1.0, 3, 5, 7]])).status is Status.OK
    skipped = cg._process_window(np.array([[1.0, 3, 5, 7]]))
    assert skipped.status is Status.NO_OUTPUT and skipped.reason
    assert skipped.valid == {"series": False} and skipped.series.size == 0
    assert skipped.to_array().shape == (0,)


def test_motion_duration_updates_one_output_or_none():
    md = MotionDuration()  # updates a field only on phase changes
    quiet = md.process(1.0)
    assert quiet.status is Status.NO_OUTPUT
    assert quiet.valid == {"motion_duration": False, "pause_duration": False}
    assert np.isnan(quiet.to_array()).all()
    changed = md.process(0.0)
    assert changed.status is Status.OK
    assert changed.valid == {"motion_duration": True, "pause_duration": False}
    assert not math.isnan(changed.motion_duration) and math.isnan(changed.pause_duration)


def test_points_density_without_points_is_invalid_input():
    empty = PointsDensity().process({})
    assert empty.status is Status.INVALID_INPUT and empty.reason == "no points"
    assert not any(empty.valid.values())
    assert np.isnan(empty.to_array()).all() and empty.to_array().shape == (4,)
    assert empty.centroid.shape == (3,)


def test_gesture_segmenter_default_filter_window_length_is_usable():
    import inspect
    assert inspect.signature(GestureSegmenter).parameters["filter_window_length"].default == 9
    assert GestureSegmenter().process(0.5).status is Status.WARMING_UP


def test_gesture_segmenter_warms_up_then_emits():
    gs = GestureSegmenter(filter_window_length=5)
    results = [gs.process(0.01 * index, timestamp=index * 0.04) for index in range(11)]
    assert all(result.status is Status.WARMING_UP for result in results[:10]) and results[10].status is Status.OK
    early, late = results[0], results[10]
    assert early.valid == {"smoothed_intensity": False, "gesturing": False, "gesture_start": False, "gesture_end": False}
    assert math.isnan(early.smoothed_intensity) and early.gesturing is False
    assert all(late.valid.values()) and not math.isnan(late.smoothed_intensity)
    assert late.timestamp == pytest.approx(10 * 0.04)


def test_motion_noise_detector_is_noise_until_it_has_seen_enough():
    detector = MotionNoiseDetector(labels=["head"])
    flags = [detector.process({"head": (2.0 * (index // 2), 0, 0)}, timestamp=0.04 * (index + 1))["noise"] for index in range(16)]
    assert flags[:14] == [True] * 14 and flags[14:] == [False, False]  # 14 speeds are needed, then the variance is large


def test_filter_contour_window_not_shorter_than_contour():
    assert FilterContour().process(SQUARE).status is Status.OK
    result = FilterContour(window_length=7).process(SQUARE)
    assert result.status is Status.NO_OUTPUT and result.reason
    assert result.valid == {"contour": False} and result.contour.shape == (0, 2)


def test_spike_profile_only_in_binary_mode():
    trains = np.vstack([np.where(EVENTS > 0, 1.0, -1.0)] * 2)
    binary = SpikeSynchronization(window=40, mode="binary")._process_window(trains)
    assert binary.valid["profile"] and binary.profile.ndim == 1
    timings = SpikeSynchronization(window=3, mode="timings", number_of_input_trains=2)._process_window(
        np.array([[1.0, 5.0, 9.0], [1.0, 5.0, 9.5]]))
    assert not timings.valid["profile"] and timings.valid["degree"]


def test_temporal_synchronization_efficiency_step_only_at_full_progression():
    ts = TemporalSynchronization(thresholds=[1, 1, 1])
    result = ts.process([2, 0.5, 0])
    assert result.progression < 1 and not result.valid["efficiency_step"] and math.isnan(result.efficiency_step)
    assert isinstance(result.step, int) and isinstance(result.state, int)


def test_structured_outputs_flatten_with_meaningful_keys():
    flat = PointsDensity().process({"a": (0, 0, 0), "b": (2, 0, 0)}).to_flat_dict()
    assert flat["centroid_x"] == pytest.approx(1.0) and "density" in flat

    per = Periodicity(window=len(PERIODIC), threshold=0.1)._process_window(PERIODIC)
    assert per.periods.shape == per.powers.shape and per.periods[0, 0] == 5

    gac = GeneralisedAutoCorrelation(window=50, tau_min=3)._process_window(signal_a[None])
    assert list(gac.taus[:2]) == [3, 4] and gac.recurrence_rate.shape == gac.taus.shape
    assert gac.taus.dtype.kind == "i"

    bp = BodyPartsFromCurvature(minimum_distance=1).process([1.0, -1, 1, -1, 1, -1, 1, -1], CIRCLE)
    for labelled in (bp.minimums, bp.maximums):
        assert all(array.shape == (2,) for array in labelled.values())


# ---------------------------------------------------------------------------- (d) parameter-dependent schemas

def test_symmetry_global_and_components():
    glob_block = Symmetry(**RATIO)
    comp_block = Symmetry(output_type="components", **RATIO)
    assert glob_block.outputs["symmetry"].shape == ()
    assert comp_block.outputs["symmetry"].shape == (3,)
    assert comp_block.outputs.flat_names == ("symmetry_x", "symmetry_y", "symmetry_z")
    glob, comp = glob_block.process(SKELETON), comp_block.process(SKELETON)
    assert isinstance(glob.symmetry, float) and comp.symmetry.shape == (3,)
    assert_fixed_shapes(glob_block.outputs, glob)
    assert_fixed_shapes(comp_block.outputs, comp)


def test_points_density_module_and_component():
    points = {"a": (0, 0, 0), "b": (2, 0, 0)}
    module = PointsDensity()
    component = PointsDensity(output_dims="component")
    assert module.outputs["density"].shape == () and component.outputs["density"].shape == (3,)
    assert component.outputs.flat_names[:3] == ("density_x", "density_y", "density_z")
    assert component.process(points).density.shape == (3,)
    assert isinstance(module.process(points).density, float)
    assert component.process({}).density.shape == (3,)


@pytest.mark.parametrize("output_type", [member.lower() for member in core.trajectory.KinematicsOutputType.__members__])
@pytest.mark.parametrize("dimension", [1, 2, 3])
@pytest.mark.parametrize("output_dimension", [member.lower() for member in core.trajectory.KinematicsOutputDimension.__members__])
def test_kinematics_schema_matches_produced_shape(output_type, dimension, output_dimension):
    block = Kinematics(dims=dimension, output_type=output_type, output_dims=output_dimension)
    (output,) = block.outputs
    assert output.name == output_type
    for index in range(8):
        point = np.arange(dimension, dtype=float) * index + index * index
        result = block.process(point, timestamp=(index + 1) * 0.04)  # a first timestamp of 0 gives the first time step 0
    assert result.status is Status.OK
    value = result[output.name]
    assert np.shape(value) == output.shape
    assert block.outputs.size == (dimension if output.shape else 1)
    assert result.timestamp == pytest.approx(8 * 0.04)
    series_block = Kinematics(dims=dimension, output_type=output_type,
                                         output_dims=output_dimension,
                                         input_mode="time_series")
    assert series_block.outputs.names == block.outputs.names
    series = series_block.process(np.vstack([np.arange(30.0) ** 2] * dimension), timestamp=0.04)
    assert np.shape(series[output.name]) == output.shape


def test_kinematics_defaults_and_forced_dimensions():
    default = Kinematics()
    assert default.outputs.names == ("velocity",) and default.outputs["velocity"].shape == ()
    comp = Kinematics(dims=3, output_dims="components")
    assert comp.outputs["velocity"].shape == (3,) and comp.outputs.flat_names == ("velocity_x", "velocity_y",
                                                                                 "velocity_z")
    assert default.inputs["point"].shape == (None,)


def test_rarity_and_sample_entropy_and_mecs_sizes_follow_parameters():
    rarity = Rarity(method="information", number_of_inputs=3)
    assert rarity.outputs["rarity"].shape == (3,) and rarity.process([0.1, 0.5, 0.9]).rarity.shape == (3,)
    entropy = SampleEntropy(window=len(SINE), embedding_dimension=4, tolerance=0.5)
    assert entropy.outputs["sample_entropy"].shape == (4,) and entropy._process_window(SINE).sample_entropy.shape == (4,)
    mecs = EventSynchronizationMECS(window=40, hop=40, event_class_number=2)
    assert mecs.outputs["events"].shape == (2,)
    out = mecs._process_window(*[np.vstack([EVENTS] * 2)] * 2)
    assert out.synchronization.shape == (2,) and out.events.shape == (2,)
    assert CorrelationsMatrix(window=50, n_inputs=3).outputs["matrix"].shape == (3, 3)


@pytest.mark.parametrize("name,expected", [
    ("Rarity", {"rarity": (2,)}),
    ("SampleEntropy", {"sample_entropy": (12,)}),
    ("CorrelationsMatrix", {"matrix": (4, 4)}),
    ("EventSynchronizationMECS", {"synchronization": (3,), "events": (3,)}),
    ("Symmetry", {"symmetry": ()}),
    ("PointsDensity", {"density": (), "centroid": (3,)}),
    ("Kinematics", {"velocity": ()}),
])
def test_default_constructor_matches_declared_defaults(name, expected):
    """Block built with no arguments: the schema's duplicated C++ defaults must be what the core produces."""
    block = {"Rarity": Rarity, "SampleEntropy": lambda: SampleEntropy(window=200),
             "CorrelationsMatrix": lambda: CorrelationsMatrix(window=50),
             "EventSynchronizationMECS": lambda: EventSynchronizationMECS(window=40, hop=40),
             "Symmetry": lambda: Symmetry(**RATIO), "PointsDensity": PointsDensity,
             "Kinematics": Kinematics}[name]()
    for output_name, shape in expected.items():
        output = block.outputs[output_name]
        assert output.shape == shape or (output.labelled and output.shape == shape)
    if name == "Rarity":
        assert block.process([0.1, 0.9]).rarity.shape == (2,)
    elif name == "SampleEntropy":
        assert block._process_window(np.sin(np.arange(200) / 3.0)).sample_entropy.shape == (12,)
    elif name == "CorrelationsMatrix":
        assert block._process_window(np.stack([signal_a, signal_b, signal_a, signal_b])).matrix.shape == (4, 4)
    elif name == "EventSynchronizationMECS":
        assert block._process_window(*[np.vstack([EVENTS] * 3)] * 2).events.shape == (3,)
    elif name == "Symmetry":
        assert isinstance(block.process(SKELETON).symmetry, float)
    elif name == "PointsDensity":
        assert isinstance(block.process({"a": (0, 0, 0)}).density, float)
    elif name == "Kinematics":
        assert isinstance(block.process([0.0, 0.0, 0.0]).velocity, float)


# ----------------------------------------------------------------------------------- (e) immutability, (f) recorder

@pytest.mark.parametrize("name", ["KineticEnergy", "CorrelationsMatrix", "Symmetry"])
def test_results_are_immutable(name):
    _, result = run(name)
    with pytest.raises(AttributeError):
        result.status = Status.NO_OUTPUT
    with pytest.raises(AttributeError):
        setattr(result, result.schema.names[0], 1.0)
    for value in result.to_dict().values():
        if isinstance(value, np.ndarray):
            with pytest.raises(ValueError):
                value[...] = 0


def test_recorder_over_a_stream_of_one_block():
    block = Kinematics(dims=2, output_dims="components",
                                  output_type="smoothed")
    recorder = Recorder(block)
    for index in range(12):
        recorder.append(block.process([float(index), 2.0 * index], timestamp=index * 0.04))
    assert len(recorder) == 12
    assert recorder.column("smoothed").shape == (12, 2)
    frame = recorder.to_frame()
    assert len(frame) == 12 and {"smoothed_x", "smoothed_y"} <= set(frame.columns)

    gs = GestureSegmenter(filter_window_length=5)
    rec = Recorder(gs)
    for index in range(12):
        rec.append(gs.process(0.01 * index, timestamp=index * 0.04))
    assert len(rec) == 12 and rec.column("gesturing").dtype == np.bool_


def test_reset_exists_on_every_block_and_attributes_pass_through():
    for factory in (ContourCurvature, EllipsoidSphericity):
        factory().reset()  # stateless blocks: no-op
    assert FilterContour().kernel is not None


def test_time_is_nan_unless_a_creation_time_is_given():
    ke = KineticEnergy(weights={"a": 1.0})
    assert math.isnan(ke.process({"a": (0, 0, 0)}).timestamp)
    assert ke.process({"a": (0, 0, 0)}, timestamp=2.0).timestamp == pytest.approx(2.0)
    kin = Kinematics(dims=1)
    assert math.isnan(kin.process([0.0]).timestamp)
    assert kin.process([0.0], timestamp=1.0).timestamp == pytest.approx(1.0)


# ------------------------------------------------------------------ array input and batch run

def _ke(labels=None):
    names = [f"j{index}" for index in range(5)]
    return names, KineticEnergy(weights={name: 1.0 + index for index, name in enumerate(names)}, labels=labels)


def test_kinetic_energy_array_input_matches_dict_input():
    names, by_dict = _ke()
    _, by_array = _ke(names)
    frames = np.random.default_rng(1).normal(size=(30, 5, 3))
    for frame in frames:
        expected = by_dict.process({name: tuple(point) for name, point in zip(names, frame)}).kinetic_energy
        assert by_array.process(frame).kinetic_energy == expected


def test_kinetic_energy_run_matches_the_frame_loop_and_can_continue_state():
    names, loop = _ke(names := [f"j{index}" for index in range(5)])
    _, batch = _ke(names)
    frames = np.random.default_rng(2).normal(size=(40, 5, 3))
    times = np.arange(40) * 0.01  # seconds
    expected = np.array([loop.process(frame, timestamp=timestamp).kinetic_energy for frame, timestamp in zip(frames, times)])
    rec = batch.run(frames[:25], timestamps=times[:25])
    rec2 = batch.run(frames[25:], timestamps=times[25:], reset=False)  # continues from the previous call
    assert np.array_equal(np.concatenate([rec["kinetic_energy"], rec2["kinetic_energy"]]), expected)
    assert rec.ok.all() and len(rec) == 25 and np.allclose(rec.timestamps, times[:25])
    assert np.array_equal(batch.run(frames[:25], timestamps=times[:25])["kinetic_energy"], rec["kinetic_energy"])  # reset: pure


def test_kinetic_energy_array_input_needs_labels_and_checks_shape():
    names, no_labels = _ke()
    with pytest.raises(ValueError, match="labels"):
        no_labels.process(np.zeros((5, 3)))
    _, with_labels = _ke(names)
    with pytest.raises(ValueError):
        with_labels.process(np.zeros((4, 3)))
    with pytest.raises(ValueError):
        with_labels.run(np.zeros((10, 4, 3)))


# ------------------------------------------------------------------------------------------------ extensions

def _velocity_block(**kw):
    return KineticEnergy(input_mode="velocity",
                                **kw)


def test_kinetic_energy_velocity_mode_values_and_input_forms():
    weights = {"a": 2.0, "b": 4.0}
    velocities = {"a": (1, 2, 2), "b": (0, 0, 1)}
    block = _velocity_block(weights=weights)
    assert block.process(velocities)["kinetic_energy"] == pytest.approx(11.0)  # first call already produces output
    assert block.process(velocities)["kinetic_energy"] == pytest.approx(11.0)
    arr = _velocity_block(weights=weights, labels=["a", "b"])
    frame = np.array([[1, 2, 2], [0, 0, 1]], dtype=float)
    assert arr.process(frame)["kinetic_energy"] == pytest.approx(11.0)
    rec = arr.run(np.stack([frame, 2 * frame]))
    assert np.allclose(rec["kinetic_energy"], [11.0, 44.0])


def test_kinetic_energy_velocity_mode_rejects_reference_point():
    with pytest.raises(ValueError):
        _velocity_block(weights={"a": 1.0}, reference_point="a")


def test_kinetic_energy_velocity_mode_matches_position_mode_on_differences():
    rng = np.random.default_rng(0)
    labels = ["a", "b", "c"]
    weights = {"a": 1.0, "b": 0.5, "c": 2.0}
    frames = rng.normal(size=(20, 3, 3))
    common = dict(weights=weights, labels=labels, sampling_rate=1)
    position = KineticEnergy(**common).run(frames)["kinetic_energy"]
    velocity = _velocity_block(weights=weights, labels=labels).run(np.diff(frames, axis=0))["kinetic_energy"]
    assert np.allclose(position[1:], velocity, rtol=1e-12)


def test_kinetic_energy_velocity_mode_parity_with_the_removed_python_class():
    from energy_reference import VelocityKineticEnergyReference
    rng = np.random.default_rng(1)
    weights = rng.uniform(0, 3, size=5)
    labels = [f"j{index}" for index in range(5)]
    block = _velocity_block(weights=dict(zip(labels, weights)), labels=labels)
    old = VelocityKineticEnergyReference(weights=weights)
    for _ in range(10):
        values = rng.normal(size=(5, 3))
        assert block.process(values)["kinetic_energy"] == pytest.approx(old.compute(values)["total_energy"], rel=1e-12)


def test_ellipsoid_sphericity_axes_path_leaves_fit_outputs_invalid():
    result = EllipsoidSphericity().process_axes(1, 2, 3)
    assert result["sphericity"] == pytest.approx(core.motion.EllipsoidSphericity.process(1, 2, 3))
    assert not result.valid["axis_ratio"] and not result.valid["radii"] and result.valid["sphericity"]


def test_ellipsoid_sphericity_points_parity_with_the_removed_python_class():
    from contraction_reference import EllipsoidFitSphericityReference
    rng = np.random.default_rng(2)
    clouds = [rng.normal(size=(30, 3)) * [3, 1, 0.2], rng.normal(size=(8, 3)), np.zeros((5, 3)), np.ones((1, 3)),
              np.outer(np.arange(6.0), [1, 2, 3]), rng.normal(size=(40, 2)).dot(rng.normal(size=(2, 3))),
              np.zeros((0, 3))]
    block = EllipsoidSphericity()
    old = EllipsoidFitSphericityReference()
    for cloud in clouds:
        result = block.process(cloud)
        if len(cloud) == 0:
            assert result["axis_ratio"] == 0.0
            continue
        assert result["axis_ratio"] == pytest.approx(old.compute(cloud)["sphericity"], abs=1e-6)
        assert result.valid["axis_ratio"] and result["radii"].shape == (3,)
    assert block.process(clouds[0])["sphericity"] == pytest.approx(
        block.process_axes(*block.process(clouds[0])["radii"])["sphericity"])
