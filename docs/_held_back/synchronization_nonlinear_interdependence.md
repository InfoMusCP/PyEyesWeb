<!-- Sections cut from docs/theory/synchronization.md for the early release (2026-11-13). -->

## Two signals

Linear correlation (see the group matrix below) sees only relations of the form $y\approx ax+b$. The nonlinear
interdependence measure detects any
dependence in which the state of one signal determines the state of the other. Each signal is embedded in a state space of
dimension $m$ (`embedding_dimension`): the state at sample $n$ is a vector of $m$ delayed samples. For each state of the
first signal $X$, the $k$ nearest states in time (`neighbours`) are found, and the interdependence $S(X|Y)$ compares the
distances of these states in the space of $X$ with the distances of the states that have the same time indices in the space of
$Y$. It is close to 1 for two signals that determine each other (identical signals give 1) and close to 0 for independent
signals. The two directions $S(X|Y)$ and $S(Y|X)$ are generally different, and their asymmetry is read as the direction of the
coupling.

{py:class}`~pyeyesweb.analysis_primitives.NonlinearInterdependence` returns both values, `first_to_second_interdependence` and
`second_to_first_interdependence`, and `threshold`, the value $(k/m)^{2/m}$ that the block computes from its parameters. A
correction of the core is that this threshold used an exclusive-or instead of the power. The result is `INVALID_INPUT` when a
value is not finite.

```{doctest}
>>> from pyeyesweb.analysis_primitives.synchronization.events import NonlinearInterdependence
>>> rng = np.random.default_rng(5)
>>> x = rng.normal(size=100)
>>> dependent = NonlinearInterdependence(window=100, neighbours=3).run(x, x ** 3)             # a nonlinear function of x
>>> independent = NonlinearInterdependence(window=100, neighbours=3).run(x, rng.normal(size=100))
>>> round(float(dependent.first_to_second_interdependence[-1]), 2), round(float(independent.first_to_second_interdependence[-1]), 2)
(0.93, 0.01)
```

