"""`Symmetry(method="reflection")` for tests that think in rows of the frame: the joints are named `j0`, `j1`, ..."""

from pyeyesweb.low_level import Symmetry


def reflection(joint_count, pairs, center=None, **params):
    """A reflection `Symmetry` for frames of `joint_count` rows; `pairs` and `center` (`None`: the barycentre) are row indices."""
    labels = [f"j{row}" for row in range(joint_count)]
    return Symmetry(method="reflection", labels=labels, pairs=[(labels[left], labels[right]) for left, right in pairs],
                    reference_point=None if center is None else labels[center], **params)
