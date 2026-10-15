"""Impulsivity of a movement: from the direction change and suddenness of a trajectory, and from the change of the
contraction index over a gesture.
"""

from typing import Any, Optional

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema
from pyeyesweb.base.inputs import InferredDims, scalar
from pyeyesweb.mid_level.suddenness import _Algorithm, _SuddennessFit


@describe(Layer.MID_LEVEL)
class SuddennessImpulsivity(_SuddennessFit, InferredDims, WindowedFeature, CoreFeature):
    r"""Impulsivity of a trajectory: its direction change when it is also sudden, else zero.

    Captures the burst-like quality of a movement as the product of a spatial and a temporal term over a window of a
    single trajectory: a movement is impulsive when it turns sharply and also does so suddenly,

    .. math::

        I = D \cdot \mathbf{1}[\text{sudden}],

    where :math:`\mathbf{1}[\text{sudden}]` is the classification of ``Suddenness`` on the speeds of the window, and
    :math:`D \in [0, 1]` is the direction change, computed from the first, the middle (index ``N // 2``) and the last
    position of the window, :math:`P_0, P_m, P_{N-1}`. With :math:`\theta` the angle between :math:`P_m - P_0` and
    :math:`P_{N-1} - P_m` (0 for a straight path, :math:`\pi` for a reversal) and :math:`a = 1 - \theta / \pi`,

    .. math::

        D = \begin{cases} 1 - \lvert a - 0.5 \rvert / \varepsilon & \lvert a - 0.5 \rvert < \varepsilon \\
            0 & \text{otherwise} \end{cases}

    so that :math:`D` is 1 for a right-angle turn and falls to 0 for a straight path or a reversal (with the default
    :math:`\varepsilon = 0.5`; a smaller ``direction_change_epsilon`` keeps only turns close to a right angle). A smooth
    or predictable movement is not sudden and so gives 0. Both terms evaluate the same single trajectory.

    Input: one position per call, the ``(dims,)`` point of a trajectory with ``dims`` equal to 2 or 3 (a ``(signals,
    dims)`` frame is rejected: average the markers before the call if one trajectory is wanted); ``process(frame, *,
    timestamp=None)``. The feature buffers ``window`` frames and computes every ``hop`` frames; ``timestamp`` is that of
    the newest frame.

    Parameters
    ----------
    window : int
        Frames per window, at least 6.
    hop : int, optional
        New frames between two windows, between 1 and ``window``. Defaults to ``1``.
    dims : int, optional
        Coordinates of the position, 2 or 3. Defaults to the size of the first position.
    direction_change_epsilon : float, optional
        Half-width :math:`\varepsilon` of the range of the normalised angle (in units of :math:`\pi`) around a right
        angle in which the direction change is not zero; dimensionless. Defaults to ``0.5``. *(live)*
    method : {"constrained", "quantile"}, optional
        The fit used by the suddenness term, as in ``Suddenness``. Defaults to ``"constrained"``. *(live)*

    Notes
    -----
    **Outputs.** ``impulsivity_index``: dimensionless, in [0, 1]; 0 when the window is not sudden.

    **Statuses.** ``WARMING_UP`` until the first window of ``window`` frames is full, ``NO_OUTPUT`` between two windows,
    ``INVALID_INPUT`` for NaN or infinite coordinates and, with ``method="quantile"``, when the distribution could not
    be fitted (the index is then empty).

    Corrected in the core: both terms evaluate the same single trajectory; the original block took the direction change
    of the mean of all the signals and the suddenness of the first signal only.

    References
    ----------
    :cite:`mazzarino2009impulsivity`, :cite:`niewiadomski2015impulsive`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.mid_level import SuddennessImpulsivity
    >>> positions = np.cumsum(np.random.default_rng(0).normal(size=(40, 3)), axis=0)
    >>> record = SuddennessImpulsivity(window=20, hop=10).run(positions)
    >>> print(f"{record.impulsivity_index[19]:.2f}")
    0.22
    """

    _OUTPUTS = Schema(
        Output("impulsivity_index", doc="Direction change times suddenness (0 when not sudden)."),
    )

    _core_class = core.motion.SuddennessImpulsivity
    _core_names = {"method": "algorithm"}
    _lazy_block = True

    def __init__(self, window: int, hop: int = 1, *, dims: Optional[int] = None, direction_change_epsilon: float = 0.5,
                 method: _Algorithm = "constrained"):
        super().__init__(window=window, hop=hop)
        self.dims = dims
        self.direction_change_epsilon = direction_change_epsilon
        self.method = method
        self._check_window()

    @property
    def direction_change_epsilon(self) -> float:
        return self._params["direction_change_epsilon"]

    @direction_change_epsilon.setter
    def direction_change_epsilon(self, value: float):
        self._set_param("direction_change_epsilon", float(value))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        trajectory = self._window_trajectory(series)
        if (unusable := self._unusable(trajectory, timestamp)) is not None:
            return unusable
        impulsivity, alpha = self._block.process(trajectory)
        return self._fit_result(alpha, timestamp, impulsivity_index=impulsivity)


