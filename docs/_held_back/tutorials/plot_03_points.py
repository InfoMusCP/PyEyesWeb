# Parts of examples/02_physical_signals/plot_03_points.py held back with their features (early release, 2026-11-13).
# Not run by the gallery; restore them when the features come back.

# %%
# A mass-spring humanoid
# ----------------------
# A captured skeleton is noisy and incomplete: joints jitter and drop out, and a forearm may change length from one frame to
# the next. A **mass-spring model** is a small physical simulation that is driven by the movement and returns the pose of
# a body that obeys simple mechanics: its joints are masses, its bones are springs, and the bone lengths stay constant.
# :doc:`/theory/humanoid_models` gives the equations.
#
# :class:`~pyeyesweb.physical_signals.MassSpringSimulator` runs, by default (``model="humanoid"``), a ready-made body of 21
# joints (``HUMANOID_JOINTS``) and 20 bones (``HUMANOID_BONES``). The head is pinned: the output is the pose of a body that hangs from where its head starts, so the
# translation of the person is not followed. To see it work we build a synthetic skeleton: the **rest pose** of the model (the
# body standing, the upper arms stretched sideways, the pose it starts from) with the left forearm swinging about the elbow.

from pyeyesweb.physical_signals.humanoid import HUMANOID_BONES, HUMANOID_JOINTS, MassSpringSimulator

RATE = 25.0  # frames per second of the synthetic skeleton
tpose = MassSpringSimulator(sampling_rate=RATE).process({"head": (0.0, 0.0, 0.0)}).joints  # (21, 3) in metres
HAND = HUMANOID_JOINTS.index("left_hand")
print(len(HUMANOID_JOINTS), "joints:", HUMANOID_JOINTS[:5], "...")
print(len(HUMANOID_BONES), "bones:", HUMANOID_BONES[:3], "...")


def swinging_forearm(frames=150, amplitude=0.6, noise=0.0, seed=0):
    """The rest pose with the left forearm swinging by +/- amplitude radians at 0.33 Hz about the elbow (metres)."""
    elbow = tpose[HUMANOID_JOINTS.index("left_elbow")]
    moving = [HUMANOID_JOINTS.index("left_wrist"), HAND]
    out = np.repeat(tpose[None], frames, axis=0)
    for frame in range(frames):
        angle = amplitude * np.sin(2 * np.pi * 0.33 * frame / RATE)
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
        out[frame, moving] = elbow + (tpose[moving] - elbow) @ rotation.T
    return out + noise * np.random.default_rng(seed).standard_normal(out.shape)


swing = swinging_forearm()
swing_time = np.arange(len(swing)) / RATE
simulator = MassSpringSimulator(sampling_rate=RATE)
print(simulator.inputs)
print(simulator.outputs)
simulated = simulator.run(swing)["joints"]
print("the body starts in the rest pose:", np.allclose(simulated[0], tpose), "| output shape", simulated.shape)

# %%
# The simulated hand follows the captured one, a little later, and the whole body stays articulated: the right plot
# draws the input and the simulated skeleton at one frame.

frame_shown = 40
fig_swing, axes = plt.subplots(1, 2, figsize=(10, 3.4))
axes[0].plot(swing_time, swing[:, HAND, 1], label="input left hand")
axes[0].plot(swing_time, simulated[:, HAND, 1], "--", label="simulated")
axes[0].set_xlabel("time (s)")
axes[0].set_ylabel("y of the left hand (m)")
axes[0].legend()
for pose, color, label in ((swing[frame_shown], "C0", "input"), (simulated[frame_shown], "C1", "simulated")):
    for bone in HUMANOID_BONES:
        a, b = (HUMANOID_JOINTS.index(name) for name in bone.split("-"))
        axes[1].plot(pose[[a, b], 0], pose[[a, b], 1], color=color, lw=1.5, label=label if bone == HUMANOID_BONES[0] else None)
