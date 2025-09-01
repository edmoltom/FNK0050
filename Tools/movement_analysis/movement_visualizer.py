import os
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from mpl_toolkits.mplot3d import Axes3D
import time

# --- Load data ---
base_path = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_path, "walking_forward_log.csv")
df = pd.read_csv(csv_path)

df = df.rename(columns={
    "fl_x": "paw0_x", "fl_y": "paw0_y", "fl_z": "paw0_z",
    "rl_x": "paw1_x", "rl_y": "paw1_y", "rl_z": "paw1_z",
    "rr_x": "paw2_x", "rr_y": "paw2_y", "rr_z": "paw2_z",
    "fr_x": "paw3_x", "fr_y": "paw3_y", "fr_z": "paw3_z",
})

offsets = [(25, 25), (-25, 25), (-25, -25), (25, -25)]
colors = ['r', 'g', 'b', 'm']
n_frames = len(df)

fig = plt.figure(figsize=(14, 8))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.3)

lines = []
for c in colors:
    line, = ax.plot([], [], [], color=c)
    lines.append(line)

ax.set_xlim(-100, 100)
ax.set_ylim(-100, 100)
ax.set_zlim(-120, -60)
ax.view_init(elev=20, azim=135)
ax.set_title("Robot Movement — Stable Timing")

# --- Sliders and button ---
ax_slider = plt.axes([0.2, 0.25, 0.6, 0.03])
frame_slider = Slider(ax_slider, 'Frame', 0, n_frames - 1, valinit=0, valstep=1)

ax_speed = plt.axes([0.2, 0.18, 0.6, 0.03])
speed_slider = Slider(ax_speed, 'Speed (slow-fast)', 1, 20, valinit=5, valstep=1)

ax_button = plt.axes([0.45, 0.08, 0.1, 0.04])
play_button = Button(ax_button, '▶ Play')

state = {
    "playing": False,
    "current_frame": 0,
}

def update_plot(frame):
    for i in range(4):
        x = df[f"paw{i}_x"][:frame] + offsets[i][0]
        z = df[f"paw{i}_z"][:frame] + offsets[i][1]
        y = -df[f"paw{i}_y"][:frame]
        lines[i].set_data(x, z)
        lines[i].set_3d_properties(y)
    fig.canvas.draw_idle()

def on_slider_change(val):
    frame = int(val)
    state["current_frame"] = frame
    update_plot(frame)

frame_slider.on_changed(on_slider_change)

# --- Controlled playback ---
def animate():
    while state["playing"] and state["current_frame"] < n_frames:
        update_plot(state["current_frame"])
        frame_slider.set_val(state["current_frame"])
        state["current_frame"] += 1
        interval = 0.05 * (21 - speed_slider.val)  
        plt.pause(interval)

    if state["current_frame"] >= n_frames:
        state["playing"] = False
        play_button.label.set_text("▶ Play")

def toggle_play(event):
    if state["playing"]:
        state["playing"] = False
        play_button.label.set_text("▶ Play")
    else:
        state["playing"] = True
        play_button.label.set_text("⏸ Pause")
        state["current_frame"] = int(frame_slider.val)
        animate()

play_button.on_clicked(toggle_play)

update_plot(0)
plt.show()
