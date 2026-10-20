"""Humanoid model features (EyesWeb catalog *HumanoidModel*, native C++).

* :class:`BoneOrientations` - direction of every bone in the frame of its
  parent bone (EyesWeb *HumanoidOrientationsExtractor*): a description of the
  posture that does not depend on where the person stands or faces.
* :class:`HumanoidFilter` - mass-spring humanoid that follows the input
  skeleton (EyesWeb *HumanoidSimulator*).  **Experimental**, see its notes.

Both are :class:`~pyeyesweb.data_models.base.StaticFeature`: they read one
``(N_joints, 3)`` frame, positions in millimetres, joints named as in
:data:`~pyeyesweb.native.skeleton.HUMANOID_JOINTS` (Kinect SDK names; use
:func:`~pyeyesweb.native.skeleton.azure_to_humanoid_frame` for Azure Kinect).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

import numpy as np

from pyeyesweb.data_models.base import StaticFeature
from pyeyesweb.data_models.results import FeatureResult
from pyeyesweb.utils.validators import validate_numeric

from ._backend import require
from .skeleton import HUMANOID_JOINTS, check_joint_names, dict_to_frame, frame_to_dict

Vec3 = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# Bone orientations
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BoneOrientationsResult(FeatureResult):
    """Output contract of :class:`BoneOrientations`.

    Attributes
    ----------
    directions : dict
        ``{"<joint1>-<joint2>": (x, y, z)}``: unit direction of each bone in
        the frame of its parent bone (20 bones).
    """
    directions: Dict[str, Vec3] = field(default_factory=dict)

    def angle_between(self, bone_a: str, bone_b: str) -> float:
        """Angle in degrees between two bone directions of this result."""
        a, b = np.asarray(self.directions[bone_a]), np.asarray(self.directions[bone_b])
        c = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


class BoneOrientations(StaticFeature):
    """Relative bone orientations of a skeleton (EyesWeb HumanoidOrientationsExtractor).

    For every bone the unit direction is expressed in the frame of the parent
    bone, so the values only change when the posture changes, not when the
    person moves or turns as a whole.  Missing joints (NaN rows) keep their
    last known position, so the feature keeps an internal state.

    Parameters
    ----------
    joint_names : sequence of str
        Name of each row of the input frame (default
        :data:`~pyeyesweb.native.skeleton.HUMANOID_JOINTS`).
    ref_dir : (float, float, float)
        Reference direction of the model (EyesWeb default ``(1, 0, 0)``).
    """

    def __init__(self, joint_names: Sequence[str] = HUMANOID_JOINTS, ref_dir: Vec3 = (1.0, 0.0, 0.0)):
        super().__init__()
        self.joint_names = check_joint_names(joint_names)
        self._impl = require().humanoid.HumanoidOrientationsExtractor(list(map(float, ref_dir)))

    def compute(self, data: np.ndarray) -> BoneOrientationsResult:
        joints = frame_to_dict(data, self.joint_names)
        if not joints:
            return BoneOrientationsResult(is_valid=False)
        return BoneOrientationsResult(directions=dict(self._impl.compute(joints)))


# ---------------------------------------------------------------------------
# Humanoid physical filter
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class HumanoidFilterResult(FeatureResult):
    """Output contract of :class:`HumanoidFilter`.

    Attributes
    ----------
    positions : numpy.ndarray of shape (N_joints, 3)
        Simulated joint positions (mm), rows in ``joint_names`` order (NaN for
        names the model does not know).
    tracking_error : float
        Mean distance (mm) between simulated and input joints in this frame.
        Watch it: values that keep growing mean the model is not following
        the input (see the notes of :class:`HumanoidFilter`).
    """
    positions: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    tracking_error: float = float("nan")


class HumanoidFilter(StaticFeature):
    """Physically-based humanoid that follows the input skeleton (EyesWeb HumanoidSimulator).

    21 point masses connected by springs (bone length and bone direction)
    are integrated at ``1 / target_integration_step_ms`` kHz; at every frame
    the rest direction of each bone is set to the observed one, so the model
    moves towards the input posture with inertia.  Bone lengths are taken
    from the first frame.

    The feature is stateful: feed frames in order, at ``rate_hz``, and call
    :meth:`reset` when the subject changes.

    Parameters
    ----------
    joint_names : sequence of str
        Name of each row of the input frame.
    rate_hz : float
        Frame rate of the input (30 for Azure Kinect).
    damping : float
        Global damping (eyw_core default 10; 0.3 reproduces EyesWeb and
        diverges).

    Notes
    -----
    **Experimental.**  The original EyesWeb model has a known instability
    along long chains (see the eyw_core README, "Stability note"): on full
    body Kinect recordings of this project the simulated joints drift tens
    of centimetres away from the input, increasingly from the head (the
    pinned root) to the feet.  Use it to study the EyesWeb model, not as a
    general-purpose skeleton filter, and check ``tracking_error``.
    """

    def __init__(self, joint_names: Sequence[str] = HUMANOID_JOINTS, rate_hz: float = 30.0,
                 damping: float = 10.0, target_integration_step_ms: float = 1.0):
        super().__init__()
        self.joint_names = check_joint_names(joint_names)
        eyw = require()
        settings = eyw.humanoid.HumanoidSimulatorSettings()
        settings.nominal_data_frequency = validate_numeric(rate_hz, "rate_hz", min_val=0.1)
        settings.damping = validate_numeric(damping, "damping", min_val=0.0)
        settings.target_integration_step_ms = validate_numeric(target_integration_step_ms,
                                                               "target_integration_step_ms", min_val=0.01)
        self._settings = settings
        self._eyw = eyw
        self._sim: Optional[object] = None
        self.reset()

    def reset(self) -> None:
        """Forget the state: the next frame re-initialises the model on the input."""
        self._sim = self._eyw.humanoid.HumanoidSimulator(self._settings)
        self._sim.reset_to_input()

    def compute(self, data: np.ndarray) -> HumanoidFilterResult:
        joints = frame_to_dict(data, self.joint_names)
        if not joints:
            return HumanoidFilterResult(is_valid=False)
        out = dict_to_frame(self._sim.step(joints), self.joint_names)
        if not np.all(np.isfinite(out[np.all(np.isfinite(np.asarray(data, float)), axis=1)])):
            # the simulation diverged: restart from the next frame
            self.reset()
            return HumanoidFilterResult(is_valid=False)
        err = np.linalg.norm(out - np.asarray(data, float), axis=1)
        return HumanoidFilterResult(positions=out, tracking_error=float(np.nanmean(err)))
