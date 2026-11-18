# Physical signals

Layer 1 of the conceptual model ({doc}`../theory/framework`) holds the signals that come from sensors and the virtual sensors
built on them. In PyEyesWeb a feature of this layer takes raw frames or a model and gives a signal again, so that the features
of the upper layers can work on cleaner or richer data: it extracts centroids or parts from an image, or locates points
in a grid. Its timescale is the frame: a value belongs to one call, not to a window. This page helps to choose
among the {{ n_physical_signals }} features of the layer; the layers are described in {doc}`../concepts/layers`.

```{feature-table} physical_signals
```

## Which feature for which problem

The features fall in two groups, one for each kind of input.

**You have video and want the body without a skeleton.** The silhouette of a person is a binary mask.

- {py:class}`~pyeyesweb.physical_signals.SilhouetteCentroids` for 14 points of a body (centre of gravity, head, shoulders,
  elbows, hands, knees, feet), cheap enough to follow at the frame rate of a camera.
- {py:class}`~pyeyesweb.physical_signals.SilhouetteBodyParts` for the bounding box and the mask of six parts (head, trunk, arms,
  legs), when you want to analyse a part of the image, not a point.
- {py:class}`~pyeyesweb.physical_signals.Videogram` to summarise a long video in one image in which a movement is a visible
  trace, for inspection or for a visual feature of the movement over time.

Theory: {doc}`../theory/imaging`. The outline of a silhouette is measured by the contour features of layer 2.

**You have positions in a plane and want to know where they fall.** {py:class}`~pyeyesweb.physical_signals.HitCellDetector`
divides a rectangle into a grid and gives the cell of each point. Its theory is in {doc}`../theory/shape_symmetry_balance`.

## A typical pipeline

The pipeline of the layer goes from an image to the measures of an outline: a mask, then
{py:class}`~pyeyesweb.physical_signals.SilhouetteCentroids` or the contour of the mask, then the contour features of
{doc}`low_level`.

## What to know before choosing

- The features of this layer do not wait for data: every valid call is `OK`, with no warm-up (see {doc}`../concepts/results`).
- The image features and `HitCellDetector` have no time axis: a value belongs to one call.
- Image features take 8-bit images or masks and return pixel coordinates (see {doc}`../concepts/inputs`).

Hands-on: see {ref}`sphx_glr_tutorials_02_physical_signals_plot_03_points.py` (points) and {ref}`sphx_glr_tutorials_02_physical_signals_plot_04_images.py` (images).
