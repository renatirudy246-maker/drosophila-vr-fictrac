import os
import sys
import tkinter as tk
from tkinter import filedialog

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


BG_COLORS = {
    "white": "#E8ECEF",
    "green": "#5BAE73",
    "red": "#D95F5F",
}


def select_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="请选择果蝇实验数据 CSV 文件",
        filetypes=[("CSV Files", "*.csv")],
    )
    return file_path


def load_clean_data(file_path):
    print(f"正在读取文件: {file_path} ...")
    data_end_index = 0
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if not line.strip() or "=== Phase Summary ===" in line or "=== State Summary ===" in line:
                data_end_index = i
                break

    if data_end_index == 0:
        data_end_index = len(lines)

    try:
        return pd.read_csv(file_path, nrows=data_end_index - 1)
    except Exception as e:
        print(f"读取数据时发生错误: {e}")
        return None


def _to_numeric(df, col):
    return pd.to_numeric(df[col], errors="coerce")


def _state_alpha(brightness_label, brightness_value):
    label = str(brightness_label).strip().lower()
    if label == "dark":
        return 0.28
    if label == "medium":
        return 0.48
    if label == "bright":
        return 0.72
    try:
        return max(0.18, min(0.78, 0.18 + float(brightness_value) * 0.62))
    except (TypeError, ValueError):
        return 0.45


def _state_segments(work_df):
    segments = []
    for state_index in sorted(work_df["State_Index"].dropna().astype(int).unique()):
        state_df = work_df[work_df["State_Index"].astype(int) == state_index]
        if state_df.empty:
            continue
        first = state_df.iloc[0]
        start_t = float(state_df["Time_s"].iloc[0])
        end_t = float(state_df["Time_s"].iloc[-1])
        bg_name = str(first.get("State_BG_Name", "unknown")).strip().lower()
        brightness_label = str(first.get("State_Brightness_Label", "")).strip().lower()
        brightness = first.get("State_Brightness", "")
        stimulus_on = bool(int(first.get("State_Stimulus_On", 0)))
        segments.append(
            {
                "state": state_index,
                "start": start_t,
                "end": end_t,
                "bg": bg_name,
                "brightness_label": brightness_label,
                "brightness": brightness,
                "stimulus_on": stimulus_on,
                "color": BG_COLORS.get(bg_name, "#9CA3AF"),
                "alpha": _state_alpha(brightness_label, brightness),
            }
        )
    return segments


def _draw_state_spans(ax, segments, label=False):
    y0, y1 = ax.get_ylim()
    text_y = y0 + (y1 - y0) * 0.92
    for seg in segments:
        ax.axvspan(seg["start"], seg["end"], color=seg["color"], alpha=seg["alpha"], linewidth=0, zorder=0)
        if seg["stimulus_on"]:
            ax.axvspan(seg["start"], seg["end"], facecolor="none", edgecolor="#111111", hatch="///", alpha=0.08, zorder=1)
        ax.axvline(seg["start"], color="#B8B8B8", linewidth=0.6, alpha=0.65, zorder=1)
        if label:
            ax.text(
                (seg["start"] + seg["end"]) / 2,
                text_y,
                f"S{seg['state']:02d}",
                ha="center",
                va="top",
                fontsize=7,
                color="#222222",
                rotation=90,
                zorder=5,
            )
    if segments:
        ax.axvline(segments[-1]["end"], color="#B8B8B8", linewidth=0.6, alpha=0.65, zorder=1)


def _smooth_series(series, window=9):
    numeric = pd.to_numeric(series, errors="coerce")
    return numeric.rolling(window=window, center=True, min_periods=1).mean()


