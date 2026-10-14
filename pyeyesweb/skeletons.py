"""Skeletons of the capture devices of the lab.

The features that must know the joints (`KineticEnergy`, `MotionNoiseDetector`, `Symmetry` with
the RATIO method) refuse to be built without them (they would silently read nothing). Give them `skeleton=` (a
`Skeleton` or its name: `"kinect_v2"`, `"qualisys_sport"`, `"mediapipe"`, `"openpose"`) to describe the joints of
your device, or explicit `weights=` / `couples=`:

=====================  ==========================================================================================
feature                fields of the skeleton it reads
=====================  ==========================================================================================
`KineticEnergy`        `joints` (labels of array input), `weights_or_uniform()` (weight of each joint)
`MotionNoiseDetector`  `joints`
`Symmetry` (RATIO)     `joints`, `pairs` (the couples), `reference`
`PointsDensity`        `joints` (names of the points; they do not enter the maths)
=====================  ==========================================================================================

A parameter given explicitly always wins over the skeleton. The fields still unknown are listed by `Skeleton.missing()` and, for all the presets, by
`SKELETON_TODO`; the entries to fill are marked `TODO(fill)` below.
"""

from typing import Any, Dict, Tuple

from pyeyesweb.data_models.skeleton import Skeleton

__all__ = ["Skeleton", "KINECT_V2", "QUALISYS_SPORT", "MEDIAPIPE", "OPENPOSE", "SKELETONS", "SKELETON_TODO",
           "get_skeleton", "with_skeleton"]


# Kinect v2 (Kinect SDK 2.0 JointType names). Weights: the EyesWeb Kinect SDK table (KineticEnergyIndex.h) through
# the correspondence v1 -> v2: head -> Head, shoulder_center -> SpineShoulder, spine -> SpineMid,
# hip_center -> SpineBase, the others by name. The joints without a v1 counterpart weigh 0, as an unlisted joint
# does in EyesWeb.
KINECT_V2 = Skeleton(
    name="kinect_v2",
    joints=("SpineBase", "SpineMid", "Neck", "Head", "ShoulderLeft", "ElbowLeft", "WristLeft", "HandLeft",
            "ShoulderRight", "ElbowRight", "WristRight", "HandRight", "HipLeft", "KneeLeft", "AnkleLeft", "FootLeft",
            "HipRight", "KneeRight", "AnkleRight", "FootRight", "SpineShoulder", "HandTipLeft", "ThumbLeft",
            "HandTipRight", "ThumbRight"),
    pairs=(("ShoulderLeft", "ShoulderRight"), ("ElbowLeft", "ElbowRight"), ("WristLeft", "WristRight"),
           ("HandLeft", "HandRight"), ("HipLeft", "HipRight"), ("KneeLeft", "KneeRight"),
           ("AnkleLeft", "AnkleRight"), ("FootLeft", "FootRight"), ("HandTipLeft", "HandTipRight"),
           ("ThumbLeft", "ThumbRight")),
    reference="SpineShoulder",  # shoulder_center, the reference of the Kinect SDK preset
    weights={"Head": 0.081, "SpineShoulder": 0.081, "SpineMid": 0.216, "SpineBase": 0.139,
             "ShoulderLeft": 0.0158, "ShoulderRight": 0.0158, "ElbowLeft": 0.028, "ElbowRight": 0.028,
             "WristLeft": 0.016, "WristRight": 0.016, "HandLeft": 0.006, "HandRight": 0.006,
             "HipLeft": 0.1, "HipRight": 0.1, "KneeLeft": 0.1, "KneeRight": 0.1,
             "AnkleLeft": 0.0465, "AnkleRight": 0.0465, "FootLeft": 0.0145, "FootRight": 0.0145,
             "Neck": 0.0, "HandTipLeft": 0.0, "HandTipRight": 0.0, "ThumbLeft": 0.0, "ThumbRight": 0.0},
)

# Qualisys "sport" marker set: the names of the MARKER_NAMES of the TSV files, spelling included.
QUALISYS_SPORT = Skeleton(
    name="qualisys_sport",
    joints=("HeadFront", "HeadL", "HeadR", "Chest", "LShoulderTop", "RShoulderTop", "SpineThoracic2",
            "SpineThoracic12", "WaistBack", "WaistLFront", "WaistRFront", "WaistL", "WaistR", "LArm", "RArm",
            "LElbowOut", "LElbowIn", "RelbowOut", "RElbowIn", "LWristIn", "LWristOut", "LHand2", "RWristIn",
            "RWristOut", "RHand2", "LThighFrontLow", "RThighFrontLow", "LKneeOut", "LKneeIn", "RKneeIn", "RKneeOut",
            "LShinFrontHigh", "RShinFrontHigh", "LHeelBack", "RHeelBack", "LAnkleOut", "RAnkleOut", "LForefoot5",
            "RForefoot5", "LForefoot2", "RForefoot2"),
    pairs=(("HeadL", "HeadR"), ("LShoulderTop", "RShoulderTop"), ("WaistLFront", "WaistRFront"),
           ("WaistL", "WaistR"), ("LArm", "RArm"), ("LElbowOut", "RelbowOut"), ("LElbowIn", "RElbowIn"),
           ("LWristIn", "RWristIn"), ("LWristOut", "RWristOut"), ("LHand2", "RHand2"),
           ("LThighFrontLow", "RThighFrontLow"), ("LKneeOut", "RKneeOut"), ("LKneeIn", "RKneeIn"),
           ("LShinFrontHigh", "RShinFrontHigh"), ("LHeelBack", "RHeelBack"), ("LAnkleOut", "RAnkleOut"),
           ("LForefoot5", "RForefoot5"), ("LForefoot2", "RForefoot2")),
    reference=None,  # TODO(fill): the marker used as origin (pelvis / spine base / neck)
    weights=None,  # TODO(fill): kinetic-energy weight of each marker
)

