# FicTrac Runtime Directory

This source repository keeps the active FicTrac configuration and calibration
images in this directory.

The Windows runtime binaries and DLLs are distributed in the downloadable
package attached to the latest GitHub Release:

<https://github.com/renatirudy246-maker/drosophila-vr-fictrac/releases/latest>

Required runtime files include:

- `fictrac.exe`
- `configGui.exe`
- `nlopt.dll`
- `opencv_world460.dll`
- `opencv_videoio_ffmpeg460_64.dll`
- `opencv_videoio_msmf460_64.dll`

Calibration is hardware-specific. Recheck the camera source, ball ROI, ignored
regions, camera model, and UDP port before collecting real data on another
computer or rig.

