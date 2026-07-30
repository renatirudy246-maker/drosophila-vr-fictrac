import json
import math
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


def select_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="请选择果蝇实验数据 CSV 文件", filetypes=[("CSV Files", "*.csv")])


def safe_name(value):
    text = "" if pd.isna(value) else str(value)
    text = text.strip() or "unknown"
    return re.sub(r'[<>:"/\\|?*\s]+', "_", text).strip("_")


def rgb_to_hex(rgb_str, default_hex):
    try:
        r, g, b = map(int, str(rgb_str).split(","))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return default_hex


def rgb_to_mpl(rgb_str, brightness=1.0, default=(1.0, 1.0, 1.0)):
    try:
        r, g, b = map(int, str(rgb_str).split(","))
        scale = max(0.0, min(1.0, float(brightness)))
        return (r / 255.0 * scale, g / 255.0 * scale, b / 255.0 * scale)
    except Exception:
        return default


def state_display_color(bg_name, brightness_label):
    bg_key = str(bg_name).strip().lower()
    level_key = str(brightness_label).strip().lower()
    palette = {
        "white": {
            "dark": "#D4D7DB",
            "medium": "#ECEFF2",
            "bright": "#FFFFFF",
        },
        "green": {
            "dark": "#2E7D32",
            "medium": "#4CAF50",
            "bright": "#8BCF8F",
        },
        "red": {
            "dark": "#C62828",
            "medium": "#E53935",
            "bright": "#FF6B6B",
        },
    }
    return palette.get(bg_key, {}).get(level_key, "#B8B8B8")


def load_clean_data(file_path):
    if not os.path.exists(file_path):
        return None

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


def load_config(df=None):
    config = {
        "V_BAR_COUNT": 2,
        "V_BAR_SPACING_DEG": 180.0,
        "BAR_VISUAL_ANGLE_DEG": 30.0,
        "MOVEMENT_SPEED_THRESHOLD": 0.05,
        "MOVEMENT_ANG_VEL_THRESHOLD": 0.05,
        "BG_COLOR": "255,255,255",
        "BAR_COLOR": "0,0,0",
    }
    if os.path.exists("settings.json"):
        try:
            with open("settings.json", "r", encoding="utf-8") as f:
                loaded = json.load(f)
                for k in config.keys():
                    if k in loaded:
                        config[k] = float(loaded[k]) if k not in ["V_BAR_COUNT", "BG_COLOR", "BAR_COLOR"] else loaded[k]
        except Exception as e:
            print(f"读取配置失败，使用默认值。错误: {e}")

    if df is not None and not df.empty:
        snapshot_map = {
            "V_BAR_COUNT": ("Cfg_V_BAR_COUNT", int),
            "V_BAR_SPACING_DEG": ("Cfg_V_BAR_SPACING_DEG", float),
            "BAR_VISUAL_ANGLE_DEG": ("Cfg_BAR_VISUAL_ANGLE_DEG", float),
            "MOVEMENT_SPEED_THRESHOLD": ("Cfg_MOVEMENT_SPEED_THRESHOLD", float),
            "MOVEMENT_ANG_VEL_THRESHOLD": ("Cfg_MOVEMENT_ANG_VEL_THRESHOLD", float),
            "BG_COLOR": ("Cfg_BG_COLOR", str),
            "BAR_COLOR": ("Cfg_BAR_COLOR", str),
        }
        first_row = df.iloc[0]
        for key, (column_name, caster) in snapshot_map.items():
            if column_name in df.columns and pd.notna(first_row[column_name]) and first_row[column_name] != "":
                try:
                    config[key] = caster(first_row[column_name])
                except (TypeError, ValueError):
                    pass

    config["V_BAR_COUNT"] = int(config["V_BAR_COUNT"])
    return config


def _stimulus_angles(cfg):
    first_bar_original = (0 - (cfg["V_BAR_COUNT"] - 1) / 2.0) * math.radians(cfg["V_BAR_SPACING_DEG"])
    rotation_offset = -first_bar_original
    bar_angles = []
    for i in range(cfg["V_BAR_COUNT"]):
        original = (i - (cfg["V_BAR_COUNT"] - 1) / 2.0) * math.radians(cfg["V_BAR_SPACING_DEG"])
        shifted = original + rotation_offset
        shifted = (shifted + math.pi) % (2 * math.pi) - math.pi
        bar_angles.append(shifted)
    return rotation_offset, bar_angles


def _state_meta(state_df):
    first = state_df.iloc[0]
    return {
        "state": int(first.get("State_Index", 0)),
        "block": first.get("State_Block", ""),
        "bg_name": first.get("State_BG_Name", ""),
        "bg_color": first.get("State_BG_Color", ""),
        "brightness": first.get("State_Brightness_Label", ""),
        "brightness_value": first.get("State_Brightness", 1.0),
        "duration": float(pd.to_numeric(state_df["Time_s"], errors="coerce").max() - pd.to_numeric(state_df["Time_s"], errors="coerce").min()),
    }


def _moving_mask(state_df, cfg):
    speed = pd.to_numeric(state_df.get("Exp_Speed_cm_s"), errors="coerce").fillna(0)
    ang_vel = pd.to_numeric(state_df.get("Exp_AngVel_rad_s"), errors="coerce").fillna(0).abs()
    return (speed > cfg["MOVEMENT_SPEED_THRESHOLD"]) | (ang_vel > cfg["MOVEMENT_ANG_VEL_THRESHOLD"])


