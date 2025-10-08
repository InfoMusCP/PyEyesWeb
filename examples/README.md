# PyEyesWeb Examples

This directory contains example scripts demonstrating the capabilities of PyEyesWeb analysis features.

## Available Examples

### Movement Analysis

- **`smoothness.py`** - Movement smoothness analysis using SPARC and jerk metrics
- **`bilateral_symmetry.py`** - Left-right symmetry analysis for bilateral movements
- **`equilibrium.py`** - Balance and postural stability evaluation
- **`synchronization.py`** - Multi-signal synchronization and phase locking analysis
- **`contraction_expansion.py`** - Body area expansion and contraction tracking

### Data Processing

- **`tsv_reader.py`** - Example of reading and processing TSV (Tab-Separated Values) files

## Running the Examples

Each script can be run independently from the project root:

```bash
python examples/smoothness.py
python examples/bilateral_symmetry.py
python examples/synchronization.py
# etc...
```

## Requirements

- Python 3.x
- PyEyesWeb package installed
- Additional dependencies as specified in each script:
  - OpenCV and MediaPipe for webcam examples (`smoothness.py`, `synchronization.py`)
  - Matplotlib for visualization (`equilibrium.py`)

## Notes

These examples demonstrate PyEyesWeb functionality using:
- Real-time webcam processing (where applicable)
- Simulated movement data
- Interactive visualizations

For automated testing with synthetic signals, see `tests/feature_test_cli.py`.
