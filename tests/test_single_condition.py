import contextlib
import io
import itertools
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import main
from data_logger import ExperimentLogger


class ConditionTests(unittest.TestCase):
    def test_all_original_conditions_are_selectable(self):
        for bg, level, stimulus in itertools.product(
            ("white", "green", "red"), ("dark", "medium", "bright"), (False, True)
        ):
            with self.subTest(bg=bg, level=level, stimulus=stimulus):
                values = dict(config._cfg, SINGLE_BG_NAME=bg,
                              SINGLE_BRIGHTNESS_LABEL=level, SINGLE_STIMULUS_ON=stimulus)
                values.pop("SINGLE_BRIGHTNESS", None)
                with patch.dict(config._cfg, values, clear=True):
                    states = main.build_state_schedule()
                self.assertEqual(len(states), 1)
                state = states[0]
                self.assertEqual(state["index"], 1)
                self.assertEqual(state["bg_name"], bg)
                self.assertEqual(state["brightness_label"], level)
                self.assertEqual(state["stimulus_on"], stimulus)
                self.assertEqual(state["block"], "stimulus" if stimulus else "no_stimulus")
                self.assertEqual(state["brightness"], values[f"STATE_{bg.upper()}_{level.upper()}_BRIGHTNESS"])

    def test_defaults(self):
        state = config.get_single_state({})
        self.assertEqual((state["bg_name"], state["brightness_label"], state["stimulus_on"]),
                         ("white", "bright", False))
        self.assertEqual(config.STATE_DURATION_S, 20)
        self.assertEqual(config.VIRTUAL_WALL_DISTANCE_CM, 9.75)

    def test_invalid_conditions_are_rejected(self):
        cases = [
            {"SINGLE_BG_NAME": "blue"},
            {"SINGLE_BRIGHTNESS_LABEL": "maximum"},
            {"SINGLE_STIMULUS_ON": "false"},
            {"SINGLE_STIMULUS_ON": 1},
            {"STATE_DURATION_S": 0},
            {"STATE_DURATION_S": -20},
            {"STATE_DURATION_S": float("nan")},
            {"STATE_DURATION_S": float("inf")},
            {"STATE_WHITE_COLOR": "255,255"},
            {"STATE_WHITE_COLOR": "256,0,0"},
            {"STATE_WHITE_BRIGHT_BRIGHTNESS": -0.1},
            {"STATE_WHITE_BRIGHT_BRIGHTNESS": float("nan")},
            {"SINGLE_BRIGHTNESS": -0.01},
            {"SINGLE_BRIGHTNESS": 1.01},
            {"SINGLE_BRIGHTNESS": float("nan")},
            {"V_BAR_COUNT": 0},
            {"V_BAR_COUNT": 2.5},
            {"V_BAR_COUNT": 13},
            {"BAR_VISUAL_ANGLE_DEG": 0},
            {"BAR_VISUAL_ANGLE_DEG": 90},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(ValueError):
                config.get_single_state(values)

    def test_direct_brightness_overrides_old_matrix(self):
        for bg in ("white", "green", "red"):
            with self.subTest(bg=bg):
                state = config.get_single_state({"SINGLE_BG_NAME": bg, "SINGLE_BRIGHTNESS": 0.42})
                self.assertEqual(state["brightness"], 0.42)
                self.assertEqual(state["brightness_label"], "custom")


def packet(frame, forward, delta_ms=100, heading=0, prefix=True):
    columns = [0] * 24
    columns[0] = frame
    columns[16] = -heading
    columns[18] = 0.01
    columns[19] = forward
    columns[21] = frame * delta_ms
    columns[22] = frame
    columns[23] = delta_ms
    return (("FT, " if prefix else "") + ", ".join(map(str, columns))).encode()


def run_synthetic_trial(stimulus, destination, prefix=True, start_with_mouse=False, delta_ms=100,
                        bar_count=2, brightness=None):
    state = {"tick": 0, "draws": [], "live": [], "loggers": []}
    steps = math.ceil(20000 / delta_ms)
    batches = {
        1: [packet(1, -50, heading=-1, prefix=prefix)],
        2: [packet(2, -40, heading=-1, prefix=prefix)],
        3: [packet(3, -30, heading=-1, prefix=prefix)],
        4: [packet(4, 100, heading=math.pi / 3, prefix=prefix)],
        5: [packet(5 + i, 100 + (i + 1) * 0.01, delta_ms=delta_ms,
                   heading=math.pi / 3, prefix=prefix) for i in range(steps + 2)],
    }

    class Renderer:
        def __init__(self, *args):
            pass

        def tick(self, fps):
            state["tick"] += 1
            if state["tick"] > 8:
                raise AssertionError("Trial did not stop after its sampling duration")

        def draw_frame(self, *args, **kwargs):
            state["draws"].append((state["tick"], args, kwargs))

        def quit(self):
            state["renderer_closed"] = True

    class Socket:
        def bind(self, address):
            pass

        def setblocking(self, value):
            pass

        def recvfrom(self, size):
            queue = batches.get(state["tick"], [])
            if not queue:
                raise BlockingIOError
            return queue.pop(0), ("127.0.0.1", 2000)

        def close(self):
            state["socket_closed"] = True

    class Logger(ExperimentLogger):
        def __init__(self, *args):
            super().__init__(*args)
            state["loggers"].append(self)

    def events():
        if state["tick"] != 3:
            return []
        if start_with_mouse:
            return [SimpleNamespace(type=main.pygame.MOUSEBUTTONDOWN)]
        return [SimpleNamespace(type=main.pygame.KEYDOWN, key=main.pygame.K_SPACE)]

    values = dict(config._cfg, SINGLE_BG_NAME="green", SINGLE_BRIGHTNESS_LABEL="medium",
                  SINGLE_STIMULUS_ON=stimulus, V_BAR_COUNT=bar_count)
    values.pop("SINGLE_BRIGHTNESS", None)
    if brightness is not None:
        values["SINGLE_BRIGHTNESS"] = brightness
    with contextlib.ExitStack() as stack:
        stack.enter_context(patch.dict(config._cfg, values, clear=True))
        stack.enter_context(patch.object(config, "V_BAR_COUNT", bar_count))
        stack.enter_context(patch.object(config, "V_BAR_SPACING_DEG", 360 / bar_count))
        stack.enter_context(patch.object(config, "SAVE_DIR", str(destination)))
        stack.enter_context(patch.object(main, "VRRenderer", Renderer))
        stack.enter_context(patch.object(main.socket, "socket", return_value=Socket()))
        stack.enter_context(patch.object(main.pygame.event, "get", side_effect=events))
        stack.enter_context(patch.object(main, "ExperimentLogger", Logger))
        stack.enter_context(patch.object(main, "write_live_trajectory",
                                        side_effect=lambda _, payload, **kw: state["live"].append(payload)))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        main.main()
    state["remaining_packets"] = len(batches[5])
    logger = state["loggers"][0]
    state["rows"] = [dict(zip(logger.csv_header, row)) for row in logger.recorded_data[1:]]
    return state


class TrialLoopTests(unittest.TestCase):
    def test_start_timing_csv_and_stop_with_queued_packets(self):
        for stimulus, prefix, mouse in itertools.product((False, True), repeat=3):
            with self.subTest(stimulus=stimulus, prefix=prefix, mouse=mouse), tempfile.TemporaryDirectory() as tmp:
                result = run_synthetic_trial(stimulus, Path(tmp), prefix, mouse)
                rows = result["rows"]
                self.assertEqual(len(rows), 200)
                self.assertEqual(rows[0]["Time_s"], 0.1)
                self.assertEqual(rows[-1]["Time_s"], 20)
                self.assertEqual({row["State_Index"] for row in rows}, {1})
                self.assertEqual({row["State_BG_Name"] for row in rows}, {"green"})
                self.assertEqual({row["State_Brightness"] for row in rows}, {0.231})
                self.assertEqual({row["State_Stimulus_On"] for row in rows}, {int(stimulus)})
                self.assertEqual({row["Cfg_EXPERIMENT_PROTOCOL"] for row in rows}, {"single_condition"})
                self.assertEqual({row["Cfg_SINGLE_BG_NAME"] for row in rows}, {"green"})
                self.assertEqual({row["Cfg_SINGLE_STIMULUS_ON"] for row in rows}, {stimulus})
                self.assertTrue(all(row["Cfg_FLY_ID"] == config._cfg["FLY_ID"] for row in rows))
                self.assertAlmostEqual(sum(row["Step_Distance_cm"] for row in rows), 1.2, places=4)
                self.assertEqual(result["remaining_packets"], 2)
                self.assertEqual(result["live"][-1]["time_s"], 20)
                self.assertTrue(result["renderer_closed"] and result["socket_closed"])
                self.assertEqual(len(list(Path(tmp).glob("*_phase_summary.csv"))), 1)
                prefix = "green_medium_" + ("on" if stimulus else "off")
                self.assertEqual(len(list(Path(tmp).glob(prefix + "_*.csv"))), 2)
                self.assertFalse((Path(tmp) / main.FICTRAC_RECORDING_ACTIVE_FLAG).exists())
                self.assertEqual(float((Path(tmp) / main.FICTRAC_RECORDING_DONE_FILE).read_text()), 20)
                self.assertTrue(all(not draw[2]["stimulus_on"] for draw in result["draws"] if draw[0] < 3))
                if stimulus:
                    self.assertEqual(rows[0]["Stim_Anchor_Time_s"], 0)
                    self.assertAlmostEqual(rows[0]["Stim_Anchor_Heading_rad"], math.pi / 3, places=4)
                    self.assertEqual(rows[0]["Stim_Anchor_X_cm"], 0)
                else:
                    self.assertTrue(all(row["Stim_Anchor_Time_s"] == "" for row in rows))
                    self.assertTrue(all(row["Stim_Facing_Any"] == 0 for row in rows))

    def test_packet_crossing_end_does_not_extend_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_synthetic_trial(False, Path(tmp), delta_ms=300)
            self.assertEqual(len(result["rows"]), 66)
            self.assertLessEqual(result["rows"][-1]["Time_s"], 20)
            self.assertEqual(result["live"][-1]["time_s"], 20)
            self.assertGreater(result["remaining_packets"], 0)

    def test_count_and_brightness_reach_rendering_and_csv(self):
        for count in (1, 2, 3, 4, 12):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as tmp:
                result = run_synthetic_trial(True, Path(tmp), bar_count=count, brightness=0.42)
                draw = next(draw for draw in result["draws"] if draw[0] >= 4)
                self.assertEqual(len(draw[1][4]), count)
                self.assertEqual(draw[1][0], 0.42)
                rows = result["rows"]
                self.assertEqual({row["State_Brightness"] for row in rows}, {0.42})
                self.assertEqual({row["State_Brightness_Label"] for row in rows}, {"custom"})
                self.assertEqual({row["Cfg_V_BAR_COUNT"] for row in rows}, {count})
                self.assertEqual({row["Cfg_V_BAR_SPACING_DEG"] for row in rows}, {360 / count})
                self.assertEqual(rows[0]["Stim_Bar_Back_X_cm"] == "", count % 2 == 1)
                self.assertEqual(rows[0]["Cfg_STIMULUS_ANGLE_REFERENCE"], "front_zero")


class PlotTests(unittest.TestCase):
    def test_all_plot_commands_accept_the_condition_output_folder(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            run_synthetic_trial(True, Path(tmp))
            env = dict(os.environ, MPLBACKEND="Agg", PYTHONIOENCODING="utf-8")
            for script in ("plot_split_trajectory.py", "plot_facing_timeline.py", "plot_polar_preference.py"):
                result = subprocess.run([sys.executable, "-B", str(source / script), tmp],
                                        env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(result.returncode, 0, script + ": " + result.stderr)
            self.assertEqual(len(list(Path(tmp).rglob("*.png"))), 4)

    def test_current_polar_angles_have_no_extra_rotation(self):
        from plot_polar_preference import _stimulus_angles
        for count in (1, 2, 3, 4, 12):
            rotation, angles = _stimulus_angles({"V_BAR_COUNT": count,
                                                "V_BAR_SPACING_DEG": 360 / count,
                                                "STIMULUS_ANGLE_REFERENCE": "front_zero"})
            self.assertEqual(rotation, 0)
            self.assertEqual(len(angles), count)
            self.assertEqual(angles[0], 0)

    def test_plots_for_single_condition_trials(self):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from PIL import Image, ImageStat
        import plot_split_trajectory as trajectory
        import plot_facing_timeline as timeline
        import plot_polar_preference as polar

        for stimulus in (False, True):
            with self.subTest(stimulus=stimulus), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run_synthetic_trial(stimulus, root)
                csv_path = next(p for p in root.glob("*.csv") if "phase_summary" not in p.name)
                self.assertEqual(Path(trajectory.find_csv_in_folder(str(root))), csv_path)
                with contextlib.redirect_stdout(io.StringIO()):
                    trajectory.plot_state_trajectories(str(csv_path))
                    timeline.plot_behavior_timeline(timeline.load_clean_data(str(csv_path)), str(csv_path))
                    polar.plot_polar_radar(str(csv_path))
                plots = list(root.rglob("*.png"))
                self.assertEqual(len(plots), 4 if stimulus else 3)
                for path in plots:
                    with Image.open(path) as picture:
                        self.assertGreater(min(picture.size), 200)
                        self.assertGreater(sum(ImageStat.Stat(picture.convert("RGB")).stddev), 10)
                self.assertEqual(len(list((root / "PolarPreference").glob("*.png"))), int(stimulus))
                plt.close("all")

    def test_legacy_18_state_paths_remain_supported(self):
        import pandas as pd
        from plot_split_trajectory import build_state_paths, build_continuous_state_paths
        rows = [{"State_Index": state, "VR_Fly_X_cm": state + step / 10,
                 "VR_Fly_Y_cm": state / 2 + step / 10}
                for state in range(1, 19) for step in range(5)]
        frame = pd.DataFrame(rows)
        self.assertEqual(len(build_state_paths(frame)[0]), 18)
        self.assertEqual(len(build_continuous_state_paths(frame)[0]), 18)


if __name__ == "__main__":
    unittest.main()
