from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass(slots=True)
class FeatureResult:
    """Standardized base output contract for all PyEyesWeb features."""
    is_valid: bool = True
    index: Optional[float] = None

    def to_flat_dict(self, prefix: str = "") -> Dict[str, Any]:
        """Flattens the dataclass, ignoring uncalculated (None) metrics."""
        raw_dict = asdict(self)
        flat = {}
        for key, value in raw_dict.items():
            if value is None:
                continue
            final_key = f"{prefix}_{key}" if prefix else key
            flat[final_key] = value
        return flat
