"""The output contract itself: Output / Schema / Result / OutputsMixin / Recorder, with toy features."""
import math

import numpy as np
import pytest

from pyeyesweb.data_models import Output, OutputsMixin, Recorder, Result, Schema, Status

XYZ = ("x", "y", "z")


# ------------------------------------------------------------------------------------------------ toy features

class StaticFeature(OutputsMixin):
    """Test helper: a pure `compute(array)` feature (the output contract does not depend on the call style)."""


DynamicFeature = StaticFeature


class Centroid(StaticFeature):
    """Static: centroid (3,) and mean distance to it (scalar, or per axis with mode='component')."""

    def __init__(self, mode="module"):
        super().__init__()
        self.mode = mode

    def _schema(self):
        density = Output("density", components=XYZ) if self.mode == "component" else Output("density", unit="m")
        return Schema(density, Output("centroid", components=XYZ, unit="m"), Output("count", kind=int))

    def compute(self, frame):
        if len(frame) == 0:
            return self._no_output(Status.INVALID_INPUT, "no points")
        centre = frame.mean(axis=0)
        distances = (np.abs(frame - centre).mean(axis=0) if self.mode == "component" else np.linalg.norm(frame - centre, axis=1).mean())
        return self._result(density=distances, centroid=centre, count=len(frame))


class Trend(DynamicFeature):
    """Dynamic: slope of the mean signal; WARMING_UP until 3 samples; the slope's validity is partial."""
    _OUTPUTS = Schema(Output("slope"), Output("n", kind=int), Output("flag", kind=bool))

    def compute(self, window):
        if len(window) < 3:
            return self._result(status=Status.WARMING_UP, reason="needs 3 samples", n=len(window))
        means = window.reshape(len(window), -1).mean(axis=1)
        return self._result(slope=float(np.polyfit(np.arange(len(means)), means, 1)[0]), n=len(means), flag=True)


# ------------------------------------------------------------------------------------------------------ Output

def test_output_infers_shape_from_labels_and_components():
    assert Output("a").shape == ()
    assert Output("a", components=XYZ).shape == (3,)
    assert Output("a", labels=("l", "r")).shape == (2,)
    assert Output("a", labels=("l", "r"), components=("x", "y")).shape == (2, 2)
    assert Output("a", 4).shape == (4,)


def test_output_flat_names_follow_c_order():
    assert Output("a").flat_names == ("a",)
    assert Output("a", components=XYZ).flat_names == ("a_x", "a_y", "a_z")
    assert Output("a", 2).flat_names == ("a_0", "a_1")
    assert Output("e", labels=("l", "r"), components=("x", "y")).flat_names == ("e_l_x", "e_l_y", "e_r_x", "e_r_y")


@pytest.mark.parametrize("make", [
    lambda: Output("not valid"),
    lambda: Output("a", kind=str),
    lambda: Output("a", 3, components=("x", "y")),
    lambda: Output("a", labels=("only",), shape=(2,)),
    lambda: Output("a", components=XYZ, shape=()),
])
def test_output_rejects_inconsistent_declarations(make):
    with pytest.raises(ValueError):
        make()


def test_variable_and_labelled_outputs_have_no_flat_names():
    for output in (Output("a", (None,)), Output("s", components=XYZ, labelled=True, shape=(3,))):
        assert not output.fixed
        with pytest.raises(ValueError):
            output.flat_names


def test_output_is_immutable():
    with pytest.raises(AttributeError):
        Output("a").name = "b"


# ------------------------------------------------------------------------------------------------------ Schema

def test_schema_layout_is_known_before_any_data():
    centroid = Centroid()
    schema = centroid.outputs
    assert schema.names == ("density", "centroid", "count")
    assert schema.flat_names == ("density", "centroid_x", "centroid_y", "centroid_z", "count")
    assert schema.size == 5 and schema.is_fixed
    assert schema.layout == (("density", 0, 1, True), ("centroid", 1, 3, False), ("count", 4, 1, True))
    assert Centroid("component").outputs.flat_names[:3] == ("density_x", "density_y", "density_z")


def test_schema_separates_fixed_and_variable_outputs():
    schema = Schema(Output("a"), Output("b", (None,)), Output("c", components=("x", "y")))
    assert [output.name for output in schema.fixed_outputs] == ["a", "c"]
    assert [output.name for output in schema.variable_outputs] == ["b"]
    assert schema.flat_names == ("a", "c_x", "c_y") and not schema.is_fixed


def test_schema_select_narrows_a_catalogue_in_declaration_order():
    catalogue = Schema(Output("a"), Output("b", components=("x", "y")), Output("c"))
    chosen = catalogue.select(["c", "b"])
    assert chosen.names == ("b", "c") and chosen.flat_names == ("b_x", "b_y", "c")
    with pytest.raises(KeyError):
        catalogue.select(["a", "nope"])


def test_schema_rejects_duplicate_names():
    with pytest.raises(ValueError):
        Schema(Output("a"), Output("a"))


