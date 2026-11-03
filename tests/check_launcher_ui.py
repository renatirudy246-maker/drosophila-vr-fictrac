import json
import math
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time
from tkinter import font as tkfont
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1]


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = Path.cwd()
        cls.temporary = tempfile.TemporaryDirectory(prefix="vr_native_ui_test_")
        cls.work = Path(cls.temporary.name)
        for path in list(SOURCE.glob("*.py")) + [SOURCE / "settings.json"]:
            shutil.copy2(path, cls.work / path.name)
        cls.settings = json.loads((cls.work / "settings.json").read_text())
        cls.settings["SAVE_DIR"] = str(cls.work / "outputs")
        cls.settings["OUTPUT_ROOT_DIR"] = str(cls.work / "outputs")
        (cls.work / "settings.json").write_text(json.dumps(cls.settings))
        runtime = cls.work / "fictrac"
        runtime.mkdir()
        (runtime / "config.txt").write_text("src_fps: 180\nsrc_fn: 1\nsave_debug: n\nsave_raw: n\nsock_port: 2000\n")
        for name in ("fictrac.exe", "configGui.exe"):
            (runtime / name).touch()
        sys.path.insert(0, str(cls.work))
        import launcher
        cls.module = launcher
        cls.app = launcher.ExperimentLauncher()
        cls.errors = []
        cls.app.report_callback_exception = lambda *error: cls.errors.append(str(error))
        cls.app.withdraw()
        cls.app.geometry(f"1280x780+{cls.app.winfo_screenwidth() + 600}+0")
        cls.app.deiconify()
        cls.pump(0.3)
        cls.initial = {key: var.get() for key, var in cls.app.tk_vars.items()}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.app._stop_fictrac_status_udp()
            cls.app.destroy()
        finally:
            os.chdir(cls.original_cwd)
            cls.temporary.cleanup()

    @classmethod
    def pump(cls, seconds=0.08):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            cls.app.update()
            time.sleep(0.003)

    def setUp(self):
        self.errors.clear()
        self.app.fictrac_process = None
        self.app.vr_process = None
        self.app.current_experiment_dir = None
        for key, value in self.initial.items():
            self.app.tk_vars[key].set(value)
        self.test_output = tempfile.TemporaryDirectory(dir=self.work, prefix="case_outputs_")
        self.case_settings = dict(self.settings, SAVE_DIR=self.test_output.name,
                                  OUTPUT_ROOT_DIR=self.test_output.name)
        for key in ("SAVE_DIR", "OUTPUT_ROOT_DIR"):
            self.app.tk_vars[key].set(self.test_output.name)
        self.app._refresh_suggested_fly_id()
        self.app.language = self.initial["UI_LANGUAGE"]
        self.app.theme_mode = self.initial["UI_THEME"]
        self.app._apply_language()
        self.app.fictrac_process = None
        self.app.vr_process = None
        self.app.current_experiment_dir = None
        self.app.fictrac_window_hwnd = None
        self.app._reset_live_trajectory_preview()

    def tearDown(self):
        self.test_output.cleanup()
        self.assertFalse(self.errors, self.errors)

    def assert_dropdown_font(self, key):
        app = self.app
        app.settings_tabs.select(1 if key == "SIMULATION_MODE" else 0)
        control = app.param_widgets[key]["control"]
        app.tk.call("ttk::combobox::Post", str(control))
        self.pump(0.02)
        try:
            popup = app.tk.call("ttk::combobox::PopdownWindow", str(control))
            listbox = f"{popup}.f.l"
            self.assertEqual(str(app.tk.call(listbox, "cget", "-font")), str(control.cget("font")), key)
            field_font = tkfont.Font(app, name=str(control.cget("font")), exists=True)
            bbox = app.tk.splitlist(app.tk.call(listbox, "bbox", 0))
            self.assertEqual(len(bbox), 4, key)
            self.assertGreaterEqual(int(bbox[3]), field_font.metrics("linespace") - 1, key)
            self.assertEqual(str(app.tk.call(listbox, "cget", "-background")), app.colors["panel_2"])
            self.assertEqual(str(app.tk.call(listbox, "cget", "-foreground")), app.colors["text"])
        finally:
            app.tk.call("ttk::combobox::Unpost", str(control))

    def test_dropdown_popup_fonts_follow_field_fonts_and_themes(self):
        app = self.app
        before = {key: variable.get() for key, variable in app.tk_vars.items()}
        for language in ("zh", "en"):
            app.language = language
            app._apply_language()
            for mode in ("dark", "light"):
                app._apply_theme(mode)
                for key in ("SINGLE_BG_NAME", "WING_CONDITION", "SINGLE_STIMULUS_ON", "SIMULATION_MODE"):
                    self.assert_dropdown_font(key)
        self.assertEqual({key: variable.get() for key, variable in app.tk_vars.items()}, before)

    def test_backend_and_parameter_inventory_are_preserved(self):
        expected = {"SINGLE_BG_NAME", "STATE_DURATION_S", "SINGLE_BRIGHTNESS", "SINGLE_STIMULUS_ON",
                    "BAR_VISUAL_ANGLE_DEG", "V_BAR_COUNT", "WING_CONDITION", "FLY_ID", "EXPERIMENT_ID",
                    "UDP_PORT", "SIMULATION_MODE", "PRE_START_BG_COLOR", "PRE_START_BRIGHTNESS",
                    "BAR_COLOR", "SCREEN_FOV_DEG", "VIRTUAL_WALL_DISTANCE_CM", "SPHERE_RADIUS_CM",
                    "MONITOR_SMOOTHING_FACTOR"}
        self.assertEqual(set(self.app.param_widgets), expected)
        self.assertEqual(len(expected), 18)
        self.assertFalse(hasattr(self.module.controller.ExperimentController, "_create_main_area"))
        for method in ("start_tracking_only", "start_vr_experiment", "_write_fictrac_run_config",
                       "_poll_fictrac_status_udp", "_parse_fictrac_status_packet", "_poll_live_trajectory",
                       "_embed_fictrac_debug_window", "_position_embedded_fictrac_window", "stop_all"):
            self.assertIs(getattr(self.module.ExperimentLauncher, method),
                          getattr(self.module.controller.ExperimentController, method))

    def test_geometry_themes_languages_and_scrolling(self):
        app = self.app
        sidebar_widths = []
        for language in ("zh", "en"):
            app.language = language
            app._apply_language()
            for size in ("1180x640", "1280x780", "1440x850"):
                app.geometry(size)
                app.settings_tabs.select(0)
                self.pump()
                sidebar_widths.append(app.param_groups_frame.winfo_width())
                self.assertFalse(hasattr(app, "main_host"))
                for index, viewport in enumerate(app._viewports):
                    app.settings_tabs.select(index)
                    self.pump(0.03)
                    for key, info in app.param_widgets.items():
                        if info["group"] is not viewport.content:
                            continue
                        label, control = info["label"], info["control"]
                        self.assertLessEqual(label.winfo_rootx() + label.winfo_width(), control.winfo_rootx(), key)
                        self.assertLessEqual(control.winfo_rootx() + control.winfo_width(),
                                             viewport.canvas.winfo_rootx() + viewport.canvas.winfo_width(), key)
                    viewport.canvas.yview_moveto(1)
                    self.pump(0.02)
                    key = "EXPERIMENT_ID" if index == 0 else "MONITOR_SMOOTHING_FACTOR"
                    control = app.param_widgets[key]["control"]
                    self.assertLessEqual(control.winfo_rooty() + control.winfo_height(),
                                         viewport.canvas.winfo_rooty() + viewport.canvas.winfo_height() + 1)
                    viewport.canvas.yview_moveto(0)
                for button in app.action_buttons.values():
                    self.assertGreaterEqual(button.winfo_rootx(), app.winfo_rootx())
                    self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), app.winfo_rootx() + app.winfo_width())
                self.assertGreater(app.camera_canvas.winfo_width(), 100)
                self.assertGreater(app.track_canvas.winfo_height(), 100)
            for mode in ("light", "dark"):
                app._apply_theme(mode)
                self.pump(0.03)
                for viewport in app._viewports:
                    self.assertEqual(viewport.content.cget("bg"), app.colors["panel"])
                    self.assertEqual(viewport.canvas.cget("bg"), app.colors["panel"])
        self.assertEqual(len(set(sidebar_widths)), 1, sidebar_widths)

    @unittest.skipUnless(os.name == "nt" and os.environ.get("VR_TEST_MIXED_DPI") == "1",
                         "Optional check for a left 100% monitor and primary 175% monitor")
    def test_cross_monitor_resize_dpi_roundtrip_and_maximize(self):
        app = self.app
        initial = {key: variable.get() for key, variable in app.tk_vars.items()}
        snapshots = []
        try:
            for index, position in enumerate(("+100+80", "+-1800+30", "+100+80", "+-1800+30")):
                app.geometry(position)
                self.pump(0.45)
                monitor = self.module.get_monitor_metrics(app)
                scale = monitor.scale
                self.assertEqual(app._get_window_scaling(), scale)
                self.assertLessEqual(abs(app.fonts["body"].cget("size")) - round(12 * scale), 1)
                self.assertEqual(app.tk.call("wm", "minsize", app._w),
                                 (round(1180 * scale), round(640 * scale)))
                if index % 2:
                    self.assertEqual(scale, 1)
                else:
                    self.assertEqual(scale, 1.75)
                for key in ("SINGLE_BG_NAME", "WING_CONDITION", "SINGLE_STIMULUS_ON", "SIMULATION_MODE"):
                    self.assert_dropdown_font(key)
                for width, height in ((1180, 640), (1450, 820), (1230, 690)):
                    app.geometry(f"{width}x{height}")
                    self.pump(0.06)
                    self.assertAlmostEqual(app.winfo_width(), round(width * scale), delta=1)
                    self.assertAlmostEqual(app.winfo_height(), round(height * scale), delta=1)
                    for tab, viewport in enumerate(app._viewports):
                        app.settings_tabs.select(tab)
                        self.pump(0.02)
                        for key, info in app.param_widgets.items():
                            if info["group"] is not viewport.content:
                                continue
                            label, control = info["label"], info["control"]
                            self.assertLessEqual(label.winfo_rootx() + label.winfo_width(), control.winfo_rootx(), key)
                    for button in app.action_buttons.values():
                        self.assertLessEqual(button.winfo_rootx() + button.winfo_width(),
                                             app.winfo_rootx() + app.winfo_width())
                snapshots.append(dict(scale=scale, size=[app.winfo_width(), app.winfo_height()],
                                      sidebar_width=app.param_groups_frame.winfo_width(),
                                      body_font=app.fonts["body"].cget("size")))
            app.state("zoomed")
            self.pump(0.25)
            self.assertEqual(app.state(), "zoomed")
            app.state("normal")
            self.pump(0.1)
            app.geometry("1210x680")
            self.pump(0.08)
            self.assertEqual((app.winfo_width(), app.winfo_height()), (1210, 680))
            self.assertEqual({key: variable.get() for key, variable in app.tk_vars.items()}, initial)
            self.assertEqual(snapshots[0], snapshots[2])
            self.assertEqual(snapshots[1], snapshots[3])
        finally:
            app.state("normal")
            app.geometry("+100+80")
            self.pump(0.6)
            self.assertEqual(app._get_window_scaling(), 1.75)
            app.geometry(f"1280x780+{app.winfo_screenwidth() + 600}+0")
            self.pump(0.2)

    def test_settings_controls_roundtrip_and_validation(self):
        app = self.app
        app.save_config()
        saved = json.loads((self.work / "settings.json").read_text())
        for key, value in self.case_settings.items():
            self.assertEqual(saved[key], value, key)
        for key in ("WING_CONDITION", "SINGLE_STIMULUS_ON", "SIMULATION_MODE"):
            selector = app.param_widgets[key]["control"]
            selector.current(1 if key == "WING_CONDITION" else 0)
            selector.event_generate("<<ComboboxSelected>>")
        self.assertEqual(app.tk_vars["WING_CONDITION"].get(), "no_wing")
        self.assertTrue(app.tk_vars["SINGLE_STIMULUS_ON"].get())
        self.assertTrue(app.tk_vars["SIMULATION_MODE"].get())
        app.tk_vars["SINGLE_BG_NAME"].set("red")
        app.tk_vars["SINGLE_BRIGHTNESS"].set("0.42")
        self.assertAlmostEqual(app.brightness_slider.get(), 0.42)
        app.brightness_slider.set(0.375)
        self.assertAlmostEqual(float(app.tk_vars["SINGLE_BRIGHTNESS"].get()), 0.375)
        app.tk_vars["V_BAR_COUNT"].set("4")
        app.save_config()
        valid_bytes = (self.work / "settings.json").read_bytes()
        for key, value in (("V_BAR_COUNT", "2.5"), ("SINGLE_BRIGHTNESS", "1.1")):
            old = app.tk_vars[key].get()
            app.tk_vars[key].set(value)
            with self.assertRaises(ValueError):
                app.save_config()
            self.assertEqual((self.work / "settings.json").read_bytes(), valid_bytes)
            app.tk_vars[key].set(old)
        entry = app.param_widgets["SINGLE_BRIGHTNESS"]["control"]
        entry.delete(0, "end")
        self.pump(0.02)
        entry.insert(0, "0.5")
        with patch.object(self.module.controller, "askcolor", return_value=((12, 34, 56), "#0c2238")):
            app.param_widgets["BAR_COLOR"]["control"].invoke()
        self.assertEqual(app.tk_vars["BAR_COLOR"].get(), "12,34,56")

    def test_compact_selectors_labels_selection_and_saved_values(self):
        app = self.app
        choices = {
            "WING_CONDITION": (("wing", "有翅", "Winged"), ("no_wing", "无翅", "Wingless")),
            "SINGLE_STIMULUS_ON": ((True, "开启", "On"), (False, "关闭", "Off")),
            "SIMULATION_MODE": ((True, "开启", "On"), (False, "关闭", "Off")),
        }
        for language in ("zh", "en"):
            app.language = language
            app._apply_language()
            for mode in ("dark", "light"):
                app._apply_theme(mode)
                self.pump(0.03)
                for key, options in choices.items():
                    selector = app.param_widgets[key]["control"]
                    background = app.param_widgets["SINGLE_BG_NAME"]["control"]
                    reference = app.param_widgets["UDP_PORT" if key == "SIMULATION_MODE" else "STATE_DURATION_S"]["control"]
                    self.assertEqual(str(selector.cget("state")), "readonly")
                    self.assertEqual(selector.winfo_reqwidth(), background.winfo_reqwidth())
                    self.assertEqual(selector.winfo_reqheight(), background.winfo_reqheight())
                    self.assertEqual(selector.winfo_width(), reference.winfo_width())
                    self.assertEqual(selector.winfo_height(), reference.winfo_height())
                    self.assertEqual(selector.winfo_x(), reference.winfo_x())
                    self.assertEqual(tuple(selector.cget("values")),
                                     tuple(zh if language == "zh" else en for _, zh, en in options))
                    for index, (value, zh, en) in enumerate(options):
                        selector.current(index)
                        selector.event_generate("<<ComboboxSelected>>")
                        self.pump(0.01)
                        self.assertEqual(app.tk_vars[key].get(), value)
                        self.assertEqual(selector.get(), zh if language == "zh" else en)
                    app.tk_vars[key].set(options[0][0])
                    self.assertEqual(selector.current(), 0)
        app.tk_vars["WING_CONDITION"].set("no_wing")
        app.tk_vars["SINGLE_STIMULUS_ON"].set(True)
        app.tk_vars["SIMULATION_MODE"].set(True)
        app.save_config()
        saved = json.loads((self.work / "settings.json").read_text())
        self.assertEqual(saved["WING_CONDITION"], "no_wing")
        self.assertIs(saved["SINGLE_STIMULUS_ON"], True)
        self.assertIs(saved["SIMULATION_MODE"], True)
        self.assertEqual(app._experiment_folder_name(), "no_wing_01_white_high")

    def test_filename_preview_uses_actual_color_intensity_and_stripes(self):
        app = self.app
        app.current_experiment_dir = None
        app._update_save_path_label()
        self.assertIn(os.path.join("wing", "wing_01_white_high"), app.save_path_label.cget("text"))
        app.tk_vars["WING_CONDITION"].set("no_wing")
        app.tk_vars["FLY_ID"].set("02")
        self.assertIn(os.path.join("no_wing", "no_wing_02_white_high"), app.save_path_label.cget("text"))
        self.assertIn("white_high_off_", app.save_path_label.cget("text"))
        app.tk_vars["SINGLE_BG_NAME"].set("green")
        app.tk_vars["SINGLE_BRIGHTNESS"].set("0.231")
        app.tk_vars["SINGLE_STIMULUS_ON"].set(True)
        self.assertIn("green_medium_on_", app.save_path_label.cget("text"))
        app.tk_vars["SINGLE_BRIGHTNESS"].set("0.42")
        self.assertIn("green_custom_on_", app.save_path_label.cget("text"))
        app.tk_vars["SINGLE_BRIGHTNESS"].set("")
        self.assertIn("condition_", app.save_path_label.cget("text"))

    def test_grouped_sample_creation_numbering_snapshot_and_overwrite_protection(self):
        app = self.app
        root = Path(self.test_output.name)
        first = Path(app._prepare_experiment_output_dir())
        self.assertEqual(first, root / "wing" / "wing_01_white_high")
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "01")
        sentinel = first / "recording.txt"
        sentinel.write_text("protected recording")
        fake = Mock()
        fake.poll.return_value = None
        app.fictrac_process = fake
        app.tk_vars["SINGLE_STIMULUS_ON"].set(True)
        self.assertEqual(Path(app._prepare_experiment_output_dir()), first)
        snapshot = json.loads((first / "experiment_settings.json").read_text())
        self.assertEqual(snapshot["FLY_ID"], "01")
        self.assertIs(snapshot["SINGLE_STIMULUS_ON"], True)
        app.tk_vars["SINGLE_BG_NAME"].set("red")
        with self.assertRaises(ValueError):
            app._prepare_experiment_output_dir()
        app.tk_vars["SINGLE_BG_NAME"].set("white")
        app.stop_all()
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "02")
        app.tk_vars["FLY_ID"].set("01")
        app.tk_vars["SINGLE_BG_NAME"].set("red")
        app.tk_vars["SINGLE_BRIGHTNESS"].set("0.329")
        with self.assertRaises(FileExistsError):
            app._prepare_experiment_output_dir()
        self.assertEqual(sentinel.read_text(), "protected recording")
        app._refresh_suggested_fly_id()
        second = Path(app._prepare_experiment_output_dir())
        self.assertEqual(second, root / "wing" / "wing_02_red_high")
        app.stop_all()
        app.tk_vars["WING_CONDITION"].set("no_wing")
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "01")
        app.tk_vars["SINGLE_BG_NAME"].set("green")
        app.tk_vars["SINGLE_BRIGHTNESS"].set("0.153")
        third = Path(app._prepare_experiment_output_dir())
        self.assertEqual(third, root / "no_wing" / "no_wing_01_green_low")
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "01")
        app.stop_all()
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "02")
        app.tk_vars["WING_CONDITION"].set("wing")
        self.assertEqual(app.tk_vars["FLY_ID"].get(), "03")
        app.tk_vars["OUTPUT_ROOT_DIR"].set(str(first))
        self.assertEqual(Path(app._get_output_root_dir()), root)

    def test_relative_export_root_produces_absolute_tracking_and_flag_paths(self):
        app = self.app
        relative = os.path.relpath(self.test_output.name, self.work)
        app.tk_vars["OUTPUT_ROOT_DIR"].set(relative)
        app.tk_vars["SAVE_DIR"].set(relative)
        folder = Path(app._prepare_experiment_output_dir())
        self.assertEqual(folder, Path(self.test_output.name) / "wing" / "wing_01_white_high")
        self.assertTrue(folder.is_absolute())
        run_config = Path(app._write_fictrac_run_config(str(folder)))
        self.assertTrue(run_config.is_absolute() and run_config.is_file())
        self.assertEqual(run_config.parent, folder)
        saved = json.loads((self.work / "settings.json").read_text())
        self.assertEqual(Path(saved["SAVE_DIR"]), folder)
        self.assertEqual(Path(saved["OUTPUT_ROOT_DIR"]), Path(self.test_output.name))

    def test_active_tracking_cannot_switch_recording_output_directories(self):
        app = self.app
        folder = Path(app._prepare_experiment_output_dir())
        fake = Mock()
        fake.poll.return_value = None
        app.fictrac_process = fake
        before = {key: variable.get() for key, variable in app.tk_vars.items()}
        with patch.object(self.module.controller.messagebox, "showerror") as error, \
                patch.object(self.module.controller.filedialog, "askdirectory") as dialog:
            app.browse_save_dir()
            error.assert_called_once()
            dialog.assert_not_called()
        self.assertEqual({key: variable.get() for key, variable in app.tk_vars.items()}, before)
        app.tk_vars["OUTPUT_ROOT_DIR"].set(str(Path(self.test_output.name) / "different_root"))
        with self.assertRaises(ValueError):
            app._prepare_experiment_output_dir()
        self.assertEqual(Path(app.current_experiment_dir), folder)
        self.assertEqual(Path(app.tk_vars["SAVE_DIR"].get()), folder)
        app.fictrac_process = None

    def test_dpi_reflow_refreshes_entry_fonts_without_changing_values(self):
        app = self.app
        before = {key: variable.get() for key, variable in app.tk_vars.items()}
        control = app.param_widgets["SINGLE_BG_NAME"]["control"]
        with patch.object(control, "configure", wraps=control.configure) as configure:
            app._native_layout_scale.apply(app._get_window_scaling())
        configure.assert_any_call(font=str(control.cget("font")))
        self.assertEqual({key: variable.get() for key, variable in app.tk_vars.items()}, before)

    def test_start_stop_calibration_video_config_and_plot_commands(self):
        app = self.app
        fake = Mock(pid=123456)
        fake.poll.return_value = None
        with patch.object(self.module.controller.subprocess, "Popen", return_value=fake) as popen, \
                patch.object(app, "_start_fictrac_status_udp") as monitor, \
                patch.object(app, "_try_embed_fictrac_window", new=lambda: None):
            app.action_buttons["calibrate"].invoke()
            self.assertEqual(popen.call_args.args[0], [app.fictrac_configGui, app.fictrac_config_txt])
            app.action_buttons["tracking"].invoke()
            self.assertIs(app.fictrac_process, fake)
            monitor.assert_called_once()
            folder = Path(app.current_experiment_dir)
            self.assertTrue(folder.is_relative_to(self.work))
            actual = popen.call_args.args[0]
            self.assertEqual(actual, [app.fictrac_exe, str(folder / "fictrac_config.txt")])
            run_config = (folder / "fictrac_config.txt").read_text()
            parsed = dict(line.split(":", 1) for line in run_config.splitlines() if ":" in line and not line.startswith("#"))
            parsed = {key.strip(): value.strip() for key, value in parsed.items()}
            self.assertEqual(parsed["src_fps"], "180")
            self.assertEqual(parsed["save_debug"], "y")
            self.assertEqual(parsed["save_raw"], "n")
            self.assertEqual(parsed["vid_codec"], "mjpg")
            app.action_buttons["vr"].invoke()
            self.assertEqual(popen.call_args.args[0], [sys.executable, "main.py"])
            self.assertIs(app.vr_process, fake)
            for name, script in (("trajectory", app.plot_traj_script), ("timeline", app.plot_timeline_script),
                                  ("polar", app.plot_polar_script)):
                app.action_buttons[name].invoke()
                self.assertEqual(popen.call_args.args[0][:2], [sys.executable, script])
            app.action_buttons["stop"].invoke()
            self.assertEqual(fake.terminate.call_count, 2)
            self.assertIsNone(app.fictrac_process)
            self.assertIsNone(app.vr_process)

    def test_live_monitoring_progress_and_preview_parent_geometry(self):
        app = self.app
        app._reset_fictrac_status_state()
        payload = dict(active=True, time_s=7.5, phase=1, fictrac_delta_ms=1000/180,
                       speed_cm_s=0.5, angular_vel_rad_s=0.2,
                       state=dict(index=1, block="stimulus", bg_name="green", brightness_label="custom"),
                       latest=dict(x=0.4, y=0.5, heading=0.3),
                       points=[[index/1000, math.sin(index/100)] for index in range(400)])
        path = Path(app.tk_vars["SAVE_DIR"].get()) / "live_trajectory.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
        app._poll_live_trajectory()
        self.assertEqual(len(app.real_track_points), 400)
        self.assertEqual(app.status_values["Time"].cget("text"), "00:07.50")
        self.assertEqual(app.status_values["Speed"].cget("text"), "0.50 cm/s")
        self.assertAlmostEqual(float(app.run_progress_bar.cget("value")), 0.375)
        self.assertGreater(len(app.track_canvas.find_all()), 10)
        user32 = Mock()
        user32.GetWindowLongW.return_value = 0
        app.fictrac_window_hwnd = 123
        app._embedded_window_size = None
        with patch.object(self.module.controller.ctypes.windll, "user32", user32):
            app._embed_fictrac_debug_window(123)
            user32.SetParent.assert_called_once_with(123, app.camera_clip_frame.winfo_id())
            self.assertEqual(user32.SetWindowPos.call_args.args[4:6], (480, 480))
            app.geometry("1280x720")
            self.pump()
            app._position_embedded_fictrac_window()
            self.assertEqual(user32.SetWindowPos.call_count, 1)
            self.assertTrue(app._camera_clip_placed)
            crop, x, y = app._camera_clip_geom
            self.assertLessEqual(crop, app.camera_canvas.winfo_width())
            self.assertLessEqual(crop, app.camera_canvas.winfo_height())
        app.fictrac_window_hwnd = None
        app._write_empty_live_trajectory()

    def test_log_has_bounded_data_and_constant_widget_count(self):
        def count(widget):
            children = widget.winfo_children()
            return len(children) + sum(count(child) for child in children)
        before = count(self.app)
        for index in range(150):
            self.app._add_event_row("12:34:56", f"event {index}")
        self.assertEqual(len(self.app._event_lines), 100)
        self.assertEqual(count(self.app), before)
        self.assertIn("event 149", self.app.log_frame.get("1.0", "end"))

    def test_udp_180fps_sample_intervals_reach_native_readouts(self):
        app = self.app
        app.tk_vars["UDP_PORT"].set(0)
        app._start_fictrac_status_udp()
        try:
            port = app.fictrac_status_socket.getsockname()[1]
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                for index in range(90):
                    columns = [0] * 24
                    columns[0] = index + 1
                    columns[19] = index / 180
                    columns[23] = 1000 / 180
                    packet = "FT, " + ", ".join(map(str, columns))
                    sender.sendto(packet.encode(), ("127.0.0.1", port))
            app._poll_fictrac_status_udp()
            self.assertAlmostEqual(app.fictrac_status_time_s, 0.5, places=6)
            self.assertEqual(app.status_values["Time"].cget("text"), "00:00.50")
            self.assertEqual(app.status_values["FicTrac Δt"].cget("text"), "5.56 ms")
            self.assertEqual(app.status_values["Speed"].cget("text"), "0.60 cm/s")
        finally:
            app._stop_fictrac_status_udp()


if __name__ == "__main__":
    unittest.main(verbosity=2)
