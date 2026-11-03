# Drosophila VR with FicTrac 2.1.1: Single-Condition Trials

A Windows-based experiment system for a tethered fly on a spherical treadmill. It receives FicTrac tracking data over UDP, displays visual stimuli on a U-shaped screen, and records behavior and trajectories.

This version runs one manually selected condition per trial, with a default duration of 20 seconds and `VIRTUAL_WALL_DISTANCE_CM = 9.75`. The original 18-state, 360-second protocol with a 10.0 cm virtual-wall distance is preserved in [drosophila-vr-fictrac-360s](https://github.com/renatirudy246-maker/drosophila-vr-fictrac-360s). This single-condition variant does not change the protocol used to collect historical data or make segments from the same fly independent biological samples.

## Setup

Use 64-bit Windows 10/11 and Python 3.9-3.11 with a compatible camera and display.

### Complete Windows Package

Download [drosophila-vr-fictrac-windows-v1.1.1.zip](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/download/v1.1.1/drosophila-vr-fictrac-windows-v1.1.1.zip) from the [v1.1.1 Release](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/tag/v1.1.1). Extract the entire archive, keeping its folder structure. It includes the Python program and the `fictrac/` runtime folder with `fictrac.exe`, `configGui.exe`, OpenCV/NLopt DLLs, configuration and calibration images. No separate FicTrac download or build is needed for this package.

Activate your Python environment, open a terminal in the extracted project directory, and run:

```powershell
python -m pip install -r requirements.txt
python launcher.py
```

The launcher runs in your Python environment; the included EXE files run FicTrac and its calibration GUI. Do not move individual files out of the extracted directories. Configuration still needs to match your camera and apparatus before collecting data.

FicTrac also requires the Microsoft Visual C++ v14 x64 runtime. If Windows reports missing `MSVCP140.dll`, `VCRUNTIME140.dll`, `VCRUNTIME140_1.dll` or `CONCRT140.dll`, install the signed Microsoft installer included at `prerequisites/VC_redist.x64.exe`, then retry. It is also available from [Microsoft's supported redistributable downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist/). This installer is not run automatically.

### Git Source Checkout

```powershell
git clone https://github.com/renatirudy246-maker/drosophila-vr-fictrac.git
cd drosophila-vr-fictrac
python -m pip install -r requirements.txt
```

The Git checkout includes FicTrac source in `fictrac-2.1.1/`, but not compiled runtime files. Copy the complete `fictrac/` folder from the Windows package above next to `launcher.py`. GitHub's automatically generated **Source code (zip)** and **Source code (tar.gz)** downloads are source-only; use the explicitly named Windows package for a complete runtime.

Recalibrate the supplied configuration for your apparatus before collecting data. The checkout alone cannot perform real tracking without these runtime files; the source directory is not a substitute for them.

## Run

```powershell
python launcher.py
```

1. Open the FicTrac configuration GUI from the launcher and check the camera source, spherical ROI, ignored regions, and camera model.
2. Set the actual sphere radius in the launcher (default: `0.6 cm`). Match the UDP port in the launcher and `fictrac/config.txt` (default: `2000`). Keep simulation mode disabled for real experiments.
3. Start the camera and FicTrac, then open the VR window. Press Space in that window to begin the experiment and recording. Preparation time is excluded; subsequent CSV timestamps use FicTrac sampling intervals.

## Select a Condition

Use the launcher's Trial tab for background, duration, brightness, stripe enable/width/count, winged/wingless status, and sample IDs. Hardware, pre-start appearance, stripe color, and recording settings are on the Advanced tab; separate white/green/red RGB controls and the original nine-cell brightness matrix are not shown. Save the configuration before starting. The launcher uses a Tk/ttk layout with fixed-width control columns and a flexible preview area; window, font and control scaling follows the active monitor's Windows DPI setting.

The equivalent keys in `settings.json` are:

```json
"STATE_DURATION_S": 20,
"SINGLE_BG_NAME": "white",
"SINGLE_BRIGHTNESS": 0.197,
"SINGLE_STIMULUS_ON": false,
"BAR_VISUAL_ANGLE_DEG": 30.0,
"V_BAR_COUNT": 2
```

`SINGLE_BG_NAME` accepts `white`, `green`, or `red`. `SINGLE_BRIGHTNESS` directly sets the display intensity from 0 to 1, independent of background selection; the default 0.197 preserves the previous calibrated white/bright value. `SINGLE_STIMULUS_ON` is a JSON boolean (`true` for stripes, `false` for no stripes). Trials using a direct intensity are logged with brightness label `custom`. Older settings without `SINGLE_BRIGHTNESS` still resolve `SINGLE_BRIGHTNESS_LABEL` through the original calibrated values.

`V_BAR_COUNT` accepts integers from 1 to 12. Vertical stripes are spaced evenly around the virtual fly, starting at its trial-start heading; two stripes retain the original front/back layout. Spacing is calculated from the count, rather than the legacy `V_BAR_SPACING_DEG` setting. Stripe width is the nominal angular width at the anchor position; it must be 21.92-46.99 degrees, matching the renderer's existing angular limits. Apparent width still varies with the fly's virtual position within these limits. `Stim_Bar_Back_*` is blank when no stripe is placed exactly behind the anchor (odd stripe counts).

Each fly is recorded in one condition, without randomization or an additional 180-second block. Recording stops after the configured sampling duration (20 seconds by default); a lack of incoming tracking data pauses the sampling clock. With stripes enabled, their virtual-world positions are anchored using the first new FicTrac sample after trial start. Fly IDs identify individual animals within each wing group. Trial ID is retained as configuration metadata and is not part of the folder name.

CSV rows retain `State_Index = 1` and record the actual background, brightness, and stimulus flag. Configuration snapshot columns identify the `single_condition` protocol, stripe count/spacing, condition settings, Fly ID, and Trial ID. Trajectory and timeline plots work with a single state; polar preference is only generated for trials with visual stripes. New recordings declare the `front_zero` angular reference, which the polar plot uses without the legacy centering rotation.

The physical screen is approximately 4 cm from the fly. `VIRTUAL_WALL_DISTANCE_CM` describes the virtual scene, not this physical distance.

## Files and Outputs

One sample folder holds one fly's single-condition recording. All generated folder names are English:

```text
exp_data/
  wing/
    wing_01_white_low/
    wing_02_red_high/
  no_wing/
    no_wing_01_green_medium/
    no_wing_02_white_high/
```

The launcher suggests `01`, `02`, `03`, and so on by reading existing sample folders in the selected group. The two groups count independently, each starting at `01`. You may edit the suggested Fly ID, but an ID already used in that group is rejected even if its color or intensity differs. Starting tracking and VR shares the same sample folder; after stopping, the next unused ID is suggested. Existing folders are never overwritten, renamed, or moved.

The export field selects the parent data directory. Relative paths such as `exp_data` are resolved to absolute paths before launching FicTrac, so the tracker, VR loop, recording flags and CSV logger use the same sample folder. Stop tracking and VR before changing the export path or sample identity.

Single-condition CSV files use `white_high_off_YYYYMMDD_HHMMSS.csv`: background (`white`/`green`/`red`), intensity (`low`/`medium`/`high`), and stripes (`on`/`off`). Intensity labels in both sample folders and CSV names are matched to that color's saved dark/medium/bright calibration values, not thirds of the 0-1 range. Unmatched or ambiguous intensities use `custom`; the exact numeric intensity remains in the CSV and configuration snapshot. Summary files use the same name with `_phase_summary` appended. Plotting accepts both these names and legacy `drosophila_exp_*` files.

| File | Purpose |
| --- | --- |
| `launcher.py` | Experiment controls, calibration access, and plotting |
| `launcher_controller.py` | Tracking/video process control, monitoring and configuration |
| `ui_scaling.py` | Window sizing and mixed-DPI native-widget layout |
| `main.py` | FicTrac input, experiment timing, motion integration, and VR loop |
| `config.py`, `settings.json` | Runtime configuration and saved settings |
| `renderer.py` | Visual stimulus rendering |
| `data_logger.py` | Frame-level CSV and state summaries |
| `output_naming.py` | Condition filenames and new/legacy CSV discovery |
| `plot_split_trajectory.py` | Trajectory plots |
| `plot_facing_timeline.py` | Facing and approaching timelines |
| `plot_polar_preference.py` | Polar preference plots |
| `requirements.txt` | Python dependencies |
| `fictrac-2.1.1/` | FicTrac source, build files, documentation, and license |
| `hardware/` | 27 SolidWorks parts and one top-level assembly |

Outputs are saved to `exp_data/` by default, including frame-level and state-summary CSV files and a live-status JSON file. Generate analysis plots through the launcher. Experiment data, logs, and the locally installed `fictrac/` runtime folder are excluded from Git.

Run the offline protocol and layout checks with `python -m unittest discover -s tests -v`. A separate desktop GUI check is available with `python tests/check_launcher_ui.py`; it uses temporary files and simulated process launches, not a camera. These checks do not replace camera or display calibration on the apparatus. The optimized launcher was also compared locally with the previous teacher UI using historical FicTrac data, independent video-window playback and complete 20-second UDP replays; those raw experimental records are not included in this repository.

Hardware models are grouped under `screen_support/`, `ball_holder/`, `circuit_board/`, `camera_mount/`, and `infrared_light/`. The assembly file is [platform_assembly.SLDASM](hardware/platform_assembly.SLDASM). Only filesystem names have been translated; internal CAD references have not been updated, so opening the assembly may require relinking components. Hardware files are optional and are not needed to run the program.

## Attribution

FicTrac was developed at the Queensland Brain Institute, University of Queensland. See the [FicTrac project](http://fictrac.rjdmoore.net). The bundled source retains its original [CC BY-NC-SA 3.0 license](fictrac-2.1.1/LICENSE.txt), including attribution, non-commercial, and share-alike requirements.

No separate license has been selected for this project's Python code or hardware models. Public availability does not grant additional reuse rights.