def test_schema_describe_and_to_dict_are_informative():
    schema = Centroid().outputs
    text = schema.describe()
    assert "centroid" in text and "(3,)" in text and "m" in text
    as_dict = schema.to_dict()
    assert as_dict["flat_names"][1] == "centroid_x" and as_dict["outputs"][2]["kind"] == "int"


# ------------------------------------------------------------------------------------------------------ Result

POINTS = np.array([[0.0, 0, 0], [2, 0, 0]])


def test_result_has_one_attribute_per_output_and_a_named_type():
    result = Centroid().compute(POINTS)
    assert type(result).__name__ == "CentroidResult" and isinstance(result, Result)
    assert result.density == pytest.approx(1.0) and result.count == 2
    assert np.allclose(result.centroid, [1, 0, 0])
    assert result.status is Status.OK and result.ok and result.is_valid and result.reason == ""
    assert math.isnan(result.timestamp)
    assert "centroid" in dir(result)


def test_missing_values_are_nan_zero_false_never_none():
    result = Trend().compute(np.zeros((2, 1, 1)))
    assert result.status is Status.WARMING_UP and not result.ok and result.reason == "needs 3 samples"
    assert math.isnan(result.slope) and result.flag is False
    assert result.n == 2 and result.valid == {"slope": False, "n": True, "flag": False}


def test_a_no_output_result_has_every_output_empty_and_invalid():
    result = Centroid().compute(np.empty((0, 3)))
    assert result.status is Status.INVALID_INPUT and result.reason == "no points"
    assert np.isnan(result.centroid).all() and result.centroid.shape == (3,) and result.count == 0
    assert not any(result.valid.values())


def test_none_counts_as_not_produced():
    result = Centroid()._result(density=None, centroid=[1, 2, 3], count=1)
    assert result.valid == {"density": False, "centroid": True, "count": True} and math.isnan(result.density)


def test_results_are_immutable_and_do_not_alias_feature_state():
    centroid = Centroid()
    source = np.array([1.0, 2, 3])
    result = centroid._result(centroid=source, density=1.0, count=1)
    source[0] = 99
    assert result.centroid[0] == 1.0
    with pytest.raises(ValueError):
        result.centroid[0] = 5
    with pytest.raises(AttributeError):
        result.density = 3.0
    with pytest.raises(AttributeError):
        result.status = Status.NO_OUTPUT


def test_result_validates_names_and_shapes():
    centroid = Centroid()
    with pytest.raises(KeyError):
        centroid._result(unknown=1.0)
    with pytest.raises(ValueError):
        centroid._result(centroid=[1.0, 2.0])
    with pytest.raises(ValueError):
        centroid._result(centroid=np.zeros((3, 3)))


def test_export_forms_agree_with_the_schema():
    centroid = Centroid()
    result = centroid.compute(POINTS)
    vec = result.to_array()
    assert vec.shape == (centroid.outputs.size,) and vec.dtype == np.float64
    assert np.allclose(vec, [1, 1, 0, 0, 2])
    assert result["centroid_x"] == 1.0 and np.allclose(result["centroid"], [1, 0, 0])
    with pytest.raises(KeyError):
        result["nope"]
    flat = result.to_flat_dict("c")
    assert list(flat) == ["c_status", "c_timestamp", "c_density", "c_centroid_x", "c_centroid_y", "c_centroid_z", "c_count"]
    assert list(result.to_flat_dict(meta=False)) == list(centroid.outputs.flat_names)
    assert set(result.to_dict()) == {"density", "centroid", "count"}


def test_fixed_layout_is_identical_for_valid_and_empty_results():
    centroid = Centroid()
    good, bad = centroid.compute(POINTS), centroid.compute(np.empty((0, 3)))
    assert good.to_flat_dict().keys() == bad.to_flat_dict().keys()
    assert good.to_array().shape == bad.to_array().shape
    assert np.isnan(bad.to_array()[:4]).all() and bad.to_array()[4] == 0


def test_variable_and_labelled_outputs_flatten_by_their_actual_size():
    class Skeleton(StaticFeature):
        _OUTPUTS = Schema(Output("scale"), Output("curve", (None,)),
                         Output("joints", components=("x", "y"), labelled=True, shape=(2,)))

        def compute(self, frame):
            return self._result(scale=1.0, curve=[3.0, 4.0, 5.0], joints={"head": (1, 2), "hip": (3, 4)})

    result = Skeleton().compute(None)
    assert result.to_array().shape == (1,)  # only the fixed output
    flat = result.to_flat_dict(meta=False)
    assert list(flat) == ["scale", "curve_0", "curve_1", "curve_2", "joints_head_x", "joints_head_y",
                          "joints_hip_x", "joints_hip_y"]
    assert flat["joints_hip_y"] == 4.0
    with pytest.raises(ValueError):
        Skeleton()._result(joints={"head": (1, 2, 3)})


