"""Native EyesWeb features (eyw_core, nanobind) on Azure Kinect body tracking.

Runs some of the EyesWeb C++ algorithms exposed by ``pyeyesweb.native`` on a
live Azure Kinect stream, or on a recorded Kinect TSV of this project:

* BoneOrientations      -> elbow angles, from the relative bone directions;
* EventSynchronization  -> Q / q between the speed peaks of the two hands;
* SpikeSynchronization  -> SPIKE-sync of the same events;
* RecurrenceRate        -> dominant lag of the right-hand trajectory (indicative period);
* HumanoidFilter        -> (optional, --humanoid) EyesWeb mass-spring humanoid;
* BodySubRegions        -> (live only) head / trunk / arms / legs boxes of the
                           silhouette, drawn over the video;
* SilhouetteCentroids   -> (live only, --centroids) EyesWeb centroids of the
                           silhouette, drawn over the video.

The silhouette is the Azure Kinect body index map of the tracked person.

Live from Azure Kinect DK (Azure Kinect SDK 1.4 + Body Tracking SDK 1.1,
``pip install pykinect_azure opencv-python``)::

    python examples/native_azure_kinect.py                  # colour video + sub-regions
    python examples/native_azure_kinect.py --view depth     # depth video
    python examples/native_azure_kinect.py --centroids      # also the silhouette centroids

Replay of a recorded Kinect TSV, at real speed or as fast as possible::

    python examples/native_azure_kinect.py --replay examples/data/kinect/trial7.tsv
    python examples/native_azure_kinect.py --replay examples/data/kinect/trial8.tsv --fast

Requirements: ``eyw_core`` installed (``pip install <EyesWeb4>/_standalone/eyw_core``).
Press q in the video window (live) or Ctrl+C to stop.
"""

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pyeyesweb.data_models import SlidingWindow  # noqa: E402
from pyeyesweb.native import (  # noqa: E402
    HUMANOID_JOINTS,
    K4ABT_JOINTS,
    BodySubRegions,
    BoneOrientations,
    EventSynchronization,
    HumanoidFilter,
    RecurrenceRate,
    SilhouetteCentroids,
    SpikeSynchronization,
    azure_to_humanoid_frame,
    eyw_core_version,
    is_available,
    mask_from_body_index,
)

J = {n: i for i, n in enumerate(HUMANOID_JOINTS)}
WINDOW = "pyeyesweb.native - Azure Kinect (q = quit)"

AZURE_HELP = """
Could not open the Azure Kinect.
 - Install Azure Kinect SDK 1.4 and Azure Kinect Body Tracking SDK 1.1 and check
   the sensor with Azure Kinect Viewer (then close it: one program at a time).
 - pip install pykinect_azure opencv-python
 - Unplug/replug power and USB (USB 3 port, no hub), then retry.
"""


# ======================================================================
# SOURCES: generators of (t [s], joints (21, 3) mm, body_mask or None, image or None)
# ======================================================================
def _body_index_to_color(body_frame):
    """Body index map re-projected on the colour camera (255 = background).

    Uses nearest-neighbour interpolation and 255 for pixels without depth:
    pykinect_azure's own helper interpolates linearly and marks them 0,
    which is a valid body index.
    """
    import ctypes

    from pykinect_azure.k4a import Image, _k4a

    tr = body_frame.transformation
    w, h = tr.color_resolution.width, tr.color_resolution.height
    depth = body_frame.get_capture().get_depth_image_object()
    bim = body_frame.get_body_index_map()
    out = Image.create(bim.format, w, h, w)
    out_depth = Image.create(_k4a.K4A_IMAGE_FORMAT_DEPTH16, w, h, w * 2)
    _k4a.k4a_transformation_depth_image_to_color_camera_custom(
        tr.handle(), depth.handle(), bim.handle(), out_depth.handle(), out.handle(),
        _k4a.K4A_TRANSFORMATION_INTERPOLATION_TYPE_NEAREST, ctypes.c_uint32(255))
    return out.to_numpy()