axes[1].set_aspect("equal")
axes[1].set_xlabel("x (m)")
axes[1].set_ylabel("y (m)")
axes[1].set_xlim(-0.7, 0.7)
axes[1].set_ylim(-0.45, 0.35)
axes[1].set_title(f"upper body, front view at {swing_time[frame_shown]:.1f} s", fontsize=9)
axes[1].legend()
fig_swing.tight_layout()

# %%
# **Takeaway.** The simulator returns a smooth, articulated pose that follows the input with a lag.

# %%
# The damping and what the model is not
# -------------------------------------
# The **damping** is the friction of the springs: a spring with a high damping reacts slowly and does not overshoot, a spring
# with a low damping reacts fast and rings. The default is 10. EyesWeb's own default of 0.3 makes chains of four or five bones
# diverge. A low damping follows clean data closely but amplifies noise (the rotation springs of a chain of bones start to
# flutter, and the error can grow to many times the size of the body), and a high damping is stable and lags. The model is a pose generator, not a noise filter: with noisy input its
# output is smooth but not closer to the truth than the input is. The figure shows the error of the left hand against the
# clean movement, for clean and for noisy input.

noisy = swinging_forearm(noise=0.010, seed=3)  # 10 mm of noise on every joint, in metres
settings = (3.0, 10.0, 30.0)
errors = {}
for damping in settings:
    for label, data in (("clean", swing), ("noisy", noisy)):
        run = MassSpringSimulator(sampling_rate=RATE, damping=damping).run(data)["joints"]
        errors[damping, label] = np.linalg.norm(run[:, HAND] - swing[:, HAND], axis=1) * 1000  # millimetres
input_noise = np.linalg.norm(noisy[:, HAND] - swing[:, HAND], axis=1).mean() * 1000
print(f"input noise on the hand: {input_noise:.1f} mm")
for damping in settings:
    print(f"damping {damping:>4g}: mean error {errors[damping, 'clean'].mean():6.1f} mm (clean input), {errors[damping, 'noisy'].mean():6.1f} mm (noisy input)")

fig_damping, axes = plt.subplots(1, 2, figsize=(10, 3), sharey=True)
for ax, label in zip(axes, ("clean", "noisy")):
    for damping in settings:
        ax.semilogy(swing_time[1:], errors[damping, label][1:], label=f"damping {damping:g}")
    ax.set_title(f"error of the hand, {label} input", fontsize=9)
    ax.set_xlabel("time (s)")
axes[0].set_ylabel("distance to the true hand (mm, log)")
axes[0].legend(fontsize=8)
fig_damping.tight_layout()

# sphinx_gallery_thumbnail_number = 3

# %%
# **Takeaway.** A higher damping is more stable and lags more; the model does not remove noise, so it is not a filter.

# %%
# Bone directions: an output and an optional input
# ------------------------------------------------
# The simulator follows the 20 **bone directions** it reads from the joints, and returns them as its second output,
# ``directions``: the unit vector of each bone, expressed in the frame of the previous bone of the chain, so that it does not
# depend on where the body is. The output has shape ``(20, 3)`` and is labelled ``"<joint1>-<joint2>"`` as in
# ``HUMANOID_BONES``. A joint that is missing in a frame keeps the position it had before.
#
# The same directions are an optional second input, which replaces the directions the simulator would read from the joints.
# Passing the output back gives the same pose.

directions = MassSpringSimulator(sampling_rate=RATE).run(swing)["directions"]  # (frames, 20, 3)
piped = MassSpringSimulator(sampling_rate=RATE).run(swing, directions)["joints"]
print("simulator driven through its directions equals the plain path (first 30 frames):", np.allclose(piped[:30], simulated[:30], atol=1e-6))

forearm = HUMANOID_BONES.index("left_elbow-left_wrist")
fig_directions, ax = plt.subplots(figsize=(8, 2.6))
ax.plot(swing_time, directions[:, forearm])
ax.legend(["x", "y", "z"], ncol=3)
ax.set_xlabel("time (s)")
ax.set_ylabel("direction (unit vector)")
ax.set_title("left_elbow-left_wrist: the forearm direction in the frame of the upper arm", fontsize=9)
fig_directions.tight_layout()

