# Camera + measured-distance milestone

Run commands from the repository root in a **camera-authorized Terminal**.
Activate the environment and update dependencies:

```bash
source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements-dev.txt
python -m pytest -q
```

1. Keep the iPhone connected with Camo Camera and Camo Studio running. The
   operator verified index 1 at 640x480 and approximately 8.4 preview FPS.
   Cover/uncover the iPhone lens to confirm the camera identity.
2. In Arduino IDE, open `arduino/ultrasonic_stream/ultrasonic_stream.ino`.
   It preserves the confirmed TRIG=D7/ECHO=D8 mapping on P7 SONIC. Select
   UNO R4 WiFi and upload manually. Keep the original diagnostic sketch.
3. Check Serial Monitor at 9600 baud: only numeric centimeters or `nan`,
   about five lines each second. Move a target to known distances and verify
   that the numbers change plausibly. **Close Serial Monitor/Plotter.**
4. Discover the current serial device; do not assume it stays the same:

```bash
python3 -m serial.tools.list_ports
python -m hub.main --list-ports
```

The inspected Mac listed `/dev/cu.usbmodemF0F5BD52589C2` as
`UNO WiFi R4 CMSIS-DAP`. Substitute the current device path below:

```bash
python -m hub.main --mode serial --serial-port /dev/cu.usbmodemF0F5BD52589C2 --seconds 10
python -m hub.main --mode combined --camera-index 1 --backend avfoundation --serial-port /dev/cu.usbmodemF0F5BD52589C2
```

The first command prints JSON with timezone-aware UTC measurement timestamps.
The second shows camera video and measured centimeters. Confirm both change
live while moving an object. Disconnect USB: the overlay should become
disconnected/stale, while video continues. Reconnect USB: the reader retries
the selected path each second. If macOS assigns a different port, restart
with that port. A missing port does not stop video; an unavailable camera
stops the preview with an error. Q/Esc/window-close exits; Ctrl-C also exits.

**Acceptance:** a live OpenCV window showing the verified iPhone feed and
fresh, physically measured ultrasonic distances. A mock overlay is a software
check and does not satisfy this hardware milestone.

## Without Arduino or camera

```bash
# Real camera + explicitly labeled synthetic distances; no Arduino needed.
python -m hub.main --mode combined --camera-index 1 --mock-serial
# All inputs synthetic, drawn person, no devices or model weights.
python -m hub.main --mode simulate
# Finite console-only smoke checks.
python -m hub.main --mode simulate --headless --seconds 3
python -m hub.main --mode serial --mock-serial --seconds 3
# Real camera only.
python -m hub.main --mode camera --camera-index 1
```

Simulation requires OpenCV/NumPy for synthetic frames, but no camera,
Arduino or ML model. Its screen is labeled SIMULATION. The synthetic sensor
includes a `nan` reading. Model inference is optional and initially off.

## Add the CPU detector after the distance overlay works

```bash
python -m hub.models
python -m hub.benchmark --runs 10
python -m hub.main --camera-index 1 --serial-port /dev/cu.usbmodemF0F5BD52589C2 --detector mobilenet-ssd --confidence 0.60 --detect-every 3
```

For detector checks without Arduino, replace `--serial-port ...` with
`--mock-serial`, or use `--mode camera`. See [model documentation](../models/README.md).
Confirm person boxes, confidence and CPU inference latency. Measure actual
preview FPS with detection enabled on the Mac; synthetic benchmarks do not
establish live performance or detection accuracy.

The reader stores only the newest reading. `nan`, malformed lines, or a
disconnect immediately remove the previous numeric distance; silence makes
it stale after one second. The numeric parser accepts 0 < cm <= 400. Serial
input is newline-framed, bounded, and independent of camera processing.
The old diagnostic firmware's `Distance: ... cm` messages are intentionally
invalid for this numeric protocol; upload the streaming alternative first.

No recordings, CSV logs, fusion alerts, motors, servos, email or SMS are
produced in this phase. Person boxes and ultrasonic echoes are separate
observations; a single sensor cannot associate an echo with a specific
person. Use one person in an aligned doorway region for initial tests.

Record firmware upload, lens-cover identity, measured-distance overlay,
USB unplug/replug and detector checks in `docs/verification.md`. They require
physical access and are not established by passing automated tests.
