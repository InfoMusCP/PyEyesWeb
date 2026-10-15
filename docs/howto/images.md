# Work with images

Three features take an image: {py:class}`~pyeyesweb.physical_signals.SilhouetteCentroids` and
{py:class}`~pyeyesweb.physical_signals.SilhouetteBodyParts`, which describe the silhouette of a person, and
{py:class}`~pyeyesweb.physical_signals.Videogram`, which summarises a sequence of frames in one image. This page says what an
image must look like, how to prepare a silhouette from your own video, and what the results cost in memory. The definitions are in
{doc}`../theory/imaging`, and {ref}`sphx_glr_tutorials_02_physical_signals_plot_04_images.py` runs all three on synthetic
silhouettes.

## What an image is

An image is `InputKind.IMAGE`: one 8-bit array per call.

| Form | Meaning |
|---|---|
| `(H, W)` | grayscale image, or a mask |
| `(H, W, C)` | colour image (only `Videogram` accepts it: 1, 3 or 4 channels); the silhouette features take `(H, W)` |
| `bool` array | a mask: `False` is 0, `True` is 1 |
| `uint8` array | pixel values 0 to 255 |
| any other numeric dtype | accepted if every value is a whole number in 0 to 255 |

`run` takes `(T, H, W)` or `(T, H, W, C)`, or a list of images (which may be used to avoid stacking them), one image per frame.
Pixels are converted to 8 bits when they reach the core. A value outside the range, a fractional value, a wrong rank or a wrong number
of channels raises `ValueError` that names the feature and the input. An image with no pixel at all, and a mask with no foreground
pixel, are data problems and give `INVALID_INPUT`.

```{doctest}
>>> from pyeyesweb.physical_signals import SilhouetteBodyParts, SilhouetteCentroids, Videogram
>>> SilhouetteCentroids().inputs
Inputs(silhouette: image (?, ?) - mask of the body: every non-zero pixel is foreground)
>>> Videogram().inputs
Inputs(frame: image (?, ?, ?) - grayscale or colour frame)
>>> centroids = SilhouetteCentroids()
>>> centroids.process(np.full((8, 8), 300))
Traceback (most recent call last):
  ...
ValueError: SilhouetteCentroids: input 'silhouette' expects whole-number pixel values in 0-255, got int64 values from 300 to 300
>>> centroids.process(np.full((8, 8), 0.5))
Traceback (most recent call last):
  ...
ValueError: SilhouetteCentroids: input 'silhouette' expects whole-number pixel values in 0-255, got float64 values from 0.5 to 0.5
>>> centroids.process(np.zeros((4, 4, 2, 2)))
Traceback (most recent call last):
  ...
ValueError: SilhouetteCentroids: input 'silhouette' expects image of shape (any, any), got shape (4, 4, 2, 2)
>>> result = centroids.process(np.zeros((8, 8), dtype=bool))
>>> result.status.name, result.reason
('INVALID_INPUT', 'no foreground pixels in the silhouette')
```

## Silhouettes

A silhouette is a mask of the person: every non-zero pixel is body. The features cut the blob out of the frame themselves, so
coordinates come back in the pixels of the frame you gave: `x` counts from the left and `y` from the top, so `y` points down, and
"left" and "right" are those of the image (left is the smaller `x`).

How you obtain the mask is outside the library: background subtraction, a person-segmentation model, a threshold on a depth
image. Give the result as a `bool` array, or as an array of 0 and 255. The synthetic body below stands in for it.

```{doctest}
>>> rows, columns = np.mgrid[:240, :320]
>>> body = (columns - 160) ** 2 / 18 ** 2 + (rows - 40) ** 2 / 22 ** 2 <= 1                      # head
>>> body |= (abs(columns - 160) <= 28) & (rows >= 60) & (rows <= 140)                          # trunk
>>> body |= (abs(rows - 75) <= 7) & (columns >= 80) & (columns <= 240)                         # arms
>>> body |= (abs(columns - 147) <= 9) & (rows > 140) & (rows <= 225)                           # left leg
>>> body |= (abs(columns - 173 - (rows - 140) * 0.3) <= 9) & (rows > 140) & (rows <= 225)      # slanted right leg
>>> body.shape, body.dtype, round(float(body.mean()), 3)
((240, 320), dtype('bool'), 0.137)
>>> as_bytes = body.astype(np.uint8) * 255
>>> result = SilhouetteCentroids().process(as_bytes)
>>> result.status.name, result.centroids.shape, result.centroids[0].tolist()
('OK', (14, 2), [161.0, 114.0])
>>> bool(np.array_equal(SilhouetteCentroids().process(body).centroids, result.centroids, equal_nan=True))
True
```