# %%
# **Takeaway.** Bone directions are a pose description without position; the simulator returns them and can take them as
# its second input.

# %%
# A real recording through ``joint_map``
# --------------------------------------
# The humanoid has its own joint names, those of the first Kinect SDK. The ``joint_map`` argument maps each of them to the
# label of your data; the names you leave out keep their own. The standard skeleton of the example data has no shoulder
# centre, so we add one, the middle of the two shoulders, as one more label. ``units="mm"`` declares the unit of the frames
# (the humanoid is defined in millimetres and converts at its boundary), ``sampling_rate=100`` is the frame rate and
# ``start_from_input=True`` puts the body on the first frame, with the bone lengths of the person instead of those of the
# rest pose, before it starts to follow. The constructor raises when the labels lack a joint that the model needs.

arm_movement = load_qualisys_trial(7, start=3, stop=5.5)
centre = (arm_movement.joint("Left_Shoulder") + arm_movement.joint("Right_Shoulder")) / 2
captured = np.concatenate([arm_movement.positions, centre[:, None, :]], axis=1)
labels = list(arm_movement.labels) + ["Shoulder_Center"]
joint_map = {"head": "Head", "neck": "Neck", "spine": "Spine", "spine_base": "Pelvis", "spine_shoulder": "Shoulder_Center"}
for side in ("left", "right"):
    for part in ("shoulder", "elbow", "wrist", "hand", "hip", "knee", "ankle", "foot"):
        joint_map[f"{side}_{part}"] = f"{side.capitalize()}_{part.capitalize()}"

follower = MassSpringSimulator(labels=labels, joint_map=joint_map, units="mm", sampling_rate=arm_movement.sampling_rate, start_from_input=True)
body = follower.run(captured)["joints"]  # (frames, 21, 3) in millimetres
measured = np.stack([captured[:, labels.index(joint_map[name])] for name in HUMANOID_JOINTS], axis=1)
print("simulated joints:", body.shape, "| first frame equals the input:", np.allclose(body[0], measured[0]))

try:
    MassSpringSimulator(labels=labels[:-1], joint_map=joint_map)
except ValueError as error:
    print("ValueError:", str(error)[:150])

# %%
# The head is pinned, so the comparison is made relative to the head. We use 2.5 seconds of trial 7 (from 3 s to 5.5 s) in
# which the person moves the arms at a moderate pace, and compare the simulated joints with the measured ones: the median
# over joints and frames is a fairer summary than the mean, because a few frames weigh more than the rest. The model is a
# pose generator and it can overshoot on fast movements (see the note in :doc:`/theory/humanoid_models`), so it is worth looking
# at the output before using it.

head = HUMANOID_JOINTS.index("head")
measured_hand = (measured - measured[:, head][:, None])[:, HAND]
simulated_hand = (body - body[:, head][:, None])[:, HAND]
error = np.linalg.norm((body - body[:, head][:, None]) - (measured - measured[:, head][:, None]), axis=2)
print(f"distance between simulated and measured joints, relative to the head: median {np.median(error):.0f} mm, mean {error.mean():.0f} mm")

fig_real, axes = plt.subplots(1, 2, figsize=(10, 3), sharey=True)
for ax, signal, title in zip(axes, (measured_hand, simulated_hand), ("measured", "simulated")):
    ax.plot(arm_movement.timestamps, signal, lw=0.9)
    ax.set_title(f"{title} left hand, relative to the head", fontsize=9)
    ax.set_xlabel("time (s)")
axes[0].set_ylabel("position (mm)")
axes[0].legend(["x", "y", "z"], ncol=3, fontsize=8)
fig_real.tight_layout()

# %%
# **Takeaway.** ``joint_map`` connects the names of the model to the labels of your recording; declare ``units`` and
# ``sampling_rate`` of the data, and check the simulated pose against the measured one.

