"""The guard that keeps a feature from reading joint names its configuration cannot match."""

from typing import Any, Optional, Set, Tuple

from pyeyesweb.data_models.results import Result, Status


class LabelGuard:
    """Mixin of the features that read joint names: they refuse names the configuration cannot match.

    A subclass gives `_label_names()`, the set of names the block reads, and keeps the joint names of array input in `_labels`; it calls
    `_set_labels(labels)` at the end of its constructor. An empty set is a configuration without joints: the constructor
    raises. A dict frame is checked centrally (`_input_problem`): with `labels` configured, a key that is not one of them raises
    `ValueError` (a wrong joint name is a configuration error), a missing joint gives `INVALID_INPUT`. A feature that
    treats missing joints as dropouts sets `_dropouts = True` and calls `_label_problem(frame, timestamp)` itself.
    """

    _dropouts = False

    @property
    def labels(self) -> Optional[Tuple[str, ...]]:
        """The joint names of array input (`None`: not given)."""
        return self._labels

    def _label_names(self) -> Set[str]:
        raise NotImplementedError

    def _set_labels(self, labels: Any) -> None:
        self._labels = None if labels is None else tuple(labels)
        self._check_labels()

    def _check_labels(self) -> None:
        names = self._label_names()
        if not names:
            raise ValueError(f"{type(self).__name__}: no joints given; pass skeleton= (e.g. 'kinect_v2') or your "
                             "own weights= / pairs=")
        if self._labels is not None and (unknown := sorted(names - set(self._labels))):
            raise ValueError(f"{type(self).__name__}: names that are not among the labels: {unknown}")

    def _input_problem(self, sample: Any, timestamp: Optional[float]) -> str:
        frame = sample[0]
        if isinstance(frame, dict) and not self._dropouts:
            names = self._label_names()
            if self._labels is not None and (unknown := sorted(map(str, set(frame) - set(self._labels)))):
                raise ValueError(f"{type(self).__name__}: unknown joint names {unknown}; expected {list(self._labels)}")
            if missing := sorted(names - set(frame)):
                return f"missing joints: {', '.join(map(str, missing))}"
        return super()._input_problem(sample, timestamp)

    def _label_problem(self, frame: Any, timestamp: Optional[float]) -> Optional[Result]:
        """`INVALID_INPUT` for a dict frame that holds none of the names the configuration reads."""
        names = self._label_names()
        if not isinstance(frame, dict) or not frame or not names.isdisjoint(frame):
            return None
        return self._no_output(Status.INVALID_INPUT, f"the keys of the frame match none of {sorted(names)}", timestamp)
