"""Complexity of a signal: sample entropy and coarse graining.

Both features work on a window of consecutive samples: `process(sample)` fills a window of `window` samples and
computes every `hop` samples.
"""

from typing import Any, Optional

import numpy as np

from pyeyesweb._core import core
from pyeyesweb.base.core_feature import CoreFeature
from pyeyesweb.base.minimum_window import MinimumWindow
from pyeyesweb.catalog import Layer, describe
from pyeyesweb.data_models.feature import WindowedFeature
from pyeyesweb.data_models.inputs import Input, InputKind, Inputs
from pyeyesweb.data_models.results import Output, Result, Schema, Status

_motion = core.motion


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="sampleentropy")
class SampleEntropy(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Sample entropy of a single-channel window, for template lengths 1 to ``embedding_dimension``.

    Sample entropy measures the irregularity of a signal: how unlikely it is that two stretches of the signal that
    are close to each other for ``m`` samples remain close at the next sample. A regular, predictable signal gives
    a low value, an irregular one a high value. Two templates of length ``k`` match when every pair of corresponding
    samples differs by less than the tolerance ``r``. With :math:`B_k` the number of matching template pairs of
    length ``k`` and :math:`A_k` the number of those that still match when extended by one sample, the entry for
    template length ``k`` is

    .. math::

        \mathrm{SampEn}_k = -\ln \frac{A_k}{B_k}, \qquad k = 1 \dots \mathtt{embedding\_dimension}.

    Parameters
    ----------
    window : int
        Samples per window (at least ``embedding_dimension + 1``). Changing it on a running feature keeps the newest
        samples.
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    embedding_dimension : int, optional
        Number of template lengths computed (the output has this many entries). Defaults to ``12``. *(structural)*
    tolerance : float or None, optional
        Absolute matching tolerance ``r``, in the units of the signal. ``None`` (default) uses
        ``relative_tolerance`` times the standard deviation of the window. *(live)*
    relative_tolerance : float, optional
        Tolerance as a fraction of the population standard deviation of the window (``1e-6`` is used as the standard
        deviation of a constant window), dimensionless. Used when ``tolerance`` is ``None``. Defaults to ``0.2``.
        *(live)*

    Notes
    -----
    **Inputs.** One value per call (a single channel).

    **Outputs.** ``sample_entropy``, shape ``(embedding_dimension,)``: entry ``k - 1`` is
    :math:`\mathrm{SampEn}_k` (nats). It is non-negative; it is ``inf`` or ``NaN`` when too few template pairs match.
    ``timestamp`` is the timestamp (seconds) of the newest sample.

    **Statuses.** ``WARMING_UP`` while the first window fills, ``NO_OUTPUT`` between two hops, ``OK`` whenever a window
    was computed.

    Corrected in the core: the template counts of length 2 and above were copied forward instead of shifted, so the
    entropies of order 2 and above were wrong. The tolerance defaults to a fraction of the standard deviation of the
    window instead of an absolute 0.3, which matched no pair on signals of another scale; an explicit ``tolerance``
    gives the former numbers exactly.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import SampleEntropy
    >>> feature = SampleEntropy(window=60, embedding_dimension=2)
    >>> result = feature.run(np.sin(0.5 * np.arange(60)))[-1]
    >>> result.sample_entropy.round(3)
    array([2.094, 0.943])
    """
    _core_class = _motion.SampleEntropy

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    @property
    def embedding_dimension(self) -> int:
        return int(self._param("embedding_dimension", 12))  # C++ default

    @embedding_dimension.setter
    def embedding_dimension(self, value: int) -> None:
        self._check_window(embedding_dimension=value)
        self._set_param("embedding_dimension", value)

    @property
    def tolerance(self) -> Optional[float]:
        return self._param("tolerance", None)  # C++ default

    @tolerance.setter
    def tolerance(self, value: Optional[float]) -> None:
        self._set_param("tolerance", value)

    @property
    def relative_tolerance(self) -> float:
        return float(self._param("relative_tolerance", 0.2))  # C++ default

    @relative_tolerance.setter
    def relative_tolerance(self, value: float) -> None:
        self._set_param("relative_tolerance", value)

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("embedding_dimension", self.embedding_dimension)) + 1

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call"))

    def _schema(self) -> Schema:
        return Schema(Output("sample_entropy", self.embedding_dimension, doc="-log(A[k] / B[k]) for template length k + 1"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float))
        return self._result(sample_entropy=raw[0], timestamp=timestamp)


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="coarsegraining")
class CoarseGraining(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Coarse-grained series of a window: means of non-overlapping groups of ``factor`` samples.

    Coarse graining looks at a signal at a slower time scale: each group of ``factor`` consecutive samples of a
    channel is replaced by its mean. It is the first step of multi-scale analyses of complexity (see
    ``MultiScaleEntropy``). For a window :math:`x_1 \dots x_N` and a factor :math:`\tau`,

    .. math::

        y_j = \frac{1}{\tau} \sum_{i=(j-1)\tau+1}^{j\tau} x_i, \qquad j = 1 \dots \lfloor N / \tau \rfloor.

    Parameters
    ----------
    window : int
        Samples per window (at least ``factor``).
    hop : int, optional
        New samples between two windows. Defaults to ``1``.
    factor : int, optional
        Number of samples averaged into one (the scale), at least 1. Defaults to ``2``. *(structural)*

    Notes
    -----
    **Inputs.** One sample per call, with one value per channel.

    **Outputs.** ``coarse_grained``, shape ``(channels, window // factor)``, in the unit of the input; a trailing
    remainder of fewer than ``factor`` samples is dropped.

    **Statuses.** ``WARMING_UP`` while the first window fills; ``NO_OUTPUT`` between two hops, and on the windows
    where the series is not recomputed (``coarse_grained`` is then not produced). As in the EyesWeb block, which
    counts its activations modulo ``factor``, the series is computed on the first full window and then on every
    ``factor``-th window, that is every ``factor * hop`` samples (the other windows say "not recomputed on this
    activation"): with ``window=4, hop=2, factor=2`` the statuses of samples 1 to 8 are ``WARMING_UP`` (three times),
    ``OK``, ``NO_OUTPUT``, ``NO_OUTPUT``, ``NO_OUTPUT``, ``OK``. With ``factor=1`` every window is computed.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import CoarseGraining
    >>> feature = CoarseGraining(window=6, factor=2)
    >>> feature.run(np.arange(6.0))[-1].coarse_grained
    array([[0.5, 2.5, 4.5]])
    """
    _core_class = _motion.CoarseGraining

    def __init__(self, window: int, hop: int = 1, **params: Any):
        super().__init__(window=window, hop=hop, **params)
        self._check_window()

    @property
    def factor(self) -> int:
        return int(self._param("factor", 2))  # C++ default

    @factor.setter
    def factor(self, value: int) -> None:
        self._check_window(factor=value)
        self._set_param("factor", value)

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("factor", self.factor))

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (None,), doc="one value per channel"))

    def _schema(self) -> Schema:
        return Schema(Output("coarse_grained", (None, None), unit="<input>", doc="coarse-grained series (channels, window // factor)"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float))
        if raw is None:
            return self._no_output(Status.NO_OUTPUT, "not recomputed on this activation", timestamp)
        return self._result(coarse_grained=raw, timestamp=timestamp)


__all__ = ["SampleEntropy", "CoarseGraining"]
