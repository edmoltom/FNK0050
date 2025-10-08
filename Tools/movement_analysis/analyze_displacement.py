import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
log_filename = "walking_forward_log.csv"
log_path = os.path.join(script_dir, log_filename)

# Create output folder
output_folder = os.path.join(script_dir, "motion_analysis_results")
os.makedirs(output_folder, exist_ok=True)

# --- LOAD DATA ---
df = pd.read_csv(log_path)
df["timestamp"] = pd.to_numeric(df["timestamp"], errors='coerce')
dt = df["timestamp"].diff().fillna(0)

# --- FUNCTION FOR INTEGRATION AND PLOTTING ---
def process_axis(axis_label):
    accel = df[f"accel_{axis_label}"] - df[f"accel_{axis_label}"].mean()
    velocity = np.cumsum(accel * dt)
    displacement = np.cumsum(velocity * dt)

    # Plot velocity
    plt.figure(figsize=(10, 4))
    plt.plot(df["step"], velocity, label=f"Velocity {axis_label.upper()}")
    plt.title(f"Estimated Velocity ({axis_label.upper()}) from Acceleration")
    plt.xlabel("Step")
    plt.ylabel("Velocity (units/s)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f"velocity_{axis_label}.png"))
    plt.close()

    # Plot displacement
    plt.figure(figsize=(10, 4))
    plt.plot(df["step"], displacement, label=f"Displacement {axis_label.upper()}", color="green")
    plt.title(f"Estimated Displacement ({axis_label.upper()}) from Acceleration")
    plt.xlabel("Step")
    plt.ylabel("Displacement (relative units)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, f"displacement_{axis_label}.png"))
    plt.close()

    print(f"[OK] Axis {axis_label.upper()} -> velocity and displacement saved.")

# --- PROCESS ALL AXES ---
for axis in ['x', 'y', 'z']:
    process_axis(axis)

# --- TRAJECTORY PLOT (Top-down view X vs Y) ---
plt.figure(figsize=(8, 6))

# Recalcular desplazamientos si no están ya en variables
accel_x = df["accel_x"] - df["accel_x"].mean()
accel_y = df["accel_y"] - df["accel_y"].mean()
velocity_x = np.cumsum(accel_x * dt)
velocity_y = np.cumsum(accel_y * dt)
displacement_x = np.cumsum(velocity_x * dt)
displacement_y = np.cumsum(velocity_y * dt)

# Plot trajectory
plt.plot(displacement_x, displacement_y, marker='o', markersize=2, linewidth=1)
plt.title("Estimated XY Trajectory from Acceleration")
plt.xlabel("Displacement X (relative)")
plt.ylabel("Displacement Y (relative)")
plt.grid(True)
plt.axis('equal')  # keep proportions
plt.tight_layout()

trajectory_path = os.path.join(output_folder, "trajectory_xy.png")
plt.savefig(trajectory_path)
print(f"[OK] XY trajectory plot saved: {trajectory_path}")
plt.show()


print("\n✅ All motion plots saved in:", output_folder)