`centroids` has one row `(x, y)` per centroid, 14 in all, in pixels; `normalized` has the same rows scaled to the frame. A centroid that
cannot be found is NaN. `parts=` chooses the centroids that are output (it is live); the others are NaN, and the shape does not
change.

```{doctest}
>>> head_only = SilhouetteCentroids(parts=["center_of_gravity", "head"]).process(body)
>>> head_only.centroids[:3].tolist()
[[161.0, 114.0], [159.0, 48.0], [nan, nan]]
```

{py:class}`~pyeyesweb.physical_signals.SilhouetteBodyParts` finds the rectangles of six parts (`right_leg`, `left_leg`, `trunk`,
`right_arm`, `left_arm`, `head`) and returns `regions` (one row `x, y, width, height` for each), `is_found`, and `masks`, a
dict with one integer mask per part:

```{doctest}
>>> parts = SilhouetteBodyParts().process(body)
>>> parts.regions[:2].tolist(), parts.is_found.tolist()
([[138, 136, 23, 90], [161, 136, 46, 90]], [True, True, True, True, True, True])
>>> {name: mask.shape for name, mask in list(parts.masks.items())[:2]}
{'right_leg': (90, 23), 'left_leg': (90, 46)}
```

## Videograms

A videogram reduces every frame to one line (the sum of each row, or of each column) and puts the lines side by side, so that a
movement becomes a visible trace; applied to a frame difference it is a motiongram. The output has the shape `(H, window, C)` for
`mode="horizontal"` (the default) and `(window, W, C)` for `"vertical"`, with `C = 1` for a grayscale input. The lines not written yet
are 0. A frame of another size than the first one restarts the image, and the `reason` says so.

```{doctest}
>>> videogram = Videogram(window=50)
>>> frames = [np.roll(body.astype(np.uint8) * 255, shift, axis=1) for shift in range(0, 30, 3)]
>>> recording = videogram.run(frames)
>>> recording
Recorder(Videogram, rows=10, columns=['videogram'], status={'OK': 10})
>>> recording[-1].videogram.shape, recording[-1].videogram.dtype
((240, 50, 1), dtype('int64'))
>>> Videogram(window=3).process(np.stack([body * 255] * 3, axis=-1).astype(np.uint8)).videogram.shape
(240, 3, 3)
>>> small = Videogram(window=3)
>>> _ = small.process(np.ones((4, 4), dtype=np.uint8))
>>> small.process(np.ones((5, 5), dtype=np.uint8)).reason
'frame size changed: videogram restarted'
```

## Images in a recorder

An image output is never a column of `to_numpy()` or `to_frame()`, which hold the fixed numeric outputs only. The image of each row is
read from the result of that row, or from `rec["videogram"]`, a list with one array per row.

```{doctest}
>>> list(recording.to_frame().columns), recording.to_numpy().shape
(['status', 'timestamp'], (10, 0))
>>> len(recording["videogram"]), recording[0].videogram.shape
(10, (240, 50, 1))
```

## Memory

Each row of a recorder keeps its own result, so a recording of a feature with an image output keeps one image per frame. The
videogram is an array of integers of 64 bits (8 bytes per value), however few the values need:

```{doctest}
>>> image = Videogram(window=500).process(body.astype(np.uint8) * 255).videogram
>>> image.shape, image.dtype, image.nbytes
((240, 500, 1), dtype('int64'), 960000)
>>> 1000 * image.nbytes / 1e6        # megabytes held by `run` on 1000 frames, at the same size
960.0
```

The input is 8 bits per pixel, so a stack of `T` frames of `H x W` takes `T * H * W` bytes (1000 frames of 480 x 640 are about 300 MB).
For a long video, do not stack and do not `run`: read one frame at a time, call `process`, keep what you need from each result (a
centroid; the videogram once, at the end, from `feature.latest`), and let the frame go.

```python
videogram, silhouette = Videogram(window=500), SilhouetteCentroids()
cog = []
for frame, mask in read_frames("video.mp4"):    # your reader: one frame and one mask at a time
    videogram.process(frame)
    cog.append(silhouette.process(mask).centroids[0])
image = videogram.latest.videogram              # the videogram of the whole video
```

One more point: the silhouette features
and the videogram read the pixels once: they do not resize, crop or convert colour, so do that in your own code before the call
(for a silhouette, convert to a single-channel mask).
