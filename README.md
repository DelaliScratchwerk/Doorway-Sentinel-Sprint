# Doorway Sentinel Sprint

A collaborative doorway-monitoring prototype combining an Arduino ultrasonic
sensor with camera-based person detection. The intended demo identifies a
person, measures proximity, displays an alert, and records a shared CSV event.

**Current milestone:** nonblocking camera + distance preview, threaded USB
serial input, full simulation and optional lightweight CPU person detection.
The operator verified live OpenCV video at index 1, AVFoundation, 640x480 and
approximately 8.4 FPS. A lens-cover test still needs to confirm iPhone identity.
The new streaming firmware is ready for manual upload; a live overlay of
**measured** ultrasonic distances remains the next hardware acceptance test.
See the [demo guide](docs/demo_guide.md) and [verification record](docs/verification.md).

## macOS setup

Inspected host: early-2015 Intel MacBook Pro, 8 GB RAM, macOS 15.7.7,
Python 3.10.7. Use Python 3.10–3.12 for this dependency set. Hardware-free CI
covers those versions; host camera compatibility must be tested separately.

```bash
cd ~/Desktop/Doorway-Sentinel-Sprint
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pytest -q
python -m hub.camera --help
```

OpenCV 4.11.0.86 has a published macOS 13+ Intel wheel; NumPy 1.26.4 is pinned
for this Python range. Binary-only installation avoids compiling on the Mac.
Use the GUI-enabled `opencv-python` package for preview. Avoid installing
multiple OpenCV distributions into the same environment. Dependencies are
local to `.venv`; no global installation or large ML downloads are required.

## First hardware verification

Connect the iPhone SE (3rd generation), run Camo Camera, and keep the working
Camo Studio 2.9.0 preview open:

```bash
source .venv/bin/activate
python -m hub.camera --list --backend avfoundation --max-index 5
```

Index 1 has been tested on this Mac; use another index if re-probing shows it changed:

```bash
python -m hub.camera --preview --camera-index 1 --backend avfoundation --seconds 20
```

Confirm visually that the feed is live from the iPhone. Never assume index 0.
See [camera instructions and troubleshooting](camera/README.md) and record the
result in [the verification record](docs/verification.md).

## Run the hub

```bash
# First verify the overlay with real camera and labeled mock distances.
python -m hub.main --mock-serial --camera-index 1 --seconds 20
# No hardware or model weights: all inputs are synthetic.
python -m hub.main --mode simulate
# Console-only simulation, useful for smoke checks.
python -m hub.main --mode simulate --headless --seconds 3
# Discover serial ports after manually uploading the streaming sketch.
python3 -m serial.tools.list_ports
python -m hub.main --list-ports
```

Replace the example device path with the current port. Close Arduino Serial
Monitor/Plotter before Python opens it:

```bash
python -m hub.main --mode serial --serial-port /dev/cu.usbmodemF0F5BD52589C2 --seconds 10
python -m hub.main --camera-index 1 --serial-port /dev/cu.usbmodemF0F5BD52589C2
python -m hub.main --mode camera --camera-index 1
python -m hub.main --help
```

Serial reads run in a background thread with timeouts and reconnects.
The preview never waits for serial data. Missing, invalid, no-echo, stale
and disconnected measurements display `--` rather than an old distance.
Freshness defaults to one second and uses a monotonic clock; measurement
timestamps use timezone-aware UTC. Valid numeric centimeters satisfy
0 < cm <= 400. See [firmware details](arduino/README.md).

Optional CPU person detection adds boxes, confidence and inference latency:

```bash
python -m hub.models
python -m hub.benchmark --runs 10
python -m hub.main --mode camera --camera-index 1 --detector mobilenet-ssd
python -m hub.main --mock-serial --detector mobilenet-ssd --confidence 0.60 --detect-every 3
```

The detector uses MobileNet-SSD through OpenCV DNN; no PyTorch installation.
Weights come from a pinned original-author revision with SHA-256 verification,
are downloaded explicitly, and stay out of Git. Inference runs in a worker
that retains only the newest pending frame. Stale detections are hidden.
See [model source, compatibility and limitations](models/README.md).

Q/Esc/window-close exits the GUI; Ctrl-C exits all modes. All modes accept
`--seconds` for finite runs. Full simulation is clearly labeled and uses a
drawn person and mock distances; it does not establish detection accuracy.
Camera failures stop the preview; missing serial data permits video to continue.

## Next implementation steps

1. Confirm the tested camera is the iPhone using a lens-cover test.
2. Upload `arduino/ultrasonic_stream/ultrasonic_stream.ino` manually in Arduino
   IDE. It preserves confirmed D7/D8 pins and streams at 9600 baud, ~5 Hz.
3. Verify the combined window with **measured** distances and USB unplug/replug.
4. Benchmark the CPU detector on live people in the controlled doorway.
5. Add fusion states (`UNKNOWN`, `CLEAR`, `APPROACHING`, `ALERT`), a configurable
   50 cm alert threshold, confirmation, cooldown and CSV logging.
6. Add CSV logging and perform the controlled doorway alert demo.

Current flow: Arduino USB serial + Camo AVFoundation capture → Python hub →
optional person detection → OpenCV display. Freshness-aware alert fusion
and CSV logging are still to be implemented.
The hub will own the shared CSV with fields
`timestamp,distance_cm,object_class,confidence,alert_status`; the authoritative
contract and its tests will be added with the logging phase. UTC timestamps
will include timezone, and missing or stale measurements will be empty.

A single ultrasonic sensor cannot establish which object produced an echo.
The initial demo assumes one person in an aligned camera/sensor region; it
does not establish reliable multi-person distance association.

## Team workflow

Work on feature branches and submit pull requests to `main`; do not merge
automatically or overwrite teammates' work. Run `python -m pytest -q` before
committing. Camera tests use fake capture objects and need no hardware,
OpenCV installation or model downloads. `.gitignore` excludes virtual
environments, live data, footage, and model weights.

Original project checklist, retained as the roadmap:

- [ ] Agree on and test the CSV contract.
- [x] Implement Arduino serial streaming alternative and Python reader (manual upload pending).
- [x] Connect a CPU camera model (physical person-detection evaluation pending).
- [ ] Integrate and test combined rows and alerts.
- [ ] Run the doorway demo.
