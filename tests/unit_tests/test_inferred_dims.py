"""`dims` taken from the first frame and string forms of `algorithm`."""
import numpy as np
import pytest

from pyeyesweb.low_level import Kinematics
from pyeyesweb.mid_level import Suddenness, SuddennessImpulsivity

FEATURES = [Suddenness, SuddennessImpulsivity]
WINDOW = 10


def _frames(dims, count=24, seed=1):
    """One point per frame: `(count, dims)`."""
    return np.cumsum(np.random.default_rng(seed).standard_normal((count, dims)), axis=0)


def _values(feature, frames):
    return [result.to_dict() for result in (feature.process(frame, timestamp=index / 50) for index, frame in enumerate(frames)) if result.ok]


@pytest.mark.parametrize("cls", FEATURES)
@pytest.mark.parametrize("dims", [2, 3])
def test_inferred_dims_gives_the_numbers_of_the_explicit_ones(cls, dims):
    frames = _frames(dims)
    inferred, explicit = _values(cls(window=WINDOW), frames), _values(cls(window=WINDOW, dims=dims), frames)
    assert inferred and inferred == explicit


@pytest.mark.parametrize("cls", FEATURES)
def test_inputs_before_and_after_the_first_frame(cls):
    feature = cls(window=WINDOW)
    assert feature.dims is None and feature.inputs[0].shape == (None,)
    feature.process(_frames(2)[0])
    assert feature.dims == 2 and feature.inputs[0].shape == (2,)


@pytest.mark.parametrize("cls", FEATURES)
def test_a_changed_dimension_is_a_shape_error(cls):
    for feature in (cls(window=WINDOW), cls(window=WINDOW, dims=2)):
        feature.process(_frames(2)[0])
        with pytest.raises(ValueError):
            feature.process(_frames(3)[0])


@pytest.mark.parametrize("cls", FEATURES)
def test_reset_forgets_an_inferred_dims_only(cls):
    feature = cls(window=WINDOW)
    feature.process(_frames(2)[0])
    feature.reset()
    assert feature.dims is None
    feature.process(_frames(3)[0])
    assert feature.dims == 3
    explicit = cls(window=WINDOW, dims=3)
    explicit.process(_frames(3)[0])
    explicit.reset()
    assert explicit.dims == 3


@pytest.mark.parametrize("cls", FEATURES)
def test_dims_is_assignable_and_a_window_needs_it(cls):
    feature = cls(window=WINDOW)
    with pytest.raises(ValueError, match="dims"):
        feature._process_window(np.zeros((3, WINDOW)))
    feature.dims = 3
    assert feature.inputs[0].shape == (3,)
    with pytest.raises(ValueError):
        feature.process(_frames(2)[0])
    with pytest.raises(ValueError, match="dims"):
        feature.__class__(window=WINDOW, dims=0)


@pytest.mark.parametrize("cls", [Suddenness, SuddennessImpulsivity])
def test_algorithm_as_a_string(cls):
    for name, member in (("quantile", "quantile"), ("Constrained", "constrained")):
        assert cls(window=WINDOW, algorithm=name).algorithm == member
    with pytest.raises(ValueError, match="algorithm"):
        cls(window=WINDOW, algorithm="new")


# ----------------------------------------------------------------------------------------------------- Kinematics

def _path(dims, count=40, seed=2):
    return np.cumsum(np.random.default_rng(seed).standard_normal((count, dims)), axis=0)


def _mode_data(mode, dims):
    """One call's data of an input mode, `dims`-dimensional: a point or a `(D, N)` series."""
    path = _path(dims)
    return {"point": path[0], "time_series": path.T}[mode]


@pytest.mark.parametrize("dims", [2, 3])
@pytest.mark.parametrize("mode", ["point", "time_series"])
def test_kinematics_infers_dims_in_every_input_mode(mode, dims):
    feature = Kinematics(input_mode=mode, output_dims="components")
    assert feature.dims is None and feature.outputs["velocity"].shape == (None,)
    assert feature.inputs[0].shape.count(None) == (1 + (mode == "time_series"))
    result = feature.process(_mode_data(mode, dims), timestamp=1.0)
    assert feature.dims == dims and feature.outputs["velocity"].shape == (dims,) and result.velocity.shape == (dims,)
    assert feature.outputs.flat_names == tuple(f"velocity_{axis}" for axis in "xyz"[:dims])
    explicit = Kinematics(input_mode=mode, output_dims="components", dims=dims)
    np.testing.assert_array_equal(explicit.process(_mode_data(mode, dims), timestamp=1.0).velocity, result.velocity)


@pytest.mark.parametrize("dims", [2, 3])
def test_kinematics_run_infers_dims(dims):
    path = _path(dims)
    inferred, explicit = Kinematics(sampling_rate=50).run(path), Kinematics(dims=dims, sampling_rate=50).run(path)
    np.testing.assert_array_equal(inferred["velocity"], explicit["velocity"])


def test_a_changed_dimension_is_rejected_and_explicit_dims_stays():
    feature = Kinematics()
    first, other = _mode_data("point", 2), _mode_data("point", 3)
    feature.process(first)
    with pytest.raises(ValueError):
        feature.process(other)
    feature.reset()
    assert feature.dims is None
    feature.process(other)
    assert feature.dims == 3
    explicit = Kinematics(dims=3)
    explicit.process(other)
    explicit.reset()
    assert explicit.dims == 3 and explicit.outputs.names and explicit.inputs[0].shape[-1] in (3, None)


def test_dims_of_kinematics_is_assignable_and_validated():
    feature = Kinematics()
    feature.dims = 2
    assert feature.inputs[0].shape == (2,)
    feature.process([0.0, 1.0], timestamp=0.1)
    feature.dims = 3  # structural: the block is built again
    assert feature.process([0.0, 1.0, 2.0], timestamp=0.2).reason.startswith("parameters changed: state reset")
    with pytest.raises(ValueError):
        Kinematics(dims=4)
    with pytest.raises(ValueError, match="dims"):
        Kinematics(dims=0)
