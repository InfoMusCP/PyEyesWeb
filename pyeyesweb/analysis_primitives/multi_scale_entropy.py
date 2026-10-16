"""Multi-scale entropy and ensemble dominance, after the analysis of dominance in social creative activities.

The multi-scale entropy algorithm (Glowinski et al., 2010; Costa et al., 2005) has two atomic pieces:

1. [MultiScaleEntropy][pyeyesweb.analysis_primitives.multi_scale_entropy.MultiScaleEntropy]: coarse-graining at several
   time scales, the sample entropy of every scale and the complexity index (the area under that curve), per signal.
2. [EnsembleDominance][pyeyesweb.high_level.dominance.EnsembleDominance]: dominance scores and the
   leader of an ensemble from the complexity indices of its participants.

The entropies agree with the pure-Python implementation of 1.x to O(1/N), not to rounding.

References
----------
Glowinski, D., Coletta, P., Volpe, G., Camurri, A., Chiorri, C., & Schenone, A. (2010).
Multi-scale entropy analysis of dominance in social creative activities.
In Proceedings of the 18th ACM international conference on Multimedia (pp. 1035-1038).

Costa, M., Goldberger, A. L., & Peng, C.-K. (2005).
Multiscale entropy analysis of biological signals.
Physical Review E, 71(2), 021906.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.inputs import non_finite
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status
from pyeyesweb.utils.validators import validate_integer, validate_numeric


@describe(Layer.ANALYSIS_PRIMITIVE)
class MultiScaleEntropy(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Multi-scale entropy curve and complexity index of one or several signals.

    Multi-scale entropy measures how irregular a signal is across time scales: a signal that stays irregular when it
    is observed more slowly (white noise excepted) is more complex than one whose irregularity vanishes at the
    slower scales. In the study of social creative activities the complexity index of the movement of each member of
    a group is the input of the dominance analysis (see ``EnsembleDominance``) :cite:`glowinski2010mse`.

    Each signal is normalised to unit standard deviation and coarse-grained at the scales
    :math:`\tau = 1 \dots` ``max_scale`` (means of non-overlapping groups of :math:`\tau` samples, as in
    ``CoarseGraining``) :cite:`costa2005multiscale`. The sample entropy of every scale (as in ``SampleEntropy``, for
    the template length ``embedding_dimension`` and a matching tolerance of ``tolerance`` times the standard deviation
    of the normalised series) forms the entropy curve :math:`E(\tau)`. The complexity index is the area under that
    curve, by the trapezoid rule over the scales used,

    .. math::

        \mathrm{CI} = \sum_{\tau=1}^{\tau_{\max}-1} \frac{E(\tau) + E(\tau + 1)}{2},

    where a scale is used while its coarse-grained series has at least ``minimum_points`` samples.

    Parameters
    ----------
    window : int, optional
        Samples per window. Must be at least ``max_scale * minimum_points`` so that every scale is used (the
        constructor raises ``ValueError`` otherwise). Defaults to ``3000``, the minimum of the default ``max_scale``
        and ``minimum_points``. Changing it on a running feature keeps the newest samples. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
    embedding_dimension : int, optional
        Template length of the sample entropy, at least 1. Defaults to ``2``. *(structural)*
    tolerance : float, optional
        Matching tolerance of the sample entropy, in standard deviations of the (normalised) series, dimensionless,
        in ``[0.0001, 0.9999]``. Defaults to ``0.15``. *(live)*
    max_scale : int, optional
        Largest scale :math:`\tau` of the coarse graining, at least 1. Defaults to ``6``. *(structural)*
    minimum_points : int, optional
        Minimum number of samples a coarse-grained series must have for its scale to be used, at least 1. Defaults
        to ``500``. *(structural)*

    Notes
    -----
    **Inputs.** One sample per call, with one value per signal. A ``(signals, dims)`` frame is flattened: every value
    is one signal. ``run`` takes a recording of shape ``(samples, signals)``.

    **Outputs.** ``complexity_index``, shape ``(signals,)``: the area under the entropy curve, non-negative;
    ``NaN`` for a constant signal, which has no entropy. ``scale_entropies``, shape ``(signals, max_scale)``: the
    sample entropy :math:`E(\tau)` of each signal at the scales 1 to ``max_scale`` (nats; ``NaN`` for a scale not
    used). ``timestamp`` is the timestamp (seconds) of the newest sample. The dominance of several signals is
    ``EnsembleDominance`` applied to the complexity indices.

    **Statuses.** ``WARMING_UP`` while the first window fills (``"k of window samples"``), ``NO_OUTPUT`` between two
    hops, ``INVALID_INPUT`` for a window that holds a ``NaN`` or an infinite value.

    The entropies are computed with the sample entropy of the core (see ``SampleEntropy``); they differ from the
    pure-Python implementation of the 1.x releases by O(1/N), not by rounding.

    References
    ----------
    :cite:`glowinski2010mse`, :cite:`costa2005multiscale`

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import MultiScaleEntropy
    >>> x = np.random.default_rng(1).normal(size=1200)
    >>> feature = MultiScaleEntropy(window=1200, max_scale=2, minimum_points=600)
    >>> result = feature.run(x)[-1]
    >>> result.complexity_index.round(1), result.scale_entropies.round(1)
    (array([2.5]), array([[2.5, 2.4]]))
    """
    _core_class = core.motion.MultiScaleEntropy
    _lazy_block = True

    def __init__(self, window: int = 3000, hop: int = 1, *, embedding_dimension: int = 2, tolerance: float = 0.15,
                 max_scale: int = 6, minimum_points: int = 500):
        super().__init__(window=window, hop=hop)
        self.embedding_dimension = embedding_dimension
        self.tolerance = tolerance
        self.max_scale = max_scale
        self.minimum_points = minimum_points

    def _scales(self, params: dict) -> tuple:
        # a parameter not set yet counts as 1 (the last one set checks all)
        values = {"max_scale": 1, "minimum_points": 1} | self._params | params
        return values["max_scale"], values["minimum_points"]

    def _minimum_window(self, **params: int) -> int:
        max_scale, minimum_points = self._scales(params)
        return max_scale * minimum_points  # keeps every scale

    def _minimum_reason(self, **params: int) -> str:
        return " (max_scale * minimum_points = {} * {}: the coarsest scale needs minimum_points samples)".format(*self._scales(params))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per signal"))

    def _schema(self) -> Schema:
        return Schema(Output("complexity_index", (None,), doc="complexity index of each signal"),
                      Output("scale_entropies", (None, self._params.get("max_scale", 1)),
                             doc="sample entropy of each signal at the scales 1..max_scale, NaN for a scale not used"))

    @property
    def embedding_dimension(self) -> int:
        return self._params["embedding_dimension"]

    @embedding_dimension.setter
    def embedding_dimension(self, value):
        self._set_param("embedding_dimension", validate_integer(value, "embedding_dimension", min_val=1))

    @property
    def tolerance(self) -> float:
        return self._params["tolerance"]

    @tolerance.setter
    def tolerance(self, value):
        self._set_param("tolerance", validate_numeric(value, "tolerance", min_val=0.0001, max_val=0.9999))

    @property
    def max_scale(self) -> int:
        return self._params["max_scale"]

    @max_scale.setter
    def max_scale(self, value):
        value = validate_integer(value, "max_scale", min_val=1)
        self._check_window(max_scale=value)
        self._set_param("max_scale", value)

    @property
    def minimum_points(self) -> int:
        return self._params["minimum_points"]

    @minimum_points.setter
    def minimum_points(self, value):
        value = validate_integer(value, "minimum_points", min_val=1)
        self._check_window(minimum_points=value)
        self._set_param("minimum_points", value)

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        """Compute the multi-scale entropy of one window.

        Parameters
        ----------
        series : array-like of shape (signals, samples)
            One row per signal, the oldest sample first (a 1-D array is one signal).
        timestamp : float, optional
            Timestamp of the window (seconds).

        Returns
        -------
        Result
            See the class documentation.
        """
        signals = np.atleast_2d(np.asarray(series, dtype=float))
        if reason := non_finite(signals):
            return self._no_output(Status.INVALID_INPUT, reason, timestamp)

        raw = self._block.process(np.ascontiguousarray(signals))
        if raw is None:
            return self._no_output(Status.WARMING_UP, f"fewer than {self.minimum_points} samples", timestamp)
        return self._result(complexity_index=raw[0], scale_entropies=raw[1], timestamp=timestamp)


__all__ = ['MultiScaleEntropy']
