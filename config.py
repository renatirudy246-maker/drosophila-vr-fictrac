import math
import json
import os

# 文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "settings.json")
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        _cfg = json.load(f)
else:
    _cfg = {}

# 数据保存目录
SAVE_DIR = _cfg.get("SAVE_DIR", os.path.join(BASE_DIR, "exp_data"))
if not os.path.isabs(SAVE_DIR):
    SAVE_DIR = os.path.join(BASE_DIR, SAVE_DIR)

# 网络与硬件
UDP_IP = _cfg.get("UDP_IP", "127.0.0.1")
UDP_PORT = int(_cfg.get("UDP_PORT", 2000))

SCREEN_FOV_DEG = float(_cfg.get("SCREEN_FOV_DEG", 270.0))
SCREEN_FOV_RAD = math.radians(SCREEN_FOV_DEG)
SPHERE_RADIUS_CM = float(_cfg.get("SPHERE_RADIUS_CM", 0.6))

# 实验与视觉参数
SIMULATION_MODE = _cfg.get("SIMULATION_MODE", False)

INVERT_ROTATION = bool(_cfg.get("INVERT_ROTATION", False))
INVERT_FORWARD = bool(_cfg.get("INVERT_FORWARD", False))

DEFAULT_BRIGHTNESS = float(_cfg.get("DEFAULT_BRIGHTNESS", 0.41))

# 条纹参数
V_BAR_COUNT = int(_cfg.get("V_BAR_COUNT", 2))
V_BAR_SPACING_DEG = float(_cfg.get("V_BAR_SPACING_DEG", 150.0))

H_BAR_COUNT = int(_cfg.get("H_BAR_COUNT", 0))
H_BAR_SPACING_CM = float(_cfg.get("H_BAR_SPACING_CM", 6.0))

VIRTUAL_WALL_DISTANCE_CM = float(_cfg.get("VIRTUAL_WALL_DISTANCE_CM", 10.0))
BAR_VISUAL_ANGLE_DEG = float(_cfg.get("BAR_VISUAL_ANGLE_DEG", 30.0))
BAR_HALF_WIDTH_CM = VIRTUAL_WALL_DISTANCE_CM * math.sin(math.radians(BAR_VISUAL_ANGLE_DEG / 2))

SMOOTHING_FACTOR = float(_cfg.get("SMOOTHING_FACTOR", 0.5))

# 旧版阶段时长，仅用于兼容已有分析。
PHASE_1_DURATION = float(_cfg.get("PHASE_1_DURATION", 5.0))
PHASE_2_DURATION = float(_cfg.get("PHASE_2_DURATION", 60.0))
PHASE_3_DURATION = float(_cfg.get("PHASE_3_DURATION", 5.0))

# 活动判定阈值
MOVEMENT_SPEED_THRESHOLD = float(_cfg.get("MOVEMENT_SPEED_THRESHOLD", 0.05))
MOVEMENT_ANG_VEL_THRESHOLD = float(_cfg.get("MOVEMENT_ANG_VEL_THRESHOLD", 0.05))

BLACK = (0, 0, 0)


# 颜色配置
def parse_color(color_str, default=(0, 0, 0)):
    try:
        return tuple(map(int, str(color_str).split(',')))
    except Exception:
        return default


def parse_named_color_options(options):
    parsed = []
    for item in str(options).split(';'):
        if not item.strip() or ':' not in item:
            continue
        name, color = item.split(':', 1)
        parsed.append({
            "name": name.strip(),
            "color": parse_color(color.strip(), (255, 255, 255)),
            "color_str": color.strip(),
        })
    return parsed


def parse_named_float_options(options):
    parsed = []
    for item in str(options).split(';'):
        if not item.strip() or ':' not in item:
            continue
        name, value = item.split(':', 1)
        try:
            parsed.append({"name": name.strip(), "value": float(value)})
        except ValueError:
            continue
    return parsed


BG_COLOR_STR = str(_cfg.get("BG_COLOR", "0,255,0"))
BAR_COLOR_STR = str(_cfg.get("BAR_COLOR", "0,0,0"))
# 默认使用绿色背景和黑色条纹。
BG_COLOR = parse_color(BG_COLOR_STR, (0, 255, 0))
BAR_COLOR = parse_color(BAR_COLOR_STR, (0, 0, 0))

# 随机状态实验
def get_float_config(key, default):
    try:
        return float(_cfg.get(key, default))
    except (TypeError, ValueError):
        return float(default)


