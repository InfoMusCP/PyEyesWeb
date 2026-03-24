# Notebook 2: The Theoretical Framework (What We Measure)

> [!NOTE]
> **Educational Material**: PyEyesWeb Erasmus+ Project & MOCO Scientific Workshop
>
> **Learning Objectives**:
> *   Understand the philosophical architecture of PyEyesWeb.
> *   Explore the difference between biological truth (`low_level`) and human expression (`mid_level`).
> *   Learn how to apply domain-agnostic `analysis_primitives` to human data streams.

In Notebook 1, we learned *how* the PyEyesWeb system consumes and statefully processes data over time using `SlidingWindow`. 

Now, we must step back and ask: **What are we actually measuring?**

When we look at a dancer, a musician, or an athlete, we see highly complex, expressive behavior. However, motion capture systems (like OptiTrack, Qualisys, or Kinect) only give us raw arrays of `(X, Y, Z)` coordinates. The gap between raw coordinates and "artistic expression" is massive. 

PyEyesWeb bridges this gap using a strict, three-tier architectural hierarchy separated into Python subpackages.

---

## 1. The `low_level` Subpackage: The Objective Truth
The `low_level` subpackage is strictly concerned with **biological and biomechanical reality**. It does not care about intention, emotion, or expression. It only evaluates the exact physical state of the body in space and time.

We subdivide this into two main categories:

### A. Spatial Geometry (The Shape of the Body)
These metrics evaluate static properties at a single frozen moment in time (Static Features). They ask: *How is this human mass distributed right now?*
*   **Contraction Index**: Compares the body's actual volume to its bounding limits.
*   **Points Density**: Measures how tightly packed the body's joints are relative to the center of mass.
*   **Bilateral Symmetry**: Measures the geometric mirroring of the left and right sides of the body.

### B. Raw Kinematics (The Physics of Motion)
These metrics evaluate purely physical derivatives of movement. 
*   **Kinetic Energy**: The total $E_k = \frac{1}{2}mv^2$ of the system.
*   **Impulse**: Sudden changes in momentum.

```python
from pyeyesweb.low_level import KineticEnergy, BoundingBoxFilledArea

# The system makes no assumptions about "why" the person is moving this way. 
# It only calculates the rigid physical truth.
energy = KineticEnergy()
contraction = BoundingBoxFilledArea()
```

---

## 2. The `mid_level` Subpackage: The Expressive Quality
The `mid_level` subpackage is fundamentally different. It steps away from strict physics and enters the realm of **perception, behavior, and intent**. It is heavily inspired by Laban Movement Analysis (LMA) and the qualitative aspects of motor control.

These features evaluate *how* a movement is performed, rather than just the physical energy it holds. Because these behaviors exist over time, they are almost exclusively **Dynamic Features** requiring a historical trajectory.

*   **Smoothness**: Does the movement flow continuously, or is it jittery and erratic? (We quantify this using advanced signal properties like SPARC, rather than just biological jerk).
*   **Direction Change**: Is the bodily trajectory direct and focused, or indirect, carving through space sporadically? 
*   **Rhythmicity**: Is there a periodic, musical tempo to the limb's movement?

```python
from pyeyesweb.low_level import Smoothness, DirectionChange
# Note: In the current architecture, some highly robust mid-level concepts like 
# Smoothness and Direction are housed in low_level due to their mathematical 
# foundational reliance on kinematics, but conceptually they describe quality, not raw physics!

smoothness_evaluator = Smoothness(rate_hz=100.0) 
direction_evaluator = DirectionChange()
```
*Crucial understanding: A machine can have high Kinetic Energy, but "Smoothness" implies a biological nervous system attempting fluid motor control.*

---

## 3. The `analysis_primitives` Subpackage: The Universal Tools
Not all analysis is inherently biological. Sometimes, we just want to interrogate abstract math on the data streams. 

The `analysis_primitives` subpackage contains **domain-agnostic statistical tools**. These tools know absolutely nothing about "humans" or "movement". They simply act upon data arrays to extract universal metrics.

*   **Volatility**: Evaluates the standard deviation/variance of a signal window.
*   **Probability / Rarity**: Is this specific posture (geometry) or velocity highly unusual compared to the last 10 minutes of the performance?
*   **Signal Synchronization**: Are the Right Hand and the Left Foot moving in phase with each other? (Cross-correlation/DTW).

You apply these primitives directly targeting other features!

```python
# A conceptual pipeline demonstrating the power of Primitives
"""
1. We extract the instantaneous raw Kinetic Energy (low_level)
   -> `energy_val = energy_feature(window_vel)`

2. We push that `energy_val` into a new 1D SlidingWindow

3. We ask a Primitive: "Is the current energy level extremely rare 
   compared to the historical energy data we've seen?"
   -> `rarity_score = probability_feature(window_energy_history)`
"""
```

By separating `low_level` physics, `mid_level` expression, and abstract `analysis_primitives`, PyEyesWeb allows researchers to endlessly stack and assemble bespoke analytical pipelines.

In Notebook 3, we will move into **Advanced Application**, looking at specific mathematical implementations (like SPARC vs Jerk) and how to interpret these graphs visually.