def azure_frames(min_confidence: int = 1, view: str = "color", draw_skeleton: bool = True):
    """Live Azure Kinect: the body closest to the camera, humanoid joints in mm.

    Joints with confidence below ``min_confidence`` (0 none, 1 low, 2 medium)
    are returned as NaN.  ``view`` is ``"color"`` (720p colour camera, the
    silhouette is re-projected on it), ``"depth"`` (colourised depth image)
    or ``None`` (no video).  The returned mask is aligned with the image.
    """
    import pykinect_azure as pykinect

    pykinect.initialize_libraries(track_body=True)
    config = pykinect.default_configuration
    if view == "color":
        config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_720P
        config.color_format = pykinect.K4A_IMAGE_FORMAT_COLOR_BGRA32
        config.synchronized_images_only = True
    else:
        config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_OFF
    config.depth_mode = pykinect.K4A_DEPTH_MODE_NFOV_UNBINNED
    config.camera_fps = pykinect.K4A_FRAMES_PER_SECOND_30
    device = pykinect.start_device(config=config)
    tracker = pykinect.start_body_tracker()
    print(f"[Azure Kinect] started ({view or 'no'} video). Stand 1-4 m in front of the sensor.")
    pelvis = K4ABT_JOINTS["pelvis"]
    t0 = None
    try:
        while True:
            capture = device.update()
            body_frame = tracker.update()
            image = None
            if view == "color":
                ok, image = capture.get_color_image()
                image = np.ascontiguousarray(image[:, :, :3]) if ok and image is not None else None
            elif view == "depth":
                ok, image = capture.get_colored_depth_image()
                image = image if ok else None
            n = body_frame.get_num_bodies()
            if n == 0:
                yield None, None, None, image
                continue
            skeletons = [body_frame.get_body_skeleton(i) for i in range(n)]
            best = min(range(n), key=lambda i: skeletons[i].joints[pelvis].position.xyz.z)
            az = np.full((32, 3), np.nan)
            for k, jt in enumerate(skeletons[best].joints[:32]):
                if int(jt.confidence_level) >= min_confidence:
                    p = jt.position.xyz
                    az[k] = (p.x, p.y, p.z)
            if view == "color":
                ok, bim = _body_index_to_color(body_frame)
            else:
                ok, bim = body_frame.get_body_index_map_image()
            mask = mask_from_body_index(bim, best) if ok else None
            if image is not None and draw_skeleton:
                cam = pykinect.K4A_CALIBRATION_TYPE_COLOR if view == "color" else pykinect.K4A_CALIBRATION_TYPE_DEPTH
                image = body_frame.draw_bodies(image, cam, only_segments=True)
            t = body_frame.get_device_timestamp_usec() * 1e-6
            t0 = t if t0 is None else t0
            yield t - t0, azure_to_humanoid_frame(az), mask, image
    finally:
        device.close()