def _plot_single_state_polar(state_df, output_png, cfg):
    meta = _state_meta(state_df)
    rotation_offset, bar_angles = _stimulus_angles(cfg)

    angles = pd.to_numeric(state_df["Stim_Mapped_Angle_rad"], errors="coerce") + rotation_offset
    angles = (angles + np.pi) % (2 * np.pi) - np.pi
    moving = _moving_mask(state_df, cfg)
    moving_angles = angles[moving & angles.notna()]
    total_moving = int(len(moving_angles))

    if total_moving == 0:
        moving_angles = angles[angles.notna()]
        total_moving = int(len(moving_angles))

    bins = np.linspace(-np.pi, np.pi, 37)
    counts, _ = np.histogram(moving_angles, bins=bins)
    percentages = (counts / total_moving * 100.0) if total_moving > 0 else counts.astype(float)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    width = bins[1] - bins[0]
    max_radius = max(1.0, float(percentages.max()) if len(percentages) else 1.0)

    fig, ax = plt.subplots(figsize=(7.2, 7.2), subplot_kw={"polar": True})
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)

    ax.bar(
        bin_centers,
        percentages,
        width=width,
        bottom=0.0,
        color="#2F5DA8",
        alpha=0.72,
        edgecolor="white",
        linewidth=0.7,
        zorder=5,
    )

    ax.set_ylim(0, max_radius * 1.34)
    ax.set_yticks([])
    ax.grid(True, linestyle=":", linewidth=0.7, alpha=0.55, zorder=1)

    plot_bar_hex = rgb_to_hex(cfg["BAR_COLOR"], "#000000")
    plot_bg_color = state_display_color(meta["bg_name"], meta["brightness"])
    stim_half_width = math.radians(cfg["BAR_VISUAL_ANGLE_DEG"]) / 2.0
    if "Stim_VisualHalfWidth_rad" in state_df.columns:
        valid_half_widths = pd.to_numeric(state_df["Stim_VisualHalfWidth_rad"], errors="coerce")
        valid_half_widths = valid_half_widths[np.isfinite(valid_half_widths) & (valid_half_widths > 0)]
        if len(valid_half_widths) > 0:
            stim_half_width = float(valid_half_widths.median())

    ax.bar(
        0,
        max_radius * 0.13,
        width=2 * np.pi,
        bottom=max_radius * 1.12,
        color=plot_bg_color,
        alpha=0.90,
        edgecolor="none",
        zorder=2,
    )
    for idx, bar_angle in enumerate(bar_angles):
        ax.bar(
            bar_angle,
            max_radius * 0.18,
            width=stim_half_width * 2.0,
            bottom=max_radius * 1.08,
            color=plot_bar_hex,
            alpha=0.95,
            edgecolor=plot_bar_hex,
            zorder=8,
        )
        label = "front stimulus" if idx == 0 else "rear stimulus"
        ax.text(bar_angle, max_radius * 1.32, label, ha="center", va="center", fontsize=8, color="#222222")
        ax.plot([bar_angle, bar_angle], [0, max_radius * 1.06], color="#6B7280", linestyle="--", linewidth=0.75, alpha=0.55, zorder=3)

    if "Stim_Facing_Any" in state_df.columns:
        facing_ratio = pd.to_numeric(state_df["Stim_Facing_Any"], errors="coerce").fillna(0).mean() * 100.0
    else:
        facing_ratio = 0.0

    title = (
        f"State {meta['state']:02d} | {meta['bg_name']} / {meta['brightness']} | stimulus ON\n"
        f"Direction distribution, {meta['duration']:.2f}s"
    )
    ax.set_title(title, fontsize=13, pad=22)
    center_text = f"moving frames: {total_moving}\nfacing ratio: {facing_ratio:.1f}%"
    fig.text(
        0.5,
        0.055,
        center_text,
        ha="center",
        fontsize=10.5,
        bbox=dict(facecolor="white", alpha=0.9, edgecolor="#9CA3AF", boxstyle="round,pad=0.45"),
    )

    fig.savefig(output_png, bbox_inches="tight", dpi=220)
    plt.close(fig)
    print(f"保存: {output_png}")


def plot_polar_radar(file_path):
    df = load_clean_data(file_path)
    if df is None or df.empty:
        return

    required_cols = ["State_Index", "State_Stimulus_On", "Stim_Mapped_Angle_rad", "Time_s"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"⚠️ 缺少极坐标方向分布所需列: {missing}")
        return

    cfg = load_config(df)
    work_df = df.copy()
    work_df["State_Index"] = pd.to_numeric(work_df["State_Index"], errors="coerce")
    work_df["State_Stimulus_On"] = pd.to_numeric(work_df["State_Stimulus_On"], errors="coerce").fillna(0).astype(int)
    work_df = work_df.dropna(subset=["State_Index"])

    stim_df = work_df[work_df["State_Stimulus_On"] == 1]
    if stim_df.empty:
        print("未检测到有视觉刺激的 state。")
        return

    output_dir = os.path.join(os.path.dirname(file_path), "PolarPreference")
    os.makedirs(output_dir, exist_ok=True)

    generated = 0
    for state_index in sorted(stim_df["State_Index"].astype(int).unique()):
        state_df = stim_df[stim_df["State_Index"].astype(int) == state_index]
        if state_df.empty:
            continue
        meta = _state_meta(state_df)
        filename = (
            f"state_{state_index:02d}_"
            f"{safe_name(meta['bg_name'])}_"
            f"{safe_name(meta['brightness'])}_polar.png"
        )
        output_png = os.path.join(output_dir, filename)
        _plot_single_state_polar(state_df, output_png, cfg)
        generated += 1

    print(f"\n完成: 共生成 {generated} 张有刺激 state 方向分布图")
    print(f"输出文件夹: {output_dir}")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else select_file()
    if not csv_path or not os.path.exists(csv_path):
        print("未选择文件，程序退出。")
        sys.exit()
    plot_polar_radar(csv_path)
