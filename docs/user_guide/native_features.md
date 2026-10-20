# Native EyesWeb Features

`pyeyesweb.native` exposes some algorithms of **EyesWeb XMI** that have been ported to C++ (`eyw_core`, in the EyesWeb sources under `_standalone/eyw_core`) and bound to Python with [nanobind](https://github.com/wjakob/nanobind).
They follow the usual PyEyesWeb contracts: a `SlidingWindow` (or a NumPy array) goes in, and a `FeatureResult` comes out.

## Installation

`eyw_core` is an optional dependency and is not on PyPI yet.
Build and install it from the EyesWeb sources.
This needs a C++17 compiler, such as Visual Studio 2019 or later on Windows:

```bash
pip install <path-to>/EyesWeb4/_standalone/eyw_core
python -c "import pyeyesweb.native as n; print(n.is_available(), n.eyw_core_version())"
```

`pyeyesweb.native` always imports.
`is_available()` tells whether `eyw_core` was found.
If it is missing, creating a native feature raises an `ImportError` that says how to install it.

## Features

| Feature | Type | EyesWeb block | Input |
|---|---|---|---|
| `EventSynchronization` | Dynamic | EventSynchronization | `(T, 2, D)`: two signals |
| `SpikeSynchronization` | Dynamic | SpikeES / SpikyES | `(T, N, D)`, N ≥ 2 |
| `NonlinearInterdependence` | Dynamic | EventSynchronization_Interdependence | `(T, 2, 1)` |
| `RecurrenceRate` | Dynamic | GeneralisedAutoCorrelation | `(T, S, D)`: one state vector |
| `BoneOrientations` | Static | HumanoidOrientationsExtractor | `(21, 3)` skeleton frame, mm |
| `HumanoidFilter` *(experimental)* | Static, stateful | HumanoidSimulator | `(21, 3)` skeleton frame, mm |
| `SilhouetteCentroids` | Image | Centroids Calc | `(H, W)` binary mask |
| `BodySubRegions` | Image | BlobSubRegions | `(H, W)` binary mask |

### Event-based synchronization

`EventSynchronization` and `SpikeSynchronization` work on **events**.
The signals are first reduced to scalars: the value itself when `D == 1`, otherwise the Euclidean norm (for example, a velocity vector becomes a speed).
Events are then extracted with `events="peaks"`, the default, which uses the EyesWeb *ScalarPeakDetector* (`peak_buffer`, `peak_threshold`).
If the signals already are event series, use `events="binary"`: every value greater than 0 is an event.
Each window is analysed independently, so overlapping sliding windows are handled correctly.

```python
from pyeyesweb.data_models import SlidingWindow
from pyeyesweb.native import EventSynchronization

# speed of the two hands (mm/s) at 30 Hz, 4 s window
window = SlidingWindow(max_length=120, n_signals=2, n_dims=1)
es = EventSynchronization(tau=3, peak_buffer=5, peak_threshold=50.0)

for left_speed, right_speed in stream:      # your data source
    window.append([left_speed, right_speed])
    if window.is_full:
        r = es(window)
        print(r.Q, r.q)   # Q in [0, 1]: strength; q > 0: the left hand leads
```

On the Kinect recordings in `examples/data/kinect`, the mean Q between the hand-speed peaks is higher in the synchronized trials than in the unsynchronized ones:

| Task | Synchronized | Unsynchronized |
|---|---|---|
| Open the window (trial 3 / 4) | 0.54 | 0.35 |
| Breathing arms (trial 5 / 6) | 0.58 | 0.47 |
| Clapping hands (trial 7 / 8) | 0.76 | 0.67 |

These numbers come from `examples/native_azure_kinect.py` with its default settings.

### Skeletons and the Azure Kinect

The humanoid features use the 21 joints of the Kinect SDK (`HUMANOID_JOINTS`, in millimetres).
The Kinect TSV files of the project use the same names.
For the Azure Kinect (32 joints), `azure_to_humanoid_frame()` selects and reorders the 21 joints the model needs; for example, `pelvis` becomes `spine_base` and `spine_chest` becomes `spine_shoulder`.

`BoneOrientations` returns the direction of each bone in the frame of its parent bone.
Because of this, the values do not change when the person moves or turns as a whole.
For example, the inner elbow angle is `180° − angle(direction["right_elbow-right_wrist"], ref_dir)`.

!!! warning "HumanoidFilter is experimental"
    The EyesWeb mass-spring humanoid has a known instability along long chains (see the eyw_core README, "Stability note").
    On full-body Kinect recordings the simulated joints drift tens of centimetres away from the input, and the drift grows from the head to the feet.
    Check `tracking_error` in the result.

### Silhouettes

`mask_from_body_index()` turns the Azure Kinect *body index map* into a binary mask.
`SilhouetteCentroids` then computes the EyesWeb centroids of the mask: COG, head, shoulders, elbows, hands, knees and feet.
In these labels, *left* and *right* refer to the image.

## Example

`examples/native_azure_kinect.py` runs these features live on the Azure Kinect.
It needs Azure Kinect SDK 1.4, Body Tracking SDK 1.1 and `pip install pykinect_azure opencv-python`.
It can also replay a recorded TSV:

Live, the script shows the colour video with the silhouette outline and the `BodySubRegions` boxes in overlay.
Use `--view depth` for the depth image, `--centroids` to also draw the silhouette centroids, and `--no-skeleton` to hide the tracked skeleton.

```bash
python examples/native_azure_kinect.py
python examples/native_azure_kinect.py --view depth --centroids
python examples/native_azure_kinect.py --replay examples/data/kinect/trial7.tsv --fast --csv trial7.csv
```
