# Suddenness Analysis Module

## Overview
The Suddenness module identifies temporally abrupt, highly accelerated movement spikes. It evaluates whether a sequence of movement represents a 'sudden' phase mathematically by modeling its velocity distribution as a heavy-tailed stable distribution.

## Theoretical Interpretation
- **Input Requirements**: An array of static positional coordinates over a temporal window. The algorithm natively computes sequential velocities.
- **Value Interpretation**: Returns a boolean classification `is_sudden`, indicating whether a sudden spike was detected. It also returns the underlying distribution parameters ($\alpha$, $\beta$, $\gamma$) which can be monitored continuously for nuanced distribution thickness analysis.

!!! note "Stable Distributions"
    Movements characterized by sudden starts and stops defy standard Gaussian assumptions, instead exhibiting velocity density functions with thick asymmetric tails. 

## Algorithm Details & Mathematics
1. **Velocity Extraction**:
Computes instantaneous velocity magnitudes $v_t$ across adjacent positional frames $X_t$:

$$ 
v_t = \|X_{t+1} - X_t\| 
$$

2. **Stable Distribution Fitting**:
The sequence of velocities $\{v_t\}$ is fitted to a statistical $\alpha$-stable distribution using McCulloch's quantile-based table interpolation. The fit yields three primary parameters:

    - $\alpha \in (0, 2]$: The stability index (tail thickness). $\alpha = 2$ indicates a standard Normal (Gaussian) distribution, whereas $\alpha \to 0$ indicates a deeply heavy-tailed distribution matching sudden, jerky motion.
    - $\beta \in [-1, 1]$: The skewness parameter, tracking the directional bias of the motion anomalies.
    - $\gamma > 0$: The generalized scale parameter (analogous to standard deviation).

3. **Classification Inequality**:
The window is aggressively classified as containing a "sudden" movement if the parameters cross a specific threshold mathematically separating thick-tailed distributions from normalized ones:

$$ 
\gamma \cdot \left(1.0 - \frac{\alpha}{2.0}\right) \cdot \beta \ge 0 
$$

## References
*McCulloch, J.H., 1986. Simple consistent estimators of stable distribution parameters. Communications in Statistics-Simulation and Computation.*
