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

## Serial streaming phase

- Operator confirmed `Documents/Arduino/sketch_nov7a/sketch_nov7a.ino` is the
  original working ultrasonic sketch: TRIG=D7, ECHO=D8, 9600 baud, 500 ms
  interval, 30,000 us pulse timeout, duration * 0.0343 / 2.0 centimeters.
- `motion_detection_sim.ino` is a separate LED/keyboard simulation. Neither
  local original sketch was changed.
- New alternative: `arduino/ultrasonic_stream/ultrasonic_stream.ino`, same pins
  and baud, numeric-only centimeters or `nan`, approximately 200 ms period.
- **Board-toolchain compile passed**, Arduino CLI 1.5.1, UNO R4 WiFi core
  1.6.0 (`arduino:renesas_uno:unor4wifi`). 52,672 bytes flash / 6,740 bytes RAM.
- **No firmware upload performed.** Operator will verify/upload in Arduino IDE.
- Threaded pyserial input implemented with bounded framing, invalid/no-echo
  handling, monotonic freshness, UTC timestamps, reconnects and 5 Hz mock mode.
- Serial phase regression run: **42 tests passed**, including real pyserial
  `loop://` software transport. No physical Arduino required.
- Port discovery succeeded: `/dev/cu.usbmodemF0F5BD52589C2`, description
  `UNO WiFi R4 CMSIS-DAP`. This establishes enumeration, not measured data.

## Combined preview and simulation phase

- Configurable camera defaults to tested index 1. Separate serial thread
  supplies a latest-reading snapshot; missing serial data never gates capture.
- Camera-only, serial-only, combined and full simulation commands implemented.
- Combined phase regression run: **56 tests passed**.
- Headless full simulation and mock serial-only commands: **passed** with
  changing synthetic distances and UTC timestamps.
- Two-second simulated OpenCV GUI: **process startup/normal exit passed**
  outside the sandbox. A sandbox GUI invocation aborted; no hardware used.
- Combined camera + mock distance check from Codex: **not verified**. Sandboxed
  capture denied access; an outside-sandbox attempt reported authorization
  status 0 and requested permission, then failed to initialize. The operator's
  successful Terminal camera test remains valid; permissions depend on the
  launching application. Repeat combined preview in the authorized Terminal.
- **Live measured-distance overlay: pending manual firmware upload and test.**

## CPU person detection phase

- Compatibility reviewed before downloading model assets. Official PyTorch
  support for macOS x64 ended with 2.2.x; selected MobileNet-SSD via existing
  OpenCV DNN instead. See [model sources and checksums](../models/README.md).
- Downloaded the original author's pinned Caffe model (23,306,119 bytes),
  network definition and MIT license. SHA-256 verification passed. Assets are
  ignored by Git; no PyTorch, Ultralytics or additional ML package installed.
- **Real OpenCV CPU network load and inference passed** on synthetic input.
- Final default benchmark: 10 runs after warmup, black 640x480 input resized
  to 300x300; median **218.29 ms**, minimum 86.00 ms, maximum 392.75 ms.
  OpenCV internal parallelism disabled, backend reported one thread. These
  timings vary with host load; they do not establish live preview FPS or
  accuracy. An earlier parallel-backend trial was faster; the default favors
  leaving CPU time for capture/display.
- Latest-frame background inference, confidence filtering and stale-result
  expiry implemented. Results expire based on source capture time.
- Detection phase regression run: **66 tests passed**; `pip check` passed.
- No physical person-detection accuracy or live detector FPS test performed.

## Pending physical acceptance

1. Lens-cover test to confirm iPhone/Camo identity at index 1.
2. Manual streaming firmware upload; check numeric output at 9600 baud, ~5 Hz.
3. Compare reported distances with known physical distances.
4. Run combined preview with real measured centimeters; unplug/reconnect USB
   and confirm video remains responsive and the reading recovers.
5. Evaluate real person detection, CPU latency and preview FPS in the doorway.

The exact commands are in [the demo guide](demo_guide.md). No hardware pass is
inferred from software tests, compilation, simulation or port enumeration.

## Remaining development

Freshness-aware alert fusion and authoritative CSV logging/contract are future
phases. A single ultrasonic sensor cannot identify which person produced an
echo; no exact person-to-distance or multi-person association is claimed.
