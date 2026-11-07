import os
import re
import sys
import tkinter as tk
from tkinter import filedialog

import matplotlib.pyplot as plt
import pandas as pd
from output_naming import find_csv_in_folder, resolve_input_path

plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial"]
plt.rcParams["axes.unicode_minus"] = False

SMOOTHING_WINDOW = 5
OUTPUT_DIR_NAME = "TrajectoryPlots"
AXIS_X_LABEL = "Virtual world Y displacement (cm)"
AXIS_Y_LABEL = "Virtual world X displacement (cm)"


def select_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select a Drosophila trajectory CSV file",
        filetypes=[("CSV Files", "*.csv")],
    )


def load_clean_data(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None

    data_end_index = 0
    with open(file_path, "r", encoding="utf-8") as file:
        for i, line in enumerate(file):
            if not line.strip() or "=== Phase Summary ===" in line or "=== State Summary ===" in line:
                data_end_index = i
                break

    if data_end_index == 0:
        with open(file_path, "r", encoding="utf-8") as file:
            data_end_index = sum(1 for _ in file)

    try:
        return pd.read_csv(file_path, nrows=max(data_end_index - 1, 0))
    except Exception as exc:
        print(f"Could not read the CSV file: {exc}")
        return None


def safe_name(value):
    text = "" if pd.isna(value) else str(value)
    text = text.strip() or "unknown"
    return re.sub(r'[<>:"/\\|?*\s]+', "_", text).strip("_")


def smooth_xy(df, x_col, y_col):
    work_df = df[[x_col, y_col]].copy()
    work_df[x_col] = pd.to_numeric(work_df[x_col], errors="coerce")
    work_df[y_col] = pd.to_numeric(work_df[y_col], errors="coerce")
    work_df = work_df.dropna(subset=[x_col, y_col])
    if work_df.empty:
        return work_df

    work_df[x_col] = work_df[x_col] - work_df[x_col].iloc[0]
    work_df[y_col] = work_df[y_col] - work_df[y_col].iloc[0]
    window = min(SMOOTHING_WINDOW, len(work_df))
    work_df["Smooth_X"] = work_df[x_col].rolling(window=window, center=True, min_periods=1).mean()
    work_df["Smooth_Y"] = work_df[y_col].rolling(window=window, center=True, min_periods=1).mean()
    return work_df


def state_meta(state_df, state_index):
    first = state_df.iloc[0]
    block = first.get("State_Block", "")
    bg_name = first.get("State_BG_Name", "")
    brightness = first.get("State_Brightness_Label", "")
    stimulus_on = first.get("State_Stimulus_On", "")
    duration = 0.0
    if "Time_s" in state_df.columns and len(state_df) > 1:
        duration = float(pd.to_numeric(state_df["Time_s"], errors="coerce").max() - pd.to_numeric(state_df["Time_s"], errors="coerce").min())
    return {
        "index": int(state_index),
        "block": block,
        "bg_name": bg_name,
        "brightness": brightness,
        "stimulus_on": stimulus_on,
        "duration": max(duration, 0.0),
    }


def build_state_paths(df):
    if "VR_Fly_X_cm" not in df.columns or "VR_Fly_Y_cm" not in df.columns:
        print("Error: CSV is missing VR_Fly_X_cm / VR_Fly_Y_cm; cannot plot virtual-world trajectories.")
        return {}, 1.0

    paths = {}
    max_abs = 1.0
    for state_index in sorted(df["State_Index"].dropna().astype(int).unique()):
        state_df = df[df["State_Index"].astype(int) == state_index]
        if state_df.empty:
            continue
        path_df = smooth_xy(state_df, "VR_Fly_X_cm", "VR_Fly_Y_cm")
        if path_df.empty:
            continue
        paths[state_index] = path_df
        max_abs = max(
            max_abs,
            float(path_df["Smooth_X"].abs().max()),
            float(path_df["Smooth_Y"].abs().max()),
        )

    axis_limit = max_abs * 1.08
    return paths, axis_limit


def build_continuous_state_paths(df):
    if "VR_Fly_X_cm" not in df.columns or "VR_Fly_Y_cm" not in df.columns:
        print("Error: CSV is missing VR_Fly_X_cm / VR_Fly_Y_cm; cannot plot the continuous trajectory.")
        return {}, 1.0

    work_df = df.copy()
    work_df["VR_Fly_X_cm"] = pd.to_numeric(work_df["VR_Fly_X_cm"], errors="coerce")
    work_df["VR_Fly_Y_cm"] = pd.to_numeric(work_df["VR_Fly_Y_cm"], errors="coerce")
    work_df = work_df.dropna(subset=["VR_Fly_X_cm", "VR_Fly_Y_cm", "State_Index"])
    if work_df.empty:
        return {}, 1.0

    work_df["World_X"] = work_df["VR_Fly_X_cm"] - work_df["VR_Fly_X_cm"].iloc[0]
    work_df["World_Y"] = work_df["VR_Fly_Y_cm"] - work_df["VR_Fly_Y_cm"].iloc[0]
    window = min(SMOOTHING_WINDOW, len(work_df))
    work_df["Smooth_X"] = work_df["World_X"].rolling(window=window, center=True, min_periods=1).mean()
    work_df["Smooth_Y"] = work_df["World_Y"].rolling(window=window, center=True, min_periods=1).mean()

    paths = {}
    max_abs = 1.0
    for state_index in sorted(work_df["State_Index"].dropna().astype(int).unique()):
        path_df = work_df[work_df["State_Index"].astype(int) == state_index]
        if path_df.empty:
            continue
        paths[state_index] = path_df
        max_abs = max(
            max_abs,
            float(path_df["Smooth_X"].abs().max()),
            float(path_df["Smooth_Y"].abs().max()),
        )

    axis_limit = max_abs * 1.08
    return paths, axis_limit


def plot_state_trajectory(path_df, output_png, meta, axis_limit):
    fig, ax = plt.subplots(figsize=(7.2, 7.2))

    stim_text = "Stimulus" if str(meta["stimulus_on"]).strip() in {"1", "True", "true"} else "No stimulus"
    title = (
        f"State {meta['index']:02d} | {meta['block']} | {meta['bg_name']} / {meta['brightness']} | "
        f"{stim_text} | {meta['duration']:.2f}s"
    )

    ax.plot(path_df["Smooth_Y"], path_df["Smooth_X"], color="#0C9B75", linewidth=1.5, alpha=0.9)
    ax.scatter(path_df["Smooth_Y"].iloc[0], path_df["Smooth_X"].iloc[0], color="#159447", s=52, label="Start", zorder=3)
    ax.scatter(path_df["Smooth_Y"].iloc[-1], path_df["Smooth_X"].iloc[-1], color="#C93B3B", s=60, marker="X", label="End", zorder=3)
    ax.set_title(title, fontsize=13, pad=12)
    ax.set_xlabel(AXIS_X_LABEL)
    ax.set_ylabel(AXIS_Y_LABEL)
    ax.set_xlim(-axis_limit, axis_limit)
    ax.set_ylim(-axis_limit, axis_limit)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)
    ax.axhline(0, color="#888888", linewidth=0.7, alpha=0.45)
    ax.axvline(0, color="#888888", linewidth=0.7, alpha=0.45)
    ax.legend(loc="upper right", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_png, bbox_inches="tight", dpi=170)
    print(f"Saved: {output_png}")
    plt.close(fig)


