"""Noise test of the skeleton motion: variances of the per-joint speeds."""

from typing import Any, Optional, Sequence, Tuple

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.base.inputs import labelled_set, points_input
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Inputs
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb.base.labels import LabelGuard
from pyeyesweb.skeletons import with_skeleton


@describe(Layer.LOW_LEVEL, eyesweb="GestureSegmenter (IsUserMotionRandomic2)")
class MotionNoiseDetector(LabelGuard, FrameFeature):
    r"""Noise test of the skeleton motion: is the motion random, with jumpy speeds?

    For every watched joint the detector keeps the last 10 speeds and computes their variance; this variance is
    averaged over 5 frames and the motion is flagged as noisy (random, jumpy) when that mean exceeds
    ``noise_threshold``. A still body, a uniform drift and the first frames have a small speed variance and are not
    flagged. The flag is the reverse of the noise input of ``GestureSegmenter``, which blocks the start of a gesture
    while its input is set: feed it ``not is_noisy`` together with the kinetic energy of the same frames, from
    ``KineticEnergy``.

    Two quirks of the original are kept: only the last joint, in label order, that has a full window counts, and the
    flag is false until 14 speeds have been seen.

    Parameters
    ----------
    labels : sequence of str, optional
        Joint names: the watched joints, which are also the names of the rows of an array frame (a dict frame carries
        its own). Taken from ``skeleton`` when that is given. *(live)*
    skeleton : str or Skeleton, optional
        A skeleton preset (``"kinect_v2"``, ...) or definition; its joints are the watched joints.
    noise_threshold : float, optional
        Threshold on the mean variance of the speed, a squared length: in m^2, scaled by ``units`` with the power 2.
        A threshold of 0 or less flags every frame as noisy, the first ones too. Defaults to ``0.5``. *(live)*
    sampling_rate : float, optional
        Sampling rate of the frames in Hz, used when no timestamp is given. Defaults to ``None`` (one second per
        frame, and the ``reason`` says so). *(live)*
    units : {"m", "mm"}, optional
        Unit of the position data: scales ``noise_threshold`` (the data and the output are never scaled). Defaults
        to ``"m"``. *(live)*

    Notes
    -----
    **Inputs.** One skeleton frame per call: an ``(N, 3)`` array in the order of ``labels`` or a dict
    ``label -> (x, y, z)``. ``process(frame, *, timestamp=None)``; ``run(frames, *, timestamps=None)`` takes a
    ``(T, N, 3)`` recording. ``timestamp`` is in seconds, from which the time step is derived.

    **Outputs.** ``is_noisy`` (bool): ``True`` when the motion is noisy, that is, random or jumpy: the mean speed
    variance exceeds ``noise_threshold``. It is ``False`` for a still body, a uniform motion and the first 14 frames.
    It is valid on every call.

    **Statuses.** ``OK`` on every valid call; ``INVALID_INPUT`` for a non-finite frame, an unknown joint or a
    timestamp that does not increase.

    Corrected in the core: ``reset()`` left the per-joint speed windows in place; it now clears them.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.low_level import MotionNoiseDetector
    >>> rng = np.random.default_rng(0)
    >>> frames = rng.normal(scale=0.3, size=(40, 1, 3))  # a joint that jumps about
    >>> feature = MotionNoiseDetector(labels=["hand"], sampling_rate=50.0)
    >>> still = feature.run(np.zeros((40, 1, 3))).is_noisy[-1]
    >>> jumping = feature.run(frames).is_noisy[-1]
    >>> bool(still), bool(jumping)
    (False, True)
    """
    _core_class = core.motion.MotionNoiseDetector
    _timed = True
    _unit_params = {"noise_threshold": 2}  # variance of a speed: length^2

    def __init__(self, labels: Optional[Sequence[str]] = None, skeleton: Any = None, **params: Any):
        labels, params = with_skeleton(skeleton, labels, params)
        super().__init__(labels=None if labels is None else list(labels), **params)
        self._set_labels(labels)

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """The watched joints, which are also the joint names of array input."""
        return self._labels

    @labels.setter
    def labels(self, value: Sequence[str]):
        self._set_param("labels", list(value))
        self._set_labels(value)

    def _label_names(self):
        return set(self._param("labels", None) or ())

    def _inputs(self) -> Inputs:
        return Inputs(points_input("skeleton", self._labels, "joint positions", accepts=(dict,)))

    def _schema(self) -> Schema:
        return Schema(Output("is_noisy", kind=bool, doc="True when the motion is noisy (random, jumpy)"))

    def _process(self, frame: Any, timestamp: Optional[float]) -> Result:
        points = labelled_set(frame, self._labels, "MotionNoiseDetector")
        return self._to_result(self._block.process(points, self._time_step(timestamp)), timestamp)

    def _to_result(self, raw: bool, timestamp: Optional[float]) -> Result:
        return self._result(is_noisy=not raw, timestamp=timestamp)


__all__ = ["MotionNoiseDetector"]
