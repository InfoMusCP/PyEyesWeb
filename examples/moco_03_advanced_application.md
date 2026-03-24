# Notebook 3: Advanced Feature Mastery & Interpretation

> [!NOTE]
> **Educational Material**: PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> *   Understand **Feature Specificity**: When algorithms fail or produce edge cases.
> *   Compare Fluidity models: *SPARC* vs. *Jerk RMS*.
> *   Build advanced pipelines combining `low_level` and `mid_level` features to interpret artistic intention.

So far, we understand how PyEyesWeb processes live data (`SlidingWindow`, `__call__`) and the theory behind what we measure (`low_level`, `mid_level`, `analysis_primitives`).

Now, it is time to practice. In expressive movement analysis, a generic algorithm will often give you terrible results if you do not understand its **specificity**.

---

## 1. Feature Specificity: The Problem with Jerk

Let's look at one of the most requested features in biomechanics: **Smoothness (Fluidity)**.

Historically, smoothness was frequently calculated by taking the third derivative of position over time, known as **Jerk**. The higher the Jerk, the less smooth the movement.

PyEyesWeb allows you to extract this:
```python
from pyeyesweb.low_level import Smoothness
jerk_feature = Smoothness(metrics=["jerk_rms"])
```

### The Edge Case (Why Jerk fails)
However, Jerk RMS has a massive mathematical flaw in real-world application: It is highly dependent on *amplitude* and *duration*.
If a dancer performs the exact same movement pattern, but does it twice as fast, the mathematical Jerk skyrockets. Is the movement technically "less smooth", or is it just faster?

If you use Jerk RMS to compare a slow, sweeping arm motion to a fast, percussive arm motion, the algorithm will mathematically guarantee that the fast motion is rough and rigid, which completely misinterprets the artistic quality of a fast, but perfectly fluid motion.

### The Solution: SPARC (Spectral Arc Length)
To solve this, PyEyesWeb implements **SPARC** (Spectral Arc Length) as its default smoothness metric.

SPARC mathematically isolates the *quality* of the movement from its speed and amplitude. It transforms the velocity profile into the frequency domain (using a Fourier Transform) and measures the arc length of the spectrum. 

*   A perfectly smooth, bell-shaped velocity profile will have a fixed, highly negative SPARC value (e.g., `-1.5`).
*   A jittery movement with constant sub-movements will have a highly negative SPARC value (e.g., `-5.0`).
*   **Crucially**: Doing the smooth movement faster/bigger does not alter the SPARC value.

```python
# Utilizing the superior algorithm for expressive analysis
sparc_feature = Smoothness(metrics=["sparc"])
# Now speed will not corrupt our smoothness data!
```

---

## 2. Assembling a Complex Analytical Pipeline

Let's build a real pipeline that extracts meaning from performance. We want to correlate **Kinetic Energy Burst** (objective physics) with **Smoothness Breakdown** (expressive quality) and **Direction Change** (spatial trajectory).

```python
import numpy as np
from tqdm.auto import tqdm
from utils.data_loader import load_motion_data
from utils.plot_utils import plot_feature_timeseries
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.low_level import KineticEnergy, Smoothness, DirectionChange

# 1. Loading the trajectory file
pos_tensor, vel_tensor, _, names = load_motion_data("data/trial0001_impulsive.tsv")
hand_idx = names.index("HAND_RIGHT")

N_frames = pos_tensor.shape[0]

# 2. Architecting the Windows
window_static_vel = SlidingWindow(max_length=1, n_signals=1, n_dims=3)     # Energy Needs
window_dynamic_traj = SlidingWindow(max_length=60, n_signals=1, n_dims=3)  # Direction Needs
window_dynamic_speed = SlidingWindow(max_length=60, n_signals=1, n_dims=1) # Smoothness Needs 1D speed

# 3. Initializing the Extractors
energy_ext = KineticEnergy()
sparc_ext = Smoothness(metrics=["sparc"])
dir_ext = DirectionChange(metrics=["polygon"])

# 4. Storage
log_energy = []
log_sparc = []
log_direction = []

# 5. The Real-time loop
for t in tqdm(range(N_frames), desc="Analyzing Expression"):
    
    # Isolate Right Hand kinematics
    hand_pos_3d = pos_tensor[t, hand_idx:hand_idx+1, :]
    hand_vel_3d = vel_tensor[t, hand_idx:hand_idx+1, :]
    hand_speed_1d = np.linalg.norm(hand_vel_3d)

    # Push to memory
    window_static_vel.append(hand_vel_3d)
    window_dynamic_traj.append(hand_pos_3d)
    window_dynamic_speed.append(hand_speed_1d)

    # Extract once historical memory is populated
    if window_dynamic_traj.is_full:
        # Objective Physics
        log_energy.append(energy_ext(window_static_vel).total_energy)
        
        # Spatial Geometry
        log_direction.append(dir_ext(window_dynamic_traj).polygon)
        
        # Expressive Quality
        log_sparc.append(sparc_ext(window_dynamic_speed).sparc)

# Convert for analysis
log_energy = np.array(log_energy)
log_direction = np.array(log_direction)
log_sparc = np.array(log_sparc)
```

---

## 3. Interpretation & Visualization

If we plot these three signals:
```python
time_axis = np.arange(len(log_energy)) / 100.0 # 100 FPS
plot_feature_timeseries(
    time_axis, 
    log_energy, 
    log_sparc, 
    log_direction,
    feature_names=["Energy Burst", "Smoothness (SPARC)", "Direction Chaos (Polygon)"],
    title="Comprehensive Expressive Pipeline"
)
```

### How to read the Data
1.  **The Impulsive Strike**: You might see a massive spike in *Kinetic Energy*.
2.  **The Trajectory Break**: Accompanying that energy spike, the *Direction Chaos* spikes immediately after, indicating the hand changed direction violently, rather than following through smoothly (like a whip crack instead of a golf swing).
3.  **The Quality Breakdown**: Simultaneously, the *SPARC* value plummets (becomes far more negative), confirming that the motor control of the limb completely lost fluidity during the strike.

By combining `low_level` physics with `mid_level` expressive qualities, you transition from simply measuring a body to interpreting a behavior. 

You are now ready to build real-time expressive pipelines!
