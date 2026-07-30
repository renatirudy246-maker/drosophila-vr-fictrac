import csv
import math
import os
from datetime import datetime
from statistics import mean, median


class ExperimentLogger:
    def __init__(self, save_dir, experiment_config_snapshot=None):
        self.save_dir = save_dir
        self.experiment_config_snapshot = experiment_config_snapshot or {}
        self.snapshot_keys = list(self.experiment_config_snapshot.keys())
        self.snapshot_header = [f"Cfg_{key}" for key in self.snapshot_keys]
        self.snapshot_row = [self.experiment_config_snapshot[key] for key in self.snapshot_keys]
        self.forward_gain = float(self.experiment_config_snapshot.get("FORWARD_GAIN", 1.0))
        self.arena_radius_cm = float(self.experiment_config_snapshot.get("ARENA_RADIUS_CM", 0.0))

        self.csv_header = [
            "Time_s", "Phase", "State_Index", "State_Block", "State_Elapsed_s", "State_BG_Name", "State_BG_Color", "State_Brightness_Label", "State_Brightness", "State_Stimulus_On",
            "FT_Frame", "FT_Timestamp_ms", "FT_Seq", "FT_Delta_ms",
            "FT_X_cm", "FT_Y_cm", "FT_Heading_rad", "FT_MoveDir_rad", "FT_Speed_cm_s",
            "FT_Forward_cm", "FT_Lateral_cm",
            "Exp_Heading_rad", "Exp_MoveDir_rad", "Exp_Speed_cm_s", "Exp_AngVel_rad_s", "Step_Distance_cm", "Is_Moving",
            "VR_Fly_X_cm", "VR_Fly_Y_cm",
            "VR_ArenaCenter_Rel_X_cm", "VR_ArenaCenter_Rel_Y_cm", "VR_DistanceFromCenter_cm", "VR_ForwardGain",
            "Stim_Nearest_Angle_rad", "Stim_Mapped_Angle_rad", "Stim_Facing_Any", "Stim_Approaching_Any",
            "Stim_VisualHalfWidth_rad", "Stim_RenderedWidth_rad",
            "Stim_Anchor_Time_s", "Stim_Anchor_X_cm", "Stim_Anchor_Y_cm", "Stim_Anchor_Heading_rad",
            "Stim_Bar_Front_X_cm", "Stim_Bar_Front_Y_cm", "Stim_Bar_Back_X_cm", "Stim_Bar_Back_Y_cm",
            *self.snapshot_header,
        ]

        self.recorded_data = []
        self.phase_stats = {}
        self.reset()

    @staticmethod
    def _round_or_blank(value, digits=4):
        if value is None:
            return ""
        return round(float(value), digits)

    @staticmethod
    def _safe_mean(values):
        return mean(values) if values else 0.0

    @staticmethod
    def _safe_median(values):
        return median(values) if values else 0.0

    @staticmethod
    def _safe_std(values):
        if len(values) < 2:
            return 0.0
        avg = mean(values)
        return math.sqrt(sum((v - avg) ** 2 for v in values) / len(values))

    @staticmethod
    def _safe_ratio(num, den):
        return (num / den * 100.0) if den else 0.0

    @staticmethod
    def _safe_index(pos_count, neg_count):
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total

    @staticmethod
    def _compute_segment_durations(times, states, target_state):
        durations = []
        start_time = None
        prev_time = None
        for t, state in zip(times, states):
            if state == target_state and start_time is None:
                start_time = t
            elif state != target_state and start_time is not None and prev_time is not None:
                durations.append(max(0.0, prev_time - start_time))
                start_time = None
            prev_time = t
        if start_time is not None and prev_time is not None:
            durations.append(max(0.0, prev_time - start_time))
        return durations

    def _new_phase_bucket(self):
        return {
            "times": [],
            "speeds": [],
            "ang_vels": [],
            "step_distances": [],
            "is_moving": [],
            "is_facing": [],
            "is_approaching": [],
            "mapped_angles": [],
            "nearest_angles": [],
            "center_distances": [],
            "ft_deltas_ms": [],
            "ft_seqs": [],
            "vr_positions": [],
            "state_block": "",
            "state_bg_name": "",
            "state_brightness_label": "",
            "state_stimulus_on": False,
        }


    def reset(self):
        self.recorded_data = [self.csv_header]
        self.phase_stats = {}

    def record_frame(
        self,
        packet_time,
        current_phase,
        ft_frame,
        ft_x_cm,
        ft_y_cm,
        ft_heading_rad,
        ft_move_dir_rad,
        ft_speed_cm_s,
        ft_forward_cm,
        ft_lateral_cm,
        exp_heading_rad,
        exp_move_dir_rad,
        exp_speed_cm_s,
        exp_ang_vel_rad_s,
        step_dist_cm,
        is_moving,
        vr_fly_x_cm,
        vr_fly_y_cm,
        arena_rel_x_cm,
        arena_rel_y_cm,
        stim_nearest_angle_rad,
        stim_mapped_angle_rad,
        stim_facing_any,
        stim_approaching_any,
        stim_visual_half_width_rad,
        stim_rendered_width_rad,
        stim_anchor_time_s=None,
        stim_anchor_x_cm=None,
        stim_anchor_y_cm=None,
        stim_anchor_heading_rad=None,
        stim_bar_front_x_cm=None,
        stim_bar_front_y_cm=None,
        stim_bar_back_x_cm=None,
        stim_bar_back_y_cm=None,
        fictrac_timestamp_ms=None,
        fictrac_seq=None,
        fictrac_delta_ms=None,
        state_index=None,
        state_block="",
        state_elapsed_s=0.0,
        state_bg_name="",
        state_bg_color="",
        state_brightness_label="",
        state_brightness=None,
        state_stimulus_on=False,
    ):
        center_distance_cm = math.hypot(arena_rel_x_cm, arena_rel_y_cm)

        if current_phase not in self.phase_stats:
            self.phase_stats[current_phase] = self._new_phase_bucket()
        if current_phase in self.phase_stats:
            phase_bucket = self.phase_stats[current_phase]
            phase_bucket["times"].append(packet_time)
            phase_bucket["speeds"].append(exp_speed_cm_s)
            phase_bucket["ang_vels"].append(exp_ang_vel_rad_s)
            phase_bucket["step_distances"].append(step_dist_cm)
            phase_bucket["is_moving"].append(bool(is_moving))
            phase_bucket["is_facing"].append(bool(stim_facing_any))
            phase_bucket["is_approaching"].append(bool(stim_approaching_any))
            phase_bucket["mapped_angles"].append(stim_mapped_angle_rad)
            phase_bucket["nearest_angles"].append(stim_nearest_angle_rad)
            phase_bucket["center_distances"].append(center_distance_cm)
            phase_bucket["vr_positions"].append((vr_fly_x_cm, vr_fly_y_cm))
            if fictrac_delta_ms is not None:
                phase_bucket["ft_deltas_ms"].append(float(fictrac_delta_ms))
            if fictrac_seq is not None:
                phase_bucket["ft_seqs"].append(int(fictrac_seq))
            if not phase_bucket["state_block"] and state_block:
                phase_bucket["state_block"] = state_block
                phase_bucket["state_bg_name"] = state_bg_name
                phase_bucket["state_brightness_label"] = state_brightness_label
                phase_bucket["state_stimulus_on"] = state_stimulus_on

        self.recorded_data.append([
            round(packet_time, 4), current_phase,
            "" if state_index is None else int(state_index), state_block, round(state_elapsed_s, 4),
            state_bg_name, state_bg_color, state_brightness_label,
            self._round_or_blank(state_brightness, 4), int(bool(state_stimulus_on)),
            "" if ft_frame is None else int(ft_frame),
            self._round_or_blank(fictrac_timestamp_ms, 3),
            "" if fictrac_seq is None else int(fictrac_seq),
            self._round_or_blank(fictrac_delta_ms, 3),
            round(ft_x_cm, 4), round(ft_y_cm, 4), round(ft_heading_rad, 4), round(ft_move_dir_rad, 4),
            round(ft_speed_cm_s, 4), round(ft_forward_cm, 4), round(ft_lateral_cm, 4),
            round(exp_heading_rad, 4), self._round_or_blank(exp_move_dir_rad, 4), round(exp_speed_cm_s, 4), round(exp_ang_vel_rad_s, 4),
            round(step_dist_cm, 4), int(bool(is_moving)),
            round(vr_fly_x_cm, 4), round(vr_fly_y_cm, 4),
            round(arena_rel_x_cm, 4), round(arena_rel_y_cm, 4), round(center_distance_cm, 4), round(self.forward_gain, 4),
            round(stim_nearest_angle_rad, 4), round(stim_mapped_angle_rad, 4), int(bool(stim_facing_any)), int(bool(stim_approaching_any)),
            round(stim_visual_half_width_rad, 4), round(stim_rendered_width_rad, 4),
            self._round_or_blank(stim_anchor_time_s, 4), self._round_or_blank(stim_anchor_x_cm, 4),
            self._round_or_blank(stim_anchor_y_cm, 4), self._round_or_blank(stim_anchor_heading_rad, 4),
            self._round_or_blank(stim_bar_front_x_cm, 4), self._round_or_blank(stim_bar_front_y_cm, 4),
            self._round_or_blank(stim_bar_back_x_cm, 4), self._round_or_blank(stim_bar_back_y_cm, 4),
            *self.snapshot_row,
        ])

    def _summarize_phase(self, phase, phase_bucket):
        total_frames = len(phase_bucket["times"])
        if total_frames == 0:
            return {
                "Phase": phase,
                "State_Info": "Unknown",
                "Duration_s": 0.0,
                "Total_Frames": 0,
                "Valid_Time_s": 0.0,
                "Moving_Frames": 0,
                "Moving_Ratio_pct": 0.0,
                "Still_Frames": 0,
                "Still_Ratio_pct": 0.0,
                "Mean_Bout_Duration_s": 0.0,
                "Mean_Stop_Duration_s": 0.0,
                "Total_Distance_cm": 0.0,
                "VR_Total_Distance_cm": 0.0,
                "VR_Net_Displacement_cm": 0.0,
                "VR_Path_Straightness": 0.0,
                "Mean_Speed_cm_s": 0.0,
                "Mean_MovingSpeed_cm_s": 0.0,
                "Median_Speed_cm_s": 0.0,
                "Peak_Speed_cm_s": 0.0,
                "Speed_SD_cm_s": 0.0,
                "Mean_AngVel_abs_rad_s": 0.0,
                "Median_AngVel_abs_rad_s": 0.0,
                "Peak_AngVel_abs_rad_s": 0.0,
                "Signed_AngVel_Mean_rad_s": 0.0,
                "Turn_Bias_Index": 0.0,
                "Facing_AnyStim_Frames": 0,
                "Facing_AnyStim_Ratio_pct": 0.0,
                "Facing_AnyStim_MovingRatio_pct": 0.0,
                "Approaching_AnyStim_Frames": 0,
                "Approaching_AnyStim_Ratio_pct": 0.0,
                "Approaching_AnyStim_MovingRatio_pct": 0.0,
                "Mean_StimError_abs_deg": 0.0,
                "Median_StimError_abs_deg": 0.0,
                "Min_StimError_abs_deg": 0.0,
                "Mean_DistanceFromCenter_cm": 0.0,
                "Median_DistanceFromCenter_cm": 0.0,
                "Max_DistanceFromCenter_cm": 0.0,
                "Center_Occupancy_pct": 0.0,
                "Edge_Occupancy_pct": 0.0,
                "Mean_FT_Delta_ms": 0.0,
                "FT_Delta_SD_ms": 0.0,
                "DroppedFrame_Estimate": 0,
                "Tracking_Reset_Count": 0,
            }

        duration_s = phase_bucket["times"][-1] - phase_bucket["times"][0] if total_frames > 1 else 0.0
        valid_time_s = sum(phase_bucket["ft_deltas_ms"]) / 1000.0 if phase_bucket["ft_deltas_ms"] else duration_s
        moving_frames = sum(phase_bucket["is_moving"])
        still_frames = total_frames - moving_frames

        moving_bouts = self._compute_segment_durations(phase_bucket["times"], phase_bucket["is_moving"], True)
        stop_bouts = self._compute_segment_durations(phase_bucket["times"], phase_bucket["is_moving"], False)

        total_distance_cm = sum(phase_bucket["step_distances"])
        vr_total_distance_cm = 0.0
        for (prev_x, prev_y), (curr_x, curr_y) in zip(phase_bucket["vr_positions"], phase_bucket["vr_positions"][1:]):
            vr_total_distance_cm += math.hypot(curr_x - prev_x, curr_y - prev_y)
        first_x, first_y = phase_bucket["vr_positions"][0]
        last_x, last_y = phase_bucket["vr_positions"][-1]
        vr_net_displacement_cm = math.hypot(last_x - first_x, last_y - first_y)
        vr_path_straightness = vr_net_displacement_cm / vr_total_distance_cm if vr_total_distance_cm > 0 else 0.0

        moving_speeds = [speed for speed, moving in zip(phase_bucket["speeds"], phase_bucket["is_moving"]) if moving]
        abs_ang_vels = [abs(v) for v in phase_bucket["ang_vels"]]
        nearest_abs_deg = [abs(math.degrees(a)) for a in phase_bucket["nearest_angles"]]
        facing_frames = sum(phase_bucket["is_facing"])
        facing_moving_frames = sum(1 for facing, moving in zip(phase_bucket["is_facing"], phase_bucket["is_moving"]) if facing and moving)
        approaching_frames = sum(phase_bucket["is_approaching"])
        approaching_moving_frames = sum(
            1 for approaching, moving in zip(phase_bucket["is_approaching"], phase_bucket["is_moving"]) if approaching and moving
        )

        pos_turns = sum(1 for v in phase_bucket["ang_vels"] if v > 0)
        neg_turns = sum(1 for v in phase_bucket["ang_vels"] if v < 0)

        center_radius = self.arena_radius_cm * 0.33 if self.arena_radius_cm > 0 else 0.0
        edge_threshold = self.arena_radius_cm * 0.8 if self.arena_radius_cm > 0 else 0.0
        center_occupancy = sum(1 for d in phase_bucket["center_distances"] if d <= center_radius) if center_radius > 0 else 0
        edge_occupancy = sum(1 for d in phase_bucket["center_distances"] if d >= edge_threshold) if edge_threshold > 0 else 0

        expected_delta_ms = 1000.0 / 180.0
        dropped_frames = sum(1 for dt in phase_bucket["ft_deltas_ms"] if dt > expected_delta_ms * 1.8)
        reset_count = 0
        prev_seq = None
        for seq in phase_bucket["ft_seqs"]:
            if prev_seq is not None and seq <= prev_seq:
                reset_count += 1
            prev_seq = seq

        block_en = "Stimulus" if phase_bucket.get("state_block") == "stimulus" else "NoStimulus"
        bg_en = (phase_bucket.get("state_bg_name") or "").capitalize()
        brightness_en = (phase_bucket.get("state_brightness_label") or "").capitalize()
        stim_on = phase_bucket.get("state_stimulus_on", False)
        stripe_en = "StripeOn" if stim_on else "StripeOff"
        state_info = f"{block_en}_{bg_en}_Brightness{brightness_en}_{stripe_en}"

        return {
            "Phase": phase,
            "State_Info": state_info,
            "Duration_s": duration_s,
            "Total_Frames": total_frames,
            "Valid_Time_s": valid_time_s,
            "Moving_Frames": moving_frames,
            "Moving_Ratio_pct": self._safe_ratio(moving_frames, total_frames),
            "Still_Frames": still_frames,
            "Still_Ratio_pct": self._safe_ratio(still_frames, total_frames),
            "Mean_Bout_Duration_s": self._safe_mean(moving_bouts),
            "Mean_Stop_Duration_s": self._safe_mean(stop_bouts),
            "Total_Distance_cm": total_distance_cm,
            "VR_Total_Distance_cm": vr_total_distance_cm,
            "VR_Net_Displacement_cm": vr_net_displacement_cm,
            "VR_Path_Straightness": vr_path_straightness,
            "Mean_Speed_cm_s": self._safe_mean(phase_bucket["speeds"]),
            "Mean_MovingSpeed_cm_s": self._safe_mean(moving_speeds),
            "Median_Speed_cm_s": self._safe_median(phase_bucket["speeds"]),
            "Peak_Speed_cm_s": max(phase_bucket["speeds"]) if phase_bucket["speeds"] else 0.0,
            "Speed_SD_cm_s": self._safe_std(phase_bucket["speeds"]),
            "Mean_AngVel_abs_rad_s": self._safe_mean(abs_ang_vels),
            "Median_AngVel_abs_rad_s": self._safe_median(abs_ang_vels),
            "Peak_AngVel_abs_rad_s": max(abs_ang_vels) if abs_ang_vels else 0.0,
            "Signed_AngVel_Mean_rad_s": self._safe_mean(phase_bucket["ang_vels"]),
            "Turn_Bias_Index": self._safe_index(pos_turns, neg_turns),
            "Facing_AnyStim_Frames": facing_frames,
            "Facing_AnyStim_Ratio_pct": self._safe_ratio(facing_frames, total_frames),
            "Facing_AnyStim_MovingRatio_pct": self._safe_ratio(facing_moving_frames, moving_frames),
            "Approaching_AnyStim_Frames": approaching_frames,
            "Approaching_AnyStim_Ratio_pct": self._safe_ratio(approaching_frames, total_frames),
            "Approaching_AnyStim_MovingRatio_pct": self._safe_ratio(approaching_moving_frames, moving_frames),
            "Mean_StimError_abs_deg": self._safe_mean(nearest_abs_deg),
            "Median_StimError_abs_deg": self._safe_median(nearest_abs_deg),
            "Min_StimError_abs_deg": min(nearest_abs_deg) if nearest_abs_deg else 0.0,
            "Mean_DistanceFromCenter_cm": self._safe_mean(phase_bucket["center_distances"]),
            "Median_DistanceFromCenter_cm": self._safe_median(phase_bucket["center_distances"]),
            "Max_DistanceFromCenter_cm": max(phase_bucket["center_distances"]) if phase_bucket["center_distances"] else 0.0,
            "Center_Occupancy_pct": self._safe_ratio(center_occupancy, total_frames),
            "Edge_Occupancy_pct": self._safe_ratio(edge_occupancy, total_frames),
            "Mean_FT_Delta_ms": self._safe_mean(phase_bucket["ft_deltas_ms"]),
            "FT_Delta_SD_ms": self._safe_std(phase_bucket["ft_deltas_ms"]),
            "DroppedFrame_Estimate": dropped_frames,
            "Tracking_Reset_Count": reset_count,
        }

    def save_and_print_summary(self):
        if len(self.recorded_data) <= 1:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"drosophila_exp_{timestamp}.csv"
        summary_filename = f"drosophila_exp_{timestamp}_phase_summary.csv"
        os.makedirs(self.save_dir, exist_ok=True)
        full_save_path = os.path.join(self.save_dir, csv_filename)
        full_summary_path = os.path.join(self.save_dir, summary_filename)

        phase_summaries = [self._summarize_phase(phase, self.phase_stats[phase]) for phase in sorted(self.phase_stats.keys())]
        summary_header = list(phase_summaries[0].keys())

        with open(full_save_path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerows(self.recorded_data)
            writer.writerow([])
            writer.writerow([])
            writer.writerow(["=== State Summary ==="])
            writer.writerow(summary_header)
            for row in phase_summaries:
                writer.writerow([row[key] for key in summary_header])

        with open(full_summary_path, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.DictWriter(file, fieldnames=summary_header)
            writer.writeheader()
            writer.writerows(phase_summaries)

        print(f"\n[OK] 原始数据成功保存至: {full_save_path}")
        print(f"[OK] 阶段汇总成功保存至: {full_summary_path}")
        print("\n================ 果蝇实验状态总结 ================")
        for row in phase_summaries:
            print(
                f"  > 状态 {row['Phase']} ({row.get('State_Info', '')}): 活动力 {row['Moving_Ratio_pct']:6.2f}% | "
                f"总距离 {row['Total_Distance_cm']:7.2f} cm | "
                f"平均速度 {row['Mean_Speed_cm_s']:6.2f} cm/s | "
                f"朝向刺激(运动帧) {row['Facing_AnyStim_MovingRatio_pct']:6.2f}% | "
                f"朝刺激移动(运动帧) {row['Approaching_AnyStim_MovingRatio_pct']:6.2f}%"
            )
        print("==================================================\n")


