"""Tests of pyeyesweb.native (EyesWeb C++ features via eyw_core / nanobind).

Skipped when the compiled eyw_core module is not installed.
"""
import numpy as np
import pytest

eyw_core = pytest.importorskip("eyw_core")

from pyeyesweb.data_models import SlidingWindow  # noqa: E402
from pyeyesweb.native import (  # noqa: E402
    AZURE_TO_HUMANOID,
    HUMANOID_JOINTS,
    K4ABT_JOINTS,
    BodySubRegions,
    BoneOrientations,
    EventSynchronization,
    HumanoidFilter,
    NonlinearInterdependence,
    RecurrenceRate,
    SilhouetteCentroids,
    SpikeSynchronization,
    azure_to_humanoid_frame,
    extract_events,
    is_available,
    mask_from_body_index,
)


def _pulses(n, period, phase):
    x = np.zeros(n)
    x[phase::period] = 1.0
    return x


def _window(signals):
    """(T, S) array -> SlidingWindow(n_signals=S, n_dims=1)."""
    w = SlidingWindow(max_length=len(signals), n_signals=signals.shape[1], n_dims=1)
    for row in signals:
        w.append(row)
    return w


def _tpose():
    pos = eyw_core.humanoid.HumanoidSimulator().positions()
    return np.array([pos[n] for n in HUMANOID_JOINTS])


# ---------------------------------------------------------------------------
def test_available():
    assert is_available()


# ---------------------------------------------------------------------------
# event extraction / synchronization
# ---------------------------------------------------------------------------
def test_extract_events_peaks_finds_maxima():
    t = np.arange(300)
    sig = np.sin(2 * np.pi * t / 30)[:, None]
    ev = extract_events(sig, "peaks", peak_buffer=5, peak_threshold=0.1)
    idx = np.flatnonzero(ev[:, 0])
    assert 9 <= len(idx) <= 10
    # peaks of sin(2 pi t / 30) at t = 7.5 + 30k; detector latency ~ buffer/2
    assert np.all(np.abs((idx - 7.5) % 30 - 2) <= 3)


def test_extract_events_binary_and_bad_mode():
    ev = extract_events(np.array([[0.0, 2.0], [0.5, -1.0]]), "binary")
    np.testing.assert_array_equal(ev, [[0, 1], [1, 0]])
    with pytest.raises(ValueError):
        extract_events(np.zeros((3, 1)), "nope")


def test_event_synchronization_lead_lag():
    x = _pulses(200, 10, 0)
    y = _pulses(200, 10, 2)                      # y follows x by 2 samples
    r = EventSynchronization(tau=3, events="binary")(_window(np.c_[x, y]))
    assert r.is_valid and r.Q == pytest.approx(1.0) and r.q == pytest.approx(1.0)
    r = EventSynchronization(tau=3, events="binary")(_window(np.c_[y, x]))
    assert r.q == pytest.approx(-1.0)


def test_event_synchronization_unsynchronized_and_invalid():
    rng = np.random.default_rng(0)
    x, y = (rng.random(400) < 0.05).astype(float), (rng.random(400) < 0.05).astype(float)
    r = EventSynchronization(tau=1, events="binary").compute(np.c_[x, y][:, :, None])
    assert r.is_valid and r.Q < 0.3
    assert not EventSynchronization(events="binary").compute(np.zeros((50, 3, 1))).is_valid
    bad = np.c_[x, y][:, :, None].copy()
    bad[3, 0, 0] = np.nan
    assert not EventSynchronization(events="binary").compute(bad).is_valid
    assert not EventSynchronization()(SlidingWindow(10, 2, 1)).is_valid       # empty window


def test_event_synchronization_on_3d_velocity():
    # two hands with the same oscillation, the right one 3 samples later
    t = np.arange(300) / 30
    vel_l = np.stack([np.sin(2 * np.pi * 0.7 * t), np.zeros_like(t), np.zeros_like(t)], 1) * 500
    vel_r = np.roll(vel_l, 3, axis=0)
    data = np.stack([vel_l, vel_r], axis=1)        # (T, 2, 3) -> speed
    r = EventSynchronization(tau=5, peak_buffer=7, peak_threshold=50).compute(data)
    assert r.is_valid and r.Q > 0.9 and r.q > 0.8


def test_spike_synchronization():
    x = _pulses(300, 15, 0)
    r = SpikeSynchronization(events="binary").compute(np.c_[x, x, np.roll(x, 1)][:, :, None])
    assert r.is_valid and r.sync == pytest.approx(1.0) and r.n_events == 3 * x.sum()
    rng = np.random.default_rng(1)
    rnd = (rng.random((300, 3)) < 0.05).astype(float)
    assert SpikeSynchronization(events="binary").compute(rnd[:, :, None]).sync < 0.7
    assert not SpikeSynchronization(events="binary").compute(x[:, None, None]).is_valid


def test_nonlinear_interdependence():
    rng = np.random.default_rng(2)
    x = np.cumsum(rng.standard_normal(300))
    dep = NonlinearInterdependence(3, 4).compute(np.c_[x, np.roll(x, 1)][:, :, None])
    ind = NonlinearInterdependence(3, 4).compute(np.c_[x, np.cumsum(rng.standard_normal(300))][:, :, None])
    assert dep.is_valid and ind.is_valid
    assert dep.s_xy > ind.s_xy and dep.s_yx > ind.s_yx


def test_recurrence_rate_finds_period():
    t = np.arange(120)
    w = SlidingWindow(max_length=120, n_signals=1, n_dims=2)
    for ti in t:
        w.append([np.sin(2 * np.pi * ti / 20), np.cos(2 * np.pi * ti / 20)])
    r = RecurrenceRate(epsilon=0.2, tau_min=5, tau_spread=30)(w)
    assert r.is_valid and r.dominant_tau == 20
    assert len(r.rr) == len(r.taus) == 30 and r.rr.max() <= 1.0


