# PyEyesWeb Feature Testing CLI

**Purpose**: This CLI tool is a **playground for exploration**. It's designed to help you quickly understand how PyEyesWeb features work by testing them with synthetic signals. This is NOT meant for production testing or scientific validation. It is simply a hands on way to get familiar with the framework's capabilities.

Command line tool for testing PyEyesWeb features with synthetic signals.

## Quick Start

```bash
# Show all available commands and options
python tests/feature_test_cli.py --help

# List all features
python tests/feature_test_cli.py list-features

# List all available signal types
python tests/feature_test_cli.py list-signals
```

## Basic Usage

```bash
python tests/feature_test_cli.py <feature> --signal <signal_type> [options]
```

## Available Features

- **smoothness** - Analyze signal smoothness (SPARC, jerk metrics)
- **bilateral-symmetry** - Left-right symmetry analysis
- **equilibrium** - Balance and stability evaluation
- **synchronization** - Multi-signal phase locking
- **contraction-expansion** - Area expansion/contraction tracking

## Common Examples

### Test Smoothness
```bash
# Basic smoothness test with sine wave
python tests/feature_test_cli.py smoothness --signal sine --length 1000

# Compare two signals (smooth vs noisy)
python tests/feature_test_cli.py smoothness --signal sine --signal2 random --length 1000

# Save results with timestamp
python tests/feature_test_cli.py smoothness --signal sine --save-results smoothness_test.json
```

### Test Synchronization
```bash
# Test phase locking between two signals
python tests/feature_test_cli.py synchronization --signal sine --freq 10

# Test with chirp signals
python tests/feature_test_cli.py synchronization --signal chirp --freq-start 1 --freq-end 50
```

### Test Bilateral Symmetry
```bash
# Single signal (compares left/right from same signal)
python tests/feature_test_cli.py bilateral-symmetry --signal sine

# Two different signals (stroke patient simulation)
python tests/feature_test_cli.py bilateral-symmetry --signal sine --signal2 random
```

### Test Equilibrium
```bash
# Analyze balance/stability
python tests/feature_test_cli.py equilibrium --signal gaussian --std 1.5 --drift 0.01
```

### Test Contraction-Expansion
```bash
# Analyze expansion patterns
python tests/feature_test_cli.py contraction-expansion --signal square --freq 5
```

## Output Files

Results are automatically saved to the `output/` directory with timestamps:

```bash
# Specify filename (timestamp added automatically)
python tests/feature_test_cli.py smoothness --signal sine --save-results mytest.json
# Creates: output/20251008_181335_mytest.json

# Files are sorted chronologically (newest first)
ls -lt output/
```

## Signal Types

Use `list-signals` to see all 38+ available signal types organized by category:
- Basic Waveforms (sine, cosine, square, triangle, sawtooth)
- Noise Signals (random, gaussian, pink, brownian)
- Chirp Signals (chirp, exponential_chirp, hyperbolic_chirp)
- Modulated (am, fm, pm, tremor, ecg, emg)
- And more...

```bash
python tests/feature_test_cli.py list-signals
```

## Advanced Options

```bash
# Set signal parameters
--length 1000              # Signal length (samples)
--freq 10.0                # Frequency (Hz)
--amplitude 1.0            # Signal amplitude
--phase 0.0                # Phase offset
--sampling-rate 100.0      # Sampling rate (Hz)

# Add noise/modulation
--noise-level 0.1          # Noise level
--std 1.5                  # Standard deviation
--drift 0.01               # Drift amount

# Chirp parameters
--freq-start 1.0           # Start frequency
--freq-end 50.0            # End frequency

# Biological signals
--heart-rate 80            # Heart rate (for ECG)

# Output control
--quiet                    # Minimal output
--save-results file.json   # Save with timestamp
--seed 42                  # Random seed for reproducibility
```

## When to Use One Signal vs Two Signals

### Smoothness

**One Signal (`--signal`)**: Test how smooth a single movement is. Example: Analyzing a patient's arm movement to detect tremor or jerkiness.

**Two Signals (`--signal` + `--signal2`)**: Compare smoothness between two different movements. Example: Testing if a patient's left arm (sine wave = smooth) moves more smoothly than their right arm (random = jerky), indicating a potential stroke.

```bash
# One signal: test if movement is smooth
python tests/feature_test_cli.py smoothness --signal sine

# Two signals: compare smooth vs jerky (stroke simulation)
python tests/feature_test_cli.py smoothness --signal sine --signal2 random
```

### Bilateral Symmetry

**One Signal (`--signal`)**: Analyze symmetry within a single signal by comparing left/right halves. Example: Checking if a person's gait has symmetrical left-right stepping patterns.

**Two Signals (`--signal` + `--signal2`)**: Compare symmetry between two separate signals representing left and right sides. Example: Testing if left arm movement (sine = healthy) is symmetrical to right arm movement (random = impaired), detecting asymmetry after injury.

```bash
# One signal: check internal left-right symmetry
python tests/feature_test_cli.py bilateral-symmetry --signal sine

# Two signals: compare left vs right movement (injury simulation)
python tests/feature_test_cli.py bilateral-symmetry --signal sine --signal2 random
```

### Synchronization

**One Signal (`--signal`)**: Generate two slightly phase-shifted versions of the same signal to test phase locking. Example: Testing if two brain regions stay synchronized during a task.

