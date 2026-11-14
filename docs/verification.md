# Verification record

## Environment inspection — 2026-11-14

- Repository initially clean on `main`; fetched `origin/main` at `6f29d8a`.
- Feature branch: `feature/python-hub-camera-integration`.
- MacBookPro12,1; Intel Core i5, 2.7 GHz; 8 GB RAM.
- macOS 15.7.7, x86_64; Python 3.10.7; Git 2.15.0.
- Approximately 760 GiB free disk space at inspection.
- No pre-existing Python implementation or firmware in this checkout.

## Camera gate

- Camo Studio live preview: **operator-reported working**.
- Virtual environment installed successfully with binary wheels: OpenCV
  4.11.0.86, NumPy 1.26.4, pytest 8.3.5. `pip check`: no broken requirements.
- OpenCV import: **passed**, reporting 4.11.0.
- AVFoundation backend availability: **passed** (`hasBackend` returned true).
- Initial sandbox probe of indices 0–5 through AVFoundation: **no frames read**. Each reported
  `OpenCV: camera access has been denied`. This does not determine whether
  Camo is available after privacy permission is granted.
- Subsequent physical test: **operator-reported success** on the Early 2015
  Intel MacBook Pro using:
  `python -m hub.camera --preview --camera-index 1 --backend avfoundation --seconds 20`.
- Index 1, AVFoundation, live video and macOS camera authorization: **working**.
- Actual preview: **640x480**, approximately **8.4 FPS**, as observed by operator.
- `AVCaptureDeviceTypeExternal` deprecation warning: observed, nonblocking.
- Camo/iPhone identity: **lens-cover test still pending**. Cover the iPhone
  lens and confirm the OpenCV image changes, then uncover it and confirm
  live movement. Working index 1 is the initial hub default, still configurable.
- This confirms the camera preview milestone, not serial integration or detection accuracy.

## Software checks

- `python -m pytest -q`: **15 passed** on host Python 3.10.7.
- `python -m pip check`: **passed**.
- `python -m hub.camera --help`: **passed**.
- `git diff --check`: **passed**.
- CI configured for Python 3.10, 3.11 and 3.12; remote results are separate
  from the locally executed Python 3.10 tests.

## Remaining phases

Serial streaming, mock serial input, person detection, fusion, CSV logging,
and combined/simulated modes follow the camera gate. No firmware is present
to verify the previously experimental D7/D8 mapping. Preserve the working
Arduino sketch and confirm its pins before preparing an alternative.

Before selecting a detector, check current package support for Intel macOS,
Python 3.10 and 8 GB RAM. No PyTorch, Ultralytics, model weights or firmware
are installed by this phase.
