"""Peak events of a scalar signal (EyesWeb DANCE).

The feature is a stateful stream over a scalar signal: `process(value, timestamp=None)` takes one sample per call and
returns a `Result` whose `timestamp` is the timestamp in seconds (`NaN` when not given); `reset()` restarts the stream.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import FrameFeature
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_dance = core.dance


class _ScalarStream(FrameFeature):
    """A block fed one scalar sample per call."""

    _input_doc = "one value per call"

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc=self._input_doc))

    def _process(self, value: Any, timestamp: Optional[float]) -> Result:
        # a scalar, or the single channel of a (1,) sample
        return self._to_result(self._block.process(np.asarray(value, dtype=float).item()), timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="scalar_peak_detector")
class ScalarPeakDetector(_ScalarStream):
    """Peak detection on a scalar signal: flags the samples at which a peak has been found.

    The detector keeps a buffer of the last ``window`` samples of the signal. The ``threshold`` is a swing, not a
    level: the buffer counts as moving when its largest and smallest values differ by more than ``threshold``, and a
    peak is reported on the first sample at which the buffer shows a fall (its maximum comes before its minimum) right
    after having shown a rise. So a peak is a maximum that is reached by a rise and left by a fall, each larger than
    ``threshold`` within the buffer; the level of the signal does not matter (a signal that stays below 0 has peaks
    too), and minima are not reported. It is used to extract events from a continuous movement signal (for example the
    peaks of a speed or an energy profile), which can be fed to ``BinaryPulsesRegularity``. A peak is reported with a
    delay after the maximum, once the fall is in the buffer: up to ``window`` samples, so ``window`` and ``threshold``
    must suit the rhythm and the amplitude of the signal (a slow, small swing is not seen by a short buffer).

    Parameters
    ----------
    window : int, optional
        Length of the buffer, in samples, at least 1. Defaults to ``5``. *(structural)*
    threshold : float, optional
        Detection threshold, in the units of the signal. Defaults to ``0.01``. *(live)*

    Notes
    -----
    **Inputs.** One value per call (a single channel); the stream keeps its state between calls and ``reset()``
    restarts it.

    **Outputs.** ``is_peak`` (bool): a peak was detected on this sample, that is, a fall larger than ``threshold`` has
    just appeared in the buffer after a rise; the sample is up to ``window`` samples after the maximum itself. ``timestamp`` is the timestamp in seconds
    (``NaN`` when not given).

    **Statuses.** ``WARMING_UP`` for the first ``window - 1`` samples, while the buffer fills (no peak can be
    reported: the original analysed a zero-filled buffer, so a signal that starts high and falls gave a false peak);
    ``OK`` afterwards; ``INVALID_INPUT`` for a NaN or infinite sample, which is kept out of the buffer.

    **Compared with** ``scipy.signal.find_peaks(x, prominence=threshold)``: the same idea, a maximum that stands out by
    more than ``threshold``, but causal and sample by sample, on a buffer of ``window`` samples only, reported with a delay,
    and as a yes/no flag instead of positions. A peak whose fall takes longer than ``window`` samples is missed.

    Corrected in the core: the running maximum was seeded with the smallest positive number, so a signal that stays
    at or below 0 never produced a peak.

    Examples
    --------
    >>> from pyeyesweb.analysis_primitives import ScalarPeakDetector
    >>> detector = ScalarPeakDetector(window=3, threshold=0.5)
    >>> results = [detector.process(value) for value in [0, 1, 3, 1, 0, 0, 2, 0, 0, 0]]
    >>> [result.is_peak for result in results]
    [False, False, False, False, True, False, False, False, True, False]
    >>> [result.status.name for result in results[:3]]
    ['WARMING_UP', 'WARMING_UP', 'OK']

    The maxima are at samples 2 and 6 and the peaks are reported two samples later, at samples 4 and 8.
    """
    _core_class = _dance.ScalarPeakDetector

    def _schema(self) -> Schema:
        return Schema(Output("is_peak", kind=bool))

    def _to_result(self, raw: Optional[bool], timestamp: Optional[float]) -> Result:
        if raw is None:
            return self._no_output(Status.WARMING_UP, "buffer filling", timestamp)
        return self._result(is_peak=raw, timestamp=timestamp)


__all__ = ["ScalarPeakDetector"]
