"""Threshold configurations for feature interpretation.

This module provides configurable thresholds for interpreting feature analysis results.
All thresholds can be easily adjusted without modifying the core testing logic.
"""
from dataclasses import dataclass


@dataclass
class SynchronizationThresholds:
    """Thresholds for Phase Locking Value (PLV) interpretation."""
    HIGH: float = 0.8  # High synchronization
    MODERATE: float = 0.5  # Moderate synchronization
    # Below MODERATE is considered low synchronization

@dataclass
class SmoothnessThresholds:
    """Thresholds for SPARC (Spectral Arc Length) interpretation.

    Note: SPARC values are negative; values closer to 0 indicate smoother movement.
    """
    VERY_SMOOTH: float = -1.6  # Very smooth signal (healthy-like movement)
    MODERATELY_SMOOTH: float = -3.0  # Moderately smooth signal
    # Below MODERATELY_SMOOTH is considered rough/pathological

@dataclass
class EquilibriumThresholds:
    """Thresholds for equilibrium/stability interpretation.

    Note: Equilibrium values range from 0 to 1, where 1 = perfect balance.
    """
    HIGH_STABILITY: float = 0.9  # High stability/equilibrium
    MODERATE_STABILITY: float = 0.7  # Moderate stability
    # Below MODERATE_STABILITY is considered low stability


@dataclass
class SymmetryThresholds:
    """Thresholds for bilateral symmetry interpretation.

    Note: Symmetry values range from 0 to 1, where 1 = perfect symmetry.
    """
    HIGH_SYMMETRY: float = 0.95  # High bilateral symmetry
    MODERATE_SYMMETRY: float = 0.8  # Moderate bilateral symmetry
    # Below MODERATE_SYMMETRY is considered low symmetry


@dataclass
class ContractionExpansionThresholds:
    """Thresholds for contraction-expansion interpretation."""
    IMBALANCE_RATIO: float = 1.2  # Ratio above which signals show imbalance
    # If contractions > expansions * IMBALANCE_RATIO, signal is contraction-heavy
    # If expansions > contractions * IMBALANCE_RATIO, signal is expansion-heavy


class FeatureThresholds:
    """Centralized access to all feature thresholds.

    Usage:
        thresholds = FeatureThresholds()
        if plv > thresholds.sync.HIGH:
            print("High synchronization detected")
    """

    def __init__(self):
        self.sync = SynchronizationThresholds()
        self.smoothness = SmoothnessThresholds()
        self.equilibrium = EquilibriumThresholds()
        self.symmetry = SymmetryThresholds()
        self.contraction_expansion = ContractionExpansionThresholds()