def test_component_names_apply_to_variable_sizes_by_position():
    class Energy(StaticFeature):
        _OUTPUTS = Schema(Output("component", (None,), components=("x", "y", "z", "w")),
                         Output("joint", (None, None), components=("x", "y", "z")))

        def compute(self, frame):
            return self._result(component=frame[0], joint=frame)

    energy = Energy()
    flat = energy.compute(np.ones((2, 3))).to_flat_dict(meta=False)
    assert list(flat) == ["component_x", "component_y", "component_z",
                          "joint_0_x", "joint_0_y", "joint_0_z", "joint_1_x", "joint_1_y", "joint_1_z"]
    # more entries than names: fall back to indices rather than guessing
    assert list(energy.compute(np.ones((1, 5))).to_flat_dict(meta=False))[:2] == ["component_0", "component_1"]


def test_equality_with_nan_and_with_time():
    centroid = Centroid()
    first, second = centroid.compute(POINTS), centroid.compute(POINTS)
    assert first == second and first != centroid.compute(POINTS * 2)
    stamped = first.with_time(5.0)
    assert stamped.timestamp == 5.0 and math.isnan(first.timestamp) and stamped == first and type(stamped) is type(first)
    assert centroid.compute(np.empty((0, 3))) == centroid.compute(np.empty((0, 3)))


def test_repr_shows_status_and_values():
    text = repr(Centroid().compute(POINTS))
    assert text.startswith("CentroidResult(status=OK") and "centroid=" in text


# ------------------------------------------------------------------------------------------------------ mixin

def test_schema_can_depend_on_parameters_and_be_rebuilt():
    centroid = Centroid("module")
    assert centroid.outputs["density"].shape == ()
    assert centroid.outputs is centroid.outputs  # cached
    centroid.mode = "component"
    centroid._outputs_changed()
    assert centroid.outputs["density"].shape == (3,)
    assert centroid.compute(POINTS).density.shape == (3,)


def test_a_feature_without_outputs_fails_loudly():
    class Bare(OutputsMixin):
        pass

    with pytest.raises(NotImplementedError):
        Bare().outputs












# ------------------------------------------------------------------------------------------------------ Recorder

def test_recorder_collects_fixed_outputs_as_columns():
    centroid = Centroid()
    rec = Recorder(centroid, capacity=2)  # forces growth
    rng = np.random.default_rng(0)
    frames = [rng.random((4, 3)) for _ in range(7)]
    for frame in frames:
        rec.append(centroid.compute(frame))
    assert len(rec) == 7
    assert rec["centroid"].shape == (7, 3) and rec["density"].shape == (7,) and rec["count"].dtype == np.int64
    assert np.allclose(rec["centroid"], [fr.mean(axis=0) for fr in frames])
    assert np.allclose(rec["centroid_y"], rec["centroid"][:, 1])
    assert rec.to_numpy().shape == (7, centroid.outputs.size)
    assert rec.ok.all() and (rec.status == Status.OK).all() and np.isnan(rec.timestamps).all()


def test_recorder_keeps_invalid_rows_aligned():
    centroid = Centroid()
    rec = Recorder(centroid.outputs)
    rec.append(centroid.compute(POINTS))
    rec.append(centroid.compute(np.empty((0, 3))))
    rec.append(centroid.compute(POINTS))
    assert list(rec.status) == [Status.OK, Status.INVALID_INPUT, Status.OK]
    assert list(rec.ok) == [True, False, True]
    assert list(rec.valid["centroid"]) == [True, False, True]
    assert np.isnan(rec["centroid"][1]).all()


def test_recorder_stores_variable_outputs_as_lists():
    class Curve(StaticFeature):
        _OUTPUTS = Schema(Output("peak"), Output("curve", (None,)))

        def compute(self, frame):
            return self._result(peak=float(frame.max()), curve=frame)

    curve = Curve()
    rec = Recorder(curve)
    rec.run(curve.compute, [np.arange(3.0), np.arange(5.0)])
    assert rec["peak"].tolist() == [2.0, 4.0]
    assert [len(third) for third in rec["curve"]] == [3, 5]
    assert rec.to_numpy().shape == (2, 1)


def test_recorder_rejects_foreign_results():
    rec = Recorder(Centroid())
    with pytest.raises(ValueError):
        rec.append(Trend().compute(np.zeros((5, 1, 1))))


def test_recorder_carries_timestamps():
    centroid = Centroid()
    rec = Recorder(centroid)
    rec.append(centroid.compute(POINTS).with_time(1.5))
    assert rec.timestamps.tolist() == [1.5]


def test_recorder_to_frame():
    pytest.importorskip("pandas")
    centroid = Centroid()
    rec = Recorder(centroid)
    rec.append(centroid.compute(POINTS).with_time(1.0))
    rec.append(centroid.compute(np.empty((0, 3))).with_time(2.0))
    frame = rec.to_frame()
    assert list(frame.columns) == ["status", "reason", "timestamp", *centroid.outputs.flat_names]
    assert list(frame["status"]) == ["OK", "INVALID_INPUT"]
    assert list(frame["status"] == "OK") == [True, False]
    assert frame.loc[0, "centroid_x"] == 1.0 and np.isnan(frame.loc[1, "centroid_x"])
    assert list(rec.to_frame(meta=False).columns) == list(centroid.outputs.flat_names)
