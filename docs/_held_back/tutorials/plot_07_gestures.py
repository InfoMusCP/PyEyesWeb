# Parts of examples/04_mid_level/plot_07_gestures.py held back with their features (early release, 2026-11-13).
# Not run by the gallery; restore them when the features come back.

# %%
# The noise flag works on the speed of the joints. A recording with a lost marker, simulated here by adding random jumps
# to every joint during the second half of a still stretch, is flagged as noise, and no gesture can start while the flag is
# set. ``noise_threshold`` is a variance of speed, in m\ :sup:`2`/s\ :sup:`2` for data in metres (set ``units="mm"`` for
# millimetres).

rng = np.random.default_rng(1)
still = np.repeat(trial.positions[:1], 400, axis=0)
jumpy = still.copy()
jumpy[200:] += rng.normal(scale=0.05, size=jumpy[200:].shape)
for label, frames in (("still", still), ("jumpy from sample 200", jumpy)):
    flags = MotionNoiseDetector(skeleton=trial.skeleton, sampling_rate=100).run(frames).is_noisy
    intensity = KineticEnergy(skeleton=trial.skeleton, sampling_rate=100).run(frames).kinetic_energy
    with_flag = GestureSegmenter(firing_threshold=1.0).run(intensity, flags)
    without_flag = GestureSegmenter(firing_threshold=1.0).run(intensity)
    print(f"{label:<22} noisy samples: {int(flags.sum()):>3} | gestures with the flag: {int(with_flag.is_gesture_start.sum())}"
          f" | without it: {int(without_flag.is_gesture_start.sum())}")

# %%
# Suddenness of a trajectory
# --------------------------
# A movement is **sudden** when its speed changes in bursts: mostly slow, now and then very fast, like a flick of the hand.
# :class:`~pyeyesweb.mid_level.Suddenness` looks at the speeds of one point over a window and fits an alpha-stable
# distribution to them (:doc:`/theory/impulsivity_suddenness`). Its outputs are ``alpha`` (2 is a Gaussian, smaller means
# heavier tails, that is more bursts), ``beta`` (the skewness: not negative when the bursts are towards large speeds),
# and ``gamma``. A window is classified as sudden when :math:`\gamma (1 - \alpha / 2) \beta \ge 0` (in practice, when ``beta``
# is not negative). It takes **one** position per call, and a window of ``window`` samples moves by ``hop`` samples. Here,
# windows of half a second every 0.1 s on the right hand:

from pyeyesweb.mid_level.suddenness import Suddenness


def is_sudden(record):
    """The classification of each window of a ``Suddenness`` record, from its outputs."""
    return record.gamma * (1 - record.alpha / 2) * record.beta >= 0


hand = trial.joint("Right_Hand")
suddenness = Suddenness(window=50, hop=10).run(hand, timestamps=time)
print(suddenness)

fig, axes = plt.subplots(4, 1, figsize=(8, 7), sharex=True)
axes[0].plot(time, speed(hand, 100), lw=0.8)
axes[0].set_ylabel("Right_Hand\nspeed (m/s)")
ok = suddenness.ok
axes[1].plot(time[ok], suddenness.alpha[ok], ".-", ms=3, lw=0.6)
axes[1].set_ylabel("alpha")
axes[2].plot(time[ok], suddenness.beta[ok], ".-", ms=3, lw=0.6, color="C1")
axes[2].axhline(0, color="0.5", lw=0.6)
axes[2].set_ylabel("beta")
axes[3].plot(time[ok], suddenness.gamma[ok], ".-", ms=3, lw=0.6, color="C2")
axes[3].set_ylabel("gamma")
axes[3].set_xlabel("time (s)")
shade_status(axes[1], time, suddenness.status)
axes[0].set_title("Suddenness of the right hand, window 0.5 s, hop 0.1 s")

# %%
# The window length is the time scale of the question: a longer window covers several movements, and the classification
# answers for all of them together. The table gives the result for four lengths. ``alpha`` is exactly 2 (the Gaussian case)
# in a window whose speeds have no heavy tail, so ``beta`` and ``gamma`` carry the detail:

print(f"{'window (s)':>11} {'windows':>8} {'% sudden':>9} {'median beta':>12} {'median gamma':>13}")
for window in (25, 50, 100, 200):
    record = Suddenness(window=window, hop=10).run(hand, timestamps=time)
    print(f"{window / 100:>11.2f} {int(record.ok.sum()):>8} {100 * is_sudden(record)[record.ok].mean():>9.0f} "
          f"{np.median(record.beta[record.ok]):>12.2f} {np.median(record.gamma[record.ok]):>13.2f}")