def plot_all_state_trajectories(state_paths, output_png, axis_limit):
    fig, ax = plt.subplots(figsize=(8.2, 8.2))
    cmap = plt.get_cmap("tab20")

    for state_index in sorted(state_paths):
        path_df = state_paths.get(state_index)
        if path_df is None or path_df.empty:
            continue
        color = cmap((state_index - 1) % cmap.N)
        ax.plot(
            path_df["Smooth_Y"],
            path_df["Smooth_X"],
            color=color,
            linewidth=1.25,
            alpha=0.9,
            label=f"State {state_index:02d}",
        )
        if state_index == 1:
            ax.scatter(path_df["Smooth_Y"].iloc[0], path_df["Smooth_X"].iloc[0], color="#159447", s=42, label="Start", zorder=4)

    last_state = max(state_paths) if state_paths else None
    if last_state is not None:
        last_path = state_paths[last_state]
        ax.scatter(last_path["Smooth_Y"].iloc[-1], last_path["Smooth_X"].iloc[-1], color="#C93B3B", s=52, marker="X", label="End", zorder=4)

    ax.set_title("All States | Continuous VR World Trajectory", fontsize=14, pad=12)
    ax.set_xlabel(AXIS_X_LABEL)
    ax.set_ylabel(AXIS_Y_LABEL)
    ax.set_xlim(-axis_limit, axis_limit)
    ax.set_ylim(-axis_limit, axis_limit)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.35)
    ax.axhline(0, color="#888888", linewidth=0.7, alpha=0.45)
    ax.axvline(0, color="#888888", linewidth=0.7, alpha=0.45)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8, frameon=False, ncol=1)

    plt.tight_layout()
    plt.savefig(output_png, bbox_inches="tight", dpi=170)
    print(f"Saved: {output_png}")
    plt.close(fig)


def plot_state_trajectories(file_path):
    df = load_clean_data(file_path)
    if df is None or df.empty:
        return

    if "State_Index" not in df.columns:
        print("Error: CSV is missing State_Index; cannot split trajectories by state.")
        return

    df = df.copy()
    df["State_Index"] = pd.to_numeric(df["State_Index"], errors="coerce")
    df = df.dropna(subset=["State_Index"])
    if df.empty:
        print("Error: State_Index contains no valid data.")
        return

    experiment_dir = os.path.dirname(os.path.abspath(file_path))
    output_dir = os.path.join(experiment_dir, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    state_paths, axis_limit = build_state_paths(df)
    if not state_paths:
        print("No virtual-world trajectory data to plot.")
        return

    continuous_paths, continuous_axis_limit = build_continuous_state_paths(df)
    if continuous_paths:
        all_output_png = os.path.join(output_dir, "00_all_states.png")
        plot_all_state_trajectories(continuous_paths, all_output_png, continuous_axis_limit)

    generated = 0
    for state_index in sorted(state_paths):
        state_df = df[df["State_Index"].astype(int) == state_index]
        path_df = state_paths.get(state_index)
        if state_df.empty or path_df is None:
            print(f"State {state_index:02d}: No valid VR trajectory data; skipping.")
            continue

        meta = state_meta(state_df, state_index)
        filename = (
            f"{state_index:02d}_"
            f"{safe_name(meta['block'])}_"
            f"{safe_name(meta['bg_name'])}_"
            f"{safe_name(meta['brightness'])}.png"
        )
        output_png = os.path.join(output_dir, filename)
        plot_state_trajectory(path_df, output_png, meta, axis_limit)
        generated += 1

    print(f"\nFinished: generated {generated} state trajectory plots")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else select_file()
    csv_path = resolve_input_path(input_path)
    if not csv_path or not os.path.exists(csv_path):
        print("No usable CSV file found. Exiting.")
        sys.exit()

    plot_state_trajectories(csv_path)
