# Statistical Moments Analysis Module

## Overview
The Statistical Moment module provides real-time computation of foundational descriptive statistics over sliding windows of motion signals. It quantifies the shape, spread, and central tendency of continuous movement patterns.

## Theoretical Interpretation
- **Input Requirements**: Evaluates a temporal sequence (window) of $N$-dimensional data points. Computations are performed independently over every dimension or feature provided.
- **Value Interpretation**:
    - **Mean ($\mu$)**: The central baseline or average persistent posture/velocity of the limb across the window.
    - **Standard Deviation ($\sigma$)**: The magnitude of the movement span. High variance denotes expansive, reaching, or highly varied effort. Low variance denotes rigidity or stillness around the mean.
    - **Skewness ($\gamma_1$)**: The asymmetry of the movement. A positive skew denotes sudden forward thrusts with slow returns; negative skew denotes slow builds with sudden snaps back to resting.
    - **Kurtosis ($\gamma_2$)**: The presence of extreme outliers or heavy tails. High kurtosis marks sudden, jerky, erratic anomalies within an otherwise regular pattern.

## Algorithm Details & Mathematics
The module isolates each one-dimensional signal array $X = \{x_1, \dots, x_N\}$ of length $N$ inside the current window block, and continuously computes the requested moments.

### 1. Mean
The arithmetic average defining the center point:

$$ \mu = \frac{1}{N} \sum_{i=1}^{N} x_i $$

### 2. Standard Deviation
The sample standard deviation (using $N-1$ degrees of freedom to correct for sample size bias), representing typical dispersal distance from the mean:

$$ s = \sqrt{\frac{1}{N-1} \sum_{i=1}^{N} (x_i - \mu)^2}  $$

### 3. Skewness
The unadjusted Fisher-Pearson coefficient of skewness, tracking symmetrical distribution:

$$ \gamma_1 = \frac{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^3}{\left(\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2\right)^{3/2}} $$

### 4. Kurtosis
Fisher's definition of excess kurtosis (subtracting 3), tracking the fatness of the tails relative to a Normal distribution:

$$ \gamma_2 = \frac{\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^4}{\left(\frac{1}{N} \sum_{i=1}^{N} (x_i - \mu)^2\right)^2} - 3.0 $$
