# Parts of examples/05_analysis_primitives/plot_09a_synchronization_signals.py held back with their features (early release, 2026-11-13).
# Not run by the gallery; restore them when the features come back.

# %%
# Nonlinear interdependence: does one signal determine the other?
# ----------------------------------------------------------------
# Correlation sees only straight-line relations. :class:`~pyeyesweb.analysis_primitives.NonlinearInterdependence` asks
# whether the *state* of one signal, a short stretch of ``embedding_dimension`` samples, determines the state of the other: the
# ``neighbours`` nearest states of one signal are looked up in the other. It returns the two directions
# (``first_to_second_interdependence`` and the reverse; they may differ, and the difference is read as the direction of
# the coupling) and a ``threshold`` computed from the parameters. Identical signals give 1 and independent signals near 0.

from pyeyesweb.analysis_primitives.synchronization.events import NonlinearInterdependence

fig, ax = plt.subplots(figsize=(8, 3))
for name, signal in heights.items():
    recorder = NonlinearInterdependence(window=300, hop=100, embedding_dimension=3, neighbours=5).run(signal[:, 0], signal[:, 1], timestamps=stamps)
    ax.plot(recorder.timestamps[recorder.ok], recorder.first_to_second_interdependence[recorder.ok], "o-", ms=3, label=f"{name}, left to right")
    ax.plot(recorder.timestamps[recorder.ok], recorder.second_to_first_interdependence[recorder.ok], "s--", ms=3, label=f"{name}, right to left")
    print(f"{name:<26} mean interdependence {np.mean(recorder.first_to_second_interdependence[recorder.ok]):.2f}, threshold {recorder.threshold[recorder.ok][0]:.2f}")
ax.set_xlabel("time (s)")
ax.set_ylabel("interdependence")
ax.legend(fontsize=7, ncol=2)
fig.tight_layout()

# %%
# **Takeaway.** Interdependence is higher when the movement of one hand determines that of the other, linearly or not.

        "interdependence": NonlinearInterdependence(window=300, hop=100, embedding_dimension=3, neighbours=5).run(left, right).first_to_second_interdependence[-1],
