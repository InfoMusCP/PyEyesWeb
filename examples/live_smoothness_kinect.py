"""Live smoothness analysis from Azure Kinect body tracking.

Streams one skeleton joint, resamples it to a uniform rate, estimates its
velocity on a sliding window and computes the PyEyesWeb ``Smoothness``
metrics in real time.

Usage
-----
Live from Azure Kinect (requires Azure Kinect SDK + Body Tracking SDK and
``pip install pykinect_azure``)::

    python examples/live_smoothness_kinect.py --joint right_hand

Replay of a recorded Kinect TSV as if it were live (no Kinect needed,
useful to test the pipeline)::

    python examples/live_smoothness_kinect.py --replay examples/data/kinect/trial8.tsv

Useful options::

    --window 3.0         sliding window length in seconds
    --update-every 3     recompute metrics every N new samples
    --osc 127.0.0.1:5006 send metrics via OSC (/smoothness/<metric>)
    --csv out.csv        log metrics to CSV
    --smooth 0.5         velocity smoothing window in seconds
    --no-plot            terminal output only

Pipeline
--------
1. Source thread (Kinect or replay) -> (timestamp [s], xyz [mm]) samples.
2. Resampling to a uniform grid (default 30 Hz) by linear interpolation:
   Kinect frames have jitter and occasional drops, while every smoothness
   metric assumes uniform sampling.
3. Velocity: Savitzky-Golay derivative over the window (polyorder 2,
   ``--smooth`` seconds, default 0.5 s). Kinect joints (hands especially)
   jitter by several cm per frame, so some smoothing is required; the
   offline KinectLoader uses an even stronger one (~0.7 s). Only the past
   window is used, so the whole pipeline stays causal.
4. ``Smoothness.compute`` on the (T, 1, 3) velocity vectors.

Metric direction: SPARC, LDLJ-V, LDLJ-A -> closer to 0 = smoother;
jerk_rms, samp_en, n_submovements -> lower = smoother/more regular.
"""

import argparse
import collections
import csv
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pyeyesweb.low_level.smoothness import Smoothness  # noqa: E402

# Azure Kinect Body Tracking joint indices (k4abt_joint_id_t)
K4ABT_JOINTS = {
    "pelvis": 0, "spine_navel": 1, "spine_chest": 2, "neck": 3,
    "left_clavicle": 4, "left_shoulder": 5, "left_elbow": 6, "left_wrist": 7,
    "left_hand": 8, "left_handtip": 9, "left_thumb": 10,
    "right_clavicle": 11, "right_shoulder": 12, "right_elbow": 13, "right_wrist": 14,
    "right_hand": 15, "right_handtip": 16, "right_thumb": 17,
    "left_hip": 18, "left_knee": 19, "left_ankle": 20, "left_foot": 21,
    "right_hip": 22, "right_knee": 23, "right_ankle": 24, "right_foot": 25,
    "head": 26, "nose": 27,
}

STOP = object()


class SourceError:
    """Wraps an exception raised in a source thread."""

    def __init__(self, exc):
        self.exc = exc


KINECT_OPEN_HELP = """
Could not open the Azure Kinect.
 - Close Azure Kinect Viewer and any other program/notebook using the camera
   (only one application at a time can open the device).
 - Check for leftover Python processes:  Get-Process python*
 - Unplug/replug power and USB (USB 3 port, no hub), then retry.
"""


# ======================================================================
# SOURCES  (each runs in its own thread and puts (t, xyz) in a queue)
# ======================================================================
def kinect_source(out_q: queue.Queue, joint: str, stop_evt: threading.Event,
                  min_confidence: int = 1, show_video: bool = True):
    """Azure Kinect body tracking source (positions in mm, camera frame).

    Any failure (pykinect_azure calls sys.exit() when the device cannot be
    opened) is forwarded to the main thread, which then stops cleanly.
    """
    try:
        _kinect_loop(out_q, joint, stop_evt, min_confidence, show_video)
    except BaseException as exc:  # includes SystemExit raised by pykinect_azure
        out_q.put(SourceError(exc))
    finally:
        out_q.put(STOP)


