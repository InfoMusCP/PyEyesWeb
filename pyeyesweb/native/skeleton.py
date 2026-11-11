"""Skeleton conventions shared by the native humanoid features.

The EyesWeb humanoid model (``eyw_core.humanoid``) uses the 21 joint names of
the Kinect SDK, in millimetres.  The project Kinect TSV files use the same
names, so they can be used directly.  Azure Kinect Body Tracking uses
different names (32 joints); :data:`AZURE_TO_HUMANOID` maps the 21 joints the
model needs.
"""

from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

#: The 21 joints of the EyesWeb humanoid, in a fixed order (chains: spine,
#: left arm, right arm, left leg, right leg).
HUMANOID_JOINTS: Tuple[str, ...] = (
    "head", "neck", "spine_shoulder", "spine", "spine_base",
    "left_shoulder", "left_elbow", "left_wrist", "left_hand",
    "right_shoulder", "right_elbow", "right_wrist", "right_hand",
    "left_hip", "left_knee", "left_ankle", "left_foot",
    "right_hip", "right_knee", "right_ankle", "right_foot",
)

#: Azure Kinect Body Tracking joint indices (``k4abt_joint_id_t``).
K4ABT_JOINTS: Dict[str, int] = {
    "pelvis": 0, "spine_navel": 1, "spine_chest": 2, "neck": 3,
    "left_clavicle": 4, "left_shoulder": 5, "left_elbow": 6, "left_wrist": 7,
    "left_hand": 8, "left_handtip": 9, "left_thumb": 10,
    "right_clavicle": 11, "right_shoulder": 12, "right_elbow": 13, "right_wrist": 14,
    "right_hand": 15, "right_handtip": 16, "right_thumb": 17,
    "left_hip": 18, "left_knee": 19, "left_ankle": 20, "left_foot": 21,
    "right_hip": 22, "right_knee": 23, "right_ankle": 24, "right_foot": 25,
    "head": 26, "nose": 27, "left_eye": 28, "left_ear": 29, "right_eye": 30, "right_ear": 31,
}

#: Humanoid joint name -> Azure Kinect joint name.
AZURE_TO_HUMANOID: Dict[str, str] = {
    "head": "head",
    "neck": "neck",
    "spine_shoulder": "spine_chest",
    "spine": "spine_navel",
    "spine_base": "pelvis",
    **{f"{s}_{j}": f"{s}_{j}"
       for s in ("left", "right")
       for j in ("shoulder", "elbow", "wrist", "hand", "hip", "knee", "ankle", "foot")},
}

#: Azure Kinect joint indices in the order of :data:`HUMANOID_JOINTS`.
AZURE_HUMANOID_INDICES: Tuple[int, ...] = tuple(
    K4ABT_JOINTS[AZURE_TO_HUMANOID[n]] for n in HUMANOID_JOINTS
)


def azure_to_humanoid_frame(azure_joints: np.ndarray) -> np.ndarray:
    """Select the 21 humanoid joints from an Azure Kinect skeleton.

    Parameters
    ----------
    azure_joints : numpy.ndarray of shape (32, 3)
        Joint positions in millimetres, rows in ``k4abt_joint_id_t`` order.

    Returns
    -------
    numpy.ndarray of shape (21, 3)
        Rows in the order of :data:`HUMANOID_JOINTS`.
    """
    azure_joints = np.asarray(azure_joints, dtype=float)
    if azure_joints.ndim != 2 or azure_joints.shape[0] < 32 or azure_joints.shape[1] < 3:
        raise ValueError(f"expected a (32, 3) Azure Kinect skeleton, got {azure_joints.shape}")
    return azure_joints[list(AZURE_HUMANOID_INDICES), :3]


def frame_to_dict(frame: np.ndarray, names: Sequence[str]) -> Dict[str, Tuple[float, float, float]]:
    """Convert a ``(N_joints, 3)`` frame to ``{name: (x, y, z)}``.

    Rows that contain NaN or infinite values (missing joints) are skipped.
    """
    frame = np.asarray(frame, dtype=float)
    if frame.ndim != 2 or frame.shape[1] != 3:
        raise ValueError(f"expected a frame of shape (N_joints, 3), got {frame.shape}")
    if frame.shape[0] != len(names):
        raise ValueError(f"frame has {frame.shape[0]} joints but {len(names)} names were given")
    ok = np.all(np.isfinite(frame), axis=1)
    return {n: (float(p[0]), float(p[1]), float(p[2])) for n, p, v in zip(names, frame, ok) if v}


def dict_to_frame(points: Mapping[str, Iterable[float]], names: Sequence[str]) -> np.ndarray:
    """Convert ``{name: (x, y, z)}`` to a ``(len(names), 3)`` array (NaN when missing)."""
    out = np.full((len(names), 3), np.nan)
    for i, n in enumerate(names):
        if n in points:
            out[i] = tuple(points[n])
    return out


def check_joint_names(names: Sequence[str]) -> List[str]:
    """Validate a joint-name list and return it as a list.

    Names unknown to the humanoid model are allowed (they are simply ignored
    by the model) but at least the spine must be present.
    """
    names = list(names)
    if len(set(names)) != len(names):
        raise ValueError("joint_names contains duplicates")
    missing = [n for n in HUMANOID_JOINTS[:5] if n not in names]
    if missing:
        raise ValueError(
            f"joint_names must contain the humanoid spine joints, missing: {missing}. "
            "Use HUMANOID_JOINTS, or map Azure Kinect joints with azure_to_humanoid_frame()."
        )
    return names