STATE_DURATION_S = float(_cfg.get("STATE_DURATION_S", 20.0))
STATE_RANDOM_SEED = int(_cfg.get("STATE_RANDOM_SEED", 0))
PRE_START_BG_COLOR_STR = str(_cfg.get("PRE_START_BG_COLOR", "255,255,255"))
PRE_START_BG_COLOR = parse_color(PRE_START_BG_COLOR_STR, (255, 255, 255))
PRE_START_BRIGHTNESS = get_float_config("PRE_START_BRIGHTNESS", 0.35)

STATE_WHITE_COLOR_STR = str(_cfg.get("STATE_WHITE_COLOR", "255,255,255"))
STATE_GREEN_COLOR_STR = str(_cfg.get("STATE_GREEN_COLOR", "0,255,0"))
STATE_RED_COLOR_STR = str(_cfg.get("STATE_RED_COLOR", "255,0,0"))
STATE_WHITE_COLOR = parse_color(STATE_WHITE_COLOR_STR, (255, 255, 255))
STATE_GREEN_COLOR = parse_color(STATE_GREEN_COLOR_STR, (0, 255, 0))
STATE_RED_COLOR = parse_color(STATE_RED_COLOR_STR, (255, 0, 0))

STATE_WHITE_DARK_BRIGHTNESS = get_float_config("STATE_WHITE_DARK_BRIGHTNESS", 0.25)
STATE_WHITE_MEDIUM_BRIGHTNESS = get_float_config("STATE_WHITE_MEDIUM_BRIGHTNESS", 0.55)
STATE_WHITE_BRIGHT_BRIGHTNESS = get_float_config("STATE_WHITE_BRIGHT_BRIGHTNESS", 1.0)
STATE_GREEN_DARK_BRIGHTNESS = get_float_config("STATE_GREEN_DARK_BRIGHTNESS", 0.25)
STATE_GREEN_MEDIUM_BRIGHTNESS = get_float_config("STATE_GREEN_MEDIUM_BRIGHTNESS", 0.55)
STATE_GREEN_BRIGHT_BRIGHTNESS = get_float_config("STATE_GREEN_BRIGHT_BRIGHTNESS", 1.0)
STATE_RED_DARK_BRIGHTNESS = get_float_config("STATE_RED_DARK_BRIGHTNESS", 0.25)
STATE_RED_MEDIUM_BRIGHTNESS = get_float_config("STATE_RED_MEDIUM_BRIGHTNESS", 0.55)
STATE_RED_BRIGHT_BRIGHTNESS = get_float_config("STATE_RED_BRIGHT_BRIGHTNESS", 1.0)

STATE_COLOR_BRIGHTNESS_MATRIX = [
    {"bg_name": "white", "bg_color": STATE_WHITE_COLOR, "bg_color_str": STATE_WHITE_COLOR_STR, "brightness_label": "dark", "brightness": STATE_WHITE_DARK_BRIGHTNESS},
    {"bg_name": "white", "bg_color": STATE_WHITE_COLOR, "bg_color_str": STATE_WHITE_COLOR_STR, "brightness_label": "medium", "brightness": STATE_WHITE_MEDIUM_BRIGHTNESS},
    {"bg_name": "white", "bg_color": STATE_WHITE_COLOR, "bg_color_str": STATE_WHITE_COLOR_STR, "brightness_label": "bright", "brightness": STATE_WHITE_BRIGHT_BRIGHTNESS},
    {"bg_name": "green", "bg_color": STATE_GREEN_COLOR, "bg_color_str": STATE_GREEN_COLOR_STR, "brightness_label": "dark", "brightness": STATE_GREEN_DARK_BRIGHTNESS},
    {"bg_name": "green", "bg_color": STATE_GREEN_COLOR, "bg_color_str": STATE_GREEN_COLOR_STR, "brightness_label": "medium", "brightness": STATE_GREEN_MEDIUM_BRIGHTNESS},
    {"bg_name": "green", "bg_color": STATE_GREEN_COLOR, "bg_color_str": STATE_GREEN_COLOR_STR, "brightness_label": "bright", "brightness": STATE_GREEN_BRIGHT_BRIGHTNESS},
    {"bg_name": "red", "bg_color": STATE_RED_COLOR, "bg_color_str": STATE_RED_COLOR_STR, "brightness_label": "dark", "brightness": STATE_RED_DARK_BRIGHTNESS},
    {"bg_name": "red", "bg_color": STATE_RED_COLOR, "bg_color_str": STATE_RED_COLOR_STR, "brightness_label": "medium", "brightness": STATE_RED_MEDIUM_BRIGHTNESS},
    {"bg_name": "red", "bg_color": STATE_RED_COLOR, "bg_color_str": STATE_RED_COLOR_STR, "brightness_label": "bright", "brightness": STATE_RED_BRIGHT_BRIGHTNESS},
]

