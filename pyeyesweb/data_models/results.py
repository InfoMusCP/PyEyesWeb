"""Standardized output contracts for feature extraction.

This module defines the [FeatureResult][pyeyesweb.data_models.results.FeatureResult]
base class, which ensures consistency in how feature values are returned,
validated, and flattened for data logging.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass(slots=True)
class FeatureResult:
    """Standardized base output contract for all PyEyesWeb features.

    Attributes
    ----------
    is_valid : bool, optional
        Flag indicating if the computation was successful.  Defaults to `True`.
        Set to `False` when input data is insufficient (e.g., empty window).
    """
    is_valid: bool = True

    def to_flat_dict(self, prefix: str = "") -> Dict[str, Any]:
        """Flatten the result into a dictionary for logging.

        Converts the dataclass to a dictionary, optionally adding a prefix to
        all keys and removing any fields with `None` values.

        Parameters
        ----------
        prefix : str, optional
            A string to prepend to each key in the dictionary.  Defaults to `""`.

        Returns
        -------
        Dict[str, Any]
            A flat dictionary containing the valid feature results.
        """
        raw_dict = asdict(self)  # type: ignore
        flat = {}
        for key, value in raw_dict.items():
            if value is None:
                continue
            final_key = f"{prefix}_{key}" if prefix else key
            flat[final_key] = value
        return flat
