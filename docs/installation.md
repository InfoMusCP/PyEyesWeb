# Installation Guide

## Requirements

InfoMove requires Python 3.8+ and the following dependencies:

### Core Dependencies
- NumPy 1.24.1
- SciPy 1.15.0
- Numba ≥0.57.0

### Development Dependencies
- MediaPipe 0.10.21
- Build tools (setuptools, wheel)

## Installation Methods

### Standard Installation

```bash
git clone https://github.com/your-org/InfoMove.git
cd InfoMove
pip install -e .
```

### Development Installation

For contributors and researchers who need development tools:

```bash
git clone https://github.com/your-org/InfoMove.git
cd InfoMove
pip install -e .[dev]
```

### Virtual Environment Setup

Recommended for research environments:

```bash
python -m venv infomove-env
source infomove-env/bin/activate  # On Windows: infomove-env\Scripts\activate
pip install -e .
```

## Verification

Test your installation:

```python
import core
from core import Smoothness, BilateralSymmetryAnalyzer
print("InfoMove successfully installed")
```

## Common Issues

### Numba Installation
If Numba fails to install, try:
```bash
conda install numba
```

### MediaPipe Dependencies
MediaPipe requires additional system libraries. On Ubuntu:
```bash
sudo apt-get install libgl1-mesa-glx
```

## System-Specific Notes

### macOS
Ensure Xcode command line tools are installed:
```bash
xcode-select --install
```

### Windows
Visual Studio Build Tools may be required for NumPy/SciPy compilation.

### Linux
Standard development packages should be sufficient for most distributions.