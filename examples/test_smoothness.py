import sys, os

# Add project root to import path
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyeyesweb.data_models.sliding_window import SlidingWindow

import cv2
import mediapipe as mp
import numpy as np
from pyeyesweb.mid_level.smoothness import Smoothness
import time

def extract_wrist_xy(results, keypoint_idx, width, height):
    keypoint = results.pose_landmarks.landmark[keypoint_idx]
    if keypoint.visibility > 0.5:
        x = int(keypoint.x * width)
        y = int(keypoint.y * height)
        return x, y
    return None

def main():
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    # Enable filter to stabilize signal
    smoother = Smoothness(rate_hz=30, use_filter=True)
    sliding_window = SlidingWindow(50, 1)
    cap = cv2.VideoCapture(0)

    LEFT_WRIST_IDX = 15
    prev_xy = None
    prev_time = None

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            frame = cv2.flip(frame, 1)
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(image)
            height, width, _ = image.shape

            if results.pose_landmarks:
                xy = extract_wrist_xy(results, LEFT_WRIST_IDX, width, height)
                now = time.time()

                if xy and prev_xy and prev_time:
                    dt = now - prev_time
                    if dt > 0:
                        dx = xy[0] - prev_xy[0]
                        dy = xy[1] - prev_xy[1]
                        velocity = np.sqrt(dx**2 + dy**2) / dt

                        # Clamp unrealistic velocity spikes (in pixels/sec)
                        if velocity < 1000:
                            sliding_window.append([velocity])
                            sparc, jerk = smoother(sliding_window)
                            if sparc is not None:
                                print(f"SPARC: {sparc:.3f}, Jerk RMS: {jerk:.1f}")

                prev_xy = xy
                prev_time = now

            cv2.imshow("Smoothness Test (Velocity-Based)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        pose.close()

if __name__ == "__main__":
    main()