**Two Signals (`--signal` + `--signal2`)**: Test synchronization between two completely different signals. Example: Checking if breathing (slow sine) synchronizes with heart rate (fast ECG), which happens during meditation.

```bash
# One signal: test phase locking with automatic phase shift
python tests/feature_test_cli.py synchronization --signal sine --freq 10

# Two signals: test if different rhythms synchronize (breathing vs heartbeat)
python tests/feature_test_cli.py synchronization --signal sine --freq 0.3 --signal2 ecg --heart-rate 80
```

### Equilibrium

**One Signal (`--signal`)**: Analyze balance stability from a single center-of-mass signal. Example: Testing how much a person sways while standing still on one foot.

**Two Signals (`--signal` + `--signal2`)**: Compare stability between two different balance conditions. Example: Testing if a person sways more with eyes closed (high noise) vs eyes open (low noise).

```bash
# One signal: test balance stability
python tests/feature_test_cli.py equilibrium --signal gaussian --std 0.5

# Two signals: compare eyes open vs eyes closed stability
python tests/feature_test_cli.py equilibrium --signal gaussian --std 0.5 --signal2 gaussian --std 2.0
```

### Contraction-Expansion

**One Signal (`--signal`)**: Measure how body area expands and contracts over time. Example: Analyzing breathing patterns to detect if someone breathes smoothly or irregularly.

**Two Signals (`--signal` + `--signal2`)**: Compare contraction patterns between two conditions. Example: Testing if breathing is smooth during rest (sine) vs irregular during anxiety (noisy signal).

```bash
# One signal: analyze breathing pattern
python tests/feature_test_cli.py contraction-expansion --signal sine --freq 0.3

# Two signals: compare calm vs anxious breathing
python tests/feature_test_cli.py contraction-expansion --signal sine --freq 0.3 --signal2 gaussian
```

## Reproducibility

Set a random seed for consistent results:

```bash
python tests/feature_test_cli.py smoothness --signal random --seed 42
```

## Tips

1. **Start Simple** - Use basic signals (sine, cosine) to understand features
2. **List First** - Always check `list-signals` and `list-features`
3. **Save Results** - Use `--save-results` to track experiments
4. **Use Seeds** - Add `--seed` for reproducible random signals
5. **Compare Signals** - Use `--signal2` to simulate real-world scenarios

## Output Format

JSON results include:
- Feature-specific metrics
- Metadata (timestamp, parameters, elapsed time)
- Signal configuration

Example output structure:
```json
{
  "sparc": -2.456,
  "jerk_rms": 0.123,
  "metadata": {
    "feature": "smoothness",
    "signal_type": "sine",
    "timestamp": "2025-10-08T18:13:35",
    "elapsed_time": 0.045,
    "parameters": {...}
  }
}
```

---

# Testing Framework

## Project Structure

```
tests/
├── feature_test_cli.py       # Main CLI tool
├── conftest.py                # Pytest fixtures & helpers
├── test_helpers/              # Reusable utilities
│   ├── cli_formatting.py      # Colors & formatting
│   ├── thresholds.py          # Threshold values
│   └── base_tester.py         # Base tester class
└── unit/
    └── test_complete.py       # Unit tests (50 tests)
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/unit/test_complete.py -v

# Run quietly
python -m pytest tests/unit/test_complete.py -q

# Run specific test class
python -m pytest tests/unit/test_complete.py::TestSynchronizationTester -v

# Run specific test
python -m pytest tests/unit/test_complete.py::TestSynchronizationTester::test_basic_sync_test -v
```

## Writing Tests

We will be using fixtures from `conftest.py` instead of creating test files manually:

```python
def test_example(sync_tester):
    """Test synchronization."""
    result = sync_tester.test('sine', length=100, freq=1.0)
    assert_valid_result(result, ['plv', 'phase_status'])
    assert result['plv'] > 0.5
```

Available fixtures:
- `sync_tester` - SynchronizationTester
- `smoothness_tester` - SmoothnessTester
- `symmetry_tester` - BilateralSymmetryTester
- `equilibrium_tester` - EquilibriumTester
- `contraction_tester` - ContractionExpansionTester

Helper function `assert_valid_result(result, expected_keys)` validates results contain expected keys.

## Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("signal_type", ['sine', 'square', 'triangle'])
def test_multiple_signals(sync_tester, signal_type):
    result = sync_tester.test(signal_type, length=100)
    assert_valid_result(result, ['plv'])
```

## Thresholds

Threshold values are in `test_helpers/thresholds.py`:

```python
from tests.test_helpers import FeatureThresholds

thresholds = FeatureThresholds()
thresholds.sync.HIGH                    # 0.8
thresholds.smoothness.VERY_SMOOTH       # -1.6
thresholds.equilibrium.HIGH_STABILITY   # 0.9
thresholds.symmetry.HIGH_SYMMETRY       # 0.95
```

Edit that file to change threshold values globally.

## Troubleshooting

**Import errors**: Install package in editable mode
```bash
pip install -e .
```

**Fixtures not found**: Verify conftest.py location
```bash
python -m pytest tests/ --collect-only
```

**Slow tests**: Use quiet mode
```bash
python -m pytest tests/unit/test_complete.py -q --tb=line
```