# 兼容旧版 settings.json 中的两列表达方式。
STATE_BG_OPTIONS_STR = str(_cfg.get(
    "STATE_BG_OPTIONS",
    "white:255,255,255;green:0,255,0;red:255,0,0"
))
STATE_BRIGHTNESS_OPTIONS_STR = str(_cfg.get(
    "STATE_BRIGHTNESS_OPTIONS",
    "dark:0.25;medium:0.55;bright:1.0"
))
STATE_BG_OPTIONS = parse_named_color_options(STATE_BG_OPTIONS_STR)
STATE_BRIGHTNESS_OPTIONS = parse_named_float_options(STATE_BRIGHTNESS_OPTIONS_STR)


def get_experiment_config_snapshot(extra_config=None):
    snapshot = {
        "SCREEN_FOV_DEG": SCREEN_FOV_DEG,
        "SPHERE_RADIUS_CM": SPHERE_RADIUS_CM,
        "SIMULATION_MODE": SIMULATION_MODE,
        "INVERT_ROTATION": INVERT_ROTATION,
        "INVERT_FORWARD": INVERT_FORWARD,
        "DEFAULT_BRIGHTNESS": DEFAULT_BRIGHTNESS,
        "V_BAR_COUNT": V_BAR_COUNT,
        "V_BAR_SPACING_DEG": V_BAR_SPACING_DEG,
        "H_BAR_COUNT": H_BAR_COUNT,
        "H_BAR_SPACING_CM": H_BAR_SPACING_CM,
        "VIRTUAL_WALL_DISTANCE_CM": VIRTUAL_WALL_DISTANCE_CM,
        "BAR_VISUAL_ANGLE_DEG": BAR_VISUAL_ANGLE_DEG,
        "BAR_HALF_WIDTH_CM": BAR_HALF_WIDTH_CM,
        "SMOOTHING_FACTOR": SMOOTHING_FACTOR,
        "PHASE_1_DURATION": PHASE_1_DURATION,
        "PHASE_2_DURATION": PHASE_2_DURATION,
        "PHASE_3_DURATION": PHASE_3_DURATION,
        "MOVEMENT_SPEED_THRESHOLD": MOVEMENT_SPEED_THRESHOLD,
        "MOVEMENT_ANG_VEL_THRESHOLD": MOVEMENT_ANG_VEL_THRESHOLD,
        "BG_COLOR": BG_COLOR_STR,
        "BAR_COLOR": BAR_COLOR_STR,
        "STATE_DURATION_S": STATE_DURATION_S,
        "STATE_RANDOM_SEED": STATE_RANDOM_SEED,
        "PRE_START_BG_COLOR": PRE_START_BG_COLOR_STR,
        "PRE_START_BRIGHTNESS": PRE_START_BRIGHTNESS,
        "STATE_WHITE_COLOR": STATE_WHITE_COLOR_STR,
        "STATE_GREEN_COLOR": STATE_GREEN_COLOR_STR,
        "STATE_RED_COLOR": STATE_RED_COLOR_STR,
        "STATE_WHITE_DARK_BRIGHTNESS": STATE_WHITE_DARK_BRIGHTNESS,
        "STATE_WHITE_MEDIUM_BRIGHTNESS": STATE_WHITE_MEDIUM_BRIGHTNESS,
        "STATE_WHITE_BRIGHT_BRIGHTNESS": STATE_WHITE_BRIGHT_BRIGHTNESS,
        "STATE_GREEN_DARK_BRIGHTNESS": STATE_GREEN_DARK_BRIGHTNESS,
        "STATE_GREEN_MEDIUM_BRIGHTNESS": STATE_GREEN_MEDIUM_BRIGHTNESS,
        "STATE_GREEN_BRIGHT_BRIGHTNESS": STATE_GREEN_BRIGHT_BRIGHTNESS,
        "STATE_RED_DARK_BRIGHTNESS": STATE_RED_DARK_BRIGHTNESS,
        "STATE_RED_MEDIUM_BRIGHTNESS": STATE_RED_MEDIUM_BRIGHTNESS,
        "STATE_RED_BRIGHT_BRIGHTNESS": STATE_RED_BRIGHT_BRIGHTNESS,
        "STATE_BG_OPTIONS": STATE_BG_OPTIONS_STR,
        "STATE_BRIGHTNESS_OPTIONS": STATE_BRIGHTNESS_OPTIONS_STR,
    }
    if extra_config:
        snapshot.update(extra_config)
    return snapshot