# %%
# **Takeaway.** ``Suddenness`` describes the shape of the speed distribution in a window of one trajectory; the window is
# the time scale of the question.

# %%
# Impulsivity of a trajectory
# ---------------------------
# An impulsive movement is sudden **and** changes direction sharply, like a strike that stops and returns.
# :class:`~pyeyesweb.mid_level.SuddennessImpulsivity` multiplies the direction change of the window by the suddenness of the
# same trajectory: the index is between 0 and 1 and is 0 when the window is not sudden or the path does not turn. The
# parameter ``direction_change_epsilon`` sets how close to a right angle a turn must be to count.

from pyeyesweb.mid_level.impulsivity import SuddennessImpulsivity

impulsivity = SuddennessImpulsivity(window=50, hop=10).run(hand, timestamps=time)
print(impulsivity)

fig, axes = plt.subplots(2, 1, figsize=(8, 4), sharex=True)
axes[0].plot(time, speed(hand, 100), lw=0.8)
axes[0].set_ylabel("Right_Hand\nspeed (m/s)")
ok = impulsivity.ok
axes[1].plot(time[ok], impulsivity.impulsivity_index[ok], ".-", ms=3, lw=0.6, color="C3")
axes[1].set_ylabel("impulsivity index")
axes[1].set_xlabel("time (s)")
shade_status(axes[1], time, impulsivity.status)
axes[0].set_title("SuddennessImpulsivity of the right hand")

# %%
# **Takeaway.** The index is high only for movement that is both sudden and sharply turning, and 0 otherwise.

# %%
# Impulsivity of the whole body
# -----------------------------
# :class:`~pyeyesweb.mid_level.ContractionImpulsivity` uses the whole body instead of one point. It needs two signals in
# [0, 1]: a *quantity of motion* and the *contraction index* of the posture, how close the limbs are to the body
# (:class:`~pyeyesweb.low_level.BoundingBoxFilledArea`, see :doc:`/theory/shape_symmetry_balance`). A gesture is a run of
# samples with the quantity of motion above ``motion_threshold``. If it is short (at most ``gesture_duration`` samples) and its
# peak reaches ``peak_threshold``, the index on the sample that closes it is the range of the contraction index divided by
# the duration in seconds: how fast the body contracted or expanded. Every other sample gives 0.
#
# We build the quantity of motion from the segmenter: its smoothed energy, divided by a fixed 20 (a fixed scale keeps trials
# comparable) and clipped to [0, 1], and 0 outside the gestures.

from pyeyesweb.low_level import BoundingBoxFilledArea
from pyeyesweb.mid_level.impulsivity import ContractionImpulsivity

quantity = np.clip(np.nan_to_num(gestures.smoothed_intensity) / 20, 0, 1) * gestures.is_gesturing
contraction = BoundingBoxFilledArea().run(trial.positions).contraction_index
body = ContractionImpulsivity(gesture_duration=100, peak_threshold=0.05, sampling_rate=100)
record = body.run(quantity, contraction, timestamps=time)
index = record.impulsivity_index
events = index > 0
print("impulsive gestures:", int(events.sum()), "| at (s):", time[events].round(2))
print("index (1/s):", index[events].round(2), "| duration (samples):", record.gesture_duration[events])

fig, axes = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
axes[0].plot(time, quantity, lw=0.9)
axes[0].axhline(body.peak_threshold, color="C3", ls="--", lw=0.8)
axes[0].set_ylabel("quantity of motion")
axes[1].plot(time, contraction, lw=0.9, color="C1")
axes[1].set_ylabel("contraction index")
axes[2].stem(time[events], index[events], linefmt="C3-", markerfmt="C3o", basefmt=" ")
axes[2].set_ylabel("impulsivity index (1/s)")
axes[2].set_xlabel("time (s)")
axes[0].set_title("ContractionImpulsivity: a value only on the sample that closes a short, energetic gesture")

# %%
# **Takeaway.** ``ContractionImpulsivity`` is an event: it is non-zero only when a short energetic gesture ends, and it says how
# fast the posture changed.

# %%
# Comparing conditions
# --------------------
# The same settings on all six trials. Trials 20 and 21 are impulsive (losing balance on one leg; reacting to a signal),
# 22 and 23 are light, 24 alternates light and heavy, 25 is slow. The table has the number of gestures, the median motion
# and pause durations, the share of sudden windows and the mean impulsivity of the right hand, and the number of impulsive
# gestures of the body.

