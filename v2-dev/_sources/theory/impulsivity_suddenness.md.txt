# Impulsivity and suddenness

An impulsive movement is one that starts abruptly and without preparation, like a flick of the hand or a strike; a sudden
movement is one whose speed changes in bursts, a quick start and stop in the middle of calm. Both are mid-level qualities
of movement in the conceptual model ({doc}`framework`): they describe a movement unit of about a second, not one frame, and
they have been studied as qualities that observers perceive and that interactive systems can recognise
{cite}`mazzarino2009need,niewiadomski2015impulsive,niewiadomski2019embodied`.

The family has three features. {py:class}`~pyeyesweb.mid_level.Suddenness` classifies the distribution of the speed of a
trajectory over a window. {py:class}`~pyeyesweb.mid_level.SuddennessImpulsivity` combines the suddenness with the sharpness of
a turn of the path to give an impulsivity index of the trajectory. {py:class}`~pyeyesweb.mid_level.ContractionImpulsivity`
takes another route: it detects short energetic gestures from the quantity of motion of the whole body and measures how fast
the body contracts or expands during them. The symbols are those of {doc}`notation`.

## Suddenness

### Definition

The speed of a point between two consecutive samples is $v_t = \lVert \mathbf{p}_{t+1} - \mathbf{p}_t \rVert$. A movement
made of sudden starts and stops does not have a Gaussian distribution of speed: most of the time the point is slow or at rest,
and now and then it is very fast, so the distribution has a heavy tail. The $\alpha$-stable distributions are the family
that has the Gaussian as one member and describes heavy-tailed and skewed distributions in general. They are parametrised by

- $\alpha \in (0, 2]$, the **stability** index, which sets the thickness of the tails: $\alpha = 2$ is the Gaussian and a
  smaller $\alpha$ gives heavier tails;
- $\beta$, the **skewness**, positive for a heavier tail on the side of large values;
- $\gamma$, the **scale**, a positive number of the order of the spread of the distribution.

{py:class}`~pyeyesweb.mid_level.Suddenness` fits these parameters to the speeds of a window by McCulloch's quantile method. With $x_5, x_{25}, x_{50}, x_{75}, x_{95}$ the quantiles of the speeds of the window,

$$
\nu_\alpha = \frac{x_{95} - x_5}{x_{75} - x_{25}}, \qquad
\nu_\beta = \frac{x_{95} + x_5 - 2 x_{50}}{x_{95} - x_5}, \qquad
\gamma = \frac{x_{75} - x_{25}}{x_{75} - x_{50}},
$$

and $\alpha$ and $\beta$ are obtained from $\nu_\alpha$ and $\nu_\beta$ by interpolation in McCulloch's tables. The window is
classified as **sudden** when

$$
\gamma \left(1 - \frac{\alpha}{2}\right) \beta \ge 0 ,
$$

which, since $\gamma$ is positive and $\alpha \le 2$, means a non-negative skewness $\beta$, or a Gaussian ($\alpha = 2$). In
words: the movement is sudden when the speeds are mostly low with occasional bursts, so that the tail is on the side of the
large values, and it is not sudden when the speeds are mostly high with occasional stops, a negative skew. A Gaussian
distribution has no tail to speak of: a window whose speeds are all equal, a point at rest or at constant speed, gives the
Gaussian fallback ($\alpha = 2$, $\beta = 0$, $\gamma = 0$) and is classified as sudden.

The speeds are differences between consecutive samples, so timestamps do not enter the computation, and $\gamma$ is a
ratio of quantile differences, so it is dimensionless.

### The feature

`Suddenness` takes one position per call, the point of a trajectory in two or three dimensions (a frame with several
markers is rejected: average the markers beforehand if one trajectory is wanted). It keeps `window` positions (at least 6,
because five speeds are needed) and computes every `hop`. Its outputs are `is_sudden` (boolean), `alpha`, `beta` and
`gamma`. The parameter `method` selects the fit: `"constrained"` (the default) restricts $\nu_\alpha$ and $\nu_\beta$ to the
range of McCulloch's tables and always gives a result; `"quantile"` uses the unrestricted values and linear percentiles, and
gives `INVALID_INPUT`, with no outputs, when the window is outside the range of the tables. The status is `WARMING_UP`
until the first window is full and `NO_OUTPUT` between windows.

