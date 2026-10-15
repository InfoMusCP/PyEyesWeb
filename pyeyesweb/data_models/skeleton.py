"""The ``Skeleton`` description of a capture device: its joints and what the features need to know about them."""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Skeleton:
    """The joints of a capture device and what the features need to know about them.

    A skeleton is a frozen description: the names of the joints in the order of the arrays, the couples of left and
    right joints, the joint used as origin, and the kinetic-energy weight of each joint. The presets of the lab are in
    :mod:`pyeyesweb.skeletons`; features take one through their ``skeleton`` parameter (by object or by name).

    Parameters
    ----------
    name : str
        Name of the device or marker set.
    joints : tuple of str
        Joint names, in the order of the rows of a frame. Must be unique.
    pairs : tuple of (str, str), optional
        ``(left, right)`` joint names, used by the symmetry features.
    reference : str, optional
        Joint used as origin / reference label (``None`` while unknown).
    weights : mapping of str to float, optional
        Kinetic-energy weight of each joint (``None`` while unknown: a feature then weighs every joint 1.0, see
        :meth:`weights_or_uniform`).

    Raises
    ------
    ValueError
        For repeated joint names, or for a name in ``pairs``, ``reference`` or ``weights`` that is not a joint.

    Notes
    -----
    A parameter given explicitly to a feature (``labels``, ``weights``, ``pairs``) always wins over the skeleton.
    :meth:`missing` lists the fields still empty.

    Examples
    --------
    >>> from pyeyesweb.data_models import Skeleton
    >>> arm = Skeleton("arm", joints=("shoulder", "elbow", "wrist"), reference="shoulder",
    ...                weights={"shoulder": 0.3, "elbow": 0.2, "wrist": 0.1})
    >>> arm.index("wrist"), arm.reference, arm.missing()
    (2, 'shoulder', ('pairs',))
    >>> arm.weights_or_uniform()["elbow"]
    0.2
    >>> Skeleton("bare", joints=("a", "b")).weights_or_uniform()
    {'a': 1.0, 'b': 1.0}
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
        """Row of the joint ``name`` in the arrays (``ValueError`` for an unknown name)."""
        return self.joints.index(name)

    def weights_or_uniform(self) -> Dict[str, float]:
        """The kinetic-energy weight of each joint: ``weights``, or 1.0 for every joint when they are not filled."""
        return dict(self.weights) if self.weights is not None else {joint: 1.0 for joint in self.joints}

    def missing(self) -> Tuple[str, ...]:
        """Names of the fields still empty among ``pairs``, ``reference`` and ``weights`` (the to-do list of a preset)."""
        empty = {"pairs": not self.pairs, "reference": self.reference is None,
                 "weights": self.weights is None}
        return tuple(name for name, is_empty in empty.items() if is_empty)
