# PyEyesWeb Examples

This directory contains example scripts and demonstrations showcasing the capabilities of PyEyesWeb modules.

## Structure

- **`test_scripts/`** - Python scripts demonstrating various analysis modules
- **`touchdesigner/`** - TouchDesigner integration examples and demos

## Test Scripts

### Movement Analysis Examples

- **`bilateral_symmetry.py`** - Demonstrates bilateral symmetry analysis with realistic human gait simulation
- **`contraction_expansion.py`** - Shows contraction and expansion analysis for movement data
- **`equilibrium.py`** - Demonstrates equilibrium analysis with elliptical balance evaluation
- **`smoothness.py`** - Examples of smoothness analysis for movement trajectories
- **`synchronization.py`** - Synchronization analysis using webcam and MediaPipe pose detection

### Data Processing

- **`tsv_reader.py`** - Example of reading and processing TSV (Tab-Separated Values) files

## TouchDesigner Integration

The `touchdesigner/` folder contains:
- TouchDesigner project files (`.toe`)
- Setup scripts for Windows environment

## Running the Examples

Each Python script can be run independently:

```bash
python examples/test_scripts/bilateral_symmetry.py
python examples/test_scripts/synchronization.py
# etc...
```

## Requirements

- Python 3.x
- PyEyesWeb package installed
- Additional dependencies as specified in each script (e.g., OpenCV, MediaPipe for synchronization example)

## Notes

These examples are designed to demonstrate the functionality of various PyEyesWeb modules. They include:
- Realistic data simulation
- Interactive visualizations
- Real-time processing capabilities
- Integration with external tools