# Lightness Analysis Module

## Overview
The Lightness module quantifies the perception of gravity-defying or "visually light" movement by evaluating the rarity of Vertical Kinetic Energy across a temporal phase. 

## Theoretical Interpretation
- **Input Requirements**: Requires a pre-derived window of velocity vectors.
- **Value Interpretation**: 
    - **High Lightness**: Implies the subject is moving in a way that minimizes gravitational effort relative to their overall total energy, or that their vertical effort profile is highly atypical (rare) compared to their recent baseline. It conceptually bridges Laban's notion of "Lightness".
    - **Low Lightness**: Represents heavy, gravity-bound, or continuously predictable movement with dominant vertical exertion.

## Algorithm Details & Mathematics
Lightness is derived sequentially by constructing a 1D effort index from 3D kinetic energy, and passing it through a Rarity analyzer.

1. **Vertical Weight Index**:
For every frame $t$ in the window, the algorithm isolates the vertical component of the kinetic energy, $E_{vertical, t}$ (typically the Y-axis energy), against the total kinetic energy, $E_{total, t}$. The relative vertical effort ratio is:

$$ 
W_t = \frac{E_{vertical, t}}{E_{total, t}} 
$$

2. **Weight Inversion**: 
To map from "Heaviness" (high vertical effort) to "Lightness", the metric is inverted:

$$ 
\bar{W}_t = 1.0 - W_t 
$$

This array $\{\bar{W}_t\}$ serves as our temporal stream of lightness measurements.

3. **Rarity Extraction**:
The final single scalar metric $L$ is calculated by computing the exact **Rarity** of this inverted weight distribution within its own sliding window:

$$ 
L = Rarity(\{\bar{W}_t\}) 
$$

## References

### TODO
