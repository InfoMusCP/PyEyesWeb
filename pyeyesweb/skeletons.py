"""Skeletons of the capture devices of the lab: presets of :class:`~pyeyesweb.data_models.Skeleton`.

The features that must know the joints (``KineticEnergy``, ``MotionNoiseDetector``, ``Symmetry``, ``PointsDensity``,
``PointsPredictor``) refuse to be built without joint information (they would silently read nothing). Give them
``skeleton=`` (a ``Skeleton`` or its name: ``"kinect_v2"``, ``"qualisys_sport"``, ``"mediapipe"``, ``"openpose"``;
case-insensitive, ``-`` and spaces count as ``_``) to describe the joints of your device, or explicit ``labels=`` /
``weights=`` / ``pairs=``. A parameter given explicitly always wins over the skeleton.

========================  ==========================================================================================
feature                   fields of the skeleton it reads
========================  ==========================================================================================
``KineticEnergy``         ``joints`` (labels of the array input), ``weights_or_uniform()`` (weight of each joint)
``MotionNoiseDetector``   ``joints``
``Symmetry``              ``joints``, ``pairs`` (the couples), ``reference`` (ratio method)
``PointsDensity``         ``joints`` (names of the points; they do not enter the maths)
``PointsPredictor``       ``joints``
========================  ==========================================================================================

Presets and their completeness:

* ``kinect_v2``: complete (25 joints, 10 pairs, reference ``SpineShoulder``, weights).
* ``qualisys_sport``, ``mediapipe``, ``openpose``: **incomplete**, kept as documented starting points. The fields still
  empty are listed by ``Skeleton.missing()`` and, for every preset, by ``SKELETON_TODO``; they are marked
  ``TODO(fill)`` in the source. Missing: ``reference`` and ``weights`` for ``qualisys_sport`` and ``mediapipe``;
  ``weights`` for ``openpose``. A missing ``weights`` becomes uniform weights of 1.0, so kinetic-energy values on these
  presets are not comparable with ``kinect_v2``; a missing ``reference`` means the barycentre for the reflection
  symmetry, and the ratio symmetry raises ``ValueError`` at construction asking for ``reference_point=``.

The joint names keep the spelling of each device (``L*/R*``, ``*Left/*Right``, ``left_*/right_*``; ``RelbowOut`` keeps
the spelling of the marker files of the lab): they are not normalised.
"""

from typing import Any, Dict, Tuple

from pyeyesweb.data_models.skeleton import Skeleton

__all__ = ["Skeleton", "KINECT_V2", "QUALISYS_SPORT", "MEDIAPIPE", "OPENPOSE", "SKELETONS", "SKELETON_TODO",
           "get_skeleton", "with_skeleton"]


def __dir__():
    return sorted(__all__)


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
    """A :class:`~pyeyesweb.data_models.Skeleton`, or the preset of that name.

    Parameters
    ----------
    skeleton : Skeleton or str
        A skeleton, returned as it is, or the name of a preset: ``"kinect_v2"``, ``"qualisys_sport"``, ``"mediapipe"``
        or ``"openpose"``. The name is case-insensitive; ``-`` and spaces count as ``_``.

    Returns
    -------
    Skeleton

    Raises
    ------
    ValueError
        For a name that is not a preset (the message lists the valid names), or any other type.

    Examples
    --------
    >>> from pyeyesweb.skeletons import get_skeleton
    >>> skeleton = get_skeleton("Kinect-V2")
    >>> skeleton.name, len(skeleton.joints), skeleton.reference
    ('kinect_v2', 25, 'SpineShoulder')
    >>> get_skeleton("openpose").missing()
    ('weights',)
    >>> get_skeleton(skeleton) is skeleton
    True
    """
    if isinstance(skeleton, Skeleton):
        return skeleton
    if isinstance(skeleton, str):
        key = skeleton.strip().lower().replace("-", "_").replace(" ", "_")
        if key in SKELETONS:
            return SKELETONS[key]
    raise ValueError(f"skeleton: invalid value {skeleton!r}; choose one of "
                     f"{', '.join(repr(name) for name in SKELETONS)} (or a Skeleton)")


def with_skeleton(skeleton: Any, labels: Any, params: Dict[str, Any], defaults: Any = None) -> Tuple[Any, Dict[str, Any]]:
    """Resolve the ``skeleton=`` parameter of a feature into its ``labels`` and parameters.

    Used by the features that accept a skeleton; a parameter given explicitly always wins over the skeleton.

    Parameters
    ----------
    skeleton : Skeleton or str or None
        The skeleton or the name of a preset; ``None`` leaves ``labels`` and ``params`` unchanged.
    labels : sequence of str or None
        The labels given explicitly, if any.
    params : dict
        The parameters given explicitly.
    defaults : callable, optional
        ``defaults(skeleton)`` returns the parameters the skeleton fills (``weights``, ``pairs``, ...).

    Returns
    -------
    labels : sequence of str or None
        ``labels``, or the joints of the skeleton when ``labels`` is ``None``.
    params : dict
        The parameters of the skeleton, updated with ``params``.

    Examples
    --------
    >>> from pyeyesweb.skeletons import with_skeleton
    >>> labels, params = with_skeleton("kinect_v2", None, {"pairs": ()}, lambda skeleton: {"pairs": skeleton.pairs})
    >>> len(labels), params
    (25, {'pairs': ()})
    >>> with_skeleton(None, ("a", "b"), {"pairs": ()})
    (('a', 'b'), {'pairs': ()})
    """
    if skeleton is None:
        return labels, params
    skeleton = get_skeleton(skeleton)
    return (skeleton.joints if labels is None else labels), {**(defaults(skeleton) if defaults else {}), **params}
