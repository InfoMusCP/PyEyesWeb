"""The guard that keeps a feature from reading joint names its configuration cannot match."""

from typing import Any, Optional, Set

from pyeyesweb.data_models.results import Result, Status


class LabelGuard:
    """Mixin of the features that read joint names: they refuse names the configuration cannot match.

    A subclass gives `_label_names()`, the set of names the block reads, and keeps the joint names of array input in `_labels`; it calls
    `_set_labels(labels)` at the end of its constructor and `_label_problem(frame, timestamp)` at the start of `_process`.
    An empty set is a configuration without joints: the constructor raises.
    """

    def _label_names(self) -> Set[str]:
        raise NotImplementedError

    def _set_labels(self, labels: Any) -> None:
        self._labels = None if labels is None else tuple(labels)
        self._check_labels()

    def _check_labels(self) -> None:
        names = self._label_names()
        if not names:
            raise ValueError(f"{type(self).__name__}: no joints given; pass skeleton= (e.g. 'kinect_v2') or your "
                             "own weights= / couples=")
        if self._labels is not None and (unknown := sorted(names - set(self._labels))):
            raise ValueError(f"{type(self).__name__}: names that are not among the labels: {unknown}")

    def _label_problem(self, frame: Any, timestamp: Optional[float]) -> Optional[Result]:
        """`INVALID_INPUT` for a dict frame that holds none of the names the configuration reads."""
        names = self._label_names()
        if not isinstance(frame, dict) or not frame or not names.isdisjoint(frame):
            return None
        return self.no_output(Status.INVALID_INPUT, f"the keys of the frame match none of {sorted(names)}", timestamp)
