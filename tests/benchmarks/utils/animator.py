import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
from tqdm import tqdm


class BenchmarkAnimator:
    def __init__(self, pos_tensor, feature_dict, marker_names, bones_edges, fps=100.0, title="Benchmark"):
        self.pos_tensor = pos_tensor
        self.feature_dict = feature_dict
        self.marker_names = marker_names
        self.bones_edges = bones_edges
        self.fps = fps
        self.N_frames, self.N_joints, _ = pos_tensor.shape
        self.running = True

        self._setup_figure(title)
        self._setup_3d_plot()
        self._setup_2d_plots()
        self._setup_controls()

    def _setup_figure(self, title):
        self.fig = plt.figure(figsize=(16, 9))
        self.fig.suptitle(title, fontsize=16)
        num_subplots = len(self.feature_dict)
        self.gs = self.fig.add_gridspec(nrows=num_subplots, ncols=2, width_ratios=[1, 1.2])
        self.ax_3d = self.fig.add_subplot(self.gs[:, 0], projection='3d')
        self.axes_2d = [self.fig.add_subplot(self.gs[i, 1]) for i in range(num_subplots)]

        for ax in self.axes_2d[:-1]:
            ax.set_xticklabels([])
        self.axes_2d[-1].set_xlabel("Frame")

    def _setup_3d_plot(self):
        min_max = np.zeros((2, 3))
        for dim in range(3):
            min_max[0, dim], min_max[1, dim] = np.nanmin(self.pos_tensor[..., dim]), np.nanmax(
                self.pos_tensor[..., dim])

        self.ax_3d.set(xlim=[min_max[0, 0], min_max[1, 0]],
                       ylim=[min_max[0, 1], min_max[1, 1]],
                       zlim=[min_max[0, 2], min_max[1, 2]])

        self.ax_3d.view_init(elev=10, azim=45)
        self.ax_3d.xaxis.pane.fill = False
        self.ax_3d.yaxis.pane.fill = False
        self.ax_3d.zaxis.pane.fill = True

        self.scatter = self.ax_3d.scatter(self.pos_tensor[0, :, 0], self.pos_tensor[0, :, 1], self.pos_tensor[0, :, 2],
                                          s=20, c='red')
        self.lines = []
        if len(self.bones_edges) > 0:
            for edge in self.bones_edges:
                line, = self.ax_3d.plot([self.pos_tensor[0, edge[0], 0], self.pos_tensor[0, edge[1], 0]],
                                        [self.pos_tensor[0, edge[0], 1], self.pos_tensor[0, edge[1], 1]],
                                        [self.pos_tensor[0, edge[0], 2], self.pos_tensor[0, edge[1], 2]], 'k-', lw=1)
                self.lines.append(line)

    def _setup_2d_plots(self):
        self.cursors = []
        colors = plt.cm.tab10.colors

        for ax, (subplot_title, lines_dict) in zip(self.axes_2d, self.feature_dict.items()):
            ax.set_title(subplot_title)
            ax.grid(True, linestyle="--", alpha=0.6)
            for i, (line_label, data_array) in enumerate(lines_dict.items()):
                color = colors[i % len(colors)]
                ax.plot(data_array, label=line_label, color=color, linewidth=1.5)
                cursor, = ax.plot(0, data_array[0], 'ko', markersize=6)
                self.cursors.append((cursor, data_array))
            ax.legend(loc='upper right')

    def _setup_controls(self):
        slider_ax = plt.axes([0.15, 0.02, 0.65, 0.03])
        self.slider = Slider(slider_ax, 'Frame', 0, self.N_frames - 1, valinit=0, valstep=1)
        self.slider.on_changed(self._update)

        button_ax = plt.axes([0.85, 0.02, 0.08, 0.04])
        self.button = Button(button_ax, 'Play/Pause')
        self.button.on_clicked(self._toggle_play)

    def _update(self, val):
        frame = int(val)
        self.scatter._offsets3d = (self.pos_tensor[frame, :, 0], self.pos_tensor[frame, :, 1],
                                   self.pos_tensor[frame, :, 2])
        for i, edge in enumerate(self.bones_edges):
            self.lines[i].set_data_3d([self.pos_tensor[frame, edge[0], 0], self.pos_tensor[frame, edge[1], 0]],
                                      [self.pos_tensor[frame, edge[0], 1], self.pos_tensor[frame, edge[1], 1]],
                                      [self.pos_tensor[frame, edge[0], 2], self.pos_tensor[frame, edge[1], 2]])

        for cursor, data_array in self.cursors:
            cursor.set_data([frame], [data_array[frame]])
        self.fig.canvas.draw_idle()

    def _toggle_play(self, event):
        if self.running:
            self.anim.pause()
        else:
            self.anim.resume()
        self.running ^= True

    def save_video(self, save_path: str, video_fps: int = 30):
        """Saves the animation directly to a file with a beautiful tqdm progress bar."""
        print(f"\nRendering video to {save_path}...")

        # Initialize progress bar
        pbar = tqdm(total=self.N_frames, desc="Saving Frames", unit="frames")

        # Progress callback for FuncAnimation
        def update_progress(current_frame, total_frames):
            pbar.update(1)

        anim = animation.FuncAnimation(
            self.fig, self._update, frames=range(self.N_frames),
            interval=1000 / self.fps, repeat=False, cache_frame_data=False
        )

        anim.save(save_path, writer='ffmpeg', fps=video_fps, progress_callback=update_progress)
        pbar.close()
        plt.close(self.fig)  # Free up memory so we can render the next video seamlessly!

    def show(self):
        """Shows the interactive GUI (blocks the script until window is closed)."""
        self.anim = animation.FuncAnimation(
            self.fig, self._update, frames=range(self.N_frames),
            interval=1000 / self.fps, repeat=True, cache_frame_data=False
        )
        plt.show()