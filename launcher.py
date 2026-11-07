import math
import tkinter as tk
from tkinter import font, ttk

import launcher_controller as controller
from customtkinter.windows.widgets.scaling import CTkScalingBaseClass, ScalingTracker
from ui_scaling import NativeLayoutScale, fit_client_size, get_monitor_metrics


class MonitorLabel(tk.Label):
    # The existing monitoring code uses CTk's text_color option.
    def configure(self, cnf=None, **kwargs):
        if "text_color" in kwargs:
            kwargs["fg"] = kwargs.pop("text_color")
        return super().configure(cnf, **kwargs)


class ProgressBar(ttk.Progressbar):
    def set(self, value):
        self.configure(value=value)


class StateSelector(ttk.Combobox):
    def __init__(self, parent, variable, choices, translate, **kwargs):
        super().__init__(parent, state="readonly", **kwargs)
        self.variable = variable
        self.choices = choices
        self.translate = translate
        variable.trace_add("write", self.refresh)
        self.bind("<<ComboboxSelected>>", self._selected)
        self.refresh()

    def refresh(self, *_):
        self.configure(values=[self.translate(zh, en) for _, zh, en in self.choices])
        value = self.variable.get()
        self.current(next(index for index, (option, _, _) in enumerate(self.choices) if option == value))

    def _selected(self, event):
        index = self.current()
        if index >= 0:
            self.variable.set(self.choices[index][0])


class ParameterViewport(tk.Frame):
    def __init__(self, parent, background):
        super().__init__(parent, bg=background, bd=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, width=1)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.content = tk.Frame(self.canvas, bg=background)
        self.window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self._content_width = None
        self._scroll_region = None
        self.canvas.bind("<Configure>", self._resize)
        self.content.bind("<Configure>", self._content_changed)

    def _resize(self, event):
        if event.width != self._content_width:
            self._content_width = event.width
            self.canvas.itemconfigure(self.window, width=event.width)

    def _content_changed(self, event):
        region = (0, 0, event.width, event.height)
        if region != self._scroll_region:
            self._scroll_region = region
            self.canvas.configure(scrollregion=region)

    def recolor(self, background):
        self.configure(bg=background)
        self.canvas.configure(bg=background)
        self.content.configure(bg=background)


