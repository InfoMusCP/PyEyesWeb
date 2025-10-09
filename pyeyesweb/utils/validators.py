"""Validation utilities for PyEyesWeb.

This module provides common validation functions used across multiple
PyEyesWeb modules to ensure consistent error handling.
"""


def validate_numeric(value, name, min_val=None, max_val=None):
    """Validate numeric parameter with optional bounds checking.

    Parameters
    ----------
    value : any
        Value to validate
    name : str
        Parameter name for error messages
    min_val : float, optional
        Minimum allowed value (inclusive)
    max_val : float, optional
        Maximum allowed value (inclusive)

    Returns
    -------
    float
        Validated numeric value as float

    Raises
    ------
    TypeError
        If value is not numeric (int or float)
    ValueError
        If value is outside specified bounds

    Examples
    --------
    >>> validate_numeric(50.0, 'rate_hz', min_val=0.1, max_val=100000)
    50.0
    >>> validate_numeric(-1, 'phase', min_val=0, max_val=1)
    ValueError: phase must be >= 0, got -1
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")

    value = float(value)

    if min_val is not None and value < min_val:
        raise ValueError(f"{name} must be >= {min_val}, got {value}")

    if max_val is not None and value > max_val:
        raise ValueError(f"{name} must be <= {max_val}, got {value}")

    return value


def validate_integer(value, name, min_val=None, max_val=None):
    """Validate integer parameter with optional bounds checking.

    Parameters
    ----------
    value : any
        Value to validate
    name : str
        Parameter name for error messages
    min_val : int, optional
        Minimum allowed value (inclusive)
    max_val : int, optional
        Maximum allowed value (inclusive)

    Returns
    -------
    int
        Validated integer value

    Raises
    ------
    TypeError
        If value is not an integer
    ValueError
        If value is outside specified bounds

    Examples
    --------
    >>> validate_integer(100, 'sensitivity', min_val=1, max_val=10000)
    100
    >>> validate_integer(0, 'max_length', min_val=1)
    ValueError: max_length must be >= 1, got 0
    """
    if not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}")

    if min_val is not None and value < min_val:
        raise ValueError(f"{name} must be >= {min_val}, got {value}")

    if max_val is not None and value > max_val:
        raise ValueError(f"{name} must be <= {max_val}, got {value}")

    return value


def validate_boolean(value, name):
    """Validate boolean parameter.

    Parameters
    ----------
    value : any
        Value to validate
    name : str
        Parameter name for error messages

    Returns
    -------
    bool
        Validated boolean value

    Raises
    ------
    TypeError
        If value is not a boolean

    Examples
    --------
    >>> validate_boolean(True, 'use_filter')
    True
    >>> validate_boolean(1, 'output_phase')
    TypeError: output_phase must be boolean, got int
    """
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be boolean, got {type(value).__name__}")
    return value


def validate_range(value, name, min_val, max_val):
    """Validate that a value is within a specific range.

    Useful for parameters that must be within a specific range like
    phase_threshold (0-1), percentages (0-100), etc.

    Parameters
    ----------
    value : float or int
        Value to validate
    name : str
        Parameter name for error messages
    min_val : float
        Minimum allowed value (inclusive)
    max_val : float
        Maximum allowed value (inclusive)

    Returns
    -------
    float
        Validated value

    Raises
    ------
    ValueError
        If value is outside the specified range

    Examples
    --------
    >>> validate_range(0.7, 'phase_threshold', 0, 1)
    0.7
    >>> validate_range(1.5, 'probability', 0, 1)
    ValueError: probability must be between 0 and 1, got 1.5
    """
    if not min_val <= value <= max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")
    return value


def validate_filter_params_tuple(value, name='filter_params'):
    """Validate filter parameters tuple structure.

    Ensures the value is a tuple/list with exactly 3 numeric elements
    before passing to validate_filter_params for frequency validation.

    Parameters
    ----------
    value : any
        Value to validate as filter parameters tuple
    name : str, optional
        Parameter name for error messages (default: 'filter_params')

    Returns
    -------
    tuple
        Validated tuple of (lowcut, highcut, fs)

    Raises
    ------
    TypeError
        If value is not a tuple/list or contains non-numeric elements
    ValueError
        If value doesn't have exactly 3 elements

    Examples
    --------
    >>> validate_filter_params_tuple((1.0, 10.0, 100.0))
    (1.0, 10.0, 100.0)
    >>> validate_filter_params_tuple([1, 10, 100])
    (1, 10, 100)
    >>> validate_filter_params_tuple("invalid")
    TypeError: filter_params must be a tuple or list, got str
    """
    if not isinstance(value, (tuple, list)):
        raise TypeError(f"{name} must be a tuple or list, got {type(value).__name__}")

    if len(value) != 3:
        raise ValueError(f"{name} must have 3 elements (lowcut, highcut, fs), got {len(value)}")

    if not all(isinstance(x, (int, float)) for x in value):
        raise TypeError(f"{name} must contain only numbers")

    return tuple(value)


def validate_and_normalize_filter_params(filter_params):
    """Validate and normalize filter parameters.

    Parameters
    ----------
    filter_params : tuple/list or None
        Filter parameters as (lowcut, highcut, fs) or None

    Returns
    -------
    tuple or None
        Validated (lowcut, highcut, fs) tuple or None if input was None
    """
    if filter_params is None:
        return None

    # Import here to avoid circular dependency
    from pyeyesweb.utils.signal_processing import validate_filter_params

    filter_params = validate_filter_params_tuple(filter_params)
    lowcut, highcut, fs = validate_filter_params(*filter_params)
    return (lowcut, highcut, fs)


def validate_window_size(value, name='window_size'):
    """Validate window size parameter.

    Standard validation for window sizes used across multiple modules.

    Parameters
    ----------
    value : int
        Window size value
    name : str
        Parameter name for error messages

    Returns
    -------
    int
        Validated window size
    """
    return validate_integer(value, name, min_val=1, max_val=10000)