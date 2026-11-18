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
from pyeyesweb.data_models.results import Output, Result, Schema

_motion = core.motion


@describe(Layer.ANALYSIS_PRIMITIVE, eyesweb="sampleentropy")
class SampleEntropy(MinimumWindow, WindowedFeature, CoreFeature):
    r"""Sample entropy of a single-channel window: how predictable the signal is.

    Sample entropy measures the irregularity of a signal: how unlikely it is that two stretches of the signal that
    are close to each other for ``m`` samples remain close at the next sample. A regular, predictable signal gives
    a low value, an irregular one a high value. Two templates of length ``m`` match when every pair of corresponding
    samples differs by at most the tolerance ``r``. With :math:`B` the number of matching template pairs of
    length ``m`` and :math:`A` the number of those that still match when extended by one sample,

    .. math::

        \mathrm{SampEn}(m, r) = -\ln \frac{A}{B},

    the definition of Richman and Moorman (2000). The feature gives this one number.

    Parameters
    ----------
    window : int
        Samples per window (at least ``embedding_dimension + 2``; in practice 100 to 200 or more). Changing it on a running
        feature keeps the newest samples. *(live)*
    hop : int, optional
        New samples between two windows. Defaults to ``1``. *(live)*
    embedding_dimension : int, optional
        The template length ``m`` of the literature. Defaults to ``2``. *(structural)*
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

    **Outputs.** ``sample_entropy``: :math:`\mathrm{SampEn}(m, r)` (nats), a single number. It is non-negative; ``0`` is a
    perfectly predictable signal, about 1 to 2.5 an irregular one, and it is ``inf`` or ``NaN`` when no template pairs
    match (the window is too short or ``r`` too small). Compare values between gestures or over time: the absolute number
    depends on the window, on ``r`` and on the sampling rate. ``timestamp`` is the timestamp (seconds) of the newest sample.

    **Statuses.** ``WARMING_UP`` while the first window fills, ``NO_OUTPUT`` between two hops, ``OK`` whenever a window
    was computed.

    Changed from the first release of the port (design review 2026-11-17): the feature used to return the entropies of
    the template lengths ``0 ... embedding_dimension - 1`` (the pyEntropy convention), so the usual SampEn(2) needed
    ``embedding_dimension=3`` and was the last entry. It now returns only SampEn(``embedding_dimension``). The template
    counts of length 2 and above were also corrected in the core (copied forward instead of shifted), and the tolerance
    defaults to a fraction of the standard deviation of the window instead of an absolute 0.3; an explicit ``tolerance``
    gives the former numbers exactly.

    Examples
    --------
    >>> import numpy as np
    >>> from pyeyesweb.analysis_primitives import SampleEntropy
    >>> feature = SampleEntropy(window=60, embedding_dimension=2)
    >>> result = feature.run(np.sin(0.5 * np.arange(60)))[-1]
    >>> round(float(result.sample_entropy), 3)
    0.331
    """
    _core_class = _motion.SampleEntropy

    def __init__(self, window: int, hop: int = 1, embedding_dimension: int = 2, **params: Any):
        super().__init__(window=window, hop=hop, embedding_dimension=embedding_dimension, **params)
        self._check_window()

    @property
    def embedding_dimension(self) -> int:
        return int(self._param("embedding_dimension", 2))

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

    def _block_params(self, params: dict) -> dict:
        # The core gives the entropies of the template lengths 0 ... E - 1 (pyEntropy); SampEn(m) is the entry m, so E = m + 1.
        template_length = int(params.get("embedding_dimension", 2))
        if template_length < 1:
            raise ValueError("embedding_dimension must be at least 1")
        return super()._block_params({**params, "embedding_dimension": template_length + 1})

    def _minimum_window(self, **params: int) -> int:
        return int(params.get("embedding_dimension", self.embedding_dimension)) + 2

    def _inputs(self) -> Inputs:
        return Inputs(Input("signal", InputKind.SAMPLE, (1,), doc="one value per call"))

    def _schema(self) -> Schema:
        return Schema(Output("sample_entropy", doc="SampEn(m, r) = -log(A / B) of the window"))

    def _process_window(self, series: Any, *, timestamp: Optional[float] = None) -> Result:
        raw = self._block.process(np.asarray(series, dtype=float))
        return self._result(sample_entropy=float(raw[0][-1]), timestamp=timestamp)


__all__ = ["SampleEntropy"]
