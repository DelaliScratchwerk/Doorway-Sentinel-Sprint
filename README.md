# Doorway Sentinel Sprint

A collaborative doorway-monitoring prototype combining an Arduino ultrasonic
sensor with camera-based person detection. The intended demo identifies a
person, measures proximity, displays an alert, and records a shared CSV event.

**Current milestone:** environment setup and an independent Camo/OpenCV camera
verification utility. Camo Studio's preview is working according to the
operator; Python access to Camo is not yet verified. The first hands-on test
is [the camera gate](camera/README.md). Serial, detection, fusion, and logging
are subsequent phases, not implemented commands yet.

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

Then replace `N` with a readable candidate index:

```bash
python -m hub.camera --preview --camera-index N --backend avfoundation --seconds 20
```

Confirm visually that the feed is live from the iPhone. Never assume index 0.
See [camera instructions and troubleshooting](camera/README.md) and record the
result in [the verification record](docs/verification.md).

## Next implementation steps

1. Verify Camo → OpenCV on connected hardware.
2. Preserve the tested Arduino sketch and verify the shield P7 SONIC pin map.
   Prepare a 9600-baud, ~5 Hz stream of numeric centimeters, or `nan` for no echo.
   Upload manually through Arduino IDE; motors and servo are outside scope.
3. Add a threaded serial reader with stale-data handling, reconnects and mock
   mode. After installing pyserial in the environment, discover macOS ports
   with `python3 -m serial.tools.list_ports`; typical ports are `/dev/cu.usbmodem*`.
4. Select and benchmark a CPU-compatible lightweight person detector.
5. Add fusion states (`UNKNOWN`, `CLEAR`, `APPROACHING`, `ALERT`), a configurable
   50 cm alert threshold, confirmation, cooldown and CSV logging.
6. Add camera-only, serial-only, combined and full simulation modes, then
   perform the controlled doorway demo.

Planned flow: Arduino USB serial + Camo AVFoundation capture → Python hub →
person detection and freshness-aware fusion → OpenCV display + CSV.
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
- [ ] Implement Arduino serial streaming.
- [ ] Connect the camera model.
- [ ] Integrate and test combined rows and alerts.
- [ ] Run the doorway demo.
