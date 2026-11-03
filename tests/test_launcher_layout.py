from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher import ExperimentLauncher
import launcher
from ui_scaling import MonitorMetrics


class LayoutTests(unittest.TestCase):
    def scheduler(self):
        jobs = {}
        serial = [0]

        def after(delay, callback):
            serial[0] += 1
            key = str(serial[0])
            jobs[key] = (delay, callback)
            return key

        def cancel(key):
            jobs.pop(key)

        return SimpleNamespace(after=after, after_cancel=cancel), jobs

    def test_monitor_change_updates_scaling_without_delayed_main_reflow(self):
        view, jobs = self.scheduler()
        view._get_window_scaling = lambda: 1.75
        view._set_scaling = Mock()
        view._poll_monitor_scaling = Mock()
        monitor = MonitorMetrics(2, 1, (-1920, 0, 0, 1032))
        with patch.object(launcher, "get_monitor_metrics", return_value=monitor), \
                patch.object(launcher.ScalingTracker, "window_scaling", 1), \
                patch.object(launcher.ScalingTracker, "widget_scaling", 1):
            ExperimentLauncher._poll_monitor_scaling(view)
        view._set_scaling.assert_called_once_with(1, 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(next(iter(jobs.values()))[1], view._poll_monitor_scaling)

    def test_unchanged_monitor_does_not_reflow_controls(self):
        view, jobs = self.scheduler()
        monitor = MonitorMetrics(2, 1, (-1920, 0, 0, 1032))
        view._monitor_key = (monitor.handle, monitor.scale, monitor.work)
        view._get_window_scaling = lambda: 1
        view._set_scaling = Mock()
        view._poll_monitor_scaling = Mock()
        with patch.object(launcher, "get_monitor_metrics", return_value=monitor), \
                patch.object(launcher.ScalingTracker, "window_scaling", 1):
            ExperimentLauncher._poll_monitor_scaling(view)
        view._set_scaling.assert_not_called()

    def test_panel_relayout_is_coalesced_and_unchanged_sizes_are_skipped(self):
        view, jobs = self.scheduler()
        view._apply_panel_sizes = lambda: ExperimentLauncher._apply_panel_sizes(view)
        panel = Mock()
        event = SimpleNamespace(width=640, height=400)
        for _ in range(100):
            ExperimentLauncher._fit_aspect_panel(view, event, panel)
        self.assertEqual(len(jobs), 1)
        _, callback = next(iter(jobs.values()))
        callback()
        panel.place_configure.assert_called_once()
        ExperimentLauncher._fit_aspect_panel(view, event, panel)
        view._apply_panel_sizes()
        panel.place_configure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
