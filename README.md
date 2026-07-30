# Drosophila VR with FicTrac 2.1.1

A Windows-based Drosophila virtual-reality experiment system that receives
FicTrac 2.1.1 tracking data over UDP, renders visual stimuli on a U-shaped
screen, and records frame-level behavior, state summaries, and analysis plots.

The current setup uses a U-shaped screen approximately 4 cm from the fly.
The default software field of view is 270 degrees. Physical screen distance
and `VIRTUAL_WALL_DISTANCE_CM` are different quantities and must not be
interchanged.

## Features

- FicTrac 2.1.1 UDP parsing with verified column indices
- experiment timing that starts only after pressing Space
- 18 randomized visual states
- frame-level CSV output with FicTrac, experiment, VR, and stimulus fields
- state-level activity, trajectory, turning, facing, and approaching summaries
- trajectory, behavior-timeline, and polar-preference plots
- portable relative output paths

## Repository Layout

| Path | Purpose |
| --- | --- |
| `launcher.py` | Main experiment control interface |
| `main.py` | VR loop, FicTrac parsing, state scheduling, and logging |
| `config.py` | Runtime configuration loader |
| `data_logger.py` | Frame-level and state-summary CSV schema |
| `renderer.py` | U-shaped screen stimulus renderer |
| `plot_*.py` | Offline plotting scripts |
| `settings.json` | Portable default configuration |
| `fictrac/` | Active configuration and calibration images |
| `fictrac-2.1.1/` | FicTrac source, headers, docs, samples, and build definitions |
| `OUTPUT_FIELDS.md` | Complete output-field and formula reference |
| `DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md` | Recommended QC and analysis workflow |

Generated build directories, experiment data, videos, logs, and installers are
intentionally excluded from Git history.

## Installation

Recommended Python version: 3.9-3.11.

```powershell
git clone https://github.com/renatirudy246-maker/drosophila-vr-fictrac.git
cd drosophila-vr-fictrac
python -m pip install -r requirements.txt
```

For normal Windows use, download and extract the package from the
[latest Release](https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/latest).
That package includes the FicTrac executables and DLLs omitted from Git
history.

## Running

```powershell
python launcher.py
```

On a new computer or camera setup:

1. Open the FicTrac configuration GUI from the launcher.
2. Recheck the camera source, spherical ROI, ignored regions, and camera model.
3. Confirm that FicTrac and the launcher use the same UDP port, default 2000.
4. Confirm the physical sphere radius, default 0.6 cm.
5. Keep `SIMULATION_MODE=false` for real experiments.

## Experiment Start

The camera and FicTrac may be started early. Formal experiment timing does not
begin until Space is pressed in the VR window.

After Space:

1. pending UDP packets are flushed;
2. the randomized 18-state schedule is created;
3. the first new FicTrac packet establishes the motion baseline;
4. subsequent FicTrac deltas advance `Time_s` and are written to CSV.

This prevents camera warm-up time from being counted as experimental time.

## State Design

The default experiment contains:

- 3 backgrounds: white, green, and red
- 3 calibrated brightness levels per background
- 9 no-stimulus states followed by 9 stimulus states
- 20 seconds per state, approximately 360 seconds total

State order is randomized within each block. `State_Index` is the order for one
run, not a stable condition identifier across flies. Cross-experiment analysis
should use `State_Block`, `State_BG_Name`, `State_Brightness_Label`, and
`State_Stimulus_On`.

## Data

Experiment outputs are written under `exp_data/` by default. Data, videos, and
logs are deliberately ignored by Git and should be archived separately.

See:

- [Output fields and formulas](OUTPUT_FIELDS.md)
- [Data preprocessing and analysis](DATA_PREPROCESSING_AND_ANALYSIS_WORKFLOW.md)

## FicTrac Source and License

The FicTrac source files retain their original
[CC BY-NC-SA 3.0 license](fictrac-2.1.1/LICENSE.txt). See
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution.

No separate open-source license has been selected for the project-specific
Python code in this repository. Public visibility does not by itself grant
additional reuse rights.