Two trajectories of 20 steps along a line illustrate the classification. The first is slow, with two bursts; the second is
fast and steady, with three brief stops:

```{doctest}
>>> from pyeyesweb.mid_level import Suddenness, SuddennessImpulsivity
>>> rng = np.random.default_rng(0)
>>> n = 20
>>> def corner(speeds, turn=True):
...     """A path that moves along x for half of the steps and then along y (or keeps going along x)."""
...     steps = np.zeros((n, 2))
...     steps[: n // 2, 0] = speeds[: n // 2]
...     steps[n // 2:, 1 if turn else 0] = speeds[n // 2:]
...     return np.vstack([[0.0, 0.0], np.cumsum(steps, axis=0)])
>>> slow = 0.01 + 0.003 * rng.random(n)
>>> bursts = slow.copy()
>>> bursts[[3, 4, 13]] = [0.3, 0.25, 0.3]                              # three fast steps in a slow movement
>>> steady = 0.1 + 0.003 * rng.random(n)
>>> steady[[3, 9, 15]] = 0.003                                          # three brief stops in a fast one
>>> for name, speeds in [("bursts", bursts), ("steady with stops", steady)]:
...     last = Suddenness(window=21, dims=2).run(corner(speeds))[-1]
...     print(f"{name:18s} sudden={bool(last.is_sudden)}  alpha={last.alpha:.2f}  beta={last.beta:.2f}")
bursts             sudden=True  alpha=0.52  beta=1.24
steady with stops  sudden=False  alpha=0.52  beta=-1.19
```

Both have the same low $\alpha$, that is heavy tails, and the sign of the skewness separates them.

## Impulsivity from the trajectory

An impulsive movement is not only sudden in time: it also changes direction sharply, like the stroke of a hammer that stops
and returns. {py:class}`~pyeyesweb.mid_level.SuddennessImpulsivity` captures this as the product of a spatial and a temporal
term over a window of one trajectory {cite}`mazzarino2009need,niewiadomski2015impulsive`,

$$
I = D \cdot \mathbf{1}[\text{sudden}],
$$