print(f"{'trial':>5} {'gestures':>9} {'motion (s)':>11} {'pause (s)':>10} {'% sudden':>9} {'impulsivity':>12} {'body events':>12}")
for number in (20, 21, 22, 23, 24, 25):
    data = load_qualisys_trial(number, start=0, stop=24).to_units("m")
    kinetic = KineticEnergy(skeleton=data.skeleton, sampling_rate=100).run(data.positions, timestamps=data.timestamps)
    flags = MotionNoiseDetector(skeleton=data.skeleton, sampling_rate=100).run(data.positions, timestamps=data.timestamps)
    seg = GestureSegmenter(firing_threshold=1.0).run(kinetic.kinetic_energy, flags.is_noisy)
    dur = MotionDuration(sampling_rate=100).run(seg.is_gesturing.astype(float))
    point = data.joint("Right_Hand")
    sud = Suddenness(window=50, hop=10).run(point)
    imp = SuddennessImpulsivity(window=50, hop=10).run(point)
    qom = np.clip(np.nan_to_num(seg.smoothed_intensity) / 20, 0, 1) * seg.is_gesturing
    ci = BoundingBoxFilledArea().run(data.positions).contraction_index
    ev = ContractionImpulsivity(gesture_duration=100, peak_threshold=0.05, sampling_rate=100).run(qom, ci).impulsivity_index
    median = lambda x: np.nanmedian(x) if np.isfinite(x).any() else float("nan")
    print(f"{number:>5} {int(seg.is_gesture_start.sum()):>9} {median(dur.motion_duration):>11.2f} {median(dur.pause_duration):>10.2f} "
          f"{100 * is_sudden(sud)[sud.ok].mean():>9.0f} {imp.impulsivity_index[imp.ok].mean():>12.3f} {int((ev > 0).sum()):>12}")

# %%
# **Takeaway.** Every feature works on every trial; the slow trial 25 has almost no gestures at this threshold, and the
# others differ in how many gestures they contain and how long the phases between them last.

# %%
# Occupation of space: potentials
# -------------------------------
# The last two features describe not the body but **where it is**. The floor is divided into a grid of cells, and a
# *potential* is kept for each cell that grows while the performer stands on it. We use the pelvis of trial 18, where the
# performer moves and turns around the room, projected on the floor (the vertical axis of the recording is ``y``, so the
# floor is ``x`` and ``z``). :class:`~pyeyesweb.physical_signals.HitCellDetector` turns a position into the cell
# ``(row, column)`` that contains it: 14 columns of 0.05 m along ``x`` and 6 rows of 0.05 m along ``z``.

from pyeyesweb.physical_signals import HitCellDetector

walk = load_qualisys_trial(18, start=0, stop=16).to_units("m")
floor = walk.joint("Pelvis")[:, [0, 2]]
hits = HitCellDetector(cells_along_x=14, cells_along_y=6, x_min=-0.4, x_max=0.3, y_min=0.7, y_max=1.0, units="m")
cells = np.stack(list(hits.run(floor[:, None, :], timestamps=walk.timestamps).cells))  # (frames, 1, 2) of (row, column)
print("hit cells:", cells.shape, "| first:", cells[0, 0], "| rows", cells[..., 0].min(), "to", cells[..., 0].max(),
      "| columns", cells[..., 1].min(), "to", cells[..., 1].max())

# %%
# :class:`~pyeyesweb.mid_level.PositionDependingPotentials` keeps a matrix with one potential per cell. With
# ``potential_type="occupation_rates"`` the potential of a cell is the percentage of the calls in which it was hit, so the
# matrix sums to 100 and shows where the performer spent time; with ``"increment_decrement"`` a hit cell gains
# ``increment_factor`` and every other cell loses ``decrement_factor``, a leaky count in which old visits fade; the Gaussian
# type has no memory and draws a spot on the present cell.

from pyeyesweb.mid_level.space_occupation import PositionDependingPotentials

kinds = {
    "occupation rates (% of time)": dict(potential_type="occupation_rates"),
    "increment / decrement": dict(potential_type="increment_decrement", increment_factor=1.0, decrement_factor=0.001),
    "Gaussian (no memory)": dict(potential_type="gaussian", gaussian_sigma_x=1.5, gaussian_sigma_y=1.0),
}
maps = {name: np.stack(list(PositionDependingPotentials(cells_along_x=14, cells_along_y=6, **kw).run(
    cells, timestamps=walk.timestamps).potential)) for name, kw in kinds.items()}
