# Module Documentation

At the moment, PyEyesWeb provides four core modules for movement analysis. Each module addresses specific aspects of movement quantification with research-validated methods.

## Core Modules Overview

| Module | Primary Function | Output Metrics |
|--------|------------------|----------------|
| [Smoothness](smoothness.md) | Movement fluidity analysis | SPARC, Jerk RMS, filtered signals |
| [Bilateral Symmetry](bilateral_symmetry.md) | Left-right coordination | Symmetry indices, phase coherence |
| [Contraction/Expansion](contraction_expansion.md) | Spatial dynamics | Area/volume rates, geometric patterns |
| [Synchronization](synchronization.md) | Multi-participant coordination | Cross-correlation, phase alignment |

## Module Architecture

Each module follows consistent design patterns for:
- Input processing
- Computational methods
- Output generation


## Performance Considerations

- **Memory efficiency**: Sliding window implementations for streaming data
- **Computational optimization**: Numba JIT compilation for critical paths
- **Scalability**: Configurable window sizes and processing parameters

While we are wprking on this, each module documentation will include:
- Theoretical background and citations
- Parameter selection guidelines
- Interpretation of output metrics
- Common use cases in movement research