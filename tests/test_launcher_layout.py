from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher import ExperimentLauncher


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

    def test_main_resize_burst_uses_only_latest_size(self):
        view, jobs = self.scheduler()
        view.main_area = Mock()
        view._apply_main_size = lambda: ExperimentLauncher._apply_main_size(view)
        for size in range(100):
            ExperimentLauncher._queue_main_resize(
                view, SimpleNamespace(width=1200 + size, height=600 + size)
            )
        self.assertEqual(len(jobs), 1)
        delay, callback = next(iter(jobs.values()))
        self.assertEqual(delay, 200)
        callback()
        view.main_area.place_configure.assert_called_once_with(width=1299, height=699)

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
