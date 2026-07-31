import pygame
import math


class VRRenderer:
    def __init__(self, fov_rad, black_color):
        self.fov_rad = fov_rad
        self.black = black_color

        pygame.init()
        pygame.display.Info()
        DISPLAY_FLAGS = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE

        try:
            self.screen = pygame.display.set_mode((0, 0), DISPLAY_FLAGS, display=1)
        except pygame.error:
            print("未检测到副屏，退回主屏幕显示...")
            self.screen = pygame.display.set_mode((0, 0), DISPLAY_FLAGS, display=0)

        pygame.display.set_caption("VR 系统")
        self.clock = pygame.time.Clock()

    def tick(self, fps=60):
        self.clock.tick(fps)

    def draw_frame(self, current_brightness, experiment_started, smoothed_heading,
                   current_phase, v_bar_world_coords, fly_x, fly_y, bar_half_width_cm,
                   h_bar_count=0, h_bar_spacing_cm=6.0, virtual_wall_dist_cm=10.0,
                   bg_color=(0, 255, 0), bar_color=(0, 0, 0), stimulus_on=None):

        """渲染背景以及横、竖条纹刺激。"""
        current_window_width, current_window_height = self.screen.get_size()
        center_x_px = current_window_width / 2
        center_y_px = current_window_height / 2

        r = min(255, max(0, int(bg_color[0] * current_brightness)))
        g = min(255, max(0, int(bg_color[1] * current_brightness)))
        b = min(255, max(0, int(bg_color[2] * current_brightness)))
        self.screen.fill((r, g, b))

        should_draw_stimulus = (current_phase == 2) if stimulus_on is None else bool(stimulus_on)
        if experiment_started and smoothed_heading is not None and should_draw_stimulus:

            # 竖向条纹
            for bx, by in v_bar_world_coords:
                dx = bx - fly_x
                dy = by - fly_y
                dist = max(math.hypot(dx, dy), bar_half_width_cm + 0.1)

                alpha = math.atan2(dy, dx)
                theta_rel = alpha - smoothed_heading

                # 将相对角度归一化到 [-pi, pi)。
                theta_rel = (theta_rel + math.pi) % (2 * math.pi) - math.pi
                safe_ratio = min(1.0, bar_half_width_cm / dist)
                w_ang = 2 * math.asin(safe_ratio)

                # 限制竖条纹的视觉角宽。
                min_visual_angle_rad = math.radians(21.92)
                max_visual_angle_rad = math.radians(46.99)
                w_ang = max(min_visual_angle_rad, min(max_visual_angle_rad, w_ang))

                angle_left_edge = theta_rel + (w_ang / 2)
                angle_right_edge = theta_rel - (w_ang / 2)

                # 跳过视场外的条纹。
                if angle_right_edge > self.fov_rad / 2 or angle_left_edge < -self.fov_rad / 2:
                    continue

                clamp_left = max(-self.fov_rad / 2, min(self.fov_rad / 2, angle_left_edge))
                clamp_right = max(-self.fov_rad / 2, min(self.fov_rad / 2, angle_right_edge))

                px_left = int(center_x_px - (clamp_left / self.fov_rad) * current_window_width)
                px_right = int(center_x_px - (clamp_right / self.fov_rad) * current_window_width)

                if px_left < px_right:
                    rect_width = px_right - px_left
                    v_bar_rect = pygame.Rect(px_left, 0, rect_width, current_window_height)
                    pygame.draw.rect(self.screen, bar_color, v_bar_rect)

            if h_bar_count > 0:
                v_fov_rad = math.radians(120.0)  # 垂直视场角

                # 横条纹的视觉角宽范围。
                min_visual_angle_rad = math.radians(10)
                max_visual_angle_rad = math.radians(90)

                for i in range(h_bar_count):
                    offset_idx = i - (h_bar_count - 1) / 2.0

                    # 横条纹在虚拟墙上的高度范围。
                    physical_y_center = offset_idx * h_bar_spacing_cm
                    top_y_physical = physical_y_center + bar_half_width_cm
                    bottom_y_physical = physical_y_center - bar_half_width_cm

                    # 将高度范围投影为垂直视角。
                    top_rad = math.atan2(top_y_physical, virtual_wall_dist_cm)
                    bottom_rad = math.atan2(bottom_y_physical, virtual_wall_dist_cm)

                    # 限制角宽并保持条纹中心不变。
                    current_w_ang = top_rad - bottom_rad
                    center_rad = (top_rad + bottom_rad) / 2.0
                    clamped_w_ang = max(min_visual_angle_rad, min(max_visual_angle_rad, current_w_ang))
                    top_rad = center_rad + (clamped_w_ang / 2.0)
                    bottom_rad = center_rad - (clamped_w_ang / 2.0)

                    # 屏幕 y 轴向下为正。
                    top_px = center_y_px - int((top_rad / v_fov_rad) * current_window_height)
                    bottom_px = center_y_px - int((bottom_rad / v_fov_rad) * current_window_height)

                    rect_y = top_px
                    h_thickness_px = bottom_px - top_px

                    h_bar_rect = pygame.Rect(0, rect_y, current_window_width, h_thickness_px)
                    pygame.draw.rect(self.screen, bar_color, h_bar_rect)

        pygame.display.flip()

    def quit(self):
        pygame.quit()