def _kinect_loop(out_q, joint, stop_evt, min_confidence, show_video):
    import pykinect_azure as pykinect

    joint_idx = K4ABT_JOINTS[joint]
    pykinect.initialize_libraries(track_body=True)
    config = pykinect.default_configuration
    config.color_resolution = pykinect.K4A_COLOR_RESOLUTION_OFF
    config.depth_mode = pykinect.K4A_DEPTH_MODE_NFOV_UNBINNED
    config.camera_fps = pykinect.K4A_FRAMES_PER_SECOND_30
    device = pykinect.start_device(config=config)
    tracker = pykinect.start_body_tracker()
    print(f"[Kinect] started, tracking joint '{joint}' (index {joint_idx})")

    cv2 = None
    if show_video:
        try:
            import cv2
        except ImportError:
            pass

    t0 = None
    try:
        while not stop_evt.is_set():
            capture = device.update()
            body_frame = tracker.update()

            if body_frame.get_num_bodies() > 0:
                skeleton = body_frame.get_body_skeleton(0)
                j = skeleton.joints[joint_idx]
                if int(j.confidence_level) >= min_confidence:
                    p = j.position
                    try:
                        xyz = np.array([p.xyz.x, p.xyz.y, p.xyz.z], dtype=float)
                    except AttributeError:
                        xyz = np.array(list(p.v)[:3], dtype=float)
                    try:
                        t = body_frame.get_device_timestamp_usec() * 1e-6
                    except Exception:
                        t = time.perf_counter()
                    if t0 is None:
                        t0 = t
                    out_q.put((t - t0, xyz))

            if cv2 is not None:
                ret, depth_img = capture.get_colored_depth_image()
                if ret:
                    img = body_frame.draw_bodies(depth_img)
                    cv2.imshow("Kinect body tracking (q = quit)", img)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        stop_evt.set()
    finally:
        device.close()
        if cv2 is not None:
            cv2.destroyAllWindows()


def replay_source(out_q: queue.Queue, path: str, joint: str, stop_evt: threading.Event,
                  speed: float = 1.0):
    try:
        _replay_loop(out_q, path, joint, stop_evt, speed)
    except BaseException as exc:
        out_q.put(SourceError(exc))
    finally:
        out_q.put(STOP)


