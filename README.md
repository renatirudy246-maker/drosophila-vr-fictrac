# Drosophila VR with FicTrac 2.1.1: Single-Condition Trials

A Windows-based experiment system for a tethered fly on a spherical treadmill. It receives FicTrac tracking data over UDP, displays visual stimuli on a U-shaped screen, and records behavior and trajectories.

This version runs one manually selected condition per trial, with a default duration of 20 seconds and `VIRTUAL_WALL_DISTANCE_CM = 9.75`. The original 18-state, 360-second protocol with a 10.0 cm virtual-wall distance is preserved in [drosophila-vr-fictrac-360s](https://github.com/renatirudy246-maker/drosophila-vr-fictrac-360s). This single-condition variant does not change the protocol used to collect historical data or make segments from the same fly independent biological samples.

## Setup

Use Python 3.9-3.11 with a compatible camera and display.

```powershell
git clone https://github.com/renatirudy246-maker/drosophila-vr-fictrac.git
cd drosophila-vr-fictrac
python -m pip install -r requirements.txt
```

The Git checkout includes FicTrac source in `fictrac-2.1.1/`, but not its runtime folder. Download the [Windows runtime package (v1.0.1)](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/download/v1.0.1/drosophila-vr-fictrac-windows-v1.0.1.zip), extract it, and copy the entire `fictrac/` folder next to `launcher.py`. This supplies `fictrac.exe`, `configGui.exe`, their DLLs, `config.txt`, and the calibration images.

Recalibrate the supplied configuration for your apparatus before collecting data. The checkout alone cannot perform real tracking without these runtime files; the source directory is not a substitute for them.

## Run

```powershell
python launcher.py
```

1. Open the FicTrac configuration GUI from the launcher and check the camera source, spherical ROI, ignored regions, and camera model.
2. Set the actual sphere radius in the launcher (default: `0.6 cm`). Match the UDP port in the launcher and `fictrac/config.txt` (default: `2000`). Keep simulation mode disabled for real experiments.
3. Start the camera and FicTrac, then open the VR window. Press Space in that window to begin the experiment and recording. Preparation time is excluded; subsequent CSV timestamps use FicTrac sampling intervals.

## Select a Condition

Edit these keys in `settings.json`, or use the launcher's Trial Condition controls and save the configuration before starting:

```json
"STATE_DURATION_S": 20,
"SINGLE_BG_NAME": "white",
"SINGLE_BRIGHTNESS_LABEL": "bright",
"SINGLE_STIMULUS_ON": false
```

`SINGLE_BG_NAME` accepts `white`, `green`, or `red`; `SINGLE_BRIGHTNESS_LABEL` accepts `dark`, `medium`, or `bright`; `SINGLE_STIMULUS_ON` is a JSON boolean (`true` for stripes, `false` for no stripes). The example selects white, bright, and no stripes. Brightness is read from the corresponding calibrated `STATE_<COLOR>_<LEVEL>_BRIGHTNESS` value, not replaced by 100% intensity.

Each run presents just that condition, without randomization or an additional 180-second block. It stops after the configured sampling duration (20 seconds by default); a lack of incoming tracking data pauses the sampling clock. With stripes enabled, their virtual-world positions are anchored using the first new FicTrac sample after trial start. Keep the same Fly ID for repeat trials on the same animal and use Trial ID to distinguish recordings.

CSV rows retain `State_Index = 1` and record the selected background, calibrated brightness, and stimulus flag. Configuration snapshot columns identify the `single_condition` protocol, condition settings, Fly ID, and Trial ID. Trajectory and timeline plots work with a single state; polar preference is only generated for trials with visual stripes.

The physical screen is approximately 4 cm from the fly. `VIRTUAL_WALL_DISTANCE_CM` describes the virtual scene, not this physical distance.

## Files and Outputs

| File | Purpose |
| --- | --- |
| `launcher.py` | Experiment controls, calibration access, and plotting |
| `main.py` | FicTrac input, experiment timing, motion integration, and VR loop |
| `config.py`, `settings.json` | Runtime configuration and saved settings |
| `renderer.py` | Visual stimulus rendering |
| `data_logger.py` | Frame-level CSV and state summaries |
| `plot_split_trajectory.py` | Trajectory plots |
| `plot_facing_timeline.py` | Facing and approaching timelines |
| `plot_polar_preference.py` | Polar preference plots |
| `requirements.txt` | Python dependencies |
| `fictrac-2.1.1/` | FicTrac source, build files, documentation, and license |
| `hardware/` | 27 SolidWorks parts and one top-level assembly |

Outputs are saved to `exp_data/` by default, including frame-level and state-summary CSV files and a live-status JSON file. Generate analysis plots through the launcher. Experiment data, logs, and the locally installed `fictrac/` runtime folder are excluded from Git.

Run the offline protocol checks with `python -m unittest discover -s tests -v`. These use synthetic tracking packets and do not replace camera or display calibration on the apparatus.

Hardware models are grouped under `screen_support/`, `ball_holder/`, `circuit_board/`, `camera_mount/`, and `infrared_light/`. The assembly file is [platform_assembly.SLDASM](hardware/platform_assembly.SLDASM). Only filesystem names have been translated; internal CAD references have not been updated, so opening the assembly may require relinking components. Hardware files are optional and are not needed to run the program.

## Attribution

FicTrac was developed at the Queensland Brain Institute, University of Queensland. See the [FicTrac project](http://fictrac.rjdmoore.net). The bundled source retains its original [CC BY-NC-SA 3.0 license](fictrac-2.1.1/LICENSE.txt), including attribution, non-commercial, and share-alike requirements.

No separate license has been selected for this project's Python code or hardware models. Public availability does not grant additional reuse rights.
