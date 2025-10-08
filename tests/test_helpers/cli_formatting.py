"""CLI formatting utilities for test output."""
from typing import Any


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class CLIFormatter:
    """Handles all CLI output formatting with consistent styling."""

    def __init__(self, verbose: bool = True):
        """
        Initialize the CLI formatter.

        Args:
            verbose: If True, display detailed output. If False, minimal output.
        """
        self.verbose = verbose

    def print_header(self, title: str) -> None:
        """
        Print a formatted header with decorative borders.

        Args:
            title: Header title text
        """
        if self.verbose:
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.BOLD}{title}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

    def print_info(self, label: str, value: Any) -> None:
        """
        Print formatted information with label-value pairs.

        Args:
            label: Information label
            value: Information value
        """
        if self.verbose:
            print(f"{Colors.OKCYAN}{label:20s}{Colors.ENDC}: {value}")

    def print_section(self, title: str) -> None:
        """
        Print a section title.

        Args:
            title: Section title text
        """
        if self.verbose:
            print(f"\n{Colors.BOLD}{title}{Colors.ENDC}")

    def print_success(self, message: str) -> None:
        """
        Print a success message with checkmark.

        Args:
            message: Success message text
        """
        if self.verbose:
            print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

    def print_warning(self, message: str) -> None:
        """
        Print a warning message with warning symbol.

        Args:
            message: Warning message text
        """
        if self.verbose:
            print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

    def print_error(self, message: str) -> None:
        """
        Print an error message with X symbol (always shown, ignores verbose).

        Args:
            message: Error message text
        """
        print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

    def print_timing(self, elapsed_time: float) -> None:
        """
        Print timing information.

        Args:
            elapsed_time: Elapsed time in seconds
        """
        if self.verbose:
            print(f"\n{Colors.OKBLUE}Test completed in {elapsed_time:.3f} seconds{Colors.ENDC}")
