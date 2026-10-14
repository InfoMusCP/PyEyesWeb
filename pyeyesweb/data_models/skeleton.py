"""The `Skeleton` description of a capture device: its joints and what the features need to know about them."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Skeleton:
    """The joints of a capture device and what the features need to know about them.

    `joints` is the order of the arrays; `pairs` are (left, right) joint names; `reference` is the joint used as
    origin / reference label;
    `weights` maps each joint to its kinetic-energy weight (`None` while unknown).
    """
    name: str
    joints: Tuple[str, ...]
    pairs: Tuple[Tuple[str, str], ...] = ()
    reference: Optional[str] = None
    weights: Optional[Mapping[str, float]] = field(default=None, hash=False)

    def __post_init__(self) -> None:
        if len(set(self.joints)) != len(self.joints):
            raise ValueError(f"skeleton {self.name!r}: repeated joint names")
        used = [label for pair in self.pairs for label in pair] + list(self.weights or ())
        used += [] if self.reference is None else [self.reference]
        if unknown := sorted(set(used) - set(self.joints)):
            raise ValueError(f"skeleton {self.name!r}: names that are not joints: {unknown}")
        if self.weights is not None:
            object.__setattr__(self, "weights", MappingProxyType(dict(self.weights)))

    def index(self, name: str) -> int:
        """Row of the joint `name` in the arrays."""
        return self.joints.index(name)

    def weights_or_uniform(self) -> Dict[str, float]:
        """The kinetic-energy weight of each joint: `weights`, or 1.0 for every joint when it is not filled."""
        return dict(self.weights) if self.weights is not None else {joint: 1.0 for joint in self.joints}

    def missing(self) -> Tuple[str, ...]:
        """Names of the fields still empty (the to-do list of the preset)."""
        empty = {"pairs": not self.pairs, "reference": self.reference is None,
                 "weights": self.weights is None}
        return tuple(name for name, is_empty in empty.items() if is_empty)
