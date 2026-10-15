# Shape, symmetry and balance

How a body occupies space is one of the oldest descriptors of expressive movement. A posture can be contracted or
expanded, symmetric or lopsided, balanced over its feet or about to lose balance, and a performer can use the whole stage or
stay in one corner. The features of this family describe one instant of a posture (or of a position on the floor) with a
single dimensionless number, and the last three describe how space is used over time. They are computed frame by frame,
keep no memory (except the space-occupation potentials) and need no sampling rate.

Notation is that of {doc}`notation`: a posture is a set of $K$ points $\mathbf{p}_k\in\mathbb{R}^d$, with $d=3$ for body
joints and $d=2$ for floor positions. Lengths are in the unit of the data; every index below is dimensionless unless stated.

| Question | Quantity | Feature |
|---|---|---|
| How much of its bounding box does the body fill? | contraction index | {py:class}`~pyeyesweb.low_level.BoundingBoxFilledArea` |
| How round is the body cloud? | sphericity, axis ratio | {py:class}`~pyeyesweb.low_level.EllipsoidSphericity` |
| How spread are the joints around their centre? | points density | {py:class}`~pyeyesweb.low_level.PointsDensity` |
| Are left and right joints mirror images? | symmetry index or score | {py:class}`~pyeyesweb.low_level.Symmetry` |
| Is the head centred over the shoulders? | triangle symmetry | {py:class}`~pyeyesweb.low_level.TriangleSymmetry` |
| Is the barycenter over the support between the feet? | equilibrium | {py:class}`~pyeyesweb.low_level.Equilibrium` |
| Which floor cells are occupied, and how often? | hit cells, potentials | {py:class}`~pyeyesweb.physical_signals.HitCellDetector`, {py:class}`~pyeyesweb.mid_level.PositionDependingPotentials`, {py:class}`~pyeyesweb.mid_level.RegionDependingPotentials` |

## Contraction and expansion

Contraction and expansion of the body are among the cues that observers use to read the emotional quality of a movement:
an expanded posture occupies more space around the body, a contracted one less {cite}`camurri2003recognizing,glowinski2011minimal`.
The library offers three complementary measures of the same idea, each computed from the $K\ge4$ points of one frame.

### Convex hull over bounding box

The bounding box of the posture is the axis-aligned box with extents $\Delta_x,\Delta_y,\Delta_z$ along the three axes, and
the convex hull is the smallest convex polyhedron that contains the points. The contraction index is the ratio of their
surface areas,

$$
I = \frac{A_{\mathrm{hull}}}{A_{\mathrm{box}}}, \qquad A_{\mathrm{box}} = 2\,(\Delta_x\Delta_y + \Delta_x\Delta_z + \Delta_y\Delta_z),
$$

with $0\le I\le1$. The index is 1 when the points fill the box (its eight corners) and smaller when the body is thin or
diagonal inside its box. It is independent of the unit of the data.
{py:class}`~pyeyesweb.low_level.BoundingBoxFilledArea` implements it. A frame whose hull is degenerate (fewer than four
points, coplanar or collinear points) or whose box has negligible area has no index and returns the status
`INVALID_INPUT`; the output is then empty.

### Sphericity of the fitted ellipsoid

The point cloud is summarised by the ellipsoid whose radii $a\ge b\ge c$ are the square roots of the eigenvalues of the
sample covariance matrix of the points (a principal component analysis, so the orientation of the body does not matter).
{py:class}`~pyeyesweb.low_level.EllipsoidSphericity` reports the radii, the axis ratio $c/a$ and the Wadell sphericity

$$
\Psi = \frac{\pi^{1/3}(6V)^{2/3}}{A}, \qquad V=\tfrac43\pi abc,
$$

