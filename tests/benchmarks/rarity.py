import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
from pathlib import Path
from io import StringIO
import ast
import time

# --- Import library components ---
from pyeyesweb.data_models.sliding_window import SlidingWindow
from pyeyesweb.analysis_primitives.rarity import Rarity

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
num_file = 0
fps = 100.0  # Qualisys default, adjust if needed

# Use a list of window lengths instead of a single value
window_lengths = [50, 100, 150]

feature_to_plot = 'Rarity'
signal = "Kinematics (Speed)"
joint_names = ["HAND_RIGHT", "HAND_LEFT"]


# ==========================================
# 2. DATA LOADING & PRE-PROCESSING
# ==========================================
def read_tsv_qualysis(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    data_start_idx = next(i for i, line in enumerate(lines) if line.startswith("Frame"))
    header = lines[data_start_idx].strip().split('\t')
    data_lines = lines[data_start_idx + 1:]

    df = pd.read_csv(StringIO(''.join(data_lines)), sep='\t', names=header)
    return df


txt_file = "data/trial0001_impulsive.tsv"

print(f"Reading file: {txt_file}")
df = read_tsv_qualysis(txt_file)
df = df.iloc[:, 3:]

print("Cleaning data...")
df.replace(0, np.nan, inplace=True)
df.interpolate(method='linear', inplace=True)
df.ffill(inplace=True)
df.bfill(inplace=True)

# Extract marker position tables
markersPosTableX = df.iloc[:, 0::3]
markersPosTableY = df.iloc[:, 1::3]
markersPosTableZ = df.iloc[:, 2::3]

# Sort columns alphabetically by marker name
markersPosTableX = markersPosTableX.reindex(sorted(markersPosTableX.columns), axis=1)
markersPosTableY = markersPosTableY.reindex(sorted(markersPosTableY.columns), axis=1)
markersPosTableZ = markersPosTableZ.reindex(sorted(markersPosTableZ.columns), axis=1)

# Clean names
clean_name = lambda name: name[:-2].strip()
markersPosTableX = markersPosTableX.rename(columns={c: clean_name(c) for c in markersPosTableX})
markersPosTableY = markersPosTableY.rename(columns={c: clean_name(c) for c in markersPosTableY})
markersPosTableZ = markersPosTableZ.rename(columns={c: clean_name(c) for c in markersPosTableZ})

markers_names = list(markersPosTableX.columns)
signalX = markersPosTableX.values
signalY = markersPosTableY.values
signalZ = markersPosTableZ.values

# Create Master Position Tensor: Shape (Time, N_joints, 3)
pos_tensor = np.stack([signalX, signalY, signalZ], axis=-1)
N_frames, N_joints, N_dims = pos_tensor.shape

# Calculate Velocity
print("Computing Kinematics (Speed)...")
vel_tensor = np.zeros_like(pos_tensor)
vel_tensor[1:] = (pos_tensor[1:] - pos_tensor[:-1]) * fps

# ==========================================
# 3. FEATURE COMPUTATION
# ==========================================
print("Computing Rarity features...")
rarity_feature = Rarity(alpha=0.5)

# Dictionaries to store results: results[window_len][joint_name] -> array of values
results = {
    w: {joint: np.zeros(N_frames) for joint in joint_names}
    for w in window_lengths
}

import tqdm

for w in window_lengths:
    for joint in joint_names:
        joint_idx = markers_names.index(joint)

        # Independent sliding window for this joint's speed at this window length
        sw_speed = SlidingWindow(max_length=w, n_signals=1, n_dims=1)

        for frame in tqdm.tqdm(range(N_frames), desc=f"Processing {joint} (w={w})"):
            # Extract 1D magnitudes
            speed = np.linalg.norm(vel_tensor[frame, joint_idx, :])

            sw_speed.append([[speed]])
            res_speed = rarity_feature(sw_speed)

            # Safe extraction using the new contract
            results[w][joint][frame] = res_speed.rarity if res_speed.is_valid else 0.0

# ==========================================
# 4. PLOTTING SETUP
# ==========================================
# %matplotlib qt  # Uncomment if running in Jupyter/Spyder

# Bones Setup
bones_file_path = "data/bones_from_names.txt"

try:
    with open(bones_file_path, "r") as f:
        bones_names = [ast.literal_eval(l.strip()) for l in f.readlines() if l.strip()]
    bones = [[markers_names.index(b[0]), markers_names.index(b[1])]
             for b in bones_names if b[0] in markers_names and b[1] in markers_names]
except FileNotFoundError:
    print(f"Warning: {bones_file_path} not found. Using empty skeleton.")
    bones = []

edges = np.array(bones)
adjacencyMatrix = np.zeros((N_joints, N_joints), dtype=bool)
if len(edges) > 0:
    adjacencyMatrix[edges[:, 0], edges[:, 1]] = True

# Initialize Figure
fig = plt.figure(f"3D Movement | Feature: {feature_to_plot}", figsize=(19.20, 10.80))
plt.clf()

# 3D Subplot
ax = fig.add_axes([0, -0.16, 1, .85], projection='3d')
ax.view_init(elev=0, azim=0)

# Three Stacked Subplots for Speed Rarity at different window lengths
left, bottom, width, total_height = 0.05, 0.55, 0.9, 0.42
gap = 0.04
height = (total_height - 2 * gap) / 3

ax_w1 = fig.add_axes([left, bottom + 2 * (height + gap), width, height])
ax_w2 = fig.add_axes([left, bottom + height + gap, width, height])
ax_w3 = fig.add_axes([left, bottom, width, height])

axes_list = [ax_w1, ax_w2, ax_w3]

# Plot the data lines
colors = {"HAND_RIGHT": "blue", "HAND_LEFT": "orange"}
for a, w in zip(axes_list, window_lengths):
    for joint in joint_names:
        a.plot(results[w][joint], color=colors[joint], linewidth=1.5, label=f"{joint}")

    a.set_ylabel(f'Rarity (w={w})')
    a.legend(loc='upper right')

    # Calculate Max Y considering both joints for this window
    max_y = max(np.max(results[w]["HAND_RIGHT"]), np.max(results[w]["HAND_LEFT"]))
    a.set_ylim(-0.05, max_y * 1.1 + 0.1)

    a.grid(axis='both', color="#cccccc")
    a.set_xticks(list(range(0, N_frames, max(1, N_frames // 10))))

ax_w1.set_title(f'Feature: {feature_to_plot} | Signal: {signal}', fontsize=12)
ax_w3.set_xlabel('Frame')

ax_w1.set_xticklabels([])  # Hide x-axis ticks for top plot
ax_w2.set_xticklabels([])  # Hide x-axis ticks for middle plot

# Initialize Cursors
cursors = []
for a, w in zip(axes_list, window_lengths):
    for joint in joint_names:
        c, = a.plot(0, 0, 'ko', markersize=5)
        cursors.append((c, w, joint))

# 3D View Boundaries
minMax = np.zeros((2, 3))
minMax[0, 0], minMax[1, 0] = np.nanmin(signalX), np.nanmax(signalX)
minMax[0, 1], minMax[1, 1] = np.nanmin(signalY), np.nanmax(signalY)
minMax[0, 2], minMax[1, 2] = np.nanmin(signalZ), np.nanmax(signalZ)

ax.set_xlim([minMax[0, 0], minMax[1, 0]])
ax.set_ylim([minMax[0, 1], minMax[1, 1]])
ax.set_zlim([minMax[0, 2], minMax[1, 2]])

# 3D Styling
plt.rcParams['grid.color'] = 'white'
ax.tick_params(axis='both', colors='white')
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = True
ax.xaxis.pane.set_edgecolor("w")
ax.yaxis.pane.set_edgecolor('w')
ax.zaxis.pane.set_edgecolor("w")
ax.xaxis.line.set_visible(False)
ax.yaxis.line.set_visible(False)
ax.zaxis.line.set_visible(False)

# Initial 3D Scatters and Lines
joint_colors = ["red"] * N_joints
for joint in joint_names:
    if joint in markers_names:
        joint_colors[markers_names.index(joint)] = colors[joint]

scatter_plot = ax.scatter(signalX[0], signalY[0], signalZ[0], s=20, c=joint_colors)
allLines = []
for i in range(len(adjacencyMatrix)):
    for j in range(len(adjacencyMatrix)):
        if adjacencyMatrix[i, j]:
            line, = ax.plot([signalX[0, i], signalX[0, j]],
                            [signalY[0, i], signalY[0, j]],
                            [signalZ[0, i], signalZ[0, j]],
                            color='k', linestyle='-', linewidth=0.7)
            allLines.append(line)

# ==========================================
# 5. ANIMATION & CONTROLS
# ==========================================
slider_ax = plt.axes([0.08, 0, 0.8, 0.03])
slider = Slider(slider_ax, 'Frame:', 0, N_frames - 1, valinit=0, valstep=1)


def update_plot(val):
    val = int(val)

    # Update 3D scatter
    scatter_plot._offsets3d = (signalX[val], signalY[val], signalZ[val])

    # Update bones
    k = 0
    for i in range(len(adjacencyMatrix)):
        for j in range(len(adjacencyMatrix)):
            if adjacencyMatrix[i, j]:
                allLines[k].set_xdata([signalX[val, i], signalX[val, j]])
                allLines[k].set_ydata([signalY[val, i], signalY[val, j]])
                allLines[k].set_3d_properties([signalZ[val, i], signalZ[val, j]])
                k += 1

    # Update cursors across all 3 subplots (2 cursors per subplot)
    for c, w, joint in cursors:
        c.set_xdata([val])
        c.set_ydata([results[w][joint][val]])

    fig.canvas.draw_idle()


slider.on_changed(update_plot)

# Play/Pause Logic
button_ax = plt.axes([0.92, 0.005, 0.06, 0.03])
button = Button(button_ax, 'Pause/Play')
running = True


def pause_play(event):
    global running
    if running:
        anim.pause()
    else:
        anim.resume()
    running ^= True


button.on_clicked(pause_play)

# Animation Loop
anim = animation.FuncAnimation(fig, slider.set_val, frames=range(0, N_frames - 1, 1),
                               interval=1000 / fps, repeat=True, cache_frame_data=False)

# Saving Logic
last_ = (time.perf_counter(), 0)
remaining_time = [1]


def _print_progress(current_frame, total_frames):
    global last_
    now = time.perf_counter()
    dt = now - last_[0]
    last_ = (now, current_frame)
    if current_frame % 5 == 2:
        remaining_time.append(dt * (total_frames - current_frame))
        if len(remaining_time) > 100:
            remaining_time.pop(0)
        avg_remaining_time = sum(remaining_time) / len(remaining_time)
        print(f"Saving frame {current_frame}/{total_frames} | ETA={avg_remaining_time:.1f}s", end="\r")


file_stem = Path(txt_file).stem

# Create a safe file name in the current directory
save_path = f"result_{file_stem}_Rarity_MultiWindow.mp4"

print(f"Starting animation save to: {save_path}")
anim.save(save_path, writer='ffmpeg', fps=30, progress_callback=_print_progress)

anim.pause()
plt.show()