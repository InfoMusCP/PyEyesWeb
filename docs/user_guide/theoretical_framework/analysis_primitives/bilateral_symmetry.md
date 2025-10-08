# Bilateral Symmetry Analysis Module

Bilateral symmetry assessment is crucial for understanding movement disorders, rehabilitation progress, and motor control strategies.  
This module analyzes coordination patterns using **three complementary methods**:

- **Bilateral Symmetry Index (BSI)** — spatial mirror-symmetry measure.
- **Phase Synchronization (PLV)** — temporal coordination of left–right movement.
- **Canonical Correlation Analysis (CCA)** — multivariate correlation of trajectories.

!!! note
    These methods assume approximately Gaussian noise and sufficient frame history.

---

## Bilateral Symmetry Index (BSI)

The **BSI** quantifies spatial symmetry between left and right trajectories by comparing mirrored movements across the sagittal plane.

**Input:**  
- Left and right 3D joint trajectories $$ L, R \in \mathbb{R}^{n \times 3} $$

**Procedure:**

1. **Mirror right trajectory** across sagittal plane:  

$$ 
R' = [-R_x, R_y, R_z] 
$$

<ol start="2">
<li>
<strong>Compute absolute difference:</strong>  
</li>
</ol>

$$
D = |L - R'| 
$$

<ol start="3">
<li>
<strong>Normalize by total magnitude:</strong>  
</li>
</ol>

$$ 
S = |L| + |R'| 
$$

<ol start="4">
<li>
<strong>Relative asymmetry percentage:</strong>  
</li>
</ol>

$$ 
A = \frac{1}{n} \sum_i \frac{D_i}{S_i} \times 100 
$$

<ol start="5">
<li>
<strong>Symmetry index:</strong>  
</li>
</ol>
 
$$ 
\text{BSI} = 1 - \frac{A}{100} 
$$

**Output:**  

$$ 
\text{BSI} \in [0, 1]
$$

!!! tip
    Higher BSI indicates more symmetric posture and movement.

---

## Phase Synchronization (Analytic Signal Approach)

Phase synchronization quantifies the temporal relationship between left and right signals by analysing the constancy of their phase difference.  
It is computed via **Hilbert transform** and expressed as **Phase Locking Value (PLV)**.

**Input:**  
Two 1D limb displacement signals $$ x(t), y(t) $$.

**Procedure:**

1. Compute analytic signals:  

$$ 
z_x(t) = x(t) + iH[x(t)],  
$$

$$
z_y(t) = y(t) + iH[y(t)] 
$$

<ol start="2">
<li>
<strong>Extract instantaneous phases:</strong>  
</li>
</ol>
  
$$ 
\phi_x(t), \phi_y(t) 
$$

<ol start="3">
<li>
<strong>Compute phase difference:</strong>  
</li>
</ol>

$$
\Delta \phi(t) = \phi_x(t) - \phi_y(t) 
$$

<ol start="4">
<li>
<strong>Compute Phase Locking Value (PLV):</strong>  
</li>
</ol>

$$
\text{PLV} = \left| \frac{1}{N} \sum_t e^{i \Delta \phi(t)} \right| 
$$

**Output:** 

$$
\text{PLV} \in [0, 1] 
$$

!!! tip
    PLV > 0.7 → strong coupling  
    PLV 0.4–0.7 → moderate  
    PLV < 0.4 → weak coupling

---

## Canonical Correlation Analysis (CCA)

CCA measures **multivariate correspondence** between left and right 3D trajectories.  
It finds linear combinations that maximize correlation, revealing shared coordination structure.

**Input:**  

$$
L, R \in \mathbb{R}^{n \times 3} 
$$

**Procedure:**

1. Flatten coordinates into features.  
2. Apply one-component CCA:  

$$
(U, V) = \text{CCA}(L, R) 
$$

<ol start="3">
<li>
<strong>Compute canonical correlation:</strong>  
</li>
</ol>

$$
\rho = \text{corr}(U, V) 
$$

**Output:** 

$$
\rho \in [0, 1] 
$$

!!! tip
    - 1.0–0.8: excellent coordination  
    - 0.8–0.6: good  
    - 0.6–0.4: moderate  
    - <0.4: poor