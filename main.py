import os

os.environ['SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS'] = '0'

import time
import socket
import math
import json
import random
import traceback
import pygame
import threading

import config as cfg
from data_logger import ExperimentLogger
from renderer import VRRenderer


def integrate_body_motion_to_world(delta_forward, delta_lateral, prev_heading, current_heading, substeps=4):
    step_dist = math.hypot(delta_forward, delta_lateral)
    if step_dist <= 1e-12:
        return 0.0, 0.0

    heading_delta = current_heading - prev_heading
    heading_delta = (heading_delta + math.pi) % (2 * math.pi) - math.pi

    dir_x = delta_forward / step_dist
    dir_y = delta_lateral / step_dist
    step_size = step_dist / substeps
    heading_step = heading_delta / substeps

    world_dx = 0.0
    world_dy = 0.0
    heading = prev_heading + heading_step / 2.0
    for _ in range(substeps):
        world_dx += step_size * (dir_x * math.cos(heading) - dir_y * math.sin(heading))
        world_dy += step_size * (dir_x * math.sin(heading) + dir_y * math.cos(heading))
        heading += heading_step

    return world_dx, world_dy


def flush_pending_socket_packets(sock):
    while True:
        try:
            sock.recvfrom(1024)
        except BlockingIOError:
            break


_live_write_thread = None

def write_live_trajectory(save_dir, payload, sync=False):
    global _live_write_thread

    def worker():
        os.makedirs(save_dir, exist_ok=True)
        live_path = os.path.join(save_dir, "live_trajectory.json")
        tmp_path = f"{live_path}.{os.getpid()}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False)
            for _ in range(8):
                try:
                    os.replace(tmp_path, live_path)
                    break
                except PermissionError:
                    time.sleep(0.015)
                except OSError:
                    break
        except OSError:
            pass
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

    if sync:
        if _live_write_thread is not None and _live_write_thread.is_alive():
            _live_write_thread.join(timeout=1.0)
        worker()
        return True
    else:
        if _live_write_thread is not None and _live_write_thread.is_alive():
            return False
        _live_write_thread = threading.Thread(target=worker, daemon=True)
        _live_write_thread.start()
        return True



FICTRAC_RECORDING_ACTIVE_FLAG = "fictrac_recording_active.flag"
FICTRAC_RECORDING_DONE_FILE = "fictrac_recording_done.txt"


def _fictrac_recording_path(filename):
    return os.path.join(cfg.SAVE_DIR, filename)


def clear_fictrac_debug_recording_flags():
    for filename in (FICTRAC_RECORDING_ACTIVE_FLAG, FICTRAC_RECORDING_DONE_FILE):
        try:
            path = _fictrac_recording_path(filename)
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def start_fictrac_debug_recording(target_duration_s):
    os.makedirs(cfg.SAVE_DIR, exist_ok=True)
    clear_fictrac_debug_recording_flags()
    try:
        with open(_fictrac_recording_path(FICTRAC_RECORDING_ACTIVE_FLAG), "w", encoding="utf-8") as file:
            file.write(f"{float(target_duration_s):.6f}\n")
    except OSError:
        pass


def finish_fictrac_debug_recording(target_duration_s):
    try:
        active_path = _fictrac_recording_path(FICTRAC_RECORDING_ACTIVE_FLAG)
        if os.path.exists(active_path):
            os.remove(active_path)
    except OSError:
        pass
    try:
        with open(_fictrac_recording_path(FICTRAC_RECORDING_DONE_FILE), "w", encoding="utf-8") as file:
            file.write(f"{max(0.0, float(target_duration_s)):.6f}\n")
    except OSError:
        pass
