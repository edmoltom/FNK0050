# analyze_stability.py
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- SETUP ---
script_dir = os.path.dirname(os.path.abspath(__file__))
log_filename = "walking_forward_log.csv"
log_path = os.path.join(script_dir, log_filename)

# Create output folder
output_folder = os.path.join(script_dir, "stability_analysis_results")
os.makedirs(output_folder, exist_ok=True)

# Load CSV with timestamp and contact info
df = pd.read_csv(log_path)

# Detect which legs are in contact
leg_names = ["fl", "rl", "rr", "fr"]
contact_matrix = pd.DataFrame(index=df.index)
for leg in leg_names:
    max_y = df[f"{leg}_y"].max()
    min_y = df[f"{leg}_y"].min()
    threshold = max_y - 0.15 * (max_y - min_y)
    contact_matrix[leg] = df[f"{leg}_y"] >= threshold

# Count number of legs in contact at each step
df["legs_in_contact"] = contact_matrix.sum(axis=1)
critical_indices = df[df["legs_in_contact"] <= 2].index

# --- PLOT 1: Combined stability and contact heatmap ---
fig, ax1 = plt.subplots(figsize=(12, 6))

# Heatmap as background
extent = [0, len(df), -0.5, 3.5]
ax1.imshow(contact_matrix.T.values, cmap='Greys', aspect='auto',
           interpolation='nearest', extent=extent, alpha=0.4)

# Label legs on left axis
ax1.set_yticks(range(len(leg_names)))
ax1.set_yticklabels(leg_names)
ax1.set_ylabel('Leg')
ax1.set_xlabel('Step')

# Plot pitch and roll on second axis
ax2 = ax1.twinx()
ax2.plot(df["step"], df["pitch"], label="Pitch (°)", color="orange")
ax2.plot(df["step"], df["roll"], label="Roll (°)", color="purple")
ax2.scatter(df.loc[critical_indices, "step"],
            df.loc[critical_indices, "pitch"],
            color='red', label="Critical (≤2 legs)", zorder=5, s=20)
ax2.set_ylabel('Angle (degrees)')

# Combined legend
lines, labels = ax2.get_legend_handles_labels()
ax2.legend(lines, labels, loc='upper right')

plt.title("Combined Stability Analysis and Leg Contact Map")
plt.tight_layout()

# Save combined figure
plot_combined_path = os.path.join(output_folder, "combined_stability.png")
plt.savefig(plot_combined_path)
plt.close()

print("\n✅ All stability plots saved in:", output_folder)