@describe(Layer.MID_LEVEL, eyesweb="Impulsivity")
class ContractionImpulsivity(CoreFeature):
    r"""Change of the contraction index over a short, energetic gesture, per second.

    Detects impulsive gestures from the quantity of motion and the contraction index of the body and measures how fast
    the body contracts or expands during them. A gesture is a run of frames with the quantity of motion above
    ``motion_threshold``, closed by the first frame at or below it; it is impulsive when it lasts at most
    ``gesture_duration`` frames and its peak quantity of motion reaches ``peak_threshold``. On the frame that closes an
    impulsive gesture the index is the range of the contraction index over the gesture divided by its duration:

    .. math::

        I = \frac{\max_t CI_t - \min_t CI_t}{T / f_s},

    where :math:`T` is the number of frames from the start of the gesture to the closing frame, inclusive, and
    :math:`f_s` is ``sampling_rate``. On every other frame both outputs are 0. Both inputs are expected in [0, 1]
    (normalised quantity of motion and contraction index); a pair outside that range is ignored and produces zeros.

    Two inputs, in call order, scalar samples: ``process(quantity_of_motion, contraction_index, *, timestamp=None)``;
    ``run`` takes the two recordings in the same order. The feature is stateful (the gesture in progress). Timestamps,
    when given, must increase; the time scale of the index comes only from ``sampling_rate``.

    Parameters
    ----------
    gesture_duration : float, optional
        Maximum duration of an impulsive gesture, in frames. Not to be confused with the output of the same name, which
        is the measured duration. Defaults to ``25``. *(live)*
    peak_threshold : float, optional
        Minimum peak of the quantity of motion for a gesture to count as energetic, in [0, 1]. Defaults to ``0.02``.
        *(live)*
    motion_threshold : float, optional
        Level of the quantity of motion above which a frame is motion and at or below which it is a pause, in [0, 1]
        (fixed to 0.01 in the original block). Defaults to ``0.01``. *(live)*
    sampling_rate : float, optional
        Frame rate, in Hz, that turns frames into seconds. Without it (``None``, the default) the index is per frame,
        not per second. *(live)*

    Notes
    -----
    **Outputs.** ``impulsivity_index``: change of the contraction index per second (per frame without
    ``sampling_rate``), not negative. ``gesture_duration``: length of the impulsive gesture, in frames. Both are 0
    except on the frame that closes an impulsive gesture.

    **Statuses.** ``OK`` for every sample; ``INVALID_INPUT`` for a timestamp that does not increase.

    References
    ----------
    :cite:`mazzarino2009impulsivity`, :cite:`niewiadomski2015impulsive`

    Examples
    --------
    >>> from pyeyesweb.mid_level import ContractionImpulsivity
    >>> quantity_of_motion = [0, 0.05, 0.2, 0.3, 0.1, 0, 0]
    >>> contraction_index = [0.5, 0.5, 0.6, 0.8, 0.7, 0.5, 0.5]
    >>> record = ContractionImpulsivity(sampling_rate=25.0).run(quantity_of_motion, contraction_index)
    >>> print(round(float(record.impulsivity_index[5]), 2), record.gesture_duration[5])
    1.5 5.0
    """
    _core_class = core.motion.ImpulsivityIndex
    _core_names = {"gesture_duration": "ges_dur", "sampling_rate": "frames"}
    _timed = True

    def _block_params(self, params: dict) -> dict:
        rate = params.get("sampling_rate")  # no rate: per frame, not the 25 Hz of the block
        return super()._block_params({**params, "sampling_rate": 1.0 if rate is None else rate})

    def _inputs(self) -> Inputs:
        return Inputs(Input("quantity_of_motion", InputKind.SAMPLE, (1,), doc="quantity of motion"),
                      Input("contraction_index", InputKind.SAMPLE, (1,), doc="contraction index"))

    def _schema(self) -> Schema:
        per = "s" if self._params["sampling_rate"] else "frame"
        return Schema(Output("impulsivity_index", unit=f"1/{per}", doc="contraction-index change per second"),
                      Output("gesture_duration", unit="frames"))

    def process(self, quantity_of_motion: Any, contraction_index: Any, *, timestamp: Optional[float] = None) -> Result:
        self._time_step(timestamp)  # only the time rule (a timestamp that goes back is rejected): the rate is `sampling_rate`
        return self._to_result(self._block.process(scalar(quantity_of_motion), scalar(contraction_index)), timestamp)

    def _to_result(self, raw: Any, timestamp: Optional[float]) -> Result:
        index, duration = raw
        return self._result(impulsivity_index=index, gesture_duration=duration, timestamp=timestamp)


__all__ = ["SuddennessImpulsivity", "ContractionImpulsivity"]