def build_state_schedule():
    state_options = getattr(cfg, "STATE_COLOR_BRIGHTNESS_MATRIX", None)
    if not state_options:
        bg_options = cfg.STATE_BG_OPTIONS or [
            {"name": "white", "color": (255, 255, 255), "color_str": "255,255,255"},
            {"name": "green", "color": (0, 255, 0), "color_str": "0,255,0"},
            {"name": "red", "color": (255, 0, 0), "color_str": "255,0,0"},
        ]
        brightness_options = cfg.STATE_BRIGHTNESS_OPTIONS or [
            {"name": "dark", "value": 0.25},
            {"name": "medium", "value": 0.55},
            {"name": "bright", "value": 1.0},
        ]
        state_options = []
        for bg in bg_options:
            for brightness in brightness_options:
                state_options.append({
                    "bg_name": bg["name"],
                    "bg_color": bg["color"],
                    "bg_color_str": bg["color_str"],
                    "brightness_label": brightness["name"],
                    "brightness": brightness["value"],
                })

    def make_block(block_name, stimulus_on):
        states = []
        for option in state_options:
            state = dict(option)
            state["block"] = block_name
            state["stimulus_on"] = stimulus_on
            states.append(state)
        return states

    rng = random.Random(cfg.STATE_RANDOM_SEED or None)
    no_stim_states = make_block("no_stimulus", False)
    stim_states = make_block("stimulus", True)
    rng.shuffle(no_stim_states)
    rng.shuffle(stim_states)

    schedule = no_stim_states + stim_states
    for index, state in enumerate(schedule, start=1):
        state["index"] = index
        state["label"] = (
            f"{index:02d}_{state['block']}_{state['bg_name']}_"
            f"{state['brightness_label']}"
        )
    return schedule

