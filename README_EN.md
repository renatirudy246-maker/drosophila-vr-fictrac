# Drosophila VR with FicTrac 2.1.1

[中文](README.md) | [English](README_EN.md)

A Windows-based Drosophila virtual-reality experiment system that receives spherical-treadmill tracking data from FicTrac 2.1.1, renders visual stimuli on a U-shaped screen, and records frame-level behavior, state summaries, and analysis plots.

## Overview

This project receives FicTrac 2.1.1 tracking results over UDP, converts the fly's spherical-treadmill motion into virtual-world displacement and heading, and presents randomized visual stimuli on a U-shaped screen.

In the current apparatus, the screen is approximately 4 cm from the fly and the default software field of view is 270 degrees. The physical screen distance and the virtual-wall parameter `VIRTUAL_WALL_DISTANCE_CM` represent different quantities and must not be interchanged.

## Features

- FicTrac 2.1.1 UDP parsing with source-verified output-column indices
- Camera and FicTrac can start early; formal timing begins only after Space is pressed
- 18 randomized visual states
- Logging of FicTrac quantities, experiment time, VR trajectory, and stimulus geometry
- Frame-level CSV and state-level activity, trajectory, turning, facing, and approaching summaries
- Trajectory, behavior-timeline, and polar-preference plots
- Portable relative paths for use on other computers

## Repository Layout

| Path | Purpose |
| --- | --- |
| `launcher.py` | Main experiment control interface |
| `main.py` | VR loop, FicTrac parsing, state scheduling, and logging |
| `config.py` | Runtime configuration loader |
| `data_logger.py` | Frame-level CSV and state-summary schemas |
| `renderer.py` | U-shaped screen stimulus renderer |
| `plot_*.py` | Offline plotting scripts |
| `settings.json` | Portable default configuration |
| `fictrac/` | Active FicTrac configuration and calibration images |
| `fictrac-2.1.1/` | FicTrac source, headers, documentation, samples, and build files |
| `hardware/零件建模/` | SolidWorks parts and top-level assembly for the apparatus |
| `hardware/果蝇VR实验平台主要材料采购链接与价格.docx` | Main materials, reference prices, and purchase links |
| `OUTPUT_FIELDS.md` | Complete output-field and formula reference |
| `DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md` | Data QC, preprocessing, and analysis workflow |

Experiment data, videos, logs, installers, and generated build directories are intentionally excluded from Git history.

## Installation

Python 3.9-3.11 is recommended.

```powershell
git clone https://github.com/renatirudy246-maker/drosophila-vr-fictrac.git
cd drosophila-vr-fictrac
python -m pip install -r requirements.txt
```

Windows users can download and extract the [latest Release](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/latest). The package includes the FicTrac executables and DLLs omitted from Git history.

## Running and Calibration

```powershell
python launcher.py
```

Before using a new computer, camera, or sphere position:

1. Open the FicTrac configuration GUI from the launcher.
2. Recheck the camera source, spherical ROI, ignored regions, and camera model.
3. Confirm that FicTrac and the launcher use the same UDP port, default `2000`.
4. Confirm the physical sphere radius, default `0.6 cm`.
5. Keep `SIMULATION_MODE=false` for real experiments.

## Experiment Start Sequence

The camera and FicTrac may be started early. Formal experiment timing begins at zero only after Space is pressed in the VR window.

After Space is pressed, the program:

1. flushes pending pre-start UDP packets;
2. generates the randomized 18-state schedule;
3. uses the first new FicTrac frame after the key press as the motion baseline;
4. calculates `Time_s`, displacement, and trajectory from subsequent FicTrac frame differences and writes them to CSV.

Camera warm-up and experiment preparation time are therefore excluded from formal experiment time.

## State Design

The default experiment contains:

- 3 backgrounds: white, green, and red
- 3 calibrated brightness levels for each background
- 9 states without stripe stimuli followed by 9 states with stripe stimuli
- 20 seconds per state, approximately 360 seconds in total

State order is randomized separately within each block. `State_Index` is the presentation order for one run, not a stable condition identifier across flies. Cross-experiment analysis should use `State_Block`, `State_BG_Name`, `State_Brightness_Label`, and `State_Stimulus_On`.

## Data and Plots

Experiment outputs are written to `exp_data/` by default. Experiment CSV files, videos, and logs are excluded by `.gitignore` and should be archived separately.

- [Output fields and formulas](OUTPUT_FIELDS.md)
- [Data preprocessing and analysis](DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md)

## FicTrac Source and License

The FicTrac source files retain their original [CC BY-NC-SA 3.0 license](fictrac-2.1.1/LICENSE.txt). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution and third-party notices.

No separate open-source license has been selected for the project-specific Python code in this repository. Public visibility does not by itself grant additional rights to copy, modify, or redistribute that code.
