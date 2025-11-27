import sys, os

# Add project root to import path
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import mediapipe as mp
import numpy as np
from pyeyesweb.mid_level.lightness import Lightness
import time
import math

# ----------- Mouse tracking -----------
mouse_pos = None

def mouse_callback(event, x, y, flags, param):
    global mouse_pos
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_pos = (x, y)

# -------------------------------------

def is_valid_number(x):
    return isinstance(x, (int, float, np.floating)) and not (math.isnan(x) or math.isinf(x))


def main():

    # Lightness processor (smoothing enabled)
    lightness = Lightness(rate_hz=60, use_filter=True)

    # Create window and mouse callback
    cv2.namedWindow("Mouse Lightness")
    cv2.setMouseCallback("Mouse Lightness", mouse_callback)

    prev_pos = None
    prev_time = None

    frame = np.zeros((400, 600, 3), dtype=np.uint8)

    while True:
        now = time.time()

        if mouse_pos is not None:
            if prev_pos is not None and prev_time is not None:

                dt = now - prev_time
                if dt > 0:
                    dx = mouse_pos[0] - prev_pos[0]
                    dy = mouse_pos[1] - prev_pos[1]

                    # CHIAMO lightness SOLO se dx e dy NON sono NaN
                    if is_valid_number(dx) and is_valid_number(dy):

                        result = lightness([dx, dy])

                        # Safe print
                        if result is None:
                            print("None")
                        elif isinstance(result, (float, np.floating)) and np.isnan(result):
                            print("NaN")
                        else:
                            print(result)

            # Aggiorna solo DOPO l'elaborazione
            prev_pos = mouse_pos
            prev_time = now

        cv2.imshow("Mouse Lightness", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
