# Parts of examples/05_analysis_primitives/plot_09b_synchronization_events.py held back with their features (early release, 2026-11-13).
# Not run by the gallery; restore them when the features come back.

# %%
# Spike trains: no tolerance to choose
# ------------------------------------
# :class:`~pyeyesweb.analysis_primitives.SpikeSynchronization` (SPIKE-synchronization) decides what is simultaneous from the local
# spacing of the events, so it has no ``max_lag``. ``degree`` is the share of events that have a partner in another train and
# ``distance`` is ``1 - degree``. It takes the trains in two forms. In ``mode="binary"`` (the default) each sample has one
# channel per train, as above; here windows of 2 s.

from pyeyesweb.analysis_primitives.synchronization.events import SpikeSynchronization

fig, ax = plt.subplots(figsize=(8, 3))
for name in trials:
    pair = np.column_stack([trains[name]["Left"][:, 0], trains[name]["Right"][:, 0]])
    recorder = SpikeSynchronization(window=200, hop=200).run(pair, timestamps=stamps)
    index = np.flatnonzero(recorder.ok)
    ax.plot(recorder.timestamps[index], recorder.degree[index], "o-", label=name)
    shade_status(ax, stamps, recorder.status, codes=(1,))
ax.set_xlabel("end of the 2 s window (s)")
ax.set_ylabel("degree of synchronization")
ax.set_ylim(0, 1.05)
ax.legend(fontsize=7)
fig.tight_layout()

# %%
# In ``mode="timings"`` you give the spike *times* themselves, as a matrix with one row per train
# ``(number_of_inputs, window)``; the times are positive and increasing, in any unit, and every train has the same number of
# spikes (``window``). Each call is independent and always ``OK``. Here the times, in seconds, of the first eight events of
# each hand.

spike_times = {}
for name in trials:
    times = [(np.flatnonzero(trains[name][side][:, 0]) + 1) / sampling_rate for side in ("Left", "Right")]
    spike_times[name] = np.array([train[:8] for train in times])
    result = SpikeSynchronization(window=8, mode="timings").process(spike_times[name])
    print(f"{name:<26} spike times (s), left hand: {spike_times[name][0].round(2)}")
    print(f"{'':<26} degree {float(result.degree):.2f}, distance {float(result.distance):.2f}")

# %%
# **Takeaway.** SPIKE-synchronization needs no tolerance, either from sampled trains (binary) or from spike times (timings).

# 2. Use ``SpikeSynchronization`` in ``"timings"`` mode with the first 8 events of the *left* hand against the first 8 of the
#    left hand shifted by 0.05 s. What degree do you expect?

# %%
# Exercise 2. A train against a shifted copy of itself: every spike has a partner.

shifted = np.array([spike_times["trial 7 (synchronised)"][0], spike_times["trial 7 (synchronised)"][0] + 0.05])
print("degree:", float(SpikeSynchronization(window=8, mode="timings").process(shifted).degree))