def plot_behavior_timeline(df, file_path):
    if df is None or df.empty:
        return

    required_cols = [
        "Time_s",
        "State_Index",
        "State_BG_Name",
        "State_Brightness_Label",
        "State_Brightness",
        "State_Stimulus_On",
        "Exp_Speed_cm_s",
        "Exp_AngVel_rad_s",
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"⚠️ 缺少行为时间图所需列: {missing}")
        return

    work_df = df.copy()
    work_df["Time_s"] = _to_numeric(work_df, "Time_s")
    work_df["State_Index"] = _to_numeric(work_df, "State_Index")
    work_df["Speed"] = _smooth_series(work_df["Exp_Speed_cm_s"], window=15)
    work_df["AbsAngVel"] = _smooth_series(pd.to_numeric(work_df["Exp_AngVel_rad_s"], errors="coerce").abs(), window=15)
    work_df = work_df.dropna(subset=["Time_s", "State_Index"])
    if work_df.empty:
        print("⚠️ 没有可绘制的时间序列数据。")
        return

    segments = _state_segments(work_df)
    filename = os.path.basename(file_path)
    base_name = os.path.splitext(filename)[0]
    save_dir = os.path.join(os.path.dirname(file_path), "BehaviorTimeline")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{base_name}_behavior_timeline.png")

    fig = plt.figure(figsize=(15.2, 8.0), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[2.2, 1.7, 0.72], hspace=0.08)
    ax_speed = fig.add_subplot(gs[0, 0])
    ax_ang = fig.add_subplot(gs[1, 0], sharex=ax_speed)
    ax_state = fig.add_subplot(gs[2, 0], sharex=ax_speed)

    speed_ymax = max(1.0, float(np.nanpercentile(work_df["Speed"], 98)) * 1.25)
    ang_ymax = max(0.5, float(np.nanpercentile(work_df["AbsAngVel"], 98)) * 1.25)

    ax_speed.set_ylim(0, speed_ymax)
    ax_ang.set_ylim(0, ang_ymax)
    _draw_state_spans(ax_speed, segments)
    _draw_state_spans(ax_ang, segments)

    ax_speed.plot(work_df["Time_s"], work_df["Speed"], color="#1F4E9A", linewidth=1.05, zorder=3)
    ax_ang.plot(work_df["Time_s"], work_df["AbsAngVel"], color="#4A4A4A", linewidth=1.0, zorder=3)

    ax_speed.set_title(f"Behavior timeline by randomized state\n{filename}", fontsize=15, pad=12)
    ax_speed.set_ylabel("Speed (cm/s)", fontsize=11)
    ax_ang.set_ylabel("|Angular velocity| (rad/s)", fontsize=11)
    ax_ang.set_xlabel("")

    for ax in (ax_speed, ax_ang):
        ax.grid(True, axis="y", linestyle="--", linewidth=0.55, alpha=0.35)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(labelsize=9)

    ax_state.set_ylim(0, 1)
    ax_state.set_yticks([])
    ax_state.set_xlabel("Experiment time (s)", fontsize=11)
    ax_state.spines["top"].set_visible(False)
    ax_state.spines["right"].set_visible(False)
    ax_state.spines["left"].set_visible(False)

    for seg in segments:
        width = max(0.0, seg["end"] - seg["start"])
        ax_state.broken_barh(
            [(seg["start"], width)],
            (0.12, 0.62),
            facecolors=seg["color"],
            alpha=seg["alpha"],
            edgecolors="#222222" if seg["stimulus_on"] else "#8A8A8A",
            linewidth=0.8 if seg["stimulus_on"] else 0.45,
            hatch="///" if seg["stimulus_on"] else None,
        )
        ax_state.text(
            seg["start"] + width / 2,
            0.43,
            f"S{seg['state']:02d}",
            ha="center",
            va="center",
            fontsize=7,
            color="#111111",
        )
        ax_state.text(
            seg["start"] + width / 2,
            0.03,
            f"{seg['bg']} {seg['brightness_label']}",
            ha="center",
            va="bottom",
            fontsize=6.5,
            color="#4D4D4D",
            rotation=35,
        )

    if segments:
        ax_state.set_xlim(segments[0]["start"], segments[-1]["end"])

    legend_handles = [
        LineOrPatch("#1F4E9A", "speed"),
        LineOrPatch("#4A4A4A", "|angular velocity|"),
        Patch(facecolor="#FFFFFF", edgecolor="#222222", hatch="///", label="stimulus ON"),
        Patch(facecolor="#FFFFFF", edgecolor="#8A8A8A", label="stimulus OFF"),
        Patch(facecolor=BG_COLORS["white"], edgecolor="none", alpha=0.72, label="white BG"),
        Patch(facecolor=BG_COLORS["green"], edgecolor="none", alpha=0.72, label="green BG"),
        Patch(facecolor=BG_COLORS["red"], edgecolor="none", alpha=0.72, label="red BG"),
    ]
    ax_speed.legend(handles=legend_handles, loc="upper right", fontsize=8, frameon=False, ncol=2)

    fig.savefig(save_path, dpi=300, bbox_inches="tight")
    print(f"行为时间图已导出至: {save_path}")
    plt.close(fig)


def LineOrPatch(color, label):
    return plt.Line2D([0], [0], color=color, linewidth=1.3, label=label)


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else select_file()
    if not csv_path or not os.path.exists(csv_path):
        print("未选择文件，程序退出。")
        sys.exit()

    fly_data = load_clean_data(csv_path)
    plot_behavior_timeline(fly_data, csv_path)
