"""Inputs of the humanoid tests: skeleton motions in the order of `HUMANOID_JOINTS` (millimetres) and a small chain model."""

import os

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.physical_signals import HUMANOID_JOINTS

REFERENCE = np.load(os.path.join(os.path.dirname(__file__), "..", "data", "humanoid_reference.npz"))

# A chain of three bones hanging from a heavy root: the model of the generic blocks (the one of the frozen reference).
CHAIN_XML = """<Model><Masses>
<Mass name="root" mass="1e10" x="0" y="0" z="0"/><Mass name="a" mass="1.5" x="100" y="0" z="0"/>
<Mass name="b" mass="1" x="200" y="0" z="0"/><Mass name="c" mass="0.8" x="300" y="0" z="0"/></Masses><Springs>
<Spring name="s1" mass1="root" mass2="a" restLength="100" lengthStiffness="2000" lengthDamping="1" restDirX="1" restDirY="0" restDirZ="0" dirStiffness="2000" dirDamping="1"/>
<Spring name="s2" mass1="a" mass2="b" restLength="100" lengthStiffness="2000" lengthDamping="1" restDirX="1" restDirY="0" restDirZ="0" dirStiffness="2000" dirDamping="1"/>
<Spring name="s3" mass1="b" mass2="c" restLength="100" lengthStiffness="2000" lengthDamping="1" restDirX="1" restDirY="0" restDirZ="0" dirStiffness="2000" dirDamping="1"/>
</Springs></Model>"""

MASSES = tuple(str(label) for label in REFERENCE["mass_labels"])
SPRINGS = tuple(str(label) for label in REFERENCE["spring_labels"])


def tpose() -> np.ndarray:
    """The T-pose of the humanoid, `(21, 3)` in the order of `HUMANOID_JOINTS`."""
    positions = core.humanoid.HumanoidSimulator().positions()
    return np.array([positions[name] for name in HUMANOID_JOINTS])


def forearm(frames: int = 80, noise: float = 0.0, seed: int = 0, amplitude: float = 0.6, rate: float = 25.0) -> np.ndarray:
    """The T-pose with the left forearm swinging +/- `amplitude` rad at 0.33 Hz about the elbow; `noise` mm on every joint."""
    pose = tpose()
    elbow = pose[HUMANOID_JOINTS.index("left_elbow")]
    moving = [HUMANOID_JOINTS.index("left_wrist"), HUMANOID_JOINTS.index("left_hand")]
    rng = np.random.default_rng(seed)
    out = np.empty((frames, 21, 3))
    for index in range(frames):
        angle = amplitude * np.sin(2 * np.pi * 0.33 * index / rate)
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
        out[index] = pose
        out[index, moving] = elbow + (pose[moving] - elbow) @ rotation.T
    return out + noise * rng.standard_normal(out.shape)