the ratio between the surface of the sphere that has the volume of the ellipsoid and the surface $A$ of the ellipsoid (the
feature uses Knud Thomsen's approximation of $A$). $\Psi=1$ for a sphere and decreases towards 0 as the ellipsoid is
stretched or flattened. A body stretched along one axis (arms up) and a body flattened in one plane (lying down) both have a
low sphericity, which separates them from a compact, roundish posture. The method `process_axes` computes the sphericity
directly from three given axis lengths.

### Dispersion around the centroid

{py:class}`~pyeyesweb.low_level.PointsDensity` measures how far the points lie from their centroid $\mathbf{c}$ (the mean, or
the per-axis median). With $d_k=\lVert\mathbf{p}_k-\mathbf{c}\rVert$,

$$
D = \operatorname{agg}_k\, d_k, \qquad \operatorname{agg}\in\{\text{mean},\text{median},\max,\textstyle\sum\},
$$

or, per axis, the aggregate of $\lvert p_{k,i}-c_i\rvert$ (one value for each of the three axes). Unlike the two indices
above, $D$ has the unit of the data: it grows with the body size, so compare it across participants only after
normalising (for example by the height). The feature also returns the centroid.

```{doctest}
>>> from pyeyesweb.low_level import BoundingBoxFilledArea, EllipsoidSphericity, PointsDensity
>>> rng = np.random.default_rng(3)
>>> expanded = rng.uniform(-0.8, 0.8, size=(15, 3))      # joints spread over a 1.6 m cube
>>> contracted = 0.3 * expanded                          # the same posture, folded to 30 percent
>>> stretched = expanded * [0.2, 0.2, 1.0]               # a tall, thin posture
>>> for name, frame in [("expanded", expanded), ("contracted", contracted), ("stretched", stretched)]:
...     index = BoundingBoxFilledArea().process(frame).contraction_index
...     sphericity = EllipsoidSphericity().process(frame).sphericity
...     density = PointsDensity().process(frame).density
...     print(f"{name:10s} index={index:.2f} sphericity={sphericity:.2f} density={density:.2f}")
expanded   index=0.44 sphericity=0.95 density=0.70
contracted index=0.44 sphericity=0.95 density=0.21
stretched  index=0.44 sphericity=0.78 density=0.30
```

Folding the posture to 30 percent leaves the contraction index and the sphericity unchanged (they are dimensionless and
scale-free) and scales the density with the size. The two indices answer different questions: the tall, thin posture has
the same hull-to-box ratio as the expanded one here, and it is the sphericity (0.78 against 0.95) that tells it apart.
The contraction index separates postures of different shape inside their box, not postures of different size; to follow how
much space the body takes, use the density or the extents themselves.

## Symmetry

### Left and right: ratio index and mirror score

A posture is bilaterally symmetric when the left half is the mirror image of the right half across the sagittal plane.
{py:class}`~pyeyesweb.low_level.Symmetry` takes couples of joints that mirror each other (left and right hand, left and
right foot, ...) and offers two formulas, selected by `method` {cite}`glowinski2011minimal`. The $x$ axis is the lateral axis.

With `method="ratio"` (the default, the EyesWeb index) the coordinates are taken relative to a reference joint (the neck by
default), and for each couple and each axis $k$ the values of the left and right joint $L_k,R_k$ give

$$
s_k = \frac{\min(\lvert L_k\rvert,\lvert R_k\rvert)}{\max(\lvert L_k\rvert,\lvert R_k\rvert)}
$$

when the sign condition holds (the joints lie on opposite sides of the reference along $x$ and on the same side along $y$
and $z$), and $s_k=0$ otherwise. The values are aggregated over couples and axes (mean by default) into one number, or over
the couples for each axis into three numbers (`output_dims="components"`). By default each joint is first divided by its
distance to the reference, so only its direction counts. One sentence of correction: in the core the normalisation distance is
measured from the reference joint, not from the coordinates before the translation.

With `method="reflection"` the right joint $R$ of each pair is reflected across the first axis, $R''=(-R_x,R_y,R_z)$, with
$L,R$ relative to a centre $C$ (a chosen joint, by default the barycenter of the frame), and the score of the pair is

$$
s = \max\!\left(0,\;1-\frac{\lVert L-R''\rVert}{\lVert L\rVert+\lVert R\rVert}\right),
$$

which is 1 for a perfect mirror image. The result is one score per pair, labelled `<left>_<right>`. Use `"ratio"` for the
EyesWeb index of a labelled skeleton with a single summary value, and `"reflection"` for a per-pair score about a body centre.

### Head over the shoulders

{py:class}`~pyeyesweb.low_level.TriangleSymmetry` measures the lateral lean of the upper body. The head (the apex) and the
two shoulders form a triangle; the base is split by the vertical line through the apex, and the two halves, mirrored on top
of each other, are compared. The index is 1 when they coincide and decreases as their areas differ, down to 0 (also when both
shoulders lie on the same side of the head). It is a posture measure, the tilt of the apex over the base, not a test that the
triangle is isosceles. The three vertices are $(x,y)$ points with $y$ growing downwards (image coordinates).

```{doctest}
>>> from pyeyesweb.low_level import Symmetry, TriangleSymmetry
>>> labels = ["neck", "left_hand", "right_hand"]
>>> pairs = [("left_hand", "right_hand")]
>>> frame = np.array([[0.0, 0.0, 0.0], [-0.5, -0.3, 0.1], [0.8, -0.1, 0.2]])
>>> Symmetry(labels, pairs=pairs, reference_point="neck").process(frame).symmetry
0.6056630888033111
>>> Symmetry(labels, pairs=pairs, method="reflection", reference_point="neck").process(frame).pair_symmetry
array([0.73692362])
>>> triangle = TriangleSymmetry()
>>> [round(float(triangle.process((0, 0), (-1, 1), (x, 1)).symmetry), 2) for x in (1, 2, 3)]
[1.0, 0.5, 0.33]
```

## Balance

{py:class}`~pyeyesweb.low_level.Equilibrium` estimates the postural balance from one snapshot of the floor plane
{cite}`ghisio2015exergames`. The support region is an ellipse centred midway between the left foot $P_L$ and the right
foot $P_R$, with its major axis along the line through the feet. With $d=\lVert P_R-P_L\rVert$, a margin $m$ that accounts
for the size of the foot and a weight $w_y$ for the depth of the stance, the semi-axes are

$$
a = \frac d2 + m, \qquad b = m\,w_y .
$$

Let $(x',y')$ be the barycenter relative to the centre of the ellipse, rotated so that the first axis runs from the left to
the right foot, and $q=(x'/a)^2+(y'/b)^2$. Then

$$
E = \begin{cases} 1-\sqrt q & q\le1\\ 0 & q>1 \end{cases}
$$

so that $E=1$ when the barycenter is at the centre of the support and falls linearly to 0 at the border of the ellipse and
outside it. The `angle` output is the direction of the foot-to-foot vector in degrees. The three inputs are $(x,y)$ points on
the floor plane: the caller computes the barycenter and projects onto the floor (for Y-up data, take the columns $[0,2]$).
The default margin is 0.1 m; pass `units="mm"` for data in millimetres. When the two feet coincide there is no support vector
and the status is `INVALID_INPUT`.

```{doctest}
>>> from pyeyesweb.low_level import Equilibrium
>>> equilibrium = Equilibrium(margin=0.1)
>>> left, right = (-0.1, 0.0), (0.1, 0.0)
>>> [round(float(equilibrium.process(left, right, (x, 0.0)).equilibrium), 2) for x in (0.0, 0.05, 0.1, 0.2)]
[1.0, 0.75, 0.5, 0.0]
```

## Use of space

The three remaining features describe where on the floor a performer is, and how often.
{py:class}`~pyeyesweb.physical_signals.HitCellDetector` divides a rectangular area
$[x_{\min},x_{\max}]\times[y_{\min},y_{\max}]$ into `cells_along_y` rows and `cells_along_x` columns and returns, for each
$(x,y)$ point, the cell $(i,j)$ (row from $y$, column from $x$) that contains it, counted from 0. Points outside the area are
clipped to the border cells unless `clip_values=False`, in which case the call is `INVALID_INPUT`.

The hit cells feed {py:class}`~pyeyesweb.mid_level.PositionDependingPotentials`, which keeps one potential value per cell
and updates it at every call. With `potential_type="increment_decrement"` a hit cell gains `increment` and every other cell
loses `decrement`; with `"occupation_rates"` the value of a cell is the fraction of calls in which it was hit (optionally
over the last `window` calls); the `"polynomial"`, `"gaussian"` and `"logarithmic"` types have no memory and draw a field
centred on each hit cell. {py:class}`~pyeyesweb.mid_level.RegionDependingPotentials` does the same for regions, groups of
cells defined by a mask (for example the zones of a stage), with linear or exponential occupation rates. Both keep state:
`reset()` restores the initial potential. An empty list of hits has status `NO_OUTPUT` and does not update the potential.

```{doctest}
>>> from pyeyesweb.physical_signals import HitCellDetector
>>> from pyeyesweb.mid_level import PositionDependingPotentials
>>> detector = HitCellDetector(cells_along_x=4, cells_along_y=2)
>>> potentials = PositionDependingPotentials(cells_along_x=4, cells_along_y=2, potential_type="occupation_rates")
>>> path = [[0.1, 0.1], [0.1, 0.1], [0.4, 0.2], [0.9, 0.7]]       # a dancer who mostly stays on the left
>>> for point in path:
...     cells = detector.process([point]).cells
...     result = potentials.process(cells)
>>> result.potential
array([[50., 25.,  0.,  0.],
       [ 0.,  0.,  0., 25.]])
```

## Practical notes

- All frame features (`BoundingBoxFilledArea`, `EllipsoidSphericity`, `PointsDensity`, `Symmetry`, `TriangleSymmetry`,
  `Equilibrium`, `HitCellDetector`) are stateless: a call depends only on its frame, `hop` and `window` do not exist, and the
  `timestamp` is only copied to the result.
- Geometric quantities need the frame to be in one consistent frame of reference. Indices based on a hull or an ellipsoid
  need enough joints: use the whole skeleton rather than a handful of points.
- Missing joints are not interpolated: a dictionary frame that lacks a joint of a couple gives `INVALID_INPUT` with the
  names of the missing joints.
- Units are those of the data for `PointsDensity` and `Equilibrium` (margin) and for the radii of `EllipsoidSphericity`; all
  other outputs are dimensionless. See {doc}`../concepts/time_units_parameters`.

## Further reading

The contraction and symmetry cues come from the study of affective gestures {cite}`camurri2003recognizing,glowinski2011minimal`;
the equilibrium measure was introduced for an exergame platform {cite}`ghisio2015exergames`. For the output objects of the
features see {doc}`../concepts/results`.
