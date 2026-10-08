# Drosophila VR with FicTrac 2.1.1

A Windows-based experiment system for a tethered fly on a spherical treadmill. It receives FicTrac tracking data over UDP, displays visual stimuli on a U-shaped screen, and records behavior and trajectories.

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

The default schedule has 18 states: nine without stripes followed by nine with stripes, randomized within each block. States combine three background colors and three brightness levels, lasting 20 seconds each (about 360 seconds total).

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

Outputs are saved to `exp_data/` by default, including experiment CSV files and JSON summaries. Generate analysis plots through the launcher. Experiment data, logs, and the locally installed `fictrac/` runtime folder are excluded from Git.

Keep the hardware model directory structure and filenames unchanged so the assembly can locate its parts. Hardware files are optional and are not needed to run the program.

## Attribution

FicTrac was developed at the Queensland Brain Institute, University of Queensland. See the [FicTrac project](http://fictrac.rjdmoore.net). The bundled source retains its original [CC BY-NC-SA 3.0 license](fictrac-2.1.1/LICENSE.txt), including attribution, non-commercial, and share-alike requirements.

No separate license has been selected for this project's Python code or hardware models. Public availability does not grant additional reuse rights.
