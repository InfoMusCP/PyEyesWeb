"""Layer 4, qualities communicated (3 s and above): social and interaction-level features."""

from .dominance import EnsembleDominance

__all__ = [
    "EnsembleDominance"
]


def __dir__():
    return sorted(__all__)