class ExperimentLauncher(controller.ExperimentController):
    def _poll_monitor_scaling(self):
        try:
            monitor = get_monitor_metrics(self)
            key = (monitor.handle, monitor.scale, monitor.work)
            previous = getattr(self, "_monitor_key", None)
            self._monitor_key = key
            expected_scale = monitor.scale * ScalingTracker.window_scaling
            if expected_scale != self._get_window_scaling() or (previous is not None and key != previous):
                self._set_scaling(monitor.scale * ScalingTracker.widget_scaling,
                                  expected_scale)
        except (OSError, tk.TclError):
            pass
        self._monitor_poll_job = self.after(200, self._poll_monitor_scaling)

    def _set_scaling(self, new_widget_scaling, new_window_scaling):
        if not hasattr(self, "_native_layout_scale"):
            return super()._set_scaling(new_widget_scaling, new_window_scaling)
        old_scale = self._get_window_scaling()
        logical_size = (self.winfo_width() / old_scale, self.winfo_height() / old_scale)
        monitor = get_monitor_metrics(self)
        size, minimum = fit_client_size(logical_size, new_window_scaling, monitor)
        # CTk temporarily locks min/max to one size; native widgets need no such lock.
        CTkScalingBaseClass._set_scaling(self, new_widget_scaling, new_window_scaling)
        ScalingTracker.window_dpi_scaling_dict[self] = monitor.scale
        self._min_width, self._min_height = (value / new_window_scaling for value in minimum)
        tk.Tk.minsize(self, *minimum)
        tk.Tk.maxsize(self, round(self._max_width * new_window_scaling),
                      round(self._max_height * new_window_scaling))
        self.tk.call("tk", "scaling", monitor.scale * 96 / 72)
        for name, native_font in self.fonts.items():
            native_font.configure(size=-round(self._native_font_sizes[name] * new_window_scaling))
        self._native_layout_scale.apply(new_window_scaling)
        self._apply_theme()
        if self.state() == "normal":
            left, top, right, bottom = monitor.work
            x = min(max(self.winfo_x(), left), right - size[0] - monitor.chrome[0])
            y = min(max(self.winfo_y(), top), bottom - size[1] - monitor.chrome[1])
            tk.Tk.geometry(self, f"{size[0]}x{size[1]}+{x}+{y}")
        self._current_width, self._current_height = (value / new_window_scaling for value in size)

    def _px(self, value):
        return round(value * self._get_window_scaling())

    def _get_palette(self, mode):
        palette = super()._get_palette(mode)
        if mode == "dark":
            palette.update(bg="#181A1D", top="#202326", panel="#202326",
                           panel_2="#292D32", canvas="#181A1D", grid="#30353B",
                           separator="#383E45", border="#454D56", muted="#A9B2BC",
                           accent="#35C79A", accent_hover="#239775")
        return palette

    def _frame(self, parent, role="panel", **kwargs):
        frame = tk.Frame(parent, bg=self.colors[role], bd=0, **kwargs)
        frame._palette_role = role
        self._native_colors.append((frame, {"bg": role}))
        return frame

    def _label(self, parent, text="", english=None, muted=False, **kwargs):
        bg_role = getattr(parent, "_palette_role", "panel")
        fg_role = "muted" if muted else "text"
        kwargs.setdefault("font", self.fonts["body"])
        kwargs.setdefault("anchor", "w")
        label = MonitorLabel(parent, text=self._t(text, english) if english else text,
                             bg=self.colors[bg_role], fg=self.colors[fg_role], **kwargs)
        self._native_colors.append((label, {"bg": bg_role, "fg": fg_role}))
        if english is not None:
            self._register_localized(label, text, english)
        return label

    def _button(self, parent, zh, en, command, style="VR.TButton"):
        button = ttk.Button(parent, text=self._t(zh, en), command=command, style=style)
        self._register_localized(button, zh, en)
        return button

    def _configure_combobox_popup(self, control):
        popup = self.tk.call("ttk::combobox::PopdownWindow", str(control))
        self.tk.call(f"{popup}.f.l", "configure", "-font", str(control.cget("font")),
                     "-background", self.colors["panel_2"], "-foreground", self.colors["text"],
                     "-selectbackground", self.colors["blue"], "-selectforeground", "#FFFFFF")

    def create_ui(self):
        self._native_colors = []
        self._viewports = []
        self.action_buttons = {}
        self.param_widgets = {}
        self._event_lines = []
        self._event_line_counts = []
        self.fonts = {
            key: font.Font(self, family=family, size=-self._px(size), weight=weight)
            for key, family, size, weight in (
                ("title", "Segoe UI", 16, "bold"),
                ("subtitle", "Segoe UI", 11, "normal"),
                ("panel", "Segoe UI", 12, "bold"),
                ("body", "Segoe UI", 12, "normal"),
                ("metric", "Consolas", 15, "bold"),
                ("clock", "Consolas", 24, "bold"),
                ("mono", "Consolas", 12, "normal"),
                ("button", "Segoe UI", 12, "normal"),
            )
        }
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._create_native_header()

        main = self._frame(self, "bg")
        main.grid(row=1, column=0, sticky="nsew", padx=self._px(8), pady=self._px(8))
        self.main_area = main
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=0, minsize=self._px(330))
        main.grid_columnconfigure(1, weight=0, minsize=self._px(270))
        main.grid_columnconfigure(2, weight=1, minsize=self._px(500))
        self._create_native_parameters(main)
        self._create_native_status(main)
        self._create_native_workspace(main)
        self._create_native_footer()
        for key in ("SINGLE_BG_NAME", "SINGLE_BRIGHTNESS", "SINGLE_STIMULUS_ON", "WING_CONDITION",
                    "FLY_ID", "EXPERIMENT_ID", "SAVE_DIR", "OUTPUT_ROOT_DIR"):
            self.tk_vars[key].trace_add("write", lambda *_: self._update_save_path_label())
        for key in ("WING_CONDITION", "OUTPUT_ROOT_DIR"):
            self.tk_vars[key].trace_add("write", self._refresh_suggested_fly_id)
        self._refresh_suggested_fly_id()
        scale = self._get_window_scaling()
        self._native_font_sizes = {name: abs(value.cget("size")) / scale for name, value in self.fonts.items()}
        self._native_layout_scale = NativeLayoutScale(self, scale, (self.camera_clip_frame,))
        self.after(200, self._poll_monitor_scaling)
        self.bind("<MouseWheel>", self._scroll_parameters, add="+")
        self._apply_theme(self.theme_mode)
        self._apply_language()

    def _create_native_header(self):
        top = self._frame(self, "top", height=self._px(52))
        self.top_bar = top
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_rowconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)
        self._label(top, "Drosophila VR Experiment Console", "Drosophila VR Experiment Console",
                    font=self.fonts["title"]).grid(row=0, column=0, sticky="w", padx=self._px(14))
        self.theme_toggle_button = self._button(top, "Theme", "Theme", self.toggle_theme_mode)
        self.theme_toggle_button.grid(row=0, column=1, padx=4)
        self.theme_toggle_button.grid_configure(padx=(4, self._px(12)))

    def _new_sidebar(self, parent, column, zh, en, width):
        panel = self._frame(parent, width=self._px(width))
        panel.grid(row=0, column=column, sticky="nsew", padx=(0, self._px(8)))
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)
        self._label(panel, zh, en, font=self.fonts["panel"]).grid(
            row=0, column=0, sticky="ew", padx=self._px(12), pady=self._px(10))
        return panel

    def _create_native_parameters(self, parent):
        panel = self._new_sidebar(parent, 0, "Experiment Setup", "Experiment Setup", 330)
        panel.grid_rowconfigure(2, weight=1)
        path = self._frame(panel)
        path.grid(row=1, column=0, sticky="ew", padx=self._px(10), pady=(0, 6))
        path.grid_columnconfigure(0, weight=1)
        self._label(path, "Export Path", "Export Path", muted=True).grid(row=0, column=0, sticky="w")
        ttk.Entry(path, textvariable=self.tk_vars["OUTPUT_ROOT_DIR"], width=1,
                  font=self.fonts["body"], style="VR.TEntry").grid(
            row=1, column=0, sticky="ew", padx=(0, 6))
        self._button(path, "Browse", "Browse", self.browse_save_dir).grid(row=1, column=1)

        self.settings_tabs = ttk.Notebook(panel, style="VR.TNotebook")
        self.settings_tabs.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)
        self.settings_tab_names = (self._t("Trial", "Trial"), self._t("Advanced", "Advanced"))
        for name in self.settings_tab_names:
            viewport = ParameterViewport(self.settings_tabs, self.colors["panel"])
            self.settings_tabs.add(viewport, text=name)
            self._viewports.append(viewport)
            viewport.content._palette_role = "panel"
            viewport.content.grid_columnconfigure(0, weight=1)
            viewport.content.grid_columnconfigure(1, weight=0)
            viewport.content.next_row = 0
        self.param_groups_frame, self.advanced_params_frame = [v.content for v in self._viewports]
        basic, advanced = self.param_groups_frame, self.advanced_params_frame
        self._parameter_section(basic, "Trial Condition", "Trial Condition", (
            ("SINGLE_BG_NAME", "Background", "Background"),
            ("STATE_DURATION_S", "Duration (s)", "Duration (s)"),
            ("SINGLE_BRIGHTNESS", "Brightness (0-1)", "Brightness (0-1)"),
            ("SINGLE_STIMULUS_ON", "Visual stripes", "Visual stripes"),
            ("BAR_VISUAL_ANGLE_DEG", "Stripe width (deg)", "Stripe width (deg)"),
            ("V_BAR_COUNT", "Stripe count", "Stripe count"),
        ))
        self._parameter_section(basic, "Sample Info", "Sample Info", (
            ("WING_CONDITION", "Wings", "Wings"),
            ("FLY_ID", "Fly ID", "Fly ID"),
            ("EXPERIMENT_ID", "Trial ID", "Trial ID"),
        ))
        self._parameter_section(advanced, "Acquisition", "Acquisition", (
            ("UDP_PORT", "FicTrac port", "FicTrac port"),
            ("SIMULATION_MODE", "Simulation mode", "Simulation mode"),
        ))
        self._parameter_section(advanced, "Pre-start Display", "Pre-start Display", (
            ("PRE_START_BG_COLOR", "Pre-start background", "Pre-start background"),
            ("PRE_START_BRIGHTNESS", "Pre-start brightness", "Pre-start brightness"),
        ))
        self._parameter_section(advanced, "Visual Stimulus", "Visual Stimulus", (
            ("BAR_COLOR", "Bar color", "Bar color"),
        ))
        self._parameter_section(advanced, "Arena Geometry", "Arena Geometry", (
            ("SCREEN_FOV_DEG", "Screen FOV (deg)", "Screen FOV (deg)"),
            ("VIRTUAL_WALL_DISTANCE_CM", "Virtual wall (cm)", "Virtual wall (cm)"),
            ("SPHERE_RADIUS_CM", "Sphere radius (cm)", "Sphere radius (cm)"),
            ("MONITOR_SMOOTHING_FACTOR", "Monitor smoothing (0-1)", "Monitor smoothing (0-1)"),
        ))
        self._button(panel, "Save Config", "Save Config", self.save_config_with_prompt,
                     "Primary.VR.TButton").grid(row=3, column=0, sticky="e", padx=10, pady=8)

    def _parameter_section(self, parent, zh, en, parameters):
        row = parent.next_row
        self._label(parent, zh, en, muted=True, font=self.fonts["subtitle"]).grid(
            row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(10, 4))
        for key, zh, en in parameters:
            row += 1
            label = self._label(parent, zh, en)
            label.grid(row=row, column=0, sticky="w", padx=(8, 6), pady=6)
            variable = self.tk_vars[key]
            if key == "SINGLE_BG_NAME":
                control = ttk.Combobox(parent, textvariable=variable, state="readonly",
                                       values=("white", "green", "red"), width=12,
                                       font=self.fonts["mono"], style="VR.TCombobox")
            elif key in ("SINGLE_STIMULUS_ON", "SIMULATION_MODE", "WING_CONDITION"):
                choices = (("wing", "Winged", "Winged"), ("no_wing", "Wingless", "Wingless")) \
                    if key == "WING_CONDITION" else ((True, "On", "On"), (False, "Off", "Off"))
                control = StateSelector(parent, variable, choices, self._t, width=12,
                                        font=self.fonts["mono"], style="VR.TCombobox")
            elif key == "SINGLE_BRIGHTNESS":
                controls = self._frame(parent)
                controls.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=6)
                control = ttk.Entry(controls, textvariable=variable, width=6,
                                    font=self.fonts["mono"], style="VR.TEntry")
                control.pack(side="right", padx=(4, 0))
                self.brightness_slider = ttk.Scale(controls, from_=0, to=1, length=self._px(54),
                                                   command=self._brightness_changed, style="VR.Horizontal.TScale")
                self.brightness_slider.pack(side="left", fill="x", expand=True)
                self._sync_brightness()
                variable.trace_add("write", self._sync_brightness)
            elif "COLOR" in key:
                control = tk.Button(parent, text="", width=5, height=1, bd=1,
                                    relief="solid", bg=self._rgb_to_hex(variable.get()),
                                    activebackground=self._rgb_to_hex(variable.get()),
                                    font=self.fonts["body"], cursor="hand2")
                control.configure(command=lambda k=key, b=control: self._open_color_picker(k, b))
            else:
                control = ttk.Entry(parent, textvariable=variable, width=13,
                                    font=self.fonts["mono"], style="VR.TEntry")
            if isinstance(control, ttk.Combobox):
                control.configure(postcommand=lambda c=control: self._configure_combobox_popup(c))
            if key != "SINGLE_BRIGHTNESS":
                control.grid(row=row, column=1, sticky="e" if "COLOR" in key else "ew", padx=(0, 8), pady=6)
            self.param_widgets[key] = dict(row=parent, label=label, control=control, group=parent)
        parent.next_row = row + 1

    def _brightness_changed(self, value):
        if not getattr(self, "_syncing_brightness", False):
            self.tk_vars["SINGLE_BRIGHTNESS"].set(str(round(float(value), 3)))

    def _sync_brightness(self, *_):
        try:
            value = float(self.tk_vars["SINGLE_BRIGHTNESS"].get())
            if math.isfinite(value) and 0 <= value <= 1:
                self._syncing_brightness = True
                try:
                    self.brightness_slider.set(value)
                finally:
                    self._syncing_brightness = False
        except ValueError:
            pass

    def _scroll_parameters(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, ParameterViewport):
                if widget.content.winfo_height() > widget.canvas.winfo_height():
                    steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
                    widget.canvas.yview_scroll(steps, "units")
                    return "break"
                return None
            widget = widget.master

    def _create_native_status(self, parent):
        panel = self._new_sidebar(parent, 1, "Session Status", "Session Status", 270)
        panel.grid_rowconfigure(6, weight=1)
        self.clock_label = self._label(panel, font=self.fonts["clock"])
        self.clock_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        metrics = self._frame(panel)
        metrics.grid(row=2, column=0, sticky="ew", padx=12)
        metrics.grid_columnconfigure(1, weight=1)
        for row, (zh, en, value) in enumerate((
            ("Tracking", "Tracking", self._state_word("IDLE")),
            ("State", "State", self._state_word("Standby")),
            ("Time", "Time", "00:00.00"),
            ("FicTrac Delta t", "FicTrac Delta t", "--"),
            ("Speed", "Speed", "0.00 cm/s"),
            ("Angular Vel.", "Angular Vel.", "0.00 rad/s"),
        )):
            self._label(metrics, zh, en, muted=True).grid(row=row, column=0, sticky="nw", pady=5, padx=(0, 8))
            label = self._label(metrics, value, font=self.fonts["mono"], width=1,
                                wraplength=self._px(150), justify="left", height=2 if en == "State" else 1)
            label.grid(row=row, column=1, sticky="ew", pady=5)
            self.status_values[en] = label

        progress = self._frame(panel)
        progress.grid(row=3, column=0, sticky="ew", padx=12, pady=10)
        progress.grid_columnconfigure(0, weight=1)
        self._label(progress, "Run Progress", "Run Progress", font=self.fonts["panel"]).grid(row=0, column=0, sticky="w")
        self.run_progress_bar = ProgressBar(progress, maximum=1, style="VR.Horizontal.TProgressbar")
        self.run_progress_bar.grid(row=1, column=0, sticky="ew", pady=6)
        self.run_progress_label = self._label(progress, width=1)
        self.run_progress_label.grid(row=2, column=0, sticky="ew")
        self.run_state_detail_label = self._label(progress, muted=True, wraplength=self._px(235),
                                                 width=1, height=2, justify="left")
        self.run_state_detail_label.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self._label(panel, "Run Notes", "Run Notes", font=self.fonts["panel"]).grid(
            row=5, column=0, sticky="w", padx=12, pady=(0, 4))
        log = self._frame(panel)
        log.grid(row=6, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log.grid_columnconfigure(0, weight=1)
        log.grid_rowconfigure(0, weight=1)
        self.log_frame = tk.Text(log, width=1, height=1, bd=0, wrap="word", state="disabled",
                                 font=self.fonts["subtitle"], highlightthickness=0)
        self.log_frame.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log, orient="vertical", command=self.log_frame.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_frame.configure(yscrollcommand=scrollbar.set)
        self._native_colors.append((self.log_frame, {"bg": "panel_2", "fg": "text", "insertbackground": "text"}))

    def _create_native_workspace(self, parent):
        workspace = self._frame(parent, "bg")
        workspace.grid(row=0, column=2, sticky="nsew")
        workspace.grid_columnconfigure(0, weight=1)
        for row, name, zh, en, detail_zh, detail_en in (
            (0, "camera", "Camera / Ball Tracking", "Camera / Ball Tracking", "ROI overlay", "ROI overlay"),
            (1, "track", "Virtual Trajectory", "Virtual Trajectory", "VR world coordinates", "VR world coordinates"),
        ):
            workspace.grid_rowconfigure(row, weight=1, uniform="preview")
            slot = self._frame(workspace, "bg")
            slot.grid(row=row, column=0, sticky="nsew", pady=(0, 4) if row == 0 else (4, 0))
            panel = self._frame(slot)
            panel.place(relx=0.5, rely=0.5, anchor="center")
            panel.grid_rowconfigure(1, weight=1)
            panel.grid_columnconfigure(0, weight=1)
            header = self._frame(panel, height=self._px(30))
            header.grid(row=0, column=0, sticky="ew")
            header.grid_propagate(False)
            self._label(header, zh, en, font=self.fonts["panel"]).pack(side="left", padx=10)
            self._label(header, detail_zh, detail_en, muted=True, font=self.fonts["subtitle"]).pack(side="right", padx=10)
            body = self._frame(panel, "canvas")
            body.grid(row=1, column=0, sticky="nsew")
            body.grid_rowconfigure(0, weight=1)
            body.grid_columnconfigure(0, weight=1)
            canvas = tk.Canvas(body, bg=self.colors["canvas"], highlightthickness=0, width=1, height=1)
            canvas.grid(row=0, column=0, sticky="nsew")
            canvas.bind("<Configure>", lambda event: self._on_camera_canvas_configure())
            slot.bind("<Configure>", lambda event, p=panel: self._fit_aspect_panel(event, p))
            setattr(self, name + "_slot", slot)
            setattr(self, name + "_panel", panel)
            setattr(self, name + "_canvas", canvas)
            self._native_colors.append((canvas, {"bg": "canvas"}))
            if name == "camera":
                self.camera_clip_frame = self._frame(body, "canvas", width=320, height=320)
                self.camera_clip_frame.place_forget()

    def _create_native_footer(self):
        bottom = self._frame(self, "top", height=self._px(48))
        self.bottom_bar = bottom
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_propagate(False)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_rowconfigure(0, weight=1)
        self.save_path_label = self._label(bottom, width=1, muted=True, font=self.fonts["subtitle"])
        self.save_path_label.grid(row=0, column=0, sticky="ew", padx=12)
        actions = self._frame(bottom, "top")
        actions.grid(row=0, column=1, sticky="e", padx=8)
        for column, (name, zh, en, command, style) in enumerate((
            ("calibrate", "Calibration", "Calibration", self.open_config_gui, "VR.TButton"),
            ("tracking", "Start Tracking", "Start Tracking", self.start_tracking_only, "Primary.VR.TButton"),
            ("vr", "Launch VR", "Launch VR", self.start_vr_experiment, "Accent.VR.TButton"),
            ("trajectory", "Plot Trajectory", "Plot Trajectory", self.run_plot_trajectory, "VR.TButton"),
            ("timeline", "Plot Timeline", "Plot Timeline", self.run_plot_timeline, "VR.TButton"),
            ("polar", "Polar Preference", "Polar Preference", self.run_plot_polar, "VR.TButton"),
            ("stop", "Stop All", "Stop All", self.stop_all, "Danger.VR.TButton"),
        )):
            button = self._button(actions, zh, en, command, style)
            button.grid(row=0, column=column, padx=3)
            self.action_buttons[name] = button

    def _apply_theme(self, mode=None):
        if mode is not None:
            self.theme_mode = mode
        self.colors = self._get_palette(self.theme_mode)
        controller.ctk.set_appearance_mode("Light" if self.theme_mode == "light" else "Dark")
        self.configure(fg_color=self.colors["bg"])
        p = self.colors
        self.style.configure("VR.TButton", background=p["panel_2"], foreground=p["text"],
                             font=self.fonts["button"], padding=(self._px(8), self._px(5)))
        self.style.map("VR.TButton", background=[("active", p["grid"])])
        for prefix, color in (("Primary", "blue"), ("Accent", "accent"), ("Danger", "danger")):
            name = prefix + ".VR.TButton"
            self.style.configure(name, background=p[color], foreground="#FFFFFF")
            self.style.map(name, background=[("active", p[color + "_hover"])], foreground=[("active", "#FFFFFF")])
        self.style.configure("VR.TNotebook", background=p["panel"], borderwidth=0, tabmargins=0)
        self.style.configure("VR.TNotebook.Tab", background=p["panel_2"], foreground=p["muted"],
                             font=self.fonts["body"], padding=(self._px(12), self._px(6)))
        self.style.map("VR.TNotebook.Tab", background=[("selected", p["panel"]), ("active", p["grid"])],
                       foreground=[("selected", p["text"])])
        for name in ("VR.TEntry", "VR.TCombobox"):
            self.style.configure(name, fieldbackground=p["panel_2"], foreground=p["text"],
                                 background=p["panel_2"], arrowcolor=p["text"],
                                 insertcolor=p["text"], bordercolor=p["border"], padding=self._px(4),
                                 font=self.fonts["mono"])
            self.style.map(name, fieldbackground=[("readonly", p["panel_2"])], foreground=[("readonly", p["text"])])
        self.style.configure("VR.Horizontal.TScale", background=p["panel"], troughcolor=p["grid"])
        self.style.configure("VR.Horizontal.TProgressbar", background=p["accent"], troughcolor=p["grid"],
                             thickness=self._px(7), borderwidth=0)
        self.style.configure("Vertical.TScrollbar", background=p["border"], troughcolor=p["panel"], borderwidth=0)
        self.option_add("*TCombobox*Listbox.background", p["panel_2"])
        self.option_add("*TCombobox*Listbox.foreground", p["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", p["blue"])
        self.option_add("*TCombobox*Listbox.font", self.fonts["mono"])
        for info in self.param_widgets.values():
            control = info["control"]
            if isinstance(control, ttk.Combobox) and self.tk.call("winfo", "exists", f"{control}.popdown.f.l"):
                self._configure_combobox_popup(control)
        for widget, options in self._native_colors:
            widget.configure(**{key: p[role] for key, role in options.items()})
        for viewport in self._viewports:
            viewport.recolor(p["panel"])
        self.log_frame.tag_configure("time", foreground=p["muted"])
        self._redraw_theme_sensitive_views()

    def _apply_language(self):
        self.language = "en"
        title = self._t("Drosophila VR Experiment Console", "Drosophila VR Experiment Console")
        self.title(title)
        for widget, zh, en, attribute in self.localized_widgets:
            widget.configure(**{attribute: self._t(zh, en)})
        for info in self.param_widgets.values():
            if isinstance(info["control"], StateSelector):
                info["control"].refresh()
        self.settings_tab_names = (self._t("Trial", "Trial"), self._t("Advanced", "Advanced"))
        for index, name in enumerate(self.settings_tab_names):
            self.settings_tabs.tab(index, text=name)
        for label in self.status_values.values():
            label.configure(text=self._translate_status_text(label.cget("text")))
        self._update_save_path_label()
        self._redraw_theme_sensitive_views()

    def _open_color_picker(self, key, button_widget):
        color = controller.askcolor(color=self._rgb_to_hex(self.tk_vars[key].get()), parent=self,
                                title=self._t("Select Color", "Select Color"))[0]
        if color:
            r, g, b = [int(value) for value in color]
            self.tk_vars[key].set(f"{r},{g},{b}")
            button_widget.configure(bg=f"#{r:02x}{g:02x}{b:02x}", activebackground=f"#{r:02x}{g:02x}{b:02x}")

    def _clear_event_log(self, initial_message=None):
        self._event_lines.clear()
        self._event_line_counts.clear()
        self.log_frame.configure(state="normal")
        self.log_frame.delete("1.0", "end")
        self.log_frame.configure(state="disabled")
        if initial_message:
            self._add_event_row("--:--", initial_message)

    def _add_event_row(self, t_text, msg):
        msg = str(msg)
        at_bottom = self.log_frame.yview()[1] >= 0.99
        self._event_lines.append((t_text, msg))
        self._event_line_counts.append(msg.count("\n") + 1)
        self.log_frame.configure(state="normal")
        self.log_frame.insert("end", t_text + "  ", "time")
        self.log_frame.insert("end", msg + "\n")
        if len(self._event_lines) > 100:
            self._event_lines.pop(0)
            lines = self._event_line_counts.pop(0)
            self.log_frame.delete("1.0", f"{lines + 1}.0")
        self.log_frame.configure(state="disabled")
        if at_bottom:
            self.log_frame.see("end")


if __name__ == "__main__":
    app = ExperimentLauncher()
    app.mainloop()
