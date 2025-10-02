# Bilateral Symmetry Analysis Module

Bilateral symmetry assessment is crucial for understanding movement disorders, rehabilitation progress, and motor control strategies.
The module analyzes coordination patterns providing multiple complementary methods:

- **Canonical Correlation Analysis (CCA)**: multivariate correlation between left-right trajectories.
- **Phase Synchronization**: temporal coordination using Hilbert transform.
- **Coefficient of Variation**: statistical symmetry indices.
- **Cross-Correlation**: temporal alignment analysis.

!!! note
     These methods assume noise is Gaussian.

## Algorithms Details

### Canonical Correlation Analysis (CCA)

CCA finds the relationship between two sets of multivariate variables.  
It works by creating linear combinations of the variables in each set that are maximally correlated with each other.
The resulting correlation coefficients indicate the strength of the relationship between the derived variables,
revealing complex patterns that are not apparent from individual variables correlations.

!!! note
      CCA assumes linear relationships between two multivariate datasets.

**Input:**  
- Left trajectory \( X \in \mathbb{R}^{n \times p} \)  
- Right trajectory \( Y \in \mathbb{R}^{n \times q} \)  

**Procedure:**  
1. **Preprocessing:**  
   Center each column of \(X, Y\) to zero mean and normalize to unit variance.  
2. **SVD decomposition:**  
   Solve

$$
\rho = \max_{a, b} \, \text{corr}(Xa, Yb)
$$  

   where \(a \in \mathbb{R}^p, b \in \mathbb{R}^q\).  
3. **Canonical variates:**  
   
$$
U = Xa, \quad V = Yb
$$  

4. **Output:** First canonical correlation coefficient  
   
$$
\rho_1 \in [0,1]
$$  

!!! tip "Interpretation"
      CCA ranges between 0 (no correlation) and 1 (perfect correlation):

      - 1.0 - 0.8: excellent bilateral coordination;
      - 0.8 - 0.6: good coordination;
      - 0.6 - 0.4: moderate coordination;
      - <0.4: poor coordination.

---

## Phase Synchronization (Analytic Signal Approach)
Phase synchronization quantifies temporal relationship between two signals by analysing the constancy of their phase difference.  
Signals are considered synchronized if their phase difference remains locked in a consistent manner over time, regardless of amplitude variations.

!!! note
      Phase analysis assumes stationarity over the analysis window.

**Input:**  
- Two signals \( x(t), y(t) \)  

**Procedure:**  
1. Compute analytic signals via Hilbert transform:  
   
$$
z_x(t) = x(t) + i \, H[x(t)], \quad z_y(t) = y(t) + i \, H[y(t)]
$$  

2. Extract instantaneous phases:  

$$
\phi_x(t) = \arg(z_x(t)), \quad \phi_y(t) = \arg(z_y(t))
$$

3. Phase difference:  

$$
\Delta \phi(t) = \phi_x(t) - \phi_y(t)
$$

4. Phase locking value (PLV):  

$$
\text{PLV} = \left| \frac{1}{N} \sum_{t=1}^N e^{i \Delta \phi(t)} \right|
$$  

**Output:** \( \text{PLV} \in [0,1] \)

!!! tip "Interpretation" 
      PLV ranges from 0 (no synchronization) to 1 (perfect synchronization):
      
      - \>0.7: strong phase coupling;
      - 0.4-0.7: moderate coupling;
      - <0.4: pour coupling.

---

## Coefficient of Variation Symmetry (CVS)

**Input:**  
- Left trajectory \( x \), right trajectory \( y \)  

**Procedure:**  
1. Compute coefficient of variation (CV):  
   
$$
CV_x = \frac{\sigma(x)}{\mu(x)}, \quad CV_y = \frac{\sigma(y)}{\mu(y)}
$$  

2. Ratio:  
 
$$
r = \frac{CV_x}{CV_y}
$$  

3. Symmetry index:  
   
$$
SI = \min(r, 1/r)
$$  

**Output:** \( SI \in (0,1] \)

!!! tip "Interpretation"
      SI ranges from 0 (high asymmetry) to 1 (perfect symmetry):
      
      - 1.0: perfect asymmetry;
      - \>0.8: good symmetry;
      - 0.6-0.8: moderate asymmetry;
      - <0.6: high asymmetry (low symmetry).

---

## Cross-Correlation Analysis (with Lag Compensation)

**Input:**  
- Left signal \( x(t) \), right signal \( y(t) \)  

**Procedure:**  
1. Normalized cross-correlation:  
   
$$
R_{xy}(\tau) = \frac{\sum_t (x(t)-\bar{x})(y(t+\tau)-\bar{y})}{\sigma_x \sigma_y}
$$  

   for \(\tau \in [-\tau_{\max}, \tau_{\max}]\).  

2. Maximum correlation and lag:  
 
$$
\rho_{\max} = \max_\tau R_{xy}(\tau), \quad \tau^* = \arg\max_\tau R_{xy}(\tau)
$$  

**Output:** \((\rho_{\max}, \tau^*)\) --> temporal coordination strength and time offset.  

---

### Gait Symmetry Analysis

```python
# Analyze walking symmetry
left_heel = extract_marker_trajectory('LEFT_HEEL', mocap_data)
right_heel = extract_marker_trajectory('RIGHT_HEEL', mocap_data)

gait_symmetry = symmetry_analyzer.calculate_symmetry_index(
    left_heel, right_heel
)

# Assess gait quality
if gait_symmetry['cca_correlation'] > 0.8:
    print("High bilateral coordination")
elif gait_symmetry['cca_correlation'] < 0.5:
    print("Potential coordination deficit")
```

### Real-Time Monitoring

```python
# Stream-based symmetry monitoring
symmetry_analyzer = BilateralSymmetryAnalyzer(window_size=50)

for frame in motion_stream:
    left_data = frame['left_markers']
    right_data = frame['right_markers']
    
    current_metrics = symmetry_analyzer.analyze_real_time(
        left_data, right_data
    )
    
    # Monitor symmetry changes
    if current_metrics['cca_correlation'] < threshold:
        trigger_alert("Asymmetry detected")
```

 ## Research Foundation

Implementation based on:

1. **Bilateral Motion Data Fusion** (2018)
   - PubMed ID: 29993408
   - CCA methodology for bilateral coordination
   - Multi-dimensional trajectory analysis

2. **Wheelchair Propulsion Symmetry** (2022)
   - MDPI Symmetry Journal
   - Coefficient of variation approach
   - Real-world validation studies

3. **Phase Synchronization Methods**
   - Hilbert transform applications
   - Phase locking value calculations
   - Neurophysiological coordination studies

## References

To be added