print("potential matrices over time:", maps["occupation rates (% of time)"].shape)
print("occupation rates sum to", maps["occupation rates (% of time)"][-1].sum().round(1), "% at the end")

moments = [int(s * 100) for s in (4, 8, 12, 15.9)]
fig, axes = plt.subplots(len(maps), len(moments), figsize=(8, 4.2), squeeze=False)
for row, (name, array) in enumerate(maps.items()):
    for column, frame in enumerate(moments):
        ax = axes[row, column]
        ax.imshow(array[frame], origin="lower", cmap="viridis", extent=(-0.4, 0.3, 0.7, 1.0))
        i, j = cells[frame, 0]
        ax.plot(-0.4 + 0.05 * (j + 0.5), 0.7 + 0.05 * (i + 0.5), "r+", ms=9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        if row == 0:
            ax.set_title(f"t = {frame / 100:.0f} s", fontsize=9)
        if column == 0:
            ax.set_ylabel(name, fontsize=7, rotation=0, ha="right", va="center")
fig.suptitle("Potential of each floor cell (x to the right, z upward; red + is the current cell)", fontsize=9)

# %%
# :class:`~pyeyesweb.mid_level.RegionDependingPotentials` does the same for **regions**: groups of cells given by a ``mask``
# with the region of each cell. It keeps one value per region. ``parts`` chooses which outputs are produced; here the cell
# matrix and the value of each region. We split the room in four vertical bands, from left to right.

from pyeyesweb.mid_level.space_occupation import RegionDependingPotentials

mask = np.tile(np.minimum(np.arange(14) // 4, 3), (6, 1))
zones = RegionDependingPotentials(cells_along_x=14, cells_along_y=6, potential_type="occupation_rates_linear", mask=mask,
                                  number_of_regions=4, parts=("potential", "region_values"))
zone_record = zones.run(cells, timestamps=walk.timestamps)
values = np.stack(list(zone_record.region_values))
print("parts:", zones.parts, "| final value of each region (%):", values[-1].round(1), "| sum:", values[-1].sum().round(1))

fig, axes = plt.subplots(1, 2, figsize=(8, 2.8), gridspec_kw={"width_ratios": [1, 2.2]})
axes[0].imshow(mask, origin="lower", cmap="tab10", vmin=0, vmax=9, extent=(-0.4, 0.3, 0.7, 1.0))
axes[0].set_xlabel("x (m)")
axes[0].set_ylabel("z (m)")
axes[0].set_title("region of each cell")
axes[0].grid(False)
for region in range(4):
    axes[1].plot(walk.timestamps, values[:, region], label=f"region {region}")
axes[1].set_xlabel("time (s)")
axes[1].set_ylabel("region value (%)")
axes[1].legend(ncol=4, fontsize=8)
axes[1].set_title("Running occupation of each region")

# %%
# **Takeaway.** The potentials turn a stream of hit cells into a running map of the floor, by cell or by region.

# 2. Compute ``Suddenness`` of the right hand of trial 25 with a window of 1 s, and compare the median ``beta`` with that of
#    trial 21.
# 3. Change the grid of the potentials to 7 columns of 0.1 m (and 3 rows). Which cell is the most visited, and for what
#    percentage of the time?

# %%
# Exercise 2. A window of 1 s is 100 samples.

for number in (25, 21):
    point = load_qualisys_trial(number, start=0, stop=24).to_units("m").joint("Right_Hand")
    result = Suddenness(window=100, hop=10).run(point)
    print(f"trial {number}: median beta {np.median(result.beta[result.ok]):.2f}")

# %%
# Exercise 3. Cells of 0.1 m along both axes: the grid is 7 columns by 3 rows.

coarse_hits = HitCellDetector(cells_along_x=7, cells_along_y=3, x_min=-0.4, x_max=0.3, y_min=0.7, y_max=1.0, units="m")
coarse_cells = np.stack(list(coarse_hits.run(floor[:, None, :], timestamps=walk.timestamps).cells))
coarse = PositionDependingPotentials(cells_along_x=7, cells_along_y=3, potential_type="occupation_rates")
final = np.stack(list(coarse.run(coarse_cells, timestamps=walk.timestamps).potential))[-1]
print(final.round(1))
print("most visited cell (row, column):", tuple(int(i) for i in np.unravel_index(final.argmax(), final.shape)), "with", final.max().round(1), "%")
