import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class MonitorMetrics:
    handle: int
    scale: float
    work: tuple
    chrome: tuple = (16, 40)


def get_monitor_metrics(window):
    if os.name != "nt":
        return MonitorMetrics(0, window._get_window_scaling(),
                              (0, 0, window.winfo_screenwidth(), window.winfo_screenheight()))

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    shcore = ctypes.WinDLL("shcore", use_last_error=True)
    user32.MonitorFromWindow.argtypes = (wintypes.HWND, wintypes.DWORD)
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MonitorInfo))
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    shcore.GetDpiForMonitor.argtypes = (wintypes.HANDLE, ctypes.c_int,
                                      ctypes.POINTER(wintypes.UINT), ctypes.POINTER(wintypes.UINT))
    shcore.GetDpiForMonitor.restype = ctypes.c_long
    hwnd = user32.GetAncestor(window.winfo_id(), 2)
    monitor = user32.MonitorFromWindow(hwnd, 2)
    info = MonitorInfo()
    info.size = ctypes.sizeof(info)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    dx, dy = wintypes.UINT(), wintypes.UINT()
    if shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dx), ctypes.byref(dy)) != 0:
        raise OSError("Cannot read the current monitor DPI")
    outer, client = wintypes.RECT(), wintypes.RECT()
    chrome = (16, 40)
    if user32.GetWindowRect(hwnd, ctypes.byref(outer)) and user32.GetClientRect(hwnd, ctypes.byref(client)):
        chrome = (max(0, outer.right - outer.left - client.right),
                  max(0, outer.bottom - outer.top - client.bottom))
    return MonitorMetrics(int(monitor), (dx.value + dy.value) / 192,
                          (info.work.left, info.work.top, info.work.right, info.work.bottom), chrome)


def fit_client_size(logical_size, scale, monitor):
    left, top, right, bottom = monitor.work
    margin = max(8, round(8 * scale))
    available = (max(1, right - left - monitor.chrome[0] - 2 * margin),
                 max(1, bottom - top - monitor.chrome[1] - 2 * margin))
    minimum = tuple(min(round(value * scale), limit)
                    for value, limit in zip((1180, 640), available))
    size = tuple(max(low, min(round(value * scale), limit))
                 for value, low, limit in zip(logical_size, minimum, available))
    return size, minimum


class NativeLayoutScale:
    """Keep creation-time layout dimensions so repeated DPI changes do not drift."""

    def __init__(self, root, scale, ignored_widgets=()):
        self.creation_scale = scale
        self.options = []
        self.geometry = []
        self.tracks = []
        self.entries = []

        def visit(parent):
            for widget in parent.winfo_children():
                if widget in ignored_widgets:
                    continue
                keys = []
                if isinstance(widget, tk.Frame):
                    keys += [key for key in ("width", "height") if int(widget.cget(key)) > 1]
                if isinstance(widget, tk.Label) and int(widget.cget("wraplength")):
                    keys.append("wraplength")
                if isinstance(widget, ttk.Scale):
                    keys.append("length")
                if isinstance(widget, ttk.Entry):
                    self.entries.append((widget, str(widget.cget("font"))))
                if keys:
                    self.options.append((widget, {key: float(widget.cget(key)) / scale for key in keys}))
                manager = widget.winfo_manager()
                if manager in ("grid", "pack"):
                    info = widget.grid_info() if manager == "grid" else widget.pack_info()
                    values = {key: tuple(float(value) / scale for value in (
                                  (info[key],) if isinstance(info[key], (int, float))
                                  else root.tk.splitlist(info[key])))
                              for key in ("padx", "pady", "ipadx", "ipady") if key in info}
                    self.geometry.append((widget, manager, values))
                columns, rows = widget.grid_size()
                for axis, count in (("column", columns), ("row", rows)):
                    method = getattr(widget, "grid_" + axis + "configure")
                    for index in range(count):
                        minimum = int(method(index)["minsize"])
                        if minimum:
                            self.tracks.append((widget, axis, index, minimum / scale))
                visit(widget)

        visit(root)

    def apply(self, scale):
        for widget, options in self.options:
            widget.configure(**{key: round(value * scale) for key, value in options.items()})
        for widget, manager, options in self.geometry:
            values = {key: tuple(round(value * scale) for value in values) for key, values in options.items()}
            getattr(widget, manager + "_configure")(**values)
        for widget, axis, index, minimum in self.tracks:
            getattr(widget, "grid_" + axis + "configure")(index, minsize=round(minimum * scale))
        # ttk text layouts can retain the previous monitor's font ascent.
        for widget, native_font in self.entries:
            widget.configure(font=native_font)
