import math
import os
import re


FLY_FOLDER_PATTERN = re.compile(
    r"(wing|no_wing)_(\d{2,})_(white|green|red)_(low|medium|high|custom)"
)


def condition_components(settings):
    color = str(settings["SINGLE_BG_NAME"]).strip().lower()
    brightness = float(settings["SINGLE_BRIGHTNESS"])
    stimulus = settings["SINGLE_STIMULUS_ON"]
    if color not in ("white", "green", "red"):
        raise ValueError("Invalid background for output filename")
    if not math.isfinite(brightness) or not 0 <= brightness <= 1:
        raise ValueError("Invalid brightness for output filename")
    if not isinstance(stimulus, bool):
        raise ValueError("Stimulus flag must be a boolean")
    matches = []
    for original, label in (("dark", "low"), ("medium", "medium"), ("bright", "high")):
        calibrated = settings.get(f"STATE_{color.upper()}_{original.upper()}_BRIGHTNESS")
        if calibrated is not None and math.isclose(brightness, float(calibrated), rel_tol=0, abs_tol=1e-9):
            matches.append(label)
    level = matches[0] if len(matches) == 1 else "custom"
    return color, level, stimulus


def condition_file_prefix(settings):
    if settings.get("EXPERIMENT_PROTOCOL") != "single_condition":
        return "drosophila_exp"
    color, level, stimulus = condition_components(settings)
    return f"{color}_{level}_{'on' if stimulus else 'off'}"


def fly_folder_name(settings, wing, fly_id):
    if wing not in ("wing", "no_wing") or not str(fly_id).isdigit() or int(fly_id) < 1:
        raise ValueError("Fly group and positive numeric ID are required")
    color, level, _ = condition_components(settings)
    return f"{wing}_{int(fly_id):02d}_{color}_{level}"


def existing_fly_ids(root_dir, wing):
    if wing not in ("wing", "no_wing"):
        raise ValueError("Invalid fly group")
    group_dir = os.path.join(root_dir, wing)
    if not os.path.isdir(group_dir):
        return set()
    with os.scandir(group_dir) as entries:
        return {int(match.group(2)) for entry in entries
                if entry.is_dir() and (match := FLY_FOLDER_PATTERN.fullmatch(entry.name))
                and match.group(1) == wing}


def output_root_dir(path):
    path = os.path.normpath(path)
    name = os.path.basename(path)
    if FLY_FOLDER_PATTERN.fullmatch(name):
        path = os.path.dirname(path)
        if os.path.basename(path) in ("wing", "no_wing"):
            path = os.path.dirname(path)
    elif re.fullmatch(r"(?:exp_\d{3}_|(?:no_)?wing_\d{2,}_\d+)", name):
        path = os.path.dirname(path)
    elif name in ("wing", "no_wing"):
        path = os.path.dirname(path)
    return os.path.normpath(path)


def is_experiment_csv(path):
    name = os.path.basename(os.fspath(path))
    if not name.lower().endswith(".csv") or "summary" in name.lower():
        return False
    return name.startswith("drosophila_exp_") or re.fullmatch(
        r"(?:white|green|red)_(?:low|medium|high|custom)_(?:on|off)_\d{8}_\d{6}\.csv", name
    ) is not None


def find_csv_in_folder(folder_path):
    candidates = [os.path.join(folder_path, name) for name in os.listdir(folder_path)
                  if is_experiment_csv(name) and os.path.isfile(os.path.join(folder_path, name))]
    return max(candidates, key=os.path.getmtime) if candidates else None


def resolve_input_path(path):
    if path and os.path.isdir(path):
        return find_csv_in_folder(path)
    return path