def main():
    renderer = VRRenderer(cfg.SCREEN_FOV_RAD, cfg.BLACK)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((cfg.UDP_IP, cfg.UDP_PORT))
    sock.setblocking(False)

    running = True
    experiment_started = False
    start_time = 0
    current_phase = 0
    state_schedule = []
    current_state = None
    state_elapsed_s = 0.0
    current_bg_color = cfg.PRE_START_BG_COLOR
    current_stimulus_on = False

    fly_x, fly_y = 0.0, 0.0
    current_brightness = cfg.PRE_START_BRIGHTNESS

    if cfg.SIMULATION_MODE:
        smoothed_heading, current_raw_heading = 0.0, 0.0
    else:
        smoothed_heading, current_raw_heading = None, None

    prev_time = None
    prev_forward, prev_lateral = 0.0, 0.0
    prev_heading = None
    prev_perf_time = None
    experiment_time_s = 0.0
    target_debug_video_duration_s = 0.0
    awaiting_first_experiment_frame = False

    vr_fly_x, vr_fly_y = 0.0, 0.0

    world_generated = False
    stimulus_initialized = False

    wall_center_x, wall_center_y = 0.0, 0.0
    arena_center_x, arena_center_y = 0.0, 0.0
    FORWARD_GAIN = 1.0
    last_no_stim_anchor = None
    stimulus_anchor = None

    def initialize_stimulus_from_anchor():
        nonlocal stimulus_initialized, stimulus_anchor, arena_center_x, arena_center_y
        nonlocal wall_center_x, wall_center_y, v_bar_world_coords

        if stimulus_initialized:
            return True

        anchor = last_no_stim_anchor
        if anchor is None:
            if current_raw_heading is None:
                return False
            anchor = {
                "time": experiment_time_s,
                "x": vr_fly_x,
                "y": vr_fly_y,
                "heading": current_raw_heading,
            }

        v_bar_world_coords.clear()
        stimulus_anchor = anchor.copy()
        arena_center_x = anchor["x"]
        arena_center_y = anchor["y"]
        wall_center_x = arena_center_x + cfg.VIRTUAL_WALL_DISTANCE_CM * math.cos(anchor["heading"])
        wall_center_y = arena_center_y + cfg.VIRTUAL_WALL_DISTANCE_CM * math.sin(anchor["heading"])

        # 第一个有刺激状态开始时，用“无刺激最后一帧”的位置和朝向锚定前/后条纹。
        # 这样第一帧刺激在果蝇视觉中位于正前方屏幕中央，之后条纹固定在虚拟世界坐标中。
        for offset_rad in (0.0, math.pi):
            abs_angle = anchor["heading"] + offset_rad
            bx = arena_center_x + cfg.VIRTUAL_WALL_DISTANCE_CM * math.cos(abs_angle)
            by = arena_center_y + cfg.VIRTUAL_WALL_DISTANCE_CM * math.sin(abs_angle)
            v_bar_world_coords.append((bx, by))

        stimulus_initialized = True
        print(
            "刺激 block 触发：条纹已按无刺激最后一帧锚定 "
            f"(t={anchor['time']:.4f}s, heading={anchor['heading']:.4f} rad)。"
        )
        return True

    logger = ExperimentLogger(
        cfg.SAVE_DIR,
        cfg.get_experiment_config_snapshot({
            "FORWARD_GAIN": FORWARD_GAIN,
            "VR_POSITION_MODE": "unbounded",
        })
    )

    v_bar_world_coords = []
    live_track_points = []
    last_live_write_time = 0.0

    clear_fictrac_debug_recording_flags()

    print(f"\n--- 虚拟现实系统就绪 (已启用高频全量记录) ---")
    print("【快捷键】：空格(开始) | ↑↓(调亮度) | F11(全屏) | ESC(退出)")

    while running:
        renderer.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    if not experiment_started:
                        flush_pending_socket_packets(sock)
                        experiment_started = True
                        start_time = time.perf_counter()
                        state_schedule = build_state_schedule()

                        target_debug_video_duration_s = len(state_schedule) * cfg.STATE_DURATION_S

                        start_fictrac_debug_recording(target_debug_video_duration_s)
                        current_state = state_schedule[0]
                        current_phase = current_state["index"]
                        state_elapsed_s = 0.0
                        current_bg_color = current_state["bg_color"]
                        current_brightness = current_state["brightness"]
                        current_stimulus_on = current_state["stimulus_on"]
                        world_generated = False
                        stimulus_initialized = False
                        last_no_stim_anchor = None
                        stimulus_anchor = None
                        v_bar_world_coords.clear()
                        prev_time, prev_heading = None, None
                        prev_perf_time = None
                        experiment_time_s = 0.0
                        awaiting_first_experiment_frame = True
                        logger.reset()
                        live_track_points = []
                        last_live_write_time = 0.0
                        write_live_trajectory(cfg.SAVE_DIR, {
                            "active": True,
                            "time_s": 0.0,
                            "phase": current_phase,
                            "state": current_state,
                            "state_elapsed_s": state_elapsed_s,
                            "fictrac_delta_ms": None,
                            "speed_cm_s": 0.0,
                            "angular_vel_rad_s": 0.0,
                            "points": [],
                            "latest": {"x": 0.0, "y": 0.0, "heading": None},
                        }, sync=True)
                        print("\n▶ 实验开始！")
                elif event.key == pygame.K_UP:
                    current_brightness = min(1.0, current_brightness + 0.1)
                elif event.key == pygame.K_DOWN:
                    current_brightness = max(0.0, current_brightness - 0.1)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not experiment_started:
                    flush_pending_socket_packets(sock)
                    experiment_started = True
                    start_time = time.perf_counter()
                    state_schedule = build_state_schedule()

                    target_debug_video_duration_s = len(state_schedule) * cfg.STATE_DURATION_S

                    start_fictrac_debug_recording(target_debug_video_duration_s)
                    current_state = state_schedule[0]
                    current_phase = current_state["index"]
                    state_elapsed_s = 0.0
                    current_bg_color = current_state["bg_color"]
                    current_brightness = current_state["brightness"]
                    current_stimulus_on = current_state["stimulus_on"]
                    world_generated = False
                    stimulus_initialized = False
                    last_no_stim_anchor = None
                    stimulus_anchor = None
                    v_bar_world_coords.clear()
                    prev_time, prev_heading = None, None
                    prev_perf_time = None
                    experiment_time_s = 0.0
                    awaiting_first_experiment_frame = True
                    logger.reset()
                    live_track_points = []
                    last_live_write_time = 0.0
                    write_live_trajectory(cfg.SAVE_DIR, {
                        "active": True,
                        "time_s": 0.0,
                        "phase": current_phase,
                        "state": current_state,
                        "state_elapsed_s": state_elapsed_s,
                        "fictrac_delta_ms": None,
                        "speed_cm_s": 0.0,
                        "angular_vel_rad_s": 0.0,
                        "points": [],
                        "latest": {"x": 0.0, "y": 0.0, "heading": None},
                    }, sync=True)
                    print("\n▶ 实验开始！")

        if experiment_started:
            elapsed_time = experiment_time_s
            total_duration_s = len(state_schedule) * cfg.STATE_DURATION_S
            if elapsed_time >= total_duration_s:
                experiment_started = False
                running = False
            elif state_schedule:
                state_pos = min(int(elapsed_time // cfg.STATE_DURATION_S), len(state_schedule) - 1)
                current_state = state_schedule[state_pos]
                current_phase = current_state["index"]
                state_elapsed_s = elapsed_time - state_pos * cfg.STATE_DURATION_S
                current_bg_color = current_state["bg_color"]
                current_brightness = current_state["brightness"]
                current_stimulus_on = current_state["stimulus_on"]

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                data_str = data.decode('utf-8')
                values = [value.strip() for value in data_str.strip().split(',')]
                has_ft_prefix = bool(values) and values[0] == 'FT'
                col = lambda n: n if has_ft_prefix else n - 1

                required_cols = [1, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
                if len(values) > max(col(n) for n in required_cols):
                    try:
                        recv_perf_time = time.perf_counter()
                        ft_frame = int(float(values[col(1)]))
                        ft_x_cm = float(values[col(15)]) * cfg.SPHERE_RADIUS_CM
                        ft_y_cm = float(values[col(16)]) * cfg.SPHERE_RADIUS_CM
                        ft_heading_rad = float(values[col(17)])
                        ft_move_dir_rad = float(values[col(18)])
                        ft_speed_cm_s = (float(values[col(19)]) * cfg.SPHERE_RADIUS_CM) / max(float(values[col(24)]) / 1000.0, 1e-9)
                        ft_forward_cm = float(values[col(20)]) * cfg.SPHERE_RADIUS_CM
                        ft_lateral_cm = float(values[col(21)]) * cfg.SPHERE_RADIUS_CM
                        fictrac_timestamp_ms = float(values[col(22)])
                        fictrac_seq = int(float(values[col(23)]))
                        fictrac_delta_ms = float(values[col(24)])

                        # FicTrac 输出列 20、21、17 分别为前进、侧移和航向。
                        raw_fly_forward = ft_forward_cm
                        raw_fly_lateral = -ft_lateral_cm
                        current_raw_heading = -ft_heading_rad
                    except (ValueError, IndexError):
                        continue

                    if cfg.INVERT_ROTATION:
                        current_raw_heading = -current_raw_heading
                        raw_fly_lateral = -raw_fly_lateral

                    if cfg.INVERT_FORWARD:
                        raw_fly_forward = -raw_fly_forward
                        raw_fly_lateral = -raw_fly_lateral

                    if smoothed_heading is None:
                        smoothed_heading = current_raw_heading
                    else:
                        diff = (current_raw_heading - smoothed_heading + math.pi) % (2 * math.pi) - math.pi
                        smoothed_heading += cfg.SMOOTHING_FACTOR * diff
                        smoothed_heading = (smoothed_heading + math.pi) % (2 * math.pi) - math.pi

                    packet_time = experiment_time_s if experiment_started else 0.0

                    raw_speed, raw_ang_vel, step_dist = 0.0, 0.0, 0.0

                    if experiment_started:
                        if awaiting_first_experiment_frame:
                            awaiting_first_experiment_frame = False
                            experiment_time_s = 0.0
                            prev_perf_time = recv_perf_time
                            prev_time = experiment_time_s
                            prev_forward = raw_fly_forward
                            prev_lateral = raw_fly_lateral
                            prev_heading = current_raw_heading
                            continue

                        perf_dt = None if prev_perf_time is None else recv_perf_time - prev_perf_time
                        if fictrac_delta_ms is not None and fictrac_delta_ms > 0:
                            dt = fictrac_delta_ms / 1000.0
                            if dt > 0.5 and perf_dt is not None and perf_dt > 0:
                                print(f"[警告] FicTrac Δt 异常: {fictrac_delta_ms:.3f} ms，改用本机计时 {perf_dt:.4f} s")
                                dt = perf_dt
                        elif perf_dt is not None:
                            dt = perf_dt
                        else:
                            dt = 0.0

                        if dt <= 0:
                            continue

                        experiment_time_s += dt
                        packet_time = experiment_time_s

                        if state_schedule:
                            state_pos = min(int(experiment_time_s // cfg.STATE_DURATION_S), len(state_schedule) - 1)
                            current_state = state_schedule[state_pos]
                            current_phase = current_state["index"]
                            state_elapsed_s = experiment_time_s - state_pos * cfg.STATE_DURATION_S
                            current_bg_color = current_state["bg_color"]
                            current_brightness = current_state["brightness"]
                            current_stimulus_on = current_state["stimulus_on"]

                        if prev_time is None:
                            prev_time = packet_time
                            prev_perf_time = recv_perf_time
                            prev_forward = raw_fly_forward
                            prev_lateral = raw_fly_lateral
                            prev_heading = current_raw_heading
                            continue

                        if dt > 0:
                            delta_forward = raw_fly_forward - prev_forward
                            delta_lateral = raw_fly_lateral - prev_lateral

                            vr_dx, vr_dy = integrate_body_motion_to_world(
                                delta_forward,
                                delta_lateral,
                                prev_heading,
                                current_raw_heading,
                            )

                            next_vr_x = vr_fly_x + vr_dx * FORWARD_GAIN
                            next_vr_y = vr_fly_y + vr_dy * FORWARD_GAIN
                            # 刺激开始后继续累计开放世界坐标。
                            vr_fly_x = next_vr_x
                            vr_fly_y = next_vr_y

                            step_dist = math.hypot(delta_forward, delta_lateral)
                            raw_speed = step_dist / dt

                            if prev_heading is not None:
                                d_heading = current_raw_heading - prev_heading
                                d_heading = (d_heading + math.pi) % (2 * math.pi) - math.pi
                                raw_ang_vel = d_heading / dt

                            prev_time = packet_time
                            prev_perf_time = recv_perf_time
                            prev_forward = raw_fly_forward
                            prev_lateral = raw_fly_lateral
                            prev_heading = current_raw_heading
                        else:
                            continue

                        if current_stimulus_on:
                            initialize_stimulus_from_anchor()
                        else:
                            last_no_stim_anchor = {
                                "time": packet_time,
                                "x": vr_fly_x,
                                "y": vr_fly_y,
                                "heading": current_raw_heading,
                            }

                        is_towards_stimulus = False
                        is_approaching_stimulus = False
                        mapped_rel_angle = 0.0
                        nearest_stim_angle = 0.0
                        stim_rendered_width_rad = 0.0
                        stim_visual_half_width_rad = 0.0
                        exp_move_dir_rad = None

                        if current_stimulus_on and len(v_bar_world_coords) > 0:
                            min_angle_diff = float('inf')
                            closest_bar_nominal_rad = 0.0
                            if step_dist > 1e-9:
                                exp_move_dir_rad = math.atan2(vr_dy, vr_dx)

                            for i, (bx, by) in enumerate(v_bar_world_coords):
                                bar_angle_rad = math.atan2(by - vr_fly_y, bx - vr_fly_x)
                                angle_diff = current_raw_heading - bar_angle_rad
                                angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi

                                dist_to_bar = max(math.hypot(bx - vr_fly_x, by - vr_fly_y), cfg.BAR_HALF_WIDTH_CM + 0.1)
                                safe_ratio = min(1.0, cfg.BAR_HALF_WIDTH_CM / dist_to_bar)
                                rendered_width = 2 * math.asin(safe_ratio)
                                rendered_width = max(math.radians(21.92), min(math.radians(46.99), rendered_width))

                                if abs(angle_diff) < abs(min_angle_diff):
                                    min_angle_diff = angle_diff
                                    nearest_stim_angle = angle_diff
                                    stimulus_angle_offsets = [0.0, math.pi]
                                    closest_bar_nominal_rad = stimulus_angle_offsets[i] if i < len(stimulus_angle_offsets) else 0.0
                                    stim_rendered_width_rad = rendered_width
                                    stim_visual_half_width_rad = rendered_width / 2.0

                                if abs(angle_diff) <= (rendered_width / 2.0):
                                    is_towards_stimulus = True

                                if exp_move_dir_rad is not None and raw_speed > cfg.MOVEMENT_SPEED_THRESHOLD:
                                    move_angle_diff = exp_move_dir_rad - bar_angle_rad
                                    move_angle_diff = (move_angle_diff + math.pi) % (2 * math.pi) - math.pi
                                    if abs(move_angle_diff) <= (rendered_width / 2.0):
                                        is_approaching_stimulus = True

                            mapped_rel_angle = closest_bar_nominal_rad + min_angle_diff
                            mapped_rel_angle = (mapped_rel_angle + math.pi) % (2 * math.pi) - math.pi

                        dx_center = arena_center_x - vr_fly_x
                        dy_center = arena_center_y - vr_fly_y
                        stim_anchor_time = stimulus_anchor["time"] if current_stimulus_on and stimulus_anchor else None
                        stim_anchor_x = stimulus_anchor["x"] if current_stimulus_on and stimulus_anchor else None
                        stim_anchor_y = stimulus_anchor["y"] if current_stimulus_on and stimulus_anchor else None
                        stim_anchor_heading = stimulus_anchor["heading"] if current_stimulus_on and stimulus_anchor else None
                        stim_bar_front_x = v_bar_world_coords[0][0] if current_stimulus_on and len(v_bar_world_coords) > 0 else None
                        stim_bar_front_y = v_bar_world_coords[0][1] if current_stimulus_on and len(v_bar_world_coords) > 0 else None
                        stim_bar_back_x = v_bar_world_coords[1][0] if current_stimulus_on and len(v_bar_world_coords) > 1 else None
                        stim_bar_back_y = v_bar_world_coords[1][1] if current_stimulus_on and len(v_bar_world_coords) > 1 else None

                        is_moving = (
                            raw_speed > cfg.MOVEMENT_SPEED_THRESHOLD or
                            abs(raw_ang_vel) > cfg.MOVEMENT_ANG_VEL_THRESHOLD
                        )

                        logger.record_frame(
                            packet_time=packet_time,
                            current_phase=current_phase,
                            ft_frame=ft_frame,
                            ft_x_cm=ft_x_cm,
                            ft_y_cm=ft_y_cm,
                            ft_heading_rad=ft_heading_rad,
                            ft_move_dir_rad=ft_move_dir_rad,
                            ft_speed_cm_s=ft_speed_cm_s,
                            ft_forward_cm=ft_forward_cm,
                            ft_lateral_cm=ft_lateral_cm,
                            exp_heading_rad=current_raw_heading,
                            exp_move_dir_rad=exp_move_dir_rad,
                            exp_speed_cm_s=raw_speed,
                            exp_ang_vel_rad_s=raw_ang_vel,
                            step_dist_cm=step_dist,
                            is_moving=is_moving,
                            vr_fly_x_cm=vr_fly_x,
                            vr_fly_y_cm=vr_fly_y,
                            arena_rel_x_cm=dx_center,
                            arena_rel_y_cm=dy_center,
                            stim_nearest_angle_rad=nearest_stim_angle,
                            stim_mapped_angle_rad=mapped_rel_angle,
                            stim_facing_any=is_towards_stimulus,
                            stim_approaching_any=is_approaching_stimulus,
                            stim_visual_half_width_rad=stim_visual_half_width_rad,
                            stim_rendered_width_rad=stim_rendered_width_rad,
                            stim_anchor_time_s=stim_anchor_time,
                            stim_anchor_x_cm=stim_anchor_x,
                            stim_anchor_y_cm=stim_anchor_y,
                            stim_anchor_heading_rad=stim_anchor_heading,
                            stim_bar_front_x_cm=stim_bar_front_x,
                            stim_bar_front_y_cm=stim_bar_front_y,
                            stim_bar_back_x_cm=stim_bar_back_x,
                            stim_bar_back_y_cm=stim_bar_back_y,
                            fictrac_timestamp_ms=fictrac_timestamp_ms,
                            fictrac_seq=fictrac_seq,
                            fictrac_delta_ms=fictrac_delta_ms,
                            state_index=None if current_state is None else current_state["index"],
                            state_block="" if current_state is None else current_state["block"],
                            state_elapsed_s=state_elapsed_s,
                            state_bg_name="" if current_state is None else current_state["bg_name"],
                            state_bg_color="" if current_state is None else current_state["bg_color_str"],
                            state_brightness_label="" if current_state is None else current_state["brightness_label"],
                            state_brightness=None if current_state is None else current_state["brightness"],
                            state_stimulus_on=current_stimulus_on,
                        )

                        live_track_points.append([round(vr_fly_x, 4), round(vr_fly_y, 4)])
                        if len(live_track_points) > 2000:
                            live_track_points = live_track_points[-2000:]

                        now = time.perf_counter()
                        if now - last_live_write_time >= 0.1:
                            write_live_trajectory(cfg.SAVE_DIR, {
                                "active": True,
                                "time_s": round(packet_time, 4),
                                "phase": current_phase,
                                "state": current_state,
                                "state_elapsed_s": round(state_elapsed_s, 4),
                                "fictrac_delta_ms": round(fictrac_delta_ms, 4),
                                "speed_cm_s": round(raw_speed, 4),
                                "angular_vel_rad_s": round(raw_ang_vel, 6),
                                "points": live_track_points,
                                "latest": {
                                    "x": round(vr_fly_x, 4),
                                    "y": round(vr_fly_y, 4),
                                    "heading": None if current_raw_heading is None else round(current_raw_heading, 6),
                                },
                            })
                            last_live_write_time = now

            except BlockingIOError:
                break

        if current_stimulus_on and not stimulus_initialized:
            initialize_stimulus_from_anchor()

        if current_stimulus_on and stimulus_initialized:
            dynamic_wall_dist = math.hypot(wall_center_x - vr_fly_x, wall_center_y - vr_fly_y)
            dynamic_wall_dist = max(0.1, dynamic_wall_dist)
        else:
            dynamic_wall_dist = cfg.VIRTUAL_WALL_DISTANCE_CM

        renderer.draw_frame(
            current_brightness, experiment_started, smoothed_heading,
            current_phase, v_bar_world_coords, vr_fly_x, vr_fly_y, cfg.BAR_HALF_WIDTH_CM,
            cfg.H_BAR_COUNT, cfg.H_BAR_SPACING_CM,
            dynamic_wall_dist,
            bg_color=current_bg_color, bar_color=cfg.BAR_COLOR,
            stimulus_on=current_stimulus_on
        )

    final_debug_duration_s = target_debug_video_duration_s if target_debug_video_duration_s and experiment_time_s >= max(target_debug_video_duration_s - 0.5, 0.0) else experiment_time_s


    finish_fictrac_debug_recording(final_debug_duration_s)



    sock.close()


    renderer.quit()
    write_live_trajectory(cfg.SAVE_DIR, {
        "active": False,
        "time_s": round(experiment_time_s, 4),
        "phase": current_phase,
        "state": current_state,
        "state_elapsed_s": round(state_elapsed_s, 4),
        "fictrac_delta_ms": None,
        "speed_cm_s": 0.0,
        "angular_vel_rad_s": 0.0,
        "points": live_track_points,
        "latest": {
            "x": round(vr_fly_x, 4),
            "y": round(vr_fly_y, 4),
            "heading": None if current_raw_heading is None else round(current_raw_heading, 6),
        },
    }, sync=True)
    logger.save_and_print_summary()



def write_runtime_error_log(exc):
    try:
        os.makedirs(cfg.SAVE_DIR, exist_ok=True)
        log_path = os.path.join(cfg.SAVE_DIR, "vr_runtime_error.log")
        with open(log_path, "a", encoding="utf-8") as file:
            file.write("\n" + "=" * 80 + "\n")
            file.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            file.write(traceback.format_exc())
    except Exception:
        pass

    try:
        write_live_trajectory(cfg.SAVE_DIR, {
            "active": False,
            "error": str(exc),
            "time_s": 0.0,
            "phase": 0,
            "state": None,
            "state_elapsed_s": 0.0,
            "fictrac_delta_ms": None,
            "speed_cm_s": 0.0,
            "angular_vel_rad_s": 0.0,
            "points": [],
            "latest": {"x": 0.0, "y": 0.0, "heading": None},
        }, sync=True)
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        write_runtime_error_log(exc)
        raise