def test_invalid_parameters():
    with pytest.raises((ValueError, TypeError)):
        EventSynchronization(tau=0)
    with pytest.raises(ValueError):
        EventSynchronization(events="other")
    with pytest.raises(ValueError):
        SilhouetteCentroids(silhouette_type="half")
    with pytest.raises(ValueError):
        BodySubRegions(not_a_param=1)


# ---------------------------------------------------------------------------
# humanoid
# ---------------------------------------------------------------------------
def test_azure_mapping():
    assert len(AZURE_TO_HUMANOID) == 21 and set(AZURE_TO_HUMANOID) == set(HUMANOID_JOINTS)
    az = np.arange(32 * 3, dtype=float).reshape(32, 3)
    hf = azure_to_humanoid_frame(az)
    assert hf.shape == (21, 3)
    np.testing.assert_array_equal(hf[HUMANOID_JOINTS.index("spine_base")], az[K4ABT_JOINTS["pelvis"]])
    np.testing.assert_array_equal(hf[HUMANOID_JOINTS.index("spine_shoulder")], az[K4ABT_JOINTS["spine_chest"]])
    with pytest.raises(ValueError):
        azure_to_humanoid_frame(np.zeros((25, 3)))


def test_bone_orientations_invariant_to_translation():
    pose = _tpose()
    w = SlidingWindow(max_length=1, n_signals=21, n_dims=3)
    w.append(pose)
    r1 = BoneOrientations()(w)
    r2 = BoneOrientations().compute(pose + np.array([500.0, -200.0, 3000.0]))
    assert r1.is_valid and len(r1.directions) == 20
    for k, v in r1.directions.items():
        np.testing.assert_allclose(v, r2.directions[k], atol=1e-9)
        assert np.linalg.norm(v) == pytest.approx(1.0)
    # bending the right elbow by 90 degrees changes the forearm direction by 90 degrees
    bent = pose.copy()
    e, wr, h = (HUMANOID_JOINTS.index(n) for n in ("right_elbow", "right_wrist", "right_hand"))
    fore = np.linalg.norm(pose[wr] - pose[e])
    bent[wr] = pose[e] + np.array([0.0, 0.0, fore])
    bent[h] = bent[wr] + np.array([0.0, 0.0, np.linalg.norm(pose[h] - pose[wr])])
    rb = BoneOrientations().compute(bent)
    d0, d1 = (np.array(r.directions["right_elbow-right_wrist"]) for r in (r1, rb))
    assert np.degrees(np.arccos(np.clip(d0 @ d1, -1, 1))) == pytest.approx(90.0, abs=1.0)
    assert rb.angle_between("right_elbow-right_wrist", "right_wrist-right_hand") == pytest.approx(
        r1.angle_between("right_elbow-right_wrist", "right_wrist-right_hand"), abs=1.0)


def test_humanoid_filter_static_pose_and_reset():
    pose = _tpose() + np.array([0.0, 900.0, 2500.0])
    f = HumanoidFilter(rate_hz=30)
    for _ in range(30):
        r = f.compute(pose)
    assert r.is_valid and r.positions.shape == (21, 3) and r.tracking_error < 1.0
    f.reset()
    r = f.compute(pose + 1000.0)                  # re-initialised on the new input
    assert r.tracking_error < 1.0


def test_humanoid_filter_missing_joints_and_names():
    pose = _tpose()
    pose[HUMANOID_JOINTS.index("left_foot")] = np.nan
    r = HumanoidFilter().compute(pose)
    assert r.is_valid and np.isfinite(r.tracking_error)
    with pytest.raises(ValueError):
        HumanoidFilter(joint_names=["left_hand", "right_hand"])
    with pytest.raises(ValueError):
        BoneOrientations().compute(np.zeros((5, 3)))


# ---------------------------------------------------------------------------
# silhouette
# ---------------------------------------------------------------------------
def _body_index_map():
    """Stick-figure body (index 0) on a 640x576 background (255)."""
    bim = np.full((576, 640), 255, np.uint8)
    bim[100:160, 300:340] = 0      # head
    bim[160:340, 270:370] = 0      # trunk
    bim[170:200, 150:270] = 0      # left arm (image left)
    bim[170:200, 370:490] = 0      # right arm
    bim[340:520, 275:310] = 0      # legs
    bim[340:520, 330:365] = 0
    return bim


def test_mask_from_body_index():
    bim = _body_index_map()
    bim[0:10, 0:10] = 1
    m = mask_from_body_index(bim)
    assert m.dtype == np.uint8 and set(np.unique(m)) == {0, 255}
    assert (mask_from_body_index(bim, 1) > 0).sum() == 100


def test_silhouette_centroids():
    mask = mask_from_body_index(_body_index_map())
    r = SilhouetteCentroids()(mask)
    assert r.is_valid
    c = r.centroids
    assert {"cog", "head", "left_hand", "right_hand", "left_foot", "right_foot"} <= set(c)
    assert c["head"][1] < c["cog"][1] < c["left_foot"][1]
    assert c["left_hand"][0] < c["cog"][0] < c["right_hand"][0]
    rn = SilhouetteCentroids(normalized=True)(mask)
    assert all(0.0 <= v <= 1.0 for xy in rn.centroids.values() for v in xy)
    assert not SilhouetteCentroids()(np.zeros((10, 10), np.uint8)).is_valid


def test_body_sub_regions():
    r = BodySubRegions()(mask_from_body_index(_body_index_map()))
    assert r.is_valid and r.regions
    for x, y, w, h in r.regions.values():
        assert 0 <= x < 640 and 0 <= y < 576 and w > 0 and h > 0
