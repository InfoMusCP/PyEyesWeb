# Notation, units and conventions

The theory pages use one notation throughout. This page lists it, with the units of the quantities, the way windows and hops
are counted, and the vocabulary of the status of a result. The rules that the code follows for time and units are in
{doc}`../concepts/time_units_parameters`, and the statuses in {doc}`../concepts/results`; this page states what the symbols
of the equations stand for.

## Symbols

| Symbol | Meaning | Unit |
|---|---|---|
| $n$ | sample index, $n = 0, 1, 2, \dots$ | none |
| $t$ | time | s |
| $f_s$ | sampling rate; the `sampling_rate` parameter | Hz |
| $\Delta t = 1/f_s$ | time step between two samples | s |
| $N$ | window length, in samples; the `window` parameter | samples |
| $H$ | hop, in samples; the `hop` parameter | samples |
| $d$ | number of coordinates of a position (1, 2 or 3) | none |
| $\mathbf{p}(t) \in \mathbb{R}^d$ | position of a point (a joint, a marker, the centre of mass) | length |
| $\mathbf{v} = \dot{\mathbf{p}}$ | velocity | length/s |
| $v = \lVert \mathbf{v} \rVert$ | speed | length/s |
| $\mathbf{a} = \dot{\mathbf{v}}$ | acceleration | length/s$^2$ |
| $\mathbf{j} = \dot{\mathbf{a}}$ | jerk | length/s$^3$ |
| $k = 1, \dots, K$ | index of a joint, of $K$ joints | none |
| $w_k$ | weight (approximate mass) of joint $k$ | dimensionless, or a mass |
| $x_i(n)$, $i = 1, \dots, M$ | the $M$ scalar signals given to a feature, such as the channels of a recording | as given |

A dot over a symbol is the derivative with respect to time in seconds. The position of joint $k$ is written
$\mathbf{p}_k(t)$ and its speed $v_k$. A discrete signal is the continuous one sampled at $t = n \, \Delta t$, so that
$\mathbf{p}(n)$ means $\mathbf{p}(n \, \Delta t)$. Where an equation uses a symbol that is not in the table, it is defined
next to the equation.

Derivatives of a sampled position are estimates, not exact values. The features that need them either take them from the
caller (the speed given to {py:class}`~pyeyesweb.low_level.SpectralArcLength`) or compute them from a polynomial fit to the
newest samples ({py:class}`~pyeyesweb.low_level.Kinematics`); the page of each family says which.

## Units

Time is always in seconds and lengths are in metres, unless a feature was given `units="mm"`, in which case the data and the
outputs are in millimetres and thresholds that are lengths are still written in metres. The unit of an output is a string
written in terms of the data: `<length>` for the unit of length of the data, and compounds such as `<length>/s` and
`<length>^2/s^2`. A dimensionless quantity has no unit. The theory pages write units in the text after a value, for example
a speed of $1.26\ \mathrm{m/s}$.

Angles are in radians in the equations, and in degrees only where an output is declared in degrees (its `unit` says `deg`).
Normalised quantities (a ratio, a correlation, an index in $[0, 1]$) are dimensionless.

## Windows and hops

A feature that works on a recent stretch of a signal keeps a **window** of $N$ samples, and computes a value every $H$
samples. Both are counted in samples, not in seconds; the duration of a window is $T = N / f_s$ seconds. The window ends at
the newest sample, so the value belongs to the last $N$ samples, and nothing is computed from samples that have not arrived.
With $H = 1$ (the default) a value is computed at every sample from the first full window on; with $H = N$ the windows do
not overlap.

For a recording of $L$ samples, the number of windows that are complete is

$$
\left\lfloor \frac{L - N}{H} \right\rfloor + 1 \qquad (L \ge N),
$$

and no value is produced before the first $N$ samples have arrived. For a recording of 30 samples, a window of 10 and a hop
of 5, that gives 5 values:

```{doctest}
>>> from pyeyesweb.low_level import SpectralArcLength
>>> speed = np.abs(np.sin(np.linspace(0.0, 6.0, 30))) + 0.5
>>> recording = SpectralArcLength(window=10, hop=5, sampling_rate=100.0).run(speed)
>>> int((recording.status == 0).sum()), (30 - 10) // 5 + 1
(5, 5)
```

Choosing $N$ is choosing the time span of a value: a short window follows the movement closely and is noisy, a long one is
stable and slow to react. Two windows of the same length and parameters give values that can be compared; a window that
contains less than one movement, or several, answers a different question. Each theory page says what a window should hold
for the quantity it describes.

## Status vocabulary

Every call of a feature returns a result with a status. The theory pages use these four words with the same meaning.

| Status | Meaning in the text |
|---|---|
| `OK` | the call produced a value |
| `WARMING_UP` | a window is still filling: fewer than $N$ samples have arrived since the start or the last reset, and the value is not yet defined |
| `NO_OUTPUT` | the feature emits a value only on some calls (between two windows when $H > 1$, or only when an event ends), and this call was not one of them |
| `INVALID_INPUT` | the call is not data: a NaN or infinite value, an empty frame, a time that does not increase; the outputs are empty and the `reason` says what is wrong |

A status other than `OK` is not an error and is not raised: it is part of the result, so that a stream can be processed
without interruption and a recording can be stored with one row per sample. A quantity that is not defined for the data it
is given (the smoothness of a movement that does not move, for example) is reported as `INVALID_INPUT`, not as a number.