def _replay_loop(out_q, path, joint, stop_evt, speed):
    """Replays a QTM-style Kinect TSV in real time.

    Kinect exports in this project are 30 fps data stored at 100 Hz by
    repeating samples, and zeros mark missing frames: only samples that
    actually change are emitted, with their original timestamps, so the
    stream looks like the live Kinect one.
    """
    import pandas as pd

    lines = Path(path).read_text().splitlines()
    header = next(i for i, l in enumerate(lines) if l.startswith("Frame\t"))
    df = pd.read_csv(path, skiprows=header, sep="\t")
    cols = [f"{joint} X", f"{joint} Y", f"{joint} Z"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        names = sorted({c.rsplit(" ", 1)[0] for c in df.columns if c.endswith(" X")})
        raise ValueError(f"Joint '{joint}' not in file. Available: {names}")

    pos = df[cols].to_numpy(float)
    t = df["Time"].to_numpy(float)
    valid = ~np.all(pos == 0, axis=1)
    pos, t = pos[valid], t[valid]
    changed = np.r_[True, np.any(np.diff(pos, axis=0) != 0, axis=1)]
    pos, t = pos[changed], t[changed] - t[changed][0]
    print(f"[Replay] {path}: {len(t)} frames, {t[-1]:.1f} s, joint '{joint}'")

    start = time.perf_counter()
    for ti, xi in zip(t, pos):
        if stop_evt.is_set():
            break
        delay = ti / speed - (time.perf_counter() - start)
        if delay > 0:
            time.sleep(delay)
        out_q.put((ti, xi))


# ======================================================================
# PROCESSING
# ======================================================================
class UniformResampler:
    """Linear interpolation of an irregular stream onto a uniform time grid."""

    def __init__(self, rate_hz: float, max_gap_s: float = 0.25):
        self.dt = 1.0 / rate_hz
        self.max_gap = max_gap_s
        self.prev = None          # (t, xyz)
        self.next_t = None

    def push(self, t, xyz):
        out = []
        if self.prev is None:
            self.prev, self.next_t = (t, xyz), t
            return [xyz]
        t_prev, x_prev = self.prev
        if t <= t_prev:
            return out
        if t - t_prev > self.max_gap:
            # Tracking lost for too long: restart the grid instead of
            # interpolating a straight line through the gap
            self.prev, self.next_t = (t, xyz), t + self.dt
            return [None, xyz]   # None = discontinuity marker
        while self.next_t <= t:
            a = (self.next_t - t_prev) / (t - t_prev)
            out.append(x_prev + a * (xyz - x_prev))
            self.next_t += self.dt
        self.prev = (t, xyz)
        return out


class LiveSmoothness:
    METRICS = ["sparc", "ldlj_v", "ldlj_a", "jerk_rms", "samp_en", "n_submovements"]

    def __init__(self, rate_hz=30.0, window_s=3.0, update_every=3,
                 min_speed=50.0, sg_window_s=0.5):
        self.rate = rate_hz
        self.n = int(round(window_s * rate_hz))
        self.update_every = update_every
        self.positions = collections.deque(maxlen=self.n)
        self.since_update = 0
        wl = max(5, int(round(sg_window_s * rate_hz)) | 1)   # odd length
        self.sg_window = wl
        self.feature = Smoothness(
            rate_hz=rate_hz, metrics=self.METRICS, min_speed_threshold=min_speed
        )

    def reset(self):
        self.positions.clear()
        self.since_update = 0

    def push(self, xyz):
        """Add one uniformly-sampled position; returns (speed, result|None)."""
        self.positions.append(np.asarray(xyz, float))
        self.since_update += 1
        if len(self.positions) < max(self.sg_window, 10):
            return None, None

        pos = np.asarray(self.positions)
        vel = savgol_filter(pos, self.sg_window, 2, deriv=1,
                            delta=1.0 / self.rate, axis=0)
        # Speed shown/logged at the centre of the last Savitzky-Golay window
        # (delay = smooth/2): the derivative at the very last sample is an
        # extrapolation and much noisier.
        speed = float(np.linalg.norm(vel[-1 - self.sg_window // 2]))

        if len(self.positions) < self.n or self.since_update < self.update_every:
            return speed, None
        self.since_update = 0
        return speed, self.feature.compute(vel[:, None, :])


# ======================================================================
# MAIN
# ======================================================================
def parse_args():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--joint", default="right_hand", help="joint name (default right_hand)")
    ap.add_argument("--replay", help="replay a Kinect TSV instead of the live camera")
    ap.add_argument("--speed", type=float, default=1.0, help="replay speed factor")
    ap.add_argument("--rate", type=float, default=30.0, help="resampling rate in Hz")
    ap.add_argument("--window", type=float, default=3.0, help="window length in s")
    ap.add_argument("--update-every", type=int, default=3, help="samples between updates")
    ap.add_argument("--min-speed", type=float, default=50.0,
                    help="rest threshold in mm/s (0 = off)")
    ap.add_argument("--smooth", type=float, default=0.5,
                    help="Savitzky-Golay window in s for velocity estimation (default 0.5). "
                         "Kinect joints are noisy: lower = more detail but more noise")
    ap.add_argument("--osc", help="send metrics via OSC to host:port")
    ap.add_argument("--csv", help="log metrics to this CSV file")
    ap.add_argument("--no-plot", action="store_true", help="disable the live plot")
    ap.add_argument("--no-video", action="store_true", help="hide the Kinect preview")
    return ap.parse_args()


def main():
    args = parse_args()
    if not args.replay and args.joint not in K4ABT_JOINTS:
        sys.exit(f"Unknown joint '{args.joint}'. Choose from: {sorted(K4ABT_JOINTS)}")

    q, stop_evt = queue.Queue(), threading.Event()
    if args.replay:
        target, targs = replay_source, (q, args.replay, args.joint, stop_evt, args.speed)
    else:
        target, targs = kinect_source, (q, args.joint, stop_evt, 1, not args.no_video)
    threading.Thread(target=target, args=targs, daemon=True).start()

    resampler = UniformResampler(args.rate)
    live = LiveSmoothness(args.rate, args.window, args.update_every, args.min_speed, args.smooth)

    osc = None
    if args.osc:
        from pythonosc.udp_client import SimpleUDPClient
        host, port = args.osc.rsplit(":", 1)
        osc = SimpleUDPClient(host, int(port))

    csv_file = csv_writer = None
    if args.csv:
        csv_file = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["time_s", "speed_mm_s", "is_valid"] + LiveSmoothness.METRICS)

    hist_len = int(20 * args.rate)   # 20 s on screen
    hist = {k: collections.deque(maxlen=hist_len)
            for k in ["t", "speed", "rt"] + LiveSmoothness.METRICS}
    state = {"n": 0, "done": False}

    def process_pending():
        """Drain the source queue; returns False when the source has ended."""
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                return True
            if isinstance(item, SourceError):
                state["error"] = item.exc
                continue
            if item is STOP:
                state["done"] = True
                return False
            for xyz in resampler.push(*item):
                if xyz is None:
                    live.reset()
                    continue
                t_now = state["n"] / args.rate
                state["n"] += 1
                speed, res = live.push(xyz)
                if speed is not None:
                    hist["t"].append(t_now)
                    hist["speed"].append(speed)
                if res is None:
                    continue
                values = {m: getattr(res, m) if res.is_valid else np.nan
                          for m in LiveSmoothness.METRICS}
                hist["rt"].append(t_now)
                for m, v in values.items():
                    hist[m].append(np.nan if v is None else v)
                if osc is not None and res.is_valid:
                    for m, v in values.items():
                        if v is not None and np.isfinite(v):
                            osc.send_message(f"/smoothness/{m}", float(v))
                if csv_writer is not None:
                    csv_writer.writerow([f"{t_now:.3f}", f"{speed:.1f}", res.is_valid]
                                        + [values[m] for m in LiveSmoothness.METRICS])
                if args.no_plot:
                    if res.is_valid:
                        print(f"t={t_now:6.1f}s  v={speed:7.1f} mm/s  "
                              f"SPARC={values['sparc']:6.2f}  LDLJ-V={values['ldlj_v']:6.2f}  "
                              f"SampEn={values['samp_en']:5.2f}  peaks={values['n_submovements']}")
                    else:
                        print(f"t={t_now:6.1f}s  v={speed:7.1f} mm/s  (rest / invalid)")

    try:
        if args.no_plot:
            while process_pending():
                time.sleep(0.02)
        else:
            # Open the plot only once the source delivers data (or fails),
            # so a device error never leaves an empty window behind.
            print("Waiting for the first samples...")
            while (not hist["t"] and state.get("error") is None
                   and not state["done"]):
                process_pending()
                time.sleep(0.05)
            if state.get("error") is None and not state["done"]:
                run_plot(args, hist, process_pending, state)
    except KeyboardInterrupt:
        pass
    finally:
        stop_evt.set()
        if csv_file:
            csv_file.close()
            print(f"Metrics saved to {args.csv}")

    err = state.get("error")
    if err is not None:
        if isinstance(err, SystemExit) and not args.replay:
            sys.exit(KINECT_OPEN_HELP)
        sys.exit(f"Source error: {type(err).__name__}: {err}")


def run_plot(args, hist, process_pending, state):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    panels = [
        ("speed", "Speed (mm/s)", "t"),
        ("sparc", "SPARC\n(closer to 0 = smoother)", "rt"),
        ("ldlj_v", "LDLJ-V\n(closer to 0 = smoother)", "rt"),
        ("samp_en", "Sample Entropy\n(lower = regular)", "rt"),
        ("n_submovements", "Speed peaks\n(lower = smoother)", "rt"),
    ]
    fig, axes = plt.subplots(len(panels), 1, sharex=True, figsize=(10, 9))
    fig.suptitle(f"Live smoothness - {args.joint} "
                 f"({'replay' if args.replay else 'Azure Kinect'}, window {args.window:g} s)")
    lines = {}
    for ax, (key, label, _) in zip(axes, panels):
        lines[key], = ax.plot([], [], lw=1.5,
                              drawstyle="steps-post" if key == "n_submovements" else "default")
        ax.set_ylabel(label, fontsize=9)
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Time (s) - metrics plotted at the end of their window")

    def update(_):
        process_pending()
        for ax, (key, _, tkey) in zip(axes, panels):
            x, y = np.asarray(hist[tkey]), np.asarray(hist[key], dtype=float)
            if len(x) != len(y) or len(x) == 0:
                continue
            lines[key].set_data(x, y)
            finite = y[np.isfinite(y)]
            if finite.size:
                lo, hi = finite.min(), finite.max()
                pad = 0.1 * (hi - lo) if hi > lo else 1.0
                ax.set_ylim(lo - pad, hi + pad)
        if len(hist["t"]):
            t_end = hist["t"][-1]
            axes[0].set_xlim(max(0.0, t_end - 20.0), max(20.0, t_end))
        if state.get("error") is not None:
            anim.event_source.stop()
            fig.suptitle(f"Source error: {state['error']}")
            return list(lines.values())
        if state["done"]:
            fig.suptitle(fig._suptitle.get_text() + "  [end of stream]")
            anim.event_source.stop()
        return list(lines.values())

    anim = FuncAnimation(fig, update, interval=100, cache_frame_data=False)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
