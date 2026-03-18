# Synchronization Analysis Module

The **Synchronization Module** quantifies temporal coordination between multiple participants, body segments, or movement components.  
It provides methods to assess how well different movement signals align in **time** and **phase**.

!!! note
     The method assumes stationarity over the analysis window and Gaussian noise.

## Algorithms Details

### Phase Coupling Analysis

Phase synchronization measures temporal alignment independent of amplitude:

1. **Hilbert Transform**: Compute analytic signals  

$$
z_x(t) = x(t) + i H[x(t)], \quad z_y(t) = y(t) + i H[y(t)]
$$

2. **Instantaneous Phases**:

$$
\phi_x(t) = \arg(z_x(t)), \quad \phi_y(t) = \arg(z_y(t))
$$

3. **Phase Difference**:

$$
\Delta \phi(t) = \phi_x(t) - \phi_y(t)
$$

4. **Phase Locking Value (PLV)**:

$$
\text{PLV} = \left| \frac{1}{N} \sum_{t=1}^{N} e^{i \Delta \phi(t)} \right|
$$

**Output:** \( \text{PLV} \in [0,1] \)

!!! tip "Interpretation"
    - \( PLV > 0.7 \): strong phase coupling
    - \( 0.4 < PLV \leq 0.7 \): moderate phase coupling
    - \( PLV \leq 0.4 \): weak phase coupling 

## References

To be added