# %%
# A model of your own: the generic blocks
# ---------------------------------------
# The humanoid is one :class:`~pyeyesweb.physical_signals.MassSpringModel`. You can describe another body, a tail, a rope
# or a robot arm, by listing its masses and springs, in code or in an EyesWeb XML file
# (``MassSpringModel.from_xml_file``). A **spring** joins two masses: the **hinge** and the **tip**; it plays the role of a
# bone. Here is a chain of three bones of length 1 hanging from a heavy root (the unit is the one of your data: a model has
# no unit of its own, so ``units`` only names it).

from pyeyesweb.physical_signals.humanoid import MassSpringModel

model = MassSpringModel()
model.add_mass("root", 1e10, (0.0, 0.0, 0.0))
for index, name in enumerate("abc", start=1):
    model.add_mass(name, 1.0, (float(index), 0.0, 0.0))
previous = "root"
for name in "abc":
    model.add_spring(f"bone_{name}", previous, name, 1.0, 100.0, (1.0, 0.0, 0.0), 100.0)
    previous = name
print(model)
print("masses:", model.mass_names, "| springs:", model.spring_names)

# %%
# We move the chain with three joint angles that oscillate at different frequencies and record the four masses.
# ``MassSpringSimulator(model=model)`` takes the positions of the masses, reads the vector of each bone (from the hinge to
# the tip, not normalised), follows those directions and gives the simulated masses, ``joints``, and the bone vectors,
# ``directions``.


CHAIN_RATE = 50.0
steps = np.arange(750)
angles = np.stack([0.3 * np.sin(2 * np.pi * 0.3 * steps / CHAIN_RATE),
                   0.3 * np.sin(2 * np.pi * 0.39 * steps / CHAIN_RATE + 1.0),
                   0.3 * np.sin(2 * np.pi * 0.51 * steps / CHAIN_RATE + 2.0)], axis=1).cumsum(axis=1)
tips = np.cumsum(np.stack([np.cos(angles), np.sin(angles)], axis=2), axis=1)  # tips of the three bones, in the x-y plane
chain = np.concatenate([np.zeros((750, 1, 2)), tips], axis=1)
chain = np.concatenate([chain, np.zeros((750, 4, 1))], axis=2)  # (frames, 4 masses, 3), rows in the order of chain_labels
chain_labels = ["root", "a", "b", "c"]

chain_simulator = MassSpringSimulator(model=model, labels=chain_labels, sampling_rate=CHAIN_RATE, damping=3.0)
mass_order = list(chain_simulator.outputs["joints"].axis_names[0])
chain_run = chain_simulator.run(chain)
followed, bones = chain_run["joints"], chain_run["directions"]
print("bone vectors:", bones.shape, "for the springs", chain_simulator.outputs["directions"].axis_names[0])
truth = chain[:, [chain_labels.index(name) for name in mass_order]]
tip = mass_order.index("c")
print("mean error of the simulated tip:", round(float(np.linalg.norm(followed[:, tip] - truth[:, tip], axis=1).mean()), 3))

fig_chain, ax = plt.subplots(figsize=(8, 3))
shown = slice(0, 300)  # the first 6 s
ax.plot(steps[shown] / CHAIN_RATE, truth[shown, tip, 1], label="tip y (measured)")
ax.plot(steps[shown] / CHAIN_RATE, followed[shown, tip, 1], "--", label="simulated")
ax.set_xlabel("time (s)")
ax.set_ylabel("y of the chain tip (model units)")
ax.legend(fontsize=8)
fig_chain.tight_layout()

# %%
# **Takeaway.** The generic blocks give any model the two steps of the humanoid: bone vectors and a simulated body.

# 2. Change the damping of the forearm simulation to 30 and compare the error of the hand with clean input with the one at
#    ``damping=10``. What does the change say about the lag?

# %%
# Exercise 2. A larger damping lags more, so the hand is further from the clean movement.

heavy = MassSpringSimulator(sampling_rate=RATE, damping=30.0).run(swing)["joints"]
print(f"damping 30: mean error {np.linalg.norm(heavy[:, HAND] - swing[:, HAND], axis=1).mean() * 1000:.1f} mm,",
      f"damping 10: {errors[10.0, 'clean'].mean():.1f} mm")
