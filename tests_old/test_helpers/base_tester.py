"""Base tester class with common functionality for all feature testers."""
from typing import Dict, Tuple, Any, Optional, List
import numpy as np
import numpy.typing as npt

from pyeyesweb.utils.signal_generators import SignalGenerator
from .cli_formatting import CLIFormatter
from .thresholds import FeatureThresholds


class FeatureTester:
    """Base class for feature testing with common utilities.

    This class provides:
    - CLI formatting utilities
    - Signal generation helpers
    - Threshold configurations
    - Common test result handling

    Subclasses should implement:
    - test(signal_type, **kwargs): Main test method
    - _modify_signal_for_comparison(...): Optional signal modification logic
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the feature tester.

        Args:
            verbose: If True, display detailed output. If False, minimal output.
        """
        self.verbose = verbose
        self.formatter = CLIFormatter(verbose)
        self.generator = SignalGenerator()
        self.thresholds = FeatureThresholds()

    def print_header(self, title: str) -> None:
        """Print a formatted header."""
        self.formatter.print_header(title)

    def print_info(self, label: str, value: Any) -> None:
        """Print formatted information."""
        self.formatter.print_info(label, value)

    def print_section(self, title: str) -> None:
        """Print a section title."""
        self.formatter.print_section(title)

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.formatter.print_success(message)

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.formatter.print_warning(message)

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.formatter.print_error(message)

    def print_timing(self, elapsed_time: float) -> None:
        """Print timing information."""
        self.formatter.print_timing(elapsed_time)

    def generate_signal_pair(
        self,
        signal_type: str,
        signal2_type: Optional[str] = None,
        **kwargs
    ) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], Dict[str, Any]]:
        """
        Generate a pair of signals for testing.

        This method handles the common pattern of generating two signals for comparison:
        - If signal2_type is specified, generates two different signal types
        - Otherwise, generates the same signal type with modifications (via _modify_signal_for_comparison)

        Args:
            signal_type: Type of the first signal
            signal2_type: Optional type of the second signal
            **kwargs: Additional parameters for signal generation

        Returns:
            Tuple of (signal1, signal2, metadata_dict)
        """
        length = kwargs.get('length', 1000)
        t1, signal1, metadata1 = self.generator.generate(signal_type, **kwargs)

        metadata = {
            'signal1_type': signal_type,
            'length': length
        }

        if signal2_type:
            # Different signal type
            t2, signal2, metadata2 = self.generator.generate(signal2_type, **kwargs)
            metadata['signal2_type'] = signal2_type
            metadata['comparison_mode'] = 'different_signals'
        else:
            # Same type with modification (subclass decides how)
            signal2 = self._modify_signal_for_comparison(signal1, signal_type, **kwargs)
            metadata['signal2_type'] = signal_type
            metadata['comparison_mode'] = 'modified_signal'

        return signal1, signal2, metadata

    def generate_single_signal(
        self,
        signal_type: str,
        **kwargs
    ) -> Tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], Dict[str, Any]]:
        """
        Generate a single signal for testing.

        Args:
            signal_type: Type of signal to generate
            **kwargs: Additional parameters for signal generation

        Returns:
            Tuple of (time_array, signal, metadata_dict)
        """
        t, signal, metadata = self.generator.generate(signal_type, **kwargs)
        return t, signal, metadata

    def _modify_signal_for_comparison(
        self,
        signal: npt.NDArray[np.float64],
        signal_type: str,
        **kwargs
    ) -> npt.NDArray[np.float64]:
        """
        Modify a signal for comparison testing.

        Override this method in subclasses to provide feature-specific signal modifications.
        Default implementation returns a copy of the signal.

        Args:
            signal: Original signal array
            signal_type: Type of signal
            **kwargs: Additional parameters that may guide modification

        Returns:
            Modified signal array
        """
        return signal.copy()

    def compare_two_signals(
        self,
        signal1: npt.NDArray[np.float64],
        signal2: npt.NDArray[np.float64],
        signal1_type: str,
        signal2_type: str,
        metric1: float,
        metric2: float,
        metric_name: str,
        higher_is_better: bool = True
    ) -> None:
        """
        Print comparison summary between two signals.

        Args:
            signal1: First signal array
            signal2: Second signal array
            signal1_type: Type/name of first signal
            signal2_type: Type/name of second signal
            metric1: Metric value for first signal
            metric2: Metric value for second signal
            metric_name: Name of the metric being compared
            higher_is_better: If True, higher metric is better; if False, lower is better
        """
        self.print_section("Comparison Summary:")
        diff = metric1 - metric2

        if (higher_is_better and diff > 0) or (not higher_is_better and diff < 0):
            better_signal = signal1_type
            abs_diff = abs(diff)
        else:
            better_signal = signal2_type
            abs_diff = abs(diff)

        self.print_info(f"Better Signal ({metric_name})", f"{better_signal} (diff: {abs_diff:.4f})")

    def _extract_common_params(self, **kwargs) -> Tuple[int, Optional[str]]:
        """
        Extract common parameters from kwargs.

        Args:
            **kwargs: Keyword arguments

        Returns:
            Tuple of (length, signal2_type)
        """
        length = kwargs.get('length', 1000)
        signal2_type = kwargs.get('signal2', None)
        return length, signal2_type

    def _generate_test_signals(
        self,
        signal_type: str,
        signal2_type: Optional[str],
        **kwargs
    ) -> Tuple[Any, Any, Any, Any]:
        """
        Generate signals for testing with optional second signal type.

        This is a helper method that supports comparing two different signal types.

        Args:
            signal_type: Type of first signal
            signal2_type: Optional type of second signal
            **kwargs: Additional signal generation parameters

        Returns:
            Tuple of (t1, signal1, t2, signal2) where t1/t2 are time arrays
        """
        if signal2_type:
            # Generate two different signal types
            t1, signal1, _ = self.generate_single_signal(signal_type, **kwargs)
            t2, signal2, _ = self.generate_single_signal(signal2_type, **kwargs)
        else:
            # Generate single signal type
            t1, signal1, _ = self.generate_single_signal(signal_type, **kwargs)
            t2, signal2 = t1, signal1

        return t1, signal1, t2, signal2

    def test(self, signal_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Main test method - must be implemented by subclasses.

        Args:
            signal_type: Type of signal to test
            **kwargs: Additional test parameters

        Returns:
            Dictionary of test results, or None if test failed
        """
        raise NotImplementedError("Subclasses must implement test method")