# MediaPipe Pose, 33 landmarks in the order of the model. There is no pelvis or neck landmark.
MEDIAPIPE = Skeleton(
    name="mediapipe",
    joints=("nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye", "right_eye_outer",
            "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder", "right_shoulder", "left_elbow",
            "right_elbow", "left_wrist", "right_wrist", "left_pinky", "right_pinky", "left_index", "right_index",
            "left_thumb", "right_thumb", "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle",
            "right_ankle", "left_heel", "right_heel", "left_foot_index", "right_foot_index"),
    pairs=(("left_eye_inner", "right_eye_inner"), ("left_eye", "right_eye"), ("left_eye_outer", "right_eye_outer"),
           ("left_ear", "right_ear"), ("mouth_left", "mouth_right"), ("left_shoulder", "right_shoulder"),
           ("left_elbow", "right_elbow"), ("left_wrist", "right_wrist"), ("left_pinky", "right_pinky"),
           ("left_index", "right_index"), ("left_thumb", "right_thumb"), ("left_hip", "right_hip"),
           ("left_knee", "right_knee"), ("left_ankle", "right_ankle"), ("left_heel", "right_heel"),
           ("left_foot_index", "right_foot_index")),
    reference=None,  # TODO(fill): no joint plays the pelvis / neck; choose one, or a derived point
    weights=None,  # TODO(fill)
)

# OpenPose BODY_25.
OPENPOSE = Skeleton(
    name="openpose",
    joints=("Nose", "Neck", "RShoulder", "RElbow", "RWrist", "LShoulder", "LElbow", "LWrist", "MidHip", "RHip",
            "RKnee", "RAnkle", "LHip", "LKnee", "LAnkle", "REye", "LEye", "REar", "LEar", "LBigToe", "LSmallToe",
            "LHeel", "RBigToe", "RSmallToe", "RHeel"),
    pairs=(("LEye", "REye"), ("LEar", "REar"), ("LShoulder", "RShoulder"), ("LElbow", "RElbow"),
           ("LWrist", "RWrist"), ("LHip", "RHip"), ("LKnee", "RKnee"), ("LAnkle", "RAnkle"),
           ("LBigToe", "RBigToe"), ("LSmallToe", "RSmallToe"), ("LHeel", "RHeel")),
    reference="Neck",  # the shoulder centre, as the Kinect SDK reference; MidHip is the pelvis alternative
    weights=None,  # TODO(fill)
)

SKELETONS: Dict[str, Skeleton] = {skeleton.name: skeleton for skeleton in (KINECT_V2, QUALISYS_SPORT, MEDIAPIPE, OPENPOSE)}

# What is still to fill, per skeleton.
SKELETON_TODO: Dict[str, Tuple[str, ...]] = {name: skeleton.missing() for name, skeleton in SKELETONS.items()}


def get_skeleton(skeleton: Any) -> Skeleton:
    """A `Skeleton`, or the preset of that name (case-insensitive; `-` and spaces count as `_`)."""
    if isinstance(skeleton, Skeleton):
        return skeleton
    if isinstance(skeleton, str):
        key = skeleton.strip().lower().replace("-", "_").replace(" ", "_")
        if key in SKELETONS:
            return SKELETONS[key]
    raise ValueError(f"skeleton: invalid value {skeleton!r}; choose one of "
                     f"{', '.join(repr(name) for name in SKELETONS)} (or a Skeleton)")


def with_skeleton(skeleton: Any, labels: Any, params: Dict[str, Any], defaults: Any = None) -> Tuple[Any, Dict[str, Any]]:
    """`labels` and `params` of a feature built with `skeleton=`: those of the skeleton unless given explicitly.

    `defaults(skeleton)`, if any, gives the block parameters the skeleton fills. Without a skeleton, nothing changes.
    """
    if skeleton is None:
        return labels, params
    skeleton = get_skeleton(skeleton)
    return (skeleton.joints if labels is None else labels), {**(defaults(skeleton) if defaults else {}), **params}