where $\mathbf{1}[\text{sudden}]$ is the classification of `Suddenness` on the speeds of the window and $D \in [0, 1]$ is the
direction change, computed from the first, the middle (index $N // 2$) and the last position of the window, $\mathbf{p}_0$,
$\mathbf{p}_m$ and $\mathbf{p}_{N-1}$. With $\theta$ the angle between $\mathbf{p}_m - \mathbf{p}_0$ and
$\mathbf{p}_{N-1} - \mathbf{p}_m$ (0 for a straight path, $\pi$ for a reversal) and $a = 1 - \theta / \pi$,

$$
D = \begin{cases} 1 - \lvert a - 0.5 \rvert / \varepsilon & \lvert a - 0.5 \rvert < \varepsilon, \\
0 & \text{otherwise,} \end{cases}
$$

so that $D$ is 1 for a right-angle turn and falls to 0 for a straight path or a reversal, with the default
$\varepsilon = 0.5$ (`direction_change_epsilon`); a smaller $\varepsilon$ keeps only the turns close to a right angle. This is
the cosine measure of {py:class}`~pyeyesweb.low_level.DirectionChange`, described in {doc}`kinematics_energy`. Either factor
being zero makes the index zero: a sharp corner traced slowly and evenly is not sudden, and a sudden movement along a straight
line does not turn. The output `impulsivity_index` is dimensionless, in $[0, 1]$. Both terms are evaluated on the same single
trajectory. Corrected in the core: the original block took the direction change of the mean of all the signals and the
suddenness of the first signal only.

The inputs, parameters and statuses are those of `Suddenness` (`window` of at least 6, `hop`, `dims`, `method`). With the
paths of the example above:

```{doctest}
>>> def impulsivity(path):
...     return round(float(SuddennessImpulsivity(window=21, dims=2).run(path)[-1].impulsivity_index), 2)
>>> impulsivity(corner(bursts)), impulsivity(corner(bursts, turn=False)), impulsivity(corner(steady))
(1.0, 0.0, 0.0)
```

The bursts that turn at a right angle give the largest value. The same bursts along a straight line give 0, because
there is no turn, and the steady movement with stops gives 0 because it is not sudden.

## Impulsivity from the body: the contraction index

The second approach uses the whole body instead of one trajectory. It needs two signals that other software supplies
and that are normalised to $[0, 1]$: the **quantity of motion**, how much the body moves in a frame, and the **contraction
index**, how contracted or expanded the posture is (high when the limbs are close to the body). A gesture is a run of frames
with the quantity of motion above `motion_threshold` (0.01 by default), closed by the first frame at or below it. It is
impulsive when it lasts at most `gesture_duration` frames (25 by default) and its peak quantity of motion reaches
`peak_threshold` (0.02). On the frame that closes an impulsive gesture,
{py:class}`~pyeyesweb.mid_level.ContractionImpulsivity` gives the range of the contraction index over the gesture divided by
its duration,

$$
I = \frac{\max_t CI_t - \min_t CI_t}{T / f_s},
$$

where $CI_t$ is the contraction index, $T$ the number of frames from the start of the gesture to the closing frame, inclusive,
and $f_s$ the `sampling_rate`. It is the rate, per second, at which the body contracts or expands during the gesture, and it
is not negative; without a sampling rate it is per frame. On every other frame both outputs, `impulsivity_index` and
`gesture_duration` (the length of the gesture, in frames), are 0. A pair of inputs outside $[0, 1]$ is ignored and gives
zeros. The status is `OK` for every sample and `INVALID_INPUT` for a timestamp that does not increase.

In the example a short energetic gesture of five frames contracts the body from 0.5 to 0.8 and back. It is closed on the
sixth frame, and the index is the range 0.3 over $5 / 25 = 0.2$ s, that is 1.5 per second:

```{doctest}
>>> from pyeyesweb.mid_level import ContractionImpulsivity
>>> quantity_of_motion = [0, 0.05, 0.2, 0.3, 0.1, 0, 0]
>>> contraction_index = [0.5, 0.5, 0.6, 0.8, 0.7, 0.5, 0.5]
>>> record = ContractionImpulsivity(sampling_rate=25.0).run(quantity_of_motion, contraction_index)
>>> record.impulsivity_index.round(2), record.gesture_duration
(array([0. , 0. , 0. , 0. , 0. , 1.5, 0. ]), array([0., 0., 0., 0., 0., 5., 0.]))
```

A gesture that goes on for more than `gesture_duration` frames, however energetic, is not impulsive, and the index stays
at 0.

## How to read the outputs

| Feature | Output | Unit | Range |
|---|---|---|---|
| `Suddenness` | `is_sudden` | none | boolean |
| | `alpha` | none | $(0, 2]$; 2 is Gaussian |
| | `beta` | none | skewness; non-negative when sudden |
| | `gamma` | none | 0 or more |
| `SuddennessImpulsivity` | `impulsivity_index` | none | $[0, 1]$; 0 when not sudden |
| `ContractionImpulsivity` | `impulsivity_index` | 1/s (1/frame without a rate) | 0 or more |
| | `gesture_duration` | frames | 0 except on the closing frame |

`ContractionImpulsivity` has a value only on the frame that closes an impulsive gesture, and the stream is zero between
gestures. For a time series
of the impulsivity of a performance, take the maximum over a stretch or the number of non-zero values.

## Practical notes

- **Window length.** The window of the two trajectory features holds one movement: the quantiles of the speeds, and the
  first, the middle and the last position, only make sense on a unit. With 21 positions at 50 Hz the window is 0.4 s. A
  window that holds several turns takes only the turn between the first, middle and last position.
- **Hop.** With a hop of 1 the classification is renewed at every sample; a hop of the length of the window gives one
  value per window, with `NO_OUTPUT` between them.
- **Noise.** The speed is a difference of positions, and noise in the position changes its distribution. A trajectory with
  jitter should be smoothed beforehand ({doc}`kinematics_energy`).
- **Rest.** A window at rest or at constant speed is classified as sudden by the Gaussian fallback, but its direction change
  is 0, so its impulsivity is 0 (status `OK`). Use the energy or the motion duration
  ({doc}`gesture_segmentation`) to ignore stillness.
- **Several markers.** Both trajectory features take one point. Average the markers of a body, or choose one, before the
  call.

## Further reading

The two motion qualities of impulsivity and smoothness: {cite}`mazzarino2009need`. Automated detection of
impulsive movements: {cite}`niewiadomski2015impulsive`. Mid-level qualities and their sonification: {cite}`niewiadomski2019embodied`.