def replay_frames(path: str, speed: float = 1.0):
    """Recorded Kinect TSV of this project (Kinect SDK joint names, mm).

    The files store ~30 fps data at 100 Hz by repeating samples, and zeros
    mark missing joints: only frames that change are emitted, with their
    original timestamps, so the stream looks like a live Kinect one.
    ``speed <= 0`` replays as fast as possible.
    """
    import pandas as pd

    lines = Path(path).read_text().splitlines()
    header = next(i for i, ln in enumerate(lines) if ln.startswith("Frame\t"))
    df = pd.read_csv(path, skiprows=header, sep="\t")
    missing = [n for n in HUMANOID_JOINTS if f"{n} X" not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing joints {missing}")
    pos = np.stack([df[[f"{n} X", f"{n} Y", f"{n} Z"]].to_numpy(float) for n in HUMANOID_JOINTS], axis=1)
    t = df["Time"].to_numpy(float)
    pos[np.all(pos == 0, axis=2)] = np.nan
    keep = np.any(np.isfinite(pos[:, :, 0]), axis=1)
    pos, t = pos[keep], t[keep]
    changed = np.r_[True, np.any(np.nan_to_num(np.diff(pos, axis=0)) != 0, axis=(1, 2))]
    pos, t = pos[changed], t[changed] - t[changed][0]
    print(f"[Replay] {path}: {len(t)} frames, {t[-1]:.1f} s ({len(t) / max(t[-1], 1e-9):.1f} fps)")
    start = time.perf_counter()
    for ti, frame in zip(t, pos):
        if speed > 0:
            delay = ti / speed - (time.perf_counter() - start)
            if delay > 0:
                time.sleep(delay)
        yield ti, frame, None, None


# ======================================================================
# ANALYSIS
# ======================================================================
def elbow_angle(result, side: str) -> float:
    """Inner elbow angle (deg): 180 = straight arm, from the relative forearm direction."""
    d = np.asarray(result.directions.get(f"{side}_elbow-{side}_wrist", (np.nan,) * 3))
    return float(180.0 - np.degrees(np.arccos(np.clip(d[0], -1.0, 1.0))))  # ref_dir = (1, 0, 0)


class HandSpeeds:
    """Speed (mm/s) of both hands, moving-average smoothed over a few frames."""

    def __init__(self, smooth: int = 5):
        self.prev = None
        self.hist = []
        self.smooth = smooth

    def push(self, t, frame):
        hands = frame[[J["left_hand"], J["right_hand"]]]
        speed = np.full(2, np.nan)
        if self.prev is not None and t > self.prev[0]:
            speed = np.linalg.norm(hands - self.prev[1], axis=1) / (t - self.prev[0])
        if np.all(np.isfinite(hands)):
            self.prev = (t, hands)
        if np.all(np.isfinite(speed)):
            self.hist = (self.hist + [speed])[-self.smooth:]
        return np.mean(self.hist, axis=0) if self.hist else None


#: BGR colour of each sub-region (subject's right/left, as named by EyesWeb)
REGION_COLORS = {
    "head": (0, 215, 255), "trunk": (255, 160, 0),
    "right_arm": (60, 60, 255), "left_arm": (60, 220, 60),
    "right_leg": (180, 60, 255), "left_leg": (220, 220, 60),
}


def _label(cv2, image, text, x, y, color, taken):
    """Text tag with a coloured background; moved down if it overlaps another tag."""
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    w, h = tw + 6, th + base + 4
    x = int(np.clip(x, 0, image.shape[1] - w))
    y = int(np.clip(y, 0, image.shape[0] - h))
    while any(x < ox + ow and ox < x + w and y < oy + oh and oy < y + h for ox, oy, ow, oh in taken):
        y += h + 1
    taken.append((x, y, w, h))
    cv2.rectangle(image, (x, y), (x + w, y + h), color, -1)
    cv2.putText(image, text, (x + 3, y + th + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)


def draw_overlay(cv2, image, mask, regions, centroids, alpha=0.35):
    """Silhouette outline, translucent sub-region boxes with labels, centroids."""
    if mask is not None and mask.shape[:2] == image.shape[:2]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(image, contours, -1, (255, 255, 255), 1, cv2.LINE_AA)
    if regions is not None and regions.is_valid:
        H, W = image.shape[:2]
        for part, (x, y, w, h) in regions.regions.items():       # translucent fill, ROI only
            x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
            if x1 > x0 and y1 > y0:
                roi = image[y0:y1, x0:x1]
                col = np.array(REGION_COLORS.get(part, (200, 200, 200)), np.float32)
                roi[:] = (roi * (1 - alpha) + col * alpha).astype(np.uint8)
        taken = []
        for part, (x, y, w, h) in regions.regions.items():
            col = REGION_COLORS.get(part, (200, 200, 200))
            cv2.rectangle(image, (x, y), (x + w, y + h), col, 2)
            _label(cv2, image, part.replace("_", " "), x, y - 18, col, taken)
    if centroids is not None and centroids.is_valid:
        for label, (x, y) in centroids.centroids.items():
            cv2.circle(image, (int(x), int(y)), 7 if label == "cog" else 4, (0, 255, 255), -1, cv2.LINE_AA)
    return image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replay", help="Kinect TSV file to replay instead of the live sensor")
    ap.add_argument("--fast", action="store_true", help="replay as fast as possible")
    ap.add_argument("--rate", type=float, default=30.0, help="frame rate of the skeleton (Hz)")
    ap.add_argument("--window", type=float, default=4.0, help="analysis window (s)")
    ap.add_argument("--every", type=int, default=15, help="update the window features every N frames")
    ap.add_argument("--tau", type=int, default=3, help="EventSynchronization max lag (frames)")
    ap.add_argument("--peak-buffer", type=int, default=5, help="peak detector buffer (frames)")
    ap.add_argument("--peak-threshold", type=float, default=50.0, help="peak detector threshold (mm/s)")
    ap.add_argument("--humanoid", action="store_true", help="also run the (experimental) HumanoidFilter")
    ap.add_argument("--view", choices=["color", "depth"], default="color",
                    help="live: video shown under the overlay (default: color)")
    ap.add_argument("--centroids", action="store_true", help="live: also draw the silhouette centroids")
    ap.add_argument("--no-skeleton", action="store_true", help="live: do not draw the tracked skeleton")
    ap.add_argument("--no-video", action="store_true", help="live: do not open the video window")
    ap.add_argument("--csv", help="write the window features to this CSV file")
    args = ap.parse_args()

    if not is_available():
        sys.exit("eyw_core is not installed: pip install <EyesWeb4>/_standalone/eyw_core")
    print(f"eyw_core {eyw_core_version()}")

    n_win = max(int(round(args.window * args.rate)), 10)
    speeds_win = SlidingWindow(max_length=n_win, n_signals=2, n_dims=1)     # left, right hand speed
    hand_win = SlidingWindow(max_length=n_win, n_signals=1, n_dims=3)       # right hand position

    orient = BoneOrientations()
    speeds = HandSpeeds()
    es = EventSynchronization(tau=args.tau, peak_buffer=args.peak_buffer, peak_threshold=args.peak_threshold)
    ss = SpikeSynchronization(peak_buffer=args.peak_buffer, peak_threshold=args.peak_threshold)
    rr = RecurrenceRate(epsilon=0.5, tau_min=max(1, int(0.3 * args.rate)), tau_spread=int(2.5 * args.rate))
    hf = HumanoidFilter(rate_hz=args.rate) if args.humanoid else None
    centroids = SilhouetteCentroids(filter_alpha=0.5)
    subregions = BodySubRegions()

    cv2 = None
    if args.replay:
        source = replay_frames(args.replay, 0.0 if args.fast else 1.0)
    else:
        if not args.no_video:
            try:
                import cv2
            except ImportError:
                print("opencv-python not installed: no video window")
        source = azure_frames(view=args.view if cv2 is not None else None,
                              draw_skeleton=not args.no_skeleton)
        if cv2 is not None:
            cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    writer, csv_file = None, None
    if args.csv:
        csv_file = open(args.csv, "w", newline="")
        writer = csv.writer(csv_file)
        writer.writerow(["t", "elbow_left", "elbow_right", "Q", "q", "events_left", "events_right",
                         "spike_sync", "period_s", "humanoid_error_mm"])

    history = []
    frame_no, t_clock = 0, time.perf_counter()
    try:
        for t, frame, mask, image in source:
            sil = centroids(mask) if mask is not None and args.centroids else None
            regions = subregions(mask) if mask is not None and cv2 is not None else None
            if frame is not None:
                frame_no += 1
                o = orient.compute(frame)
                elbows = (elbow_angle(o, "left"), elbow_angle(o, "right")) if o.is_valid else (np.nan, np.nan)
                v = speeds.push(t, frame)
                if v is not None:
                    speeds_win.append(v, timestamp=t)
                if np.all(np.isfinite(frame[J["right_hand"]])):
                    hand_win.append(frame[J["right_hand"]], timestamp=t)
                herr = hf.compute(frame).tracking_error if hf is not None else np.nan

                if frame_no % args.every == 0 and speeds_win.is_full:
                    r_es, r_ss = es(speeds_win), ss(speeds_win)
                    r_rr = rr(hand_win) if hand_win.is_full else None
                    period = r_rr.dominant_tau / args.rate if r_rr is not None and r_rr.dominant_tau else np.nan
                    row = [t, *elbows,
                           r_es.Q if r_es.is_valid else np.nan, r_es.q if r_es.is_valid else np.nan,
                           r_es.events_x, r_es.events_y,
                           r_ss.sync if r_ss.is_valid else np.nan, period, herr]
                    history.append(row)
                    if writer:
                        writer.writerow([f"{x:.4f}" if isinstance(x, float) else x for x in row])
                    hum = f"  humanoid err {herr:5.0f} mm" if hf is not None else ""
                    cog = sil.centroids.get("cog") if sil is not None and sil.is_valid else None
                    cog = f"  silhouette COG ({cog[0]:.0f}, {cog[1]:.0f}) px" if cog else ""
                    print(f"t={t:6.1f}s  elbows L {elbows[0]:5.1f} R {elbows[1]:5.1f} deg  "
                          f"EventSync Q {row[3]:.2f} q {row[4]:+.2f} (events {row[5]}/{row[6]})  "
                          f"SPIKE {row[7]:.2f}  RR period {period:.2f}s{hum}{cog}")

            if cv2 is not None and image is not None:
                draw_overlay(cv2, image, mask, regions, sil if args.centroids else None)
                cv2.imshow(WINDOW, image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    except KeyboardInterrupt:
        pass
    except (SystemExit, ImportError, OSError, RuntimeError) as exc:
        # pykinect_azure calls sys.exit() when the device or the SDK cannot be opened
        if args.replay:
            raise
        print(f"\n[Azure Kinect] {type(exc).__name__}: {exc}\n{AZURE_HELP}")
    finally:
        if csv_file:
            csv_file.close()
        if cv2 is not None:
            cv2.destroyAllWindows()

    if history:
        h = np.array(history, dtype=float)
        dt = time.perf_counter() - t_clock
        print(f"\n{frame_no} frames in {dt:.1f} s ({frame_no / max(dt, 1e-9):.0f} fps processed)")
        print(f"mean EventSync Q {np.nanmean(h[:, 3]):.2f}, q {np.nanmean(h[:, 4]):+.2f}; "
              f"mean SPIKE-sync {np.nanmean(h[:, 7]):.2f}; median period {np.nanmedian(h[:, 8]):.2f} s"
              + (f"; mean humanoid error {np.nanmean(h[:, 9]):.0f} mm" if hf is not None else ""))


if __name__ == "__main__":
    main()
