"""Units of the outputs (`Output.unit`) of every catalog feature.

The unit is documentation, in terms of the data: `"<length>"` stands for whatever length unit the data is in, `"<input>"` for the
unit of the input, and a feature with a `units="m"|"mm"` parameter names the unit it was given (`"mm/s"`). An output with no unit is
dimensionless and must be listed here with the reason (`EXEMPT`); a boolean output is a flag and needs no entry.
"""

import pytest

from test_contract_all_features import NAMES, factory_and_recordings

EXEMPT = {
    "a ratio, an index or a score without a unit": (
        "SilhouetteCentroids.normalized BoundingBoxFilledArea.contraction_index EllipsoidSphericity.sphericity "
        "EllipsoidSphericity.axis_ratio Symmetry.symmetry TriangleSymmetry.symmetry "
        "SpectralArcLength.spectral_arc_length LogDimensionlessJerk.log_dimensionless_jerk Harmonicity.harmonicity "
        "CurvatureDispersion.curvature_dispersion CurvatureVelocityCorrelation.smoothness Equilibrium.equilibrium "
        "DirectionChange.cosine Directness.directness_index SuddennessImpulsivity.impulsivity_index "
        "Suddenness.alpha Suddenness.beta Suddenness.gamma EnsembleDominance.dominance_score PhaseLockingValue.phase_locking_value "
        "CorrelationsMatrix.correlations_matrix PartialRecurrenceSynchronization.synchronization_matrix "
        "GeneralisedAutoCorrelation.recurrence_rate EventSynchronization.synchronization EventSynchronization.delay "
        "EventSynchronizationMECS.synchronization NonlinearInterdependence.first_to_second_interdependence "
        "NonlinearInterdependence.second_to_first_interdependence NonlinearInterdependence.threshold "
        "SpikeSynchronization.degree SpikeSynchronization.distance SpikeSynchronization.profile "
        "RecurrencePlot.recurrence_matrix CrossRecurrencePlot.cross_recurrence_matrix "
        "TemporalSynchronization.progression TemporalSynchronization.efficiency_step Periodicity.powers "
        "HumanoidOrientations.directions"),
    "a logarithm of a ratio (an information measure)": (
        "SampleEntropy.sample_entropy Rarity.rarity MultiScaleEntropy.complexity_index MultiScaleEntropy.scale_entropies"),
    "a count or an index": (
        "SubmovementCount.submovement_count BinaryPulsesRegularity.pulse_count EnsembleDominance.leader_index "
        "EventSynchronizationMECS.events SequenceDetector.sequence_count TemporalSynchronization.step "
        "TemporalSynchronization.state"),
    "a potential, defined by the potential type and not by a unit": (
        "PositionDependingPotentials.potential RegionDependingPotentials.potential"),
    "an image of pixel values (0-255)": "SilhouetteBodyParts.masks Videogram.videogram",
    "a cost mixing direction, position and speed errors": "GenericModelEstimator.error",
}
EXEMPT = {tuple(entry.split(".")): reason for reason, entries in EXEMPT.items() for entry in entries.split()}

# A feature with `units=`: the outputs that are a length (or a speed...) and must name the unit it was given.
LENGTH_OUTPUTS = {
    "HumanoidSimulator": ("joints",), "GenericModelSimulator": ("positions",), "GenericModelPredictor": ("positions",),
    "GenericModelEstimator": ("positions",), "Kinematics": ("velocity",), "TrajectoryNonPlanarity": ("curvature_radius",),
    "HitCellDetector": (), "CurvatureDispersion": (), "Equilibrium": (), "MotionNoiseDetector": (),
}


def _feature(name):
    return factory_and_recordings(name)[0]()


@pytest.mark.parametrize("name", NAMES)
def test_every_output_has_a_unit_or_is_listed_as_dimensionless(name):
    for output in _feature(name).outputs:
        if output.kind is not bool and not output.unit:
            assert (name, output.name) in EXEMPT, f"{name}.{output.name} has no unit and is not in EXEMPT"
        else:
            assert (name, output.name) not in EXEMPT, f"{name}.{output.name} has a unit (or is a flag): drop it from EXEMPT"


def test_exempt_entries_name_outputs_that_exist():
    existing = {(name, output.name) for name in NAMES for output in _feature(name).outputs}
    assert set(EXEMPT) <= existing


@pytest.mark.parametrize("name", NAMES)
def test_a_feature_with_units_names_the_unit_it_was_given(name):
    feature = _feature(name)
    if not type(feature)._unit_params:
        assert name not in LENGTH_OUTPUTS
        return
    feature.units = "mm"
    for output in LENGTH_OUTPUTS[name]:
        assert "mm" in feature.outputs[output].unit and "<" not in feature.outputs[output].unit
