# Parts of examples/03_low_level/plot_05_motion.py held back with their features (early release, 2026-11-13).
# Not run by the gallery; restore them when the features come back.

# %%
# Is the tracking noisy?
# ----------------------
# A motion capture system that loses a marker or confuses two labels makes the speed of a joint jump about at random, and the
# energy of that signal is not movement. :class:`~pyeyesweb.low_level.MotionNoiseDetector` keeps the last 10 speeds of the
# watched joints, computes their variance and averages it over 5 frames; ``is_noisy`` is ``True`` while that mean is above
# ``noise_threshold`` (a variance of speed in m\ :sup:`2`/s\ :sup:`2` when ``units="m"``).
#
# Three things to know. ``True`` means **noise**: this flag is meant to go straight to the ``noise`` input of
# :class:`~pyeyesweb.mid_level.GestureSegmenter`, which then does not start a gesture. The flag is ``False`` for the first 14
# frames while the speeds fill up. And with several joints, **only the alphabetically last joint name decides the flag**
# (a jumpy joint with another name is not seen, whatever the order of the labels; this is the behaviour of the underlying
# EyesWeb block, see the docstring). Here the names are Head, Left_Hand and Right_Hand, so Right_Hand decides. We add a
# random jump of a few centimetres to trial 21, once on Right_Hand and once on Head.

from pyeyesweb.low_level.motion_noise import MotionNoiseDetector

reactive = load_qualisys_trial(21, start=0, stop=12).to_units("m")
watched = ["Head", "Left_Hand", "Right_Hand"]
frames = np.stack([reactive.joint(name) for name in watched], axis=1)  # (frames, 3 joints, 3)
detector = MotionNoiseDetector(labels=watched, sampling_rate=RATE)
rng = np.random.default_rng(0)


def with_jumps(joint):
    """The frames with a random displacement (standard deviation 5 cm) added to one joint."""
    noisy = frames.copy()
    noisy[:, watched.index(joint)] += rng.normal(scale=0.05, size=(len(frames), 3))
    return noisy


cases = {"recording as it is": frames, "jumps on Right_Hand (alphabetically last)": with_jumps("Right_Hand"), "jumps on Head (alphabetically first)": with_jumps("Head")}
fig, axes = plt.subplots(len(cases), 1, figsize=(8, 3.6), sharex=True, sharey=True)
for ax, (name, data) in zip(axes, cases.items()):
    flag = detector.run(data, timestamps=reactive.timestamps).is_noisy
    ax.fill_between(reactive.timestamps, flag.astype(float), step="mid", color="#c0504d", alpha=0.6)
    ax.set_yticks([0, 1], ["no", "noise"], fontsize=7)
    ax.set_title(name, fontsize=8, loc="left")
    print(f"{name:<28} fraction of frames flagged: {np.mean(flag):.2f}")
axes[-1].set_xlabel("time (s)")
fig.tight_layout()

# %%
# The recording as it is is flagged only for an instant, jumps on Right_Hand raise the flag for the whole recording, and the
# same jumps on Head are not seen.
#
# **Takeaway.** ``is_noisy`` is ``True`` for random, jumpy speeds, goes to the segmenter as it is, and is decided by the
# alphabetically last joint name.

# 3. Reduce the standard deviation of the jumps added to ``Right_Hand`` for ``MotionNoiseDetector`` (5 cm above) until the flag
#    stops being raised. What is the smallest value, in a list of 5, 2, 1 and 0.5 cm, that is still flagged?

# %%
# Exercise 3. The flag needs a variance of the speed above the threshold, so it needs larger jumps than the tracker noise.

for centimetres in (5, 2, 1, 0.5):
    noisy = frames.copy()
    noisy[:, -1] += np.random.default_rng(0).normal(scale=centimetres / 100, size=(len(frames), 3))
    flagged = detector.run(noisy, timestamps=reactive.timestamps).is_noisy
    print(f"jumps of {centimetres} cm: {np.mean(flagged):.2f} of the frames flagged")
