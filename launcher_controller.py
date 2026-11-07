import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.colorchooser import askcolor
import subprocess
import os
import json
import sys
import math
import time
import ctypes
import socket
import re
from ctypes import wintypes
import config as experiment_config
from output_naming import (FLY_FOLDER_PATTERN, condition_file_prefix, existing_fly_ids,
                           fly_folder_name, output_root_dir)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

CONFIG_FILE = "settings.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ExperimentController(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.theme_mode = "dark"
        self.language = "en"
        self.localized_widgets = []
        self.widget_groups = {
            "frames": [],
            "headers": [],
            "cards": [],
            "separators": [],
            "buttons": [],
            "labels": [],
            "muted_labels": [],
            "inputs": [],
            "canvases": [],
            "chips": [],
        }
        self.event_labels = []
        self.colors = self._get_palette(self.theme_mode)
        self.title(self._t("Drosophila VR Experiment Console", "Drosophila VR Experiment Console | Drosophila VR Experiment Console"))
        available_height = int((self.winfo_screenheight() - 100) / self._get_window_scaling())
        window_height = min(820, max(640, available_height))
        self.geometry(f"1280x{window_height}")
        self.minsize(1180, 640)
        self.resizable(True, True)

        self.fonts = {
            "title": ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            "subtitle": ctk.CTkFont(family="Segoe UI", size=11),
            "panel": ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            "body": ctk.CTkFont(family="Segoe UI", size=11),
            "metric": ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            "clock": ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            "mono": ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            "button": ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        }

        self.configure(fg_color=self.colors["bg"])

        fictrac_folder = "fictrac" if os.path.isdir(os.path.join(os.getcwd(), "fictrac")) else "FicTrac"
        self.fictrac_dir = os.path.join(os.getcwd(), fictrac_folder)
        self.fictrac_exe = os.path.join(self.fictrac_dir, "fictrac.exe")
        self.fictrac_configGui = os.path.join(self.fictrac_dir, "configGui.exe")
        self.fictrac_config_txt = os.path.join(self.fictrac_dir, "config.txt")

        self.is_frozen = getattr(sys, 'frozen', False)
        self.vr_script = "main.exe" if self.is_frozen else "main.py"
        self.plot_traj_script = "plot_split_trajectory.exe" if self.is_frozen else "plot_split_trajectory.py"
        self.plot_polar_script = "plot_polar_preference.exe" if self.is_frozen else "plot_polar_preference.py"
        self.plot_timeline_script = "plot_facing_timeline.exe" if self.is_frozen else "plot_facing_timeline.py"

        self.fictrac_process = None
        self.vr_process = None
        self.current_experiment_dir = None
        self.fictrac_run_config_txt = None

        self.params = {}
        self.tk_vars = {}
        self.status_values = {}
        self.metric_values = {}
        self.demo_t = 0.0
        self.demo_path = []
        self.live_demo_enabled = False
        self.real_track_points = []
        self.real_track_heading = None
        self.real_track_active = False
        self.real_track_delta_ms = None
        self.track_view_center = [0.0, 0.0]
        self.track_view_window_s = 7.0
        self.track_view_max_draw_points = 420
        self.fictrac_window_hwnd = None
        self.fictrac_embed_attempts = 0
        self.fictrac_status_socket = None
        self.fictrac_status_polling = False
        self.fictrac_status_time_s = 0.0
        self.fictrac_status_prev_forward = None
        self.fictrac_status_prev_lateral = None
        self.fictrac_status_prev_heading = None
        self.fictrac_status_smooth_speed = None
        self.fictrac_status_smooth_ang_vel = None

        self.load_config()
        self.create_ui()
        self._reset_session_display(
            clear_log=True,
            initial_message=self._t("Waiting; save config, then start tracking and VR.", "Waiting; save config, then start tracking and VR."),
            reset_live_file=True,
        )
        self._update_clock()
        self.after(120, self._draw_idle_panels)
        self.after(200, self._poll_live_trajectory)

    def _get_palette(self, mode):
        if mode == "light":
            return {
                "bg": "#F8FAFC",
                "top": "#FFFFFF",
                "panel": "#FFFFFF",
                "panel_2": "#F1F5F9",
                "canvas": "#F8FAFC",
                "grid": "#E2E8F0",
                "separator": "#E2E8F0",
                "border": "#CBD5E1",
                "text": "#0F172A",
                "muted": "#64748B",
                "accent": "#0EA5E9",
                "accent_hover": "#0284C7",
                "blue": "#2563EB",
                "blue_hover": "#1D4ED8",
                "danger": "#EF4444",
                "danger_hover": "#DC2626",
                "warning": "#F59E0B",
            }
        return {
            "bg": "#0B0F12",
            "top": "#131A22",
            "panel": "#131A22",
            "panel_2": "#1E293B",
            "canvas": "#0B0F12",
            "grid": "#1E293B",
            "separator": "#1E293B",
            "border": "#334155",
            "text": "#F8FAFC",
            "muted": "#94A3B8",
            "accent": "#38BDF8",
            "accent_hover": "#0EA5E9",
            "blue": "#60A5FA",
            "blue_hover": "#3B82F6",
            "danger": "#F87171",
            "danger_hover": "#EF4444",
            "warning": "#FBBF24",
        }

    def _t(self, zh, en):
        return en

    def _pair(self, value):
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            return value[0], value[1]
        return value, value

    def _state_word(self, english):
        return english

    def _translate_status_text(self, text):
        return text

    def _register_localized(self, widget, zh, en, attr="text"):
        self.localized_widgets.append((widget, zh, en, attr))

    def _redraw_theme_sensitive_views(self):
        try:
            if self.real_track_points:
                self._draw_real_track()
            elif self.live_demo_enabled:
                self._draw_track()
            else:
                self._draw_track_idle()
        except Exception:
            pass
        try:
            self._draw_camera()
        except Exception:
            pass
        if hasattr(self, "timeline_canvas"):
            try:
                if self.live_demo_enabled:
                    self._draw_timeline()
                else:
                    self._draw_timeline_idle()
            except Exception:
                pass

    def toggle_theme_mode(self):
        next_mode = "light" if self.theme_mode == "dark" else "dark"
        self._apply_theme(next_mode)
        self._apply_language()
        self._save_ui_preferences()

    def toggle_language(self):
        self.language = "en"
        self._apply_language()
        self._save_ui_preferences()

    def load_config(self):
        default_save_dir = os.path.join(os.getcwd(), "exp_data")
        default_config = {
            "UI_THEME": "dark",
            "UI_LANGUAGE": "en",
            "SAVE_DIR": default_save_dir,
            "OUTPUT_ROOT_DIR": default_save_dir,
            "WING_CONDITION": "wing",
            "FLY_ID": "01",
            "EXPERIMENT_ID": "1",
            "UDP_PORT": 2000,
            "SCREEN_FOV_DEG": 270.0,
            "SIMULATION_MODE": False,
            "DEFAULT_BRIGHTNESS": 0.41,
            "PHASE_1_DURATION": 5,
            "PHASE_2_DURATION": 60,
            "PHASE_3_DURATION": 5,
            "V_BAR_COUNT": 2,
            "V_BAR_SPACING_DEG": 150.0,
            "H_BAR_COUNT": 0,
            "H_BAR_SPACING_CM": 6.0,
            "VIRTUAL_WALL_DISTANCE_CM": 9.75,
            "BAR_VISUAL_ANGLE_DEG": 30.0,
            "BG_COLOR": "0,255,0",
            "BAR_COLOR": "0,0,0",
            "SPHERE_RADIUS_CM": 0.6,
            "MONITOR_SMOOTHING_FACTOR": 0.65,
            "STATE_DURATION_S": 20,
            "SINGLE_BG_NAME": "white",
            "SINGLE_BRIGHTNESS_LABEL": "bright",
            "SINGLE_STIMULUS_ON": False,
            "PRE_START_BG_COLOR": "255,255,255",
            "PRE_START_BRIGHTNESS": 0.35,
            "STATE_WHITE_COLOR": "255,255,255",
            "STATE_GREEN_COLOR": "0,255,0",
            "STATE_RED_COLOR": "255,0,0",
            "STATE_WHITE_DARK_BRIGHTNESS": 0.25,
            "STATE_WHITE_MEDIUM_BRIGHTNESS": 0.55,
            "STATE_WHITE_BRIGHT_BRIGHTNESS": 1.0,
            "STATE_GREEN_DARK_BRIGHTNESS": 0.25,
            "STATE_GREEN_MEDIUM_BRIGHTNESS": 0.55,
            "STATE_GREEN_BRIGHT_BRIGHTNESS": 1.0,
            "STATE_RED_DARK_BRIGHTNESS": 0.25,
            "STATE_RED_MEDIUM_BRIGHTNESS": 0.55,
            "STATE_RED_BRIGHT_BRIGHTNESS": 1.0,
            "STATE_BG_OPTIONS": "white:255,255,255;green:0,255,0;red:255,0,0",
            "STATE_BRIGHTNESS_OPTIONS": "dark:0.25;medium:0.55;bright:1.0",
        }

        self.params = default_config.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    loaded_data.pop("PLOT_BG_COLOR", None)
                    loaded_data.pop("PLOT_BAR_COLOR", None)
                    self.params.update(loaded_data)
            except Exception:
                pass

        if "SINGLE_BRIGHTNESS" not in self.params:
            self.params["SINGLE_BRIGHTNESS"] = experiment_config.get_single_state(self.params)["brightness"]
        wing = str(self.params.get("WING_CONDITION", "wing")).strip().lower()
        self.params["WING_CONDITION"] = "no_wing" if wing in {"no", "none", "false", "0", "no_wing", "nowing"} else "wing"

        theme = str(self.params.get("UI_THEME", "dark")).strip().lower()
        self.theme_mode = "light" if theme == "light" else "dark"
        self.language = "en"
        self.params["UI_LANGUAGE"] = "en"

        if "OUTPUT_ROOT_DIR" not in self.params or not self.params.get("OUTPUT_ROOT_DIR"):
            save_dir = str(self.params.get("SAVE_DIR", default_save_dir))
            self.params["OUTPUT_ROOT_DIR"] = output_root_dir(save_dir)

        for key, val in self.params.items():
            if key in ("V_BAR_COUNT", "STATE_DURATION_S", "BAR_VISUAL_ANGLE_DEG", "SINGLE_BRIGHTNESS"):
                self.tk_vars[key] = ctk.StringVar(value=str(val))
            elif isinstance(val, bool):
                self.tk_vars[key] = ctk.BooleanVar(value=val)
            elif isinstance(val, int):
                self.tk_vars[key] = ctk.IntVar(value=val)
            elif isinstance(val, float):
                self.tk_vars[key] = ctk.DoubleVar(value=val)
            else:
                self.tk_vars[key] = ctk.StringVar(value=str(val))

    def _save_ui_preferences(self):
        if "UI_THEME" in self.tk_vars:
            self.tk_vars["UI_THEME"].set(self.theme_mode)
        if "UI_LANGUAGE" in self.tk_vars:
            self.tk_vars["UI_LANGUAGE"].set(self.language)
        try:
            self.save_config()
        except Exception:
            pass

    def save_config(self):
        self.language = "en"
        if "UI_THEME" in self.tk_vars:
            self.tk_vars["UI_THEME"].set(self.theme_mode)
        if "UI_LANGUAGE" in self.tk_vars:
            self.tk_vars["UI_LANGUAGE"].set(self.language)
        for key, var in self.tk_vars.items():
            self.params[key] = var.get()
        experiment_config.get_single_state(self.params)
        self.params["V_BAR_COUNT"] = int(float(self.params["V_BAR_COUNT"]))
        for key in ("STATE_DURATION_S", "BAR_VISUAL_ANGLE_DEG", "SINGLE_BRIGHTNESS"):
            self.params[key] = float(self.params[key])
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.params, f, indent=4)

    def save_config_with_prompt(self):
        try:
            self.save_config()
            self._set_event("Config saved")
            messagebox.showinfo("Success", "Configuration saved. It will load on the next launch.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save parameters: {e}")

    def browse_save_dir(self):
        if any(process is not None and process.poll() is None
               for process in (self.fictrac_process, self.vr_process)):
            messagebox.showerror("Notice", "Stop tracking and VR before changing the export path.")
            return
        current_dir = self.tk_vars["SAVE_DIR"].get()
        initial_dir = current_dir if os.path.exists(current_dir) else os.getcwd()
        selected_dir = filedialog.askdirectory(initialdir=initial_dir, title="Select the experiment data directory")
        if selected_dir:
            selected_dir = os.path.normpath(selected_dir)
            self.tk_vars["SAVE_DIR"].set(selected_dir)
            if "OUTPUT_ROOT_DIR" in self.tk_vars:
                self.tk_vars["OUTPUT_ROOT_DIR"].set(selected_dir)
            self.current_experiment_dir = None
            self._update_save_path_label()

    def _looks_like_experiment_dir(self, path):
        name = os.path.basename(os.path.normpath(str(path)))
        return FLY_FOLDER_PATTERN.fullmatch(name) is not None or re.match(
            r"^(?:exp_\d{3}_|(?:no_)?wing_\d{2,}_\d+)$", name) is not None

    def _get_output_root_dir(self):
        if "OUTPUT_ROOT_DIR" in self.tk_vars:
            root_dir = str(self.tk_vars["OUTPUT_ROOT_DIR"].get()).strip()
        else:
            root_dir = ""
        if not root_dir:
            root_dir = str(self.tk_vars["SAVE_DIR"].get()).strip()
        return os.path.abspath(output_root_dir(root_dir or os.path.join(os.getcwd(), "exp_data")))

    def _normalized_wing_condition(self):
        raw = str(self.tk_vars.get("WING_CONDITION", tk.StringVar(value="wing")).get()).strip().lower()
        raw = raw.replace("-", "_").replace(" ", "_")
        if raw in {"no", "none", "false", "0", "no_wing", "nowing"}:
            return "no_wing"
        return "wing"

    def _format_fly_id(self):
        raw = str(self.tk_vars.get("FLY_ID", tk.StringVar(value="01")).get()).strip()
        digits = re.sub(r"\D", "", raw)
        if not digits:
            digits = "1"
        return f"{int(digits):02d}"

    def _format_experiment_id(self):
        raw = str(self.tk_vars.get("EXPERIMENT_ID", tk.StringVar(value="1")).get()).strip()
        digits = re.sub(r"\D", "", raw)
        if not digits:
            digits = "1"
        return str(int(digits))

    def _experiment_folder_name(self):
        values = {key: variable.get() for key, variable in self.tk_vars.items()}
        state = experiment_config.get_single_state(values)
        values["SINGLE_BRIGHTNESS"] = state["brightness"]
        return fly_folder_name(values, self._normalized_wing_condition(), self._format_fly_id())

    def _refresh_suggested_fly_id(self, *_):
        if self.current_experiment_dir:
            return
        try:
            used = existing_fly_ids(self._get_output_root_dir(), self._normalized_wing_condition())
            self.tk_vars["FLY_ID"].set(f"{max(used, default=0) + 1:02d}")
        except (OSError, ValueError, tk.TclError):
            pass

    def _next_experiment_dir(self, root_dir):
        os.makedirs(root_dir, exist_ok=True)
        wing = self._normalized_wing_condition()
        group_dir = os.path.join(root_dir, wing)
        folder_name = self._experiment_folder_name()
        experiment_dir = os.path.join(group_dir, folder_name)
        if int(self._format_fly_id()) in existing_fly_ids(root_dir, wing) or os.path.exists(experiment_dir):
            raise FileExistsError(f"{wing} group fly ID {self._format_fly_id()} is already in use.\nChoose a new fly ID; existing data will not be overwritten.")
        return experiment_dir

    def _update_save_path_label(self):
        if hasattr(self, "save_path_label"):
            try:
                save_dir = self.current_experiment_dir or os.path.join(
                    self._get_output_root_dir(), self._normalized_wing_condition(), self._experiment_folder_name())
                values = {key: variable.get() for key, variable in self.tk_vars.items()}
                state = experiment_config.get_single_state(values)
                values.update(EXPERIMENT_PROTOCOL="single_condition", SINGLE_BRIGHTNESS=state["brightness"])
                prefix = condition_file_prefix(values)
            except (ValueError, TypeError, tk.TclError):
                save_dir = self._get_output_root_dir()
                prefix = "condition"
            self.save_path_label.configure(text=f"{save_dir}\\{prefix}_YYYYMMDD_HHMMSS.csv")

    def _prepare_experiment_output_dir(self):
        fictrac_running = self.fictrac_process is not None and self.fictrac_process.poll() is None
        vr_running = self.vr_process is not None and self.vr_process.poll() is None
        if self.current_experiment_dir and os.path.isdir(self.current_experiment_dir) and (fictrac_running or vr_running):
            expected_dir = os.path.join(self._get_output_root_dir(), self._normalized_wing_condition(),
                                        self._experiment_folder_name())
            if os.path.normcase(os.path.abspath(self.current_experiment_dir)) != os.path.normcase(expected_dir):
                raise ValueError("The export path, fly ID, wing group or light condition has changed. Stop tracking before starting a new experiment.")
            self.save_config()
            with open(os.path.join(self.current_experiment_dir, "experiment_settings.json"), "w", encoding="utf-8") as file:
                json.dump(self.params, file, indent=4)
            return self.current_experiment_dir
        if self.current_experiment_dir:
            self.current_experiment_dir = None
            self._refresh_suggested_fly_id()
        root_dir = self._get_output_root_dir()
        experiment_dir = self._next_experiment_dir(root_dir)
        os.makedirs(experiment_dir, exist_ok=False)
        self.current_experiment_dir = experiment_dir
        if "OUTPUT_ROOT_DIR" in self.tk_vars:
            self.tk_vars["OUTPUT_ROOT_DIR"].set(root_dir)
        self.tk_vars["SAVE_DIR"].set(experiment_dir)
        self.save_config()
        self._update_save_path_label()
        snapshot_path = os.path.join(experiment_dir, "experiment_settings.json")
        with open(snapshot_path, "w", encoding="utf-8") as file:
            json.dump(self.params, file, indent=4)
        return experiment_dir

    def _write_fictrac_run_config(self, experiment_dir):
        with open(self.fictrac_config_txt, "r", encoding="utf-8", errors="ignore") as file:
            lines = file.readlines()
        updates = {
            "save_debug": "y",
            "save_raw": "n",
            "vid_codec": "mjpg",
            "sock_port": str(int(self.tk_vars["UDP_PORT"].get())),
        }
        seen = set()
        output_lines = []
        for line in lines:
            stripped = line.strip()
            if ":" in line and stripped and not stripped.startswith("#"):
                key = line.split(":", 1)[0].strip()
                if key in updates:
                    output_lines.append(f"{key:<16}: {updates[key]}\n")
                    seen.add(key)
                    continue
            output_lines.append(line)
        for key, value in updates.items():
            if key not in seen:
                output_lines.append(f"{key:<16}: {value}\n")
        run_config = os.path.join(experiment_dir, "fictrac_config.txt")
        with open(run_config, "w", encoding="utf-8") as file:
            file.writelines(output_lines)
        self.fictrac_run_config_txt = run_config
        return run_config

    def _rgb_to_hex(self, rgb_str):
        try:
            r, g, b = map(int, str(rgb_str).split(","))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#FFFFFF"

    def _update_clock(self):
        if hasattr(self, "clock_label"):
            self.clock_label.configure(text=time.strftime("%H:%M:%S"))
        self.after(1000, self._update_clock)

    def _format_duration_label(self, seconds):
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            seconds = 0.0
        minutes = int(seconds // 60)
        rem = int(round(seconds - minutes * 60))
        if minutes <= 0:
            return f"{seconds:g}s"
        return f"{minutes}m {rem:02d}s"

    def _protocol_summary_text(self):
        try:
            values = {key: var.get() for key, var in self.tk_vars.items()}
            state = experiment_config.get_single_state(values)
            duration = float(values["STATE_DURATION_S"])
        except (tk.TclError, KeyError, TypeError, ValueError):
            return self._t("Invalid trial condition", "Invalid trial condition")
        return self._t(
            f"Single-condition trial - {duration:g}s\n",
            f"Single-condition trial - {duration:g}s\n",
        ) + (
            f"{self._state_color_label(state['bg_name'])} / "
            f"{self._state_brightness_label(state['brightness_label'])} "
            f"({state['brightness']:g}) / {self._state_block_label(state['block'])}"
        )

    def _update_protocol_summary(self):
        if hasattr(self, "protocol_summary_var"):
            self.protocol_summary_var.set(self._protocol_summary_text())

    def _state_block_label(self, block):
        return "No stimulus" if block == "no_stimulus" else "Stimulus" if block == "stimulus" else str(block)

    def _state_color_label(self, color_name):
        return {"white": "White", "green": "Green", "red": "Red"}.get(str(color_name), str(color_name))

    def _state_brightness_label(self, brightness_name):
        return {"dark": "Dark", "medium": "Medium", "bright": "Bright", "custom": "Custom"}.get(str(brightness_name), str(brightness_name))

    def _update_run_progress_from_payload(self, payload):
        if not hasattr(self, "run_progress_bar"):
            return
        try:
            state_seconds = float(self.tk_vars["STATE_DURATION_S"].get())
        except (KeyError, TypeError, ValueError):
            state_seconds = 20.0
        total_seconds = max(state_seconds, 1.0)
        seconds = max(float(payload.get("time_s", 0.0)), 0.0)
        progress = min(max(seconds / total_seconds, 0.0), 1.0)
        self.run_progress_bar.set(progress)

        state = payload.get("state") or {}
        state_index = int(state.get("index", payload.get("phase", 0)) or 0)
        if state_index:
            progress_text = self._t(
                f"State {state_index}/1 - {self._format_duration_label(seconds)} / {self._format_duration_label(total_seconds)}",
                f"State {state_index}/1 - {self._format_duration_label(seconds)} / {self._format_duration_label(total_seconds)}",
            )
            detail_text = (
                f"{self._state_block_label(state.get('block', ''))} - "
                f"{self._state_color_label(state.get('bg_name', ''))} / "
                f"{self._state_brightness_label(state.get('brightness_label', ''))}"
            )
        else:
            progress_text = self._t("Waiting to start", "Waiting to start")
            detail_text = self._t("Press space or click to begin; pre-start background is white.", "Press space or click to begin; pre-start background is white.")
        self.run_progress_label.configure(text=progress_text)
        self.run_state_detail_label.configure(text=detail_text)

    def _reset_run_progress(self):
        if hasattr(self, "run_progress_bar"):
            self.run_progress_bar.set(0)
        if hasattr(self, "run_progress_label"):
            self.run_progress_label.configure(text=self._t("Waiting to start", "Waiting to start"))
        if hasattr(self, "run_state_detail_label"):
            self.run_state_detail_label.configure(text=self._t("Press space or click to begin; pre-start background is white.", "Press space or click to begin; pre-start background is white."))

    def _fit_aspect_panel(self, event, panel):
        aspect_ratio = 3 / 2
        available_w = max(event.width - 16, 1)
        available_h = max(event.height - 16, 1)
        panel_w = min(available_w, int(available_h * aspect_ratio))
        panel_w = max(280, panel_w)
        panel_h = int(panel_w / aspect_ratio)
        if panel_h > available_h:
            panel_h = available_h
            panel_w = int(panel_h * aspect_ratio)
        if not hasattr(self, "_pending_panel_sizes"):
            self._pending_panel_sizes = {}
        self._pending_panel_sizes[panel] = (panel_w, panel_h)
        if getattr(self, "_panel_resize_job", None) is None:
            self._panel_resize_job = self.after(16, self._apply_panel_sizes)

    def _apply_panel_sizes(self):
        self._panel_resize_job = None
        pending = self._pending_panel_sizes
        self._pending_panel_sizes = {}
        for panel, size in pending.items():
            if getattr(panel, "_last_resize_size", None) != size:
                panel.place_configure(relx=0.5, rely=0.5, anchor="center", width=size[0], height=size[1])
                panel._last_resize_size = size

    def _reset_status_readouts(self):
        if "State" in self.status_values:
            self.status_values["State"].configure(text=self._state_word("Standby"), text_color=self.colors["text"])
        if "Time" in self.status_values:
            self.status_values["Time"].configure(text="00:00.00", text_color=self.colors["text"])
        if "FicTrac Delta t" in self.status_values:
            self.status_values["FicTrac Delta t"].configure(text="--", text_color=self.colors["text"])
        if "Speed" in self.status_values:
            self.status_values["Speed"].configure(text="0.00 cm/s", text_color=self.colors["text"])
        if "Angular Vel." in self.status_values:
            self.status_values["Angular Vel."].configure(text="0.00 rad/s", text_color=self.colors["text"])

    def _reset_session_display(self, clear_log=False, initial_message=None, reset_live_file=True):
        self.live_demo_enabled = False
        self.demo_t = 0.0
        self.demo_path = []
        self.real_track_points = []
        self.real_track_heading = None
        self.real_track_active = False
        self._reset_status_readouts()
        self._reset_run_progress()
        if clear_log:
            self._clear_event_log(initial_message)
        if reset_live_file:
            self._write_empty_live_trajectory()
        try:
            self._draw_track_idle()
            if hasattr(self, "timeline_canvas"):
                self._draw_timeline_idle()
        except Exception:
            pass

    def _write_empty_live_trajectory(self):
        live_path = os.path.join(self.tk_vars["SAVE_DIR"].get(), "live_trajectory.json")
        try:
            os.makedirs(os.path.dirname(live_path), exist_ok=True)
            with open(live_path, "w", encoding="utf-8") as file:
                json.dump({
                    "active": False,
                    "time_s": 0.0,
                    "phase": 0,
                    "state": None,
                    "state_elapsed_s": 0.0,
                    "fictrac_delta_ms": None,
                    "speed_cm_s": 0.0,
                    "angular_vel_rad_s": 0.0,
                    "points": [],
                    "latest": {"x": 0.0, "y": 0.0, "heading": None},
                }, file, ensure_ascii=False)
        except OSError:
            pass

    def _update_demo_panels(self):
        if not self.live_demo_enabled:
            self._draw_idle_panels()
            return
        self.demo_t += 0.075
        self._draw_camera()
        self._draw_real_track()
        if hasattr(self, "timeline_canvas"):
            self._draw_timeline()
        self._update_demo_text()
        self.after(80, self._update_demo_panels)

    def _start_live_demo(self):
        if self.live_demo_enabled:
            return
        self.live_demo_enabled = True
        self.demo_t = 0.0
        self.demo_path = []
        self._update_demo_panels()

    def _draw_idle_panels(self):
        self._draw_camera_idle()
        self._draw_track_idle()
        if hasattr(self, "timeline_canvas"):
            self._draw_timeline_idle()
        if "Tracking" in self.status_values:
            tracking_label = self.status_values["Tracking"]
            stop_word = self._state_word("STOPPED")
            if stop_word not in str(tracking_label.cget("text")) and "STOPPED" not in str(tracking_label.cget("text")):
                tracking_label.configure(text=self._state_word("IDLE"), text_color=self.colors["text"])
        if "State" in self.status_values:
            self.status_values["State"].configure(text=self._state_word("Standby"), text_color=self.colors["text"])
        if "Time" in self.status_values:
            self.status_values["Time"].configure(text="00:00.00", text_color=self.colors["text"])
        if "FicTrac Delta t" in self.status_values:
            self.status_values["FicTrac Delta t"].configure(text="--", text_color=self.colors["text"])
        if "Speed" in self.status_values:
            self.status_values["Speed"].configure(text="0.00 cm/s", text_color=self.colors["text"])
        if "Angular Vel." in self.status_values:
            self.status_values["Angular Vel."].configure(text="0.00 rad/s", text_color=self.colors["text"])
        if self.metric_values:
            self.metric_values["Facing Stimulus"].configure(text="--")
            self.metric_values["Approaching"].configure(text="--")
            self.metric_values["Total Distance"].configure(text="0.0 cm")
            self.metric_values["Path Straightness"].configure(text="--")

    def _draw_camera_idle(self):
        if hasattr(self, "camera_clip_frame"):
            self.camera_clip_frame.place_forget()
        c = self.camera_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")
        cx = w * 0.5
        cy = h * 0.5
        r = min(w, h) * 0.24
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["panel_2"], outline=pal["border"], width=1)
        c.create_oval(cx - r * 1.08, cy - r * 1.08, cx + r * 1.08, cy + r * 1.08, outline=pal["grid"], width=1)
        c.create_line(cx - r * 1.18, cy, cx + r * 1.18, cy, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_line(cx, cy - r * 1.18, cx, cy + r * 1.18, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_text(cx, cy, text=self._t("Camera standby", "Camera standby"), fill=pal["muted"], font=("Segoe UI", 12, "bold"))
        c.create_text(cx, cy + 22, text=self._t("Start Tracking to show live values", "Start Tracking to show live values"), fill=pal["muted"], font=("Segoe UI", 9))

    def _draw_camera_waiting(self):
        if hasattr(self, "camera_clip_frame"):
            self.camera_clip_frame.place_forget()
        c = self.camera_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")
        cx = w * 0.5
        cy = h * 0.5
        r = min(w, h) * 0.24
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["panel_2"], outline=pal["border"], width=1)
        c.create_oval(cx - r * 1.08, cy - r * 1.08, cx + r * 1.08, cy + r * 1.08, outline=pal["grid"], width=1)
        c.create_line(cx - r * 1.18, cy, cx + r * 1.18, cy, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_line(cx, cy - r * 1.18, cx, cy + r * 1.18, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_text(cx, cy, text=self._t("Waiting for FicTrac", "Waiting for FicTrac"), fill=pal["warning"], font=("Segoe UI", 12, "bold"))
        c.create_text(cx, cy + 22, text=self._t("Camera preview will appear here", "Camera preview will appear here"), fill=pal["muted"], font=("Segoe UI", 9))

    def _draw_track_idle(self):
        if self.real_track_points:
            self._draw_real_track()
            return
        c = self.track_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")
        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=pal["grid"], width=1)
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=pal["grid"], width=1)
        cx = w * 0.5
        cy = h * 0.5
        arena_r = min(w, h) * 0.28
        c.create_oval(cx - arena_r, cy - arena_r, cx + arena_r, cy + arena_r, outline=pal["border"], width=1)
        c.create_line(cx - arena_r * 1.18, cy, cx + arena_r * 1.18, cy, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_line(cx, cy - arena_r * 1.18, cx, cy + arena_r * 1.18, fill=pal["grid"], width=1, dash=(4, 4))
        c.create_text(cx, cy, text=self._t("Trajectory standby", "Trajectory standby"), fill=pal["muted"], font=("Segoe UI", 12, "bold"))
        c.create_text(cx, cy + 22, text=self._t("Waiting for live_trajectory.json", "Waiting for live_trajectory.json"), fill=pal["muted"], font=("Segoe UI", 9))

    def _poll_live_trajectory(self):
        if self.fictrac_status_socket is not None:
            self.after(100, self._poll_live_trajectory)
            return
        live_path = os.path.join(self.tk_vars["SAVE_DIR"].get(), "live_trajectory.json")
        try:
            if os.path.exists(live_path):
                with open(live_path, "r", encoding="utf-8") as file:
                    payload = json.load(file)

                points = []
                for item in payload.get("points", [])[-2000:]:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        points.append((float(item[0]), float(item[1])))

                latest = payload.get("latest", {}) or {}
                heading = latest.get("heading")
                self.real_track_points = points
                self.real_track_heading = None if heading is None else float(heading)
                self.real_track_active = bool(payload.get("active", False))

                if "State" in self.status_values:
                    phase = payload.get("phase", 0)
                    state = payload.get("state") or {}
                    if state:
                        state_text = (
                            f"{state.get('index', phase)}/1 | "
                            f"{self._state_block_label(state.get('block', ''))} | "
                            f"{self._state_color_label(state.get('bg_name', ''))}/"
                            f"{self._state_brightness_label(state.get('brightness_label', ''))}"
                        )
                    else:
                        state_text = f"{self._t('State', 'State')} {phase}" if phase else self._state_word("Standby")
                    self.status_values["State"].configure(text=state_text)
                self._update_run_progress_from_payload(payload)
                if "Time" in self.status_values:
                    seconds = float(payload.get("time_s", 0.0))
                    minutes = int(seconds // 60)
                    rem = seconds - minutes * 60
                    self.status_values["Time"].configure(text=f"{minutes:02d}:{rem:05.2f}")
                if "FicTrac Delta t" in self.status_values:
                    delta_ms = payload.get("fictrac_delta_ms")
                    try:
                        self.real_track_delta_ms = None if delta_ms is None else float(delta_ms)
                    except (TypeError, ValueError):
                        self.real_track_delta_ms = None
                    self.status_values["FicTrac Delta t"].configure(text="--" if delta_ms is None else f"{float(delta_ms):.2f} ms")
                speed = payload.get("speed_cm_s")
                angular_vel = payload.get("angular_vel_rad_s")
                if speed is not None:
                    speed = self._smooth_monitor_value("fictrac_status_smooth_speed", speed)
                if angular_vel is not None:
                    angular_vel = self._smooth_monitor_value("fictrac_status_smooth_ang_vel", angular_vel)
                if "Speed" in self.status_values:
                    self.status_values["Speed"].configure(text="0.00 cm/s" if speed is None else f"{float(speed):.2f} cm/s")
                if "Angular Vel." in self.status_values:
                    self.status_values["Angular Vel."].configure(text="0.00 rad/s" if angular_vel is None else f"{float(angular_vel):.2f} rad/s")

                if points:
                    self._draw_real_track()
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

        self.after(500, self._poll_live_trajectory)

    def _reset_fictrac_status_state(self):
        self.fictrac_status_time_s = 0.0
        self.fictrac_status_prev_forward = None
        self.fictrac_status_prev_lateral = None
        self.fictrac_status_prev_heading = None
        self.fictrac_status_smooth_speed = None
        self.fictrac_status_smooth_ang_vel = None

    def _start_fictrac_status_udp(self):
        self._stop_fictrac_status_udp()
        try:
            port = int(self.tk_vars["UDP_PORT"].get())
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", port))
            sock.setblocking(False)
            self.fictrac_status_socket = sock
            self.fictrac_status_polling = True
            self._reset_fictrac_status_state()
            self._poll_fictrac_status_udp()
        except OSError as exc:
            self.fictrac_status_socket = None
            self.fictrac_status_polling = False
            self._set_event(f"FicTrac UDP status unavailable: {exc}")

    def _stop_fictrac_status_udp(self):
        self.fictrac_status_polling = False
        if self.fictrac_status_socket is not None:
            try:
                self.fictrac_status_socket.close()
            except OSError:
                pass
        self.fictrac_status_socket = None

    def _poll_fictrac_status_udp(self):
        sock = self.fictrac_status_socket
        if not self.fictrac_status_polling or sock is None:
            return

        updated = False
        while True:
            try:
                data, _ = sock.recvfrom(1024)
            except BlockingIOError:
                break
            except OSError:
                self._stop_fictrac_status_udp()
                return

            sample = self._parse_fictrac_status_packet(data)
            if sample is not None:
                self._apply_fictrac_status_sample(sample)
                updated = True

        if updated and "Tracking" in self.status_values:
            self.status_values["Tracking"].configure(text=f"* {self._state_word('CAMERA')}", text_color=self.colors["accent"])

        self.after(30, self._poll_fictrac_status_udp)

    def _parse_fictrac_status_packet(self, data):
        try:
            values = [value.strip() for value in data.decode("utf-8").strip().split(",")]
            has_ft_prefix = bool(values) and values[0] == "FT"
            col = lambda n: n if has_ft_prefix else n - 1
            required_cols = [1, 17, 20, 21, 24]
            if len(values) <= max(col(n) for n in required_cols):
                return None

            frame = int(float(values[col(1)]))
            sphere_radius_cm = float(self.tk_vars["SPHERE_RADIUS_CM"].get())
            heading = -float(values[col(17)])
            forward = float(values[col(20)]) * sphere_radius_cm
            lateral = -float(values[col(21)]) * sphere_radius_cm
            delta_ms = float(values[col(24)])
            if delta_ms <= 0:
                return None

            if self.tk_vars.get("INVERT_ROTATION") and self.tk_vars["INVERT_ROTATION"].get():
                heading = -heading
                lateral = -lateral
            if self.tk_vars.get("INVERT_FORWARD") and self.tk_vars["INVERT_FORWARD"].get():
                forward = -forward
                lateral = -lateral

            dt = delta_ms / 1000.0
            speed = 0.0
            angular_vel = 0.0
            if self.fictrac_status_prev_forward is not None:
                delta_forward = forward - self.fictrac_status_prev_forward
                delta_lateral = lateral - self.fictrac_status_prev_lateral
                speed = math.hypot(delta_forward, delta_lateral) / dt
            if self.fictrac_status_prev_heading is not None:
                d_heading = heading - self.fictrac_status_prev_heading
                d_heading = (d_heading + math.pi) % (2 * math.pi) - math.pi
                angular_vel = d_heading / dt

            self.fictrac_status_prev_forward = forward
            self.fictrac_status_prev_lateral = lateral
            self.fictrac_status_prev_heading = heading
            self.fictrac_status_time_s += dt

            return {
                "frame": frame,
                "time_s": self.fictrac_status_time_s,
                "fictrac_delta_ms": delta_ms,
                "speed_cm_s": speed,
                "angular_vel_rad_s": angular_vel,
            }
        except (UnicodeDecodeError, ValueError, IndexError, tk.TclError):
            return None

    def _monitor_smoothing_factor(self):
        try:
            value = float(self.tk_vars.get("MONITOR_SMOOTHING_FACTOR").get())
        except Exception:
            value = 0.65
        return max(0.0, min(0.95, value))

    def _smooth_monitor_value(self, attr_name, value):
        alpha = self._monitor_smoothing_factor()
        previous = getattr(self, attr_name, None)
        if previous is None:
            smoothed = float(value)
        else:
            smoothed = previous * alpha + float(value) * (1.0 - alpha)
        setattr(self, attr_name, smoothed)
        return smoothed

    def _apply_fictrac_status_sample(self, sample):
        seconds = float(sample["time_s"])
        minutes = int(seconds // 60)
        rem = seconds - minutes * 60
        # Skip layout and embedded-window redraws when status text is unchanged.
        if "Time" in self.status_values:
            time_text = f"{minutes:02d}:{rem:05.2f}"
            if getattr(self, "_status_text_cache_time", None) != time_text:
                self.status_values["Time"].configure(text=time_text)
                self._status_text_cache_time = time_text
        if "FicTrac Delta t" in self.status_values:
            delta_text = f"{sample['fictrac_delta_ms']:.2f} ms"
            if getattr(self, "_status_text_cache_delta", None) != delta_text:
                self.status_values["FicTrac Delta t"].configure(text=delta_text)
                self._status_text_cache_delta = delta_text
        display_speed = self._smooth_monitor_value("fictrac_status_smooth_speed", sample["speed_cm_s"])
        display_ang_vel = self._smooth_monitor_value("fictrac_status_smooth_ang_vel", sample["angular_vel_rad_s"])
        if "Speed" in self.status_values:
            self.status_values["Speed"].configure(text=f"{display_speed:.2f} cm/s")
        if "Angular Vel." in self.status_values:
            self.status_values["Angular Vel."].configure(text=f"{display_ang_vel:.2f} rad/s")

    def _reset_live_trajectory_preview(self):
        self.real_track_points = []
        self.real_track_heading = None
        self.real_track_active = False
        self.real_track_delta_ms = None
        self.track_view_center = [0.0, 0.0]
        self.fictrac_status_smooth_speed = None
        self.fictrac_status_smooth_ang_vel = None
        live_path = os.path.join(self.tk_vars["SAVE_DIR"].get(), "live_trajectory.json")
        try:
            os.makedirs(os.path.dirname(live_path), exist_ok=True)
            with open(live_path, "w", encoding="utf-8") as file:
                json.dump({
                    "active": False,
                    "time_s": 0.0,
                    "phase": 0,
                    "state": None,
                    "state_elapsed_s": 0.0,
                    "fictrac_delta_ms": None,
                    "speed_cm_s": 0.0,
                    "angular_vel_rad_s": 0.0,
                    "points": [],
                    "latest": {"x": 0.0, "y": 0.0, "heading": None},
                }, file, ensure_ascii=False)
        except OSError:
            pass
        if "Time" in self.status_values:
            self.status_values["Time"].configure(text="00:00.00")
        if "FicTrac Delta t" in self.status_values:
            self.status_values["FicTrac Delta t"].configure(text="--")
        if "Speed" in self.status_values:
            self.status_values["Speed"].configure(text="0.00 cm/s")
        if "Angular Vel." in self.status_values:
            self.status_values["Angular Vel."].configure(text="0.00 rad/s")
        self._reset_run_progress()
        self._draw_track_idle()

    def _draw_real_track(self):
        c = self.track_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")

        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=pal["grid"], width=1)
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=pal["grid"], width=1)

        if not self.real_track_points:
            c.create_text(w * 0.5, h * 0.5, text="Waiting for live trajectory", fill=self.colors["muted"], font=("Segoe UI", 12, "bold"))
            return

        delta_ms = self.real_track_delta_ms
        if delta_ms is not None and delta_ms > 0:
            visible_count = int(self.track_view_window_s * 1000.0 / delta_ms) + 2
        else:
            visible_count = int(self.track_view_window_s * 180.0) + 2
        visible_count = max(40, min(1600, visible_count))
        pts = self.real_track_points[-visible_count:]

        # Keep a fixed physical scale and pan only near the view edge.
        origin_x = w * 0.5
        origin_y = h * 0.5
        base_radius_cm = 6.0
        scale = min((w - 44) / (2 * base_radius_cm), (h - 52) / (2 * base_radius_cm))
        scale = max(8.0, scale)

        if not hasattr(self, "track_view_center") or self.track_view_center is None:
            self.track_view_center = [0.0, 0.0]

        latest_x, latest_y = pts[-1]
        safe_left = w * 0.20
        safe_right = w * 0.80
        safe_top = h * 0.20
        safe_bottom = h * 0.80

        latest_sx = origin_x + (latest_y - self.track_view_center[1]) * scale
        latest_sy = origin_y - (latest_x - self.track_view_center[0]) * scale

        if latest_sx < safe_left:
            self.track_view_center[1] -= (safe_left - latest_sx) / scale
        elif latest_sx > safe_right:
            self.track_view_center[1] += (latest_sx - safe_right) / scale

        if latest_sy < safe_top:
            self.track_view_center[0] += (safe_top - latest_sy) / scale
        elif latest_sy > safe_bottom:
            self.track_view_center[0] -= (latest_sy - safe_bottom) / scale

        def to_canvas(point):
            x, y = point
            # Map world +X upward and world +Y to the right.
            return (
                origin_x + (y - self.track_view_center[1]) * scale,
                origin_y - (x - self.track_view_center[0]) * scale,
            )

        # Use the same 6 cm reference radius as main.py.
        arena_r = 6.0 * scale
        arena_cx, arena_cy = to_canvas((0.0, 0.0))
        c.create_oval(arena_cx - arena_r, arena_cy - arena_r, arena_cx + arena_r, arena_cy + arena_r, outline=pal["border"], width=1)

        if len(pts) >= 2:
            step = max(1, math.ceil(len(pts) / self.track_view_max_draw_points))
            draw_pts = pts[::step]
            if draw_pts[-1] != pts[-1]:
                draw_pts.append(pts[-1])
            flat = []
            for p in draw_pts:
                cx, cy = to_canvas(p)
                flat.extend((cx, cy))
            if len(flat) >= 4:
                c.create_line(*flat, fill=self._rgba_to_hex(47, 155, 124, 0.95), width=2, smooth=True)

        px, py = to_canvas(pts[-1])
        c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=pal["accent"], outline="")
        if self.real_track_heading is not None:
            # Use a 1.5 cm heading line; heading=0 points upward.
            heading_len = 1.5 * scale
            c.create_line(
                px,
                py,
                px + math.sin(self.real_track_heading) * heading_len,
                py - math.cos(self.real_track_heading) * heading_len,
                fill="#D6FFF0" if self.theme_mode == "dark" else "#1f5f73",
                width=2,
            )

        status = self._t("LIVE VR trajectory", "LIVE VR trajectory") if self.real_track_active else self._t("LAST VR trajectory", "LAST VR trajectory")
        points_label = self._t("points", "points")
        window_label = self._t("window", "window")
        c.create_text(
            14,
            18,
            text=f"{status}   {window_label}: {self.track_view_window_s:.0f}s   {points_label}: {len(pts)}",
            fill=pal["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )

    def _draw_timeline_idle(self):
        c = self.timeline_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")
        for i in range(7):
            x = 8 + (w - 16) * i / 6
            c.create_line(x, 8, x, h - 10, fill=pal["grid"])
        c.create_line(8, h * 0.52, w - 8, h * 0.52, fill=pal["border"], width=1)
        c.create_text(w * 0.5, h * 0.5, text=self._t("Waiting for data", "Waiting for data"), fill=pal["muted"], font=("Segoe UI", 9))

    def _draw_camera(self):
        pal = self.colors
        tracking_running = self.fictrac_process is not None and self.fictrac_process.poll() is None
        if tracking_running:
            if self._draw_fictrac_input_preview():
                return
            self._draw_camera_waiting()
            return
        if self._draw_fictrac_input_preview():
            return
        if hasattr(self, "camera_clip_frame"):
            self.camera_clip_frame.place_forget()
        c = self.camera_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")

        cx = w * 0.5
        cy = h * 0.48
        r = min(w, h) * 0.28
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=pal["panel_2"], outline=pal["border"], width=2)
        c.create_oval(cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78, outline=pal["grid"], width=1)

        for i in range(34):
            angle = i * 2.399 + self.demo_t * 0.45
            rr = r * (0.18 + ((i * 37) % 78) / 100)
            x = cx + math.cos(angle) * rr
            y = cy + math.sin(angle * 1.17) * rr * 0.78
            size = 2 + (i % 5)
            fill = "#E9EFE3" if i % 3 == 0 else ("#101516" if self.theme_mode == "dark" else "#1f2a2f")
            c.create_oval(x - size, y - size, x + size, y + size, fill=fill, outline="")

        c.create_oval(cx - r * 1.08, cy - r * 1.08, cx + r * 1.08, cy + r * 1.08, outline=pal["accent"], width=2)
        c.create_line(cx - r * 1.18, cy, cx + r * 1.18, cy, fill=pal["blue"], width=1, dash=(4, 4))
        c.create_line(cx, cy - r * 1.18, cx, cy + r * 1.18, fill=pal["blue"], width=1, dash=(4, 4))

    def _draw_track(self):
        c = self.track_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")

        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=pal["grid"], width=1)
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=pal["grid"], width=1)

        cx = w * 0.5
        cy = h * 0.5
        scale = min(w, h) / 18
        arena_r = 6 * scale
        c.create_oval(cx - arena_r, cy - arena_r, cx + arena_r, cy + arena_r, outline=pal["border"], width=1)

        for angle in (0, math.pi):
            sx = cx + math.cos(angle) * arena_r
            sy = cy - math.sin(angle) * arena_r
            c.create_rectangle(sx - 5, sy - 28, sx + 5, sy + 28, fill=pal["canvas"], outline=pal["border"])

        x = math.cos(self.demo_t * 0.72) * 2.8 + math.sin(self.demo_t * 0.21) * 1.2
        y = math.sin(self.demo_t * 0.68) * 2.1 + math.cos(self.demo_t * 0.31) * 0.9
        self.demo_path.append((x, y))
        if len(self.demo_path) > 220:
            self.demo_path.pop(0)

        for i in range(1, len(self.demo_path)):
            alpha = 0.18 + i / len(self.demo_path) * 0.72
            fill = self._rgba_to_hex(47, 155, 124, alpha)
            x1, y1 = self.demo_path[i - 1]
            x2, y2 = self.demo_path[i]
            c.create_line(cx + x1 * scale, cy - y1 * scale, cx + x2 * scale, cy - y2 * scale, fill=fill, width=2)

        px = cx + x * scale
        py = cy - y * scale
        heading = self.demo_t * 0.9
        c.create_oval(px - 5, py - 5, px + 5, py + 5, fill=self.colors["accent"], outline="")
        c.create_line(px, py, px + math.cos(heading) * 24, py - math.sin(heading) * 24, fill="#D6FFF0", width=2)
        c.create_text(14, 18, text=self._t("cm", "cm"), fill=pal["muted"], font=("Segoe UI", 9), anchor="w")

    def _draw_timeline(self):
        c = self.timeline_canvas
        w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 1)
        pal = self.colors
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=pal["canvas"], outline="")
        for i in range(7):
            x = 8 + (w - 16) * i / 6
            c.create_line(x, 8, x, h - 10, fill=pal["grid"])
        band_top = h * 0.38
        band_bottom = h * 0.62
        c.create_rectangle(8, band_top, w - 8, band_bottom, fill="#dceee8" if self.theme_mode == "light" else "#1D3B34", outline="")

        points = []
        for i in range(max(int(w - 16), 2)):
            x = 8 + i
            y = h * 0.52 + math.sin(i * 0.045 + self.demo_t) * 18 + math.sin(i * 0.013) * 8
            points.extend([x, y])
        c.create_line(*points, fill=pal["blue"], width=2, smooth=True)

    def _update_demo_text(self):
        seconds = self.demo_t
        self.status_values["Time"].configure(text=f"00:{seconds:05.2f}")
        self.status_values["FicTrac Delta t"].configure(text=f"{5.52 + math.sin(self.demo_t) * 0.07:.2f} ms")
        self.status_values["Speed"].configure(text=f"{0.78 + math.sin(self.demo_t * 0.8) * 0.2:.2f} cm/s")
        self.status_values["Angular Vel."].configure(text=f"{0.28 + math.cos(self.demo_t * 0.9) * 0.12:.2f} rad/s")
        if self.metric_values:
            self.metric_values["Facing Stimulus"].configure(text=f"{36 + math.sin(self.demo_t * 0.4) * 3:.1f}%")
            self.metric_values["Approaching"].configure(text=f"{22 + math.cos(self.demo_t * 0.35) * 2:.1f}%")
            self.metric_values["Total Distance"].configure(text=f"{18 + self.demo_t * 0.12:.1f} cm")
            self.metric_values["Path Straightness"].configure(text=f"{0.64 + math.sin(self.demo_t * 0.25) * 0.04:.2f}")

    @staticmethod
    def _rgba_to_hex(r, g, b, alpha):
        bg = 17
        rr = int(bg * (1 - alpha) + r * alpha)
        gg = int(bg * (1 - alpha) + g * alpha)
        bb = int(bg * (1 - alpha) + b * alpha)
        return f"#{rr:02x}{gg:02x}{bb:02x}"

    def _try_embed_fictrac_window(self):
        if os.name != "nt":
            return
        if self.fictrac_process is None or self.fictrac_process.poll() is not None:
            return

        hwnd = self._find_fictrac_debug_window(self.fictrac_process.pid)
        if hwnd:
            self.fictrac_window_hwnd = hwnd
            self._embed_fictrac_debug_window(hwnd)
            self.status_values["Tracking"].configure(text=f"* {self._state_word('CAMERA')}", text_color=self.colors["accent"])
            return

        self.fictrac_embed_attempts += 1
        # Retry for about 7.5 seconds, increasing later polling intervals.
        if self.fictrac_embed_attempts <= 15:
            delay = 400 if self.fictrac_embed_attempts <= 6 else 700
            self.after(delay, self._try_embed_fictrac_window)

    def _find_fictrac_debug_window(self, pid):
        user32 = ctypes.windll.user32
        target_title = "fictrac-debug"
        found = {"hwnd": None}

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def find_proc(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value != pid:
                return True
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buffer, 512)
            if title_buffer.value.lower() == target_title:
                found["hwnd"] = hwnd
                return False
            return True

        user32.EnumWindows(find_proc, 0)
        return found["hwnd"]

    def _on_camera_canvas_configure(self):
        if getattr(self, "_view_resize_job", None) is None:
            self._view_resize_job = self.after(33, self._redraw_resized_views)

    def _redraw_resized_views(self):
        self._view_resize_job = None
        if self.fictrac_window_hwnd:
            self._position_embedded_fictrac_window()
        else:
            self._draw_camera()
        if self.real_track_points:
            self._draw_real_track()
        elif self.live_demo_enabled:
            self._draw_track()
        else:
            self._draw_track_idle()

    def _embed_fictrac_debug_window(self, hwnd):
        if os.name != "nt":
            return
        try:
            user32 = ctypes.windll.user32
            self._position_camera_clip_frame()
            parent_hwnd = self.camera_clip_frame.winfo_id()
            gwl_style = -16
            ws_child = 0x40000000
            ws_visible = 0x10000000
            ws_popup = 0x80000000
            ws_caption = 0x00C00000
            ws_thickframe = 0x00040000
            style = user32.GetWindowLongW(hwnd, gwl_style)
            style = (style | ws_child | ws_visible) & ~(ws_popup | ws_caption | ws_thickframe)
            user32.SetWindowLongW(hwnd, gwl_style, style)
            user32.SetParent(hwnd, parent_hwnd)
            self._position_embedded_fictrac_window()
        except Exception as exc:
            self._set_event(f"FicTrac preview embed failed: {exc}")

    def _position_camera_clip_frame(self):
        if not hasattr(self, "camera_clip_frame"):
            return
        canvas_w = max(self.camera_canvas.winfo_width(), 1)
        canvas_h = max(self.camera_canvas.winfo_height(), 1)
        crop_size = max(1, min(480, canvas_w, canvas_h))
        x = max(0, (canvas_w - crop_size) // 2)
        y = max(0, (canvas_h - crop_size) // 2)
        # Skip layout updates when geometry is unchanged.
        geom = (crop_size, x, y)
        if getattr(self, "_camera_clip_geom", None) == geom and getattr(self, "_camera_clip_placed", False):
            return
        self.camera_clip_frame.configure(width=crop_size, height=crop_size, bg=self.colors["canvas"])
        self.camera_clip_frame.place(x=x, y=y, width=crop_size, height=crop_size)
        self.camera_clip_frame.lift()
        self._camera_clip_geom = geom
        self._camera_clip_placed = True

    def _position_embedded_fictrac_window(self):
        if os.name != "nt" or not self.fictrac_window_hwnd:
            return
        try:
            self._position_camera_clip_frame()
            # Avoid repeated cross-process SetWindowPos calls when the size is unchanged.
            if getattr(self, "_embedded_window_size", None) == (480, 480):
                return
            user32 = ctypes.windll.user32
            swp_noactivate = 0x0010
            swp_nozorder = 0x0004
            # Keep the child size; the parent clips the upper-left input view.
            user32.SetWindowPos(self.fictrac_window_hwnd, None, 0, 0, 480, 480, swp_noactivate | swp_nozorder)
            self._embedded_window_size = (480, 480)
        except Exception:
            pass

    def _draw_fictrac_input_preview(self):
        if os.name != "nt" or not self.fictrac_window_hwnd:
            return False
        self._position_embedded_fictrac_window()
        return True

    def _set_event(self, message):
        if not hasattr(self, "log_frame"):
            return
        self._add_event_row(time.strftime("%H:%M:%S"), message)

    def open_config_gui(self):
        if os.path.exists(self.fictrac_configGui):
            subprocess.Popen([self.fictrac_configGui, self.fictrac_config_txt], cwd=self.fictrac_dir,
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
            self._set_event("Calibration launched")
        else:
            messagebox.showerror("Error", "Cannot find configGui.exe.")

    def start_tracking_only(self):
        if self.fictrac_process is not None and self.fictrac_process.poll() is None:
            messagebox.showinfo("Notice", "Camera tracking is already running.")
            self._try_embed_fictrac_window()
            return
        if os.path.exists(self.fictrac_exe):
            try:
                experiment_dir = self._prepare_experiment_output_dir()
                run_config = self._write_fictrac_run_config(experiment_dir)
            except Exception as exc:
                messagebox.showerror("Error", f"Could not create the experiment output directory:\n{exc}")
                return
            self._reset_session_display(clear_log=True, initial_message=self._t("New tracking session cleared.", "New tracking session cleared."), reset_live_file=True)
            # HIGH_PRIORITY_CLASS
            high_priority_flag = 0x00000080
            self.fictrac_process = subprocess.Popen([self.fictrac_exe, run_config], cwd=experiment_dir,
                                                    creationflags=subprocess.CREATE_NEW_CONSOLE | high_priority_flag)
            self.status_values["Tracking"].configure(text=f"* {self._state_word('RUNNING')}", text_color=self.colors["accent"])
            self._set_event(f"FicTrac tracking started | {experiment_dir}")
            self.live_demo_enabled = False
            self.demo_t = 0.0
            self.demo_path = []
            self._start_fictrac_status_udp()
            self.fictrac_window_hwnd = None
            self.fictrac_embed_attempts = 0
            self._camera_clip_geom = None
            self._camera_clip_placed = False
            self._embedded_window_size = None
            self.after(1000, self._try_embed_fictrac_window)
        else:
            messagebox.showerror("Error", f"Cannot find {self.fictrac_exe}. Check the FicTrac directory.")

    def start_vr_experiment(self):
        try:
            self.save_config()
        except Exception:
            messagebox.showerror("Error", "Could not save parameters. Check their format.")
            return

        if not self.tk_vars["SIMULATION_MODE"].get():
            if self.fictrac_process is None or self.fictrac_process.poll() is not None:
                response = messagebox.askyesno(
                    "Notice",
                    "No running FicTrac process was detected.\n\nContinue with the VR display only?"
                )
                if not response:
                    return

        if self.vr_process is None or self.vr_process.poll() is not None:
            try:
                experiment_dir = self._prepare_experiment_output_dir()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not create the experiment output directory:\n{exc}")
                return
            self._stop_fictrac_status_udp()
            self._reset_session_display(clear_log=True, initial_message=self._t("New VR session cleared.", "New VR session cleared."), reset_live_file=True)
            if self.is_frozen:
                self.vr_process = subprocess.Popen([self.vr_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                self.vr_process = subprocess.Popen([sys.executable, self.vr_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.status_values["State"].configure(text=self._state_word("Ready"))
            self._set_event(f"VR session launched | {experiment_dir}")
        else:
            messagebox.showinfo("Notice", "The VR experiment is already running.")

    def run_plot_trajectory(self):
        try:
            self.save_config()
        except Exception:
            pass
        if os.path.exists(self.plot_traj_script):
            plot_target = self.current_experiment_dir or self.tk_vars["SAVE_DIR"].get()
            if self.is_frozen:
                subprocess.Popen([self.plot_traj_script, plot_target], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([sys.executable, self.plot_traj_script, plot_target], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self._set_event("Trajectory plot opened")
        else:
            messagebox.showerror("Missing file", f"Not found:\n{self.plot_traj_script}")

    def run_plot_timeline(self):
        if os.path.exists(self.plot_timeline_script):
            if self.is_frozen:
                subprocess.Popen([self.plot_timeline_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([sys.executable, self.plot_timeline_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self._set_event("Timeline plot opened")
        else:
            messagebox.showerror("Missing file", f"Not found:\n{self.plot_timeline_script}")

    def run_plot_polar(self):
        try:
            self.save_config()
        except Exception as e:
            print(f"Could not save plot color settings: {e}")
        if os.path.exists(self.plot_polar_script):
            if self.is_frozen:
                subprocess.Popen([self.plot_polar_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([sys.executable, self.plot_polar_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self._set_event("Polar preference plot opened")
        else:
            messagebox.showerror("Missing file", f"Not found:\n{self.plot_polar_script}")

    def stop_all(self):
        self._stop_fictrac_status_udp()
        if self.fictrac_process:
            self.fictrac_process.terminate()
            self.fictrac_process = None
        if self.vr_process:
            self.vr_process.terminate()
            self.vr_process = None
        self.fictrac_window_hwnd = None
        self.fictrac_embed_attempts = 0
        self._camera_clip_geom = None
        self._camera_clip_placed = False
        self._embedded_window_size = None
        self.current_experiment_dir = None
        self.fictrac_run_config_txt = None
        self._refresh_suggested_fly_id()
        self._reset_session_display(clear_log=True, initial_message=None, reset_live_file=False)
        self.status_values["Tracking"].configure(text=f"* {self._state_word('STOPPED')}", text_color=self.colors["danger"])
        self._set_event("All processes terminated")
        self.after(50, self._draw_idle_panels)
