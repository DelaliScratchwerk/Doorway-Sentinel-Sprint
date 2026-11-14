"""Minimal camera + distance preview; CPU detection is optional."""

import argparse
import json
import math
import sys
import time
from contextlib import ExitStack

from hub.camera import Camera, CameraConfig, CameraError, load_cv2
from hub.serial_reader import SensorSnapshot, SerialReader, list_ports


def distance_label(snapshot):
    if snapshot.distance_cm is None:
        return f"Distance: -- cm ({snapshot.status})"
    return f"Distance: {snapshot.distance_cm:.1f} cm"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("combined", "camera", "serial", "simulate"), default="combined")
    parser.add_argument("--list-ports", action="store_true")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--serial-port", help="e.g. /dev/cu.usbmodem...; no automatic port selection")
    source.add_argument("--mock-serial", action="store_true", help="Synthetic 5 Hz distances")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--stale-after", type=float, default=1.0, help="Sensor freshness in seconds")
    parser.add_argument("--camera-index", type=int, default=1, help="Initial tested index (default: 1)")
    parser.add_argument("--backend", choices=("auto", "avfoundation", "any"), default="auto")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--seconds", type=float, default=0, help="0 runs until Q / Esc / Ctrl-C")
    parser.add_argument("--headless", action="store_true", help="Print JSON status; no display window")
    parser.add_argument("--detector", choices=("none", "mobilenet-ssd"), default="none")
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--confidence", type=float, default=0.60)
    parser.add_argument("--detect-every", type=int, default=3, help="Submit every Nth captured frame")
    parser.add_argument("--detection-stale-after", type=float, default=1.5)
    args = parser.parse_args(argv)
    if args.list_ports:
        return args
    if args.mode in ("combined", "serial") and not (args.serial_port or args.mock_serial):
        parser.error("Select --serial-port or --mock-serial; use --list-ports to discover devices")
    if args.mode in ("camera", "simulate") and (args.serial_port or args.mock_serial):
        parser.error("Camera-only mode has no serial input; simulate uses automatic mock input")
    if args.mode in ("serial", "simulate") and args.detector != "none":
        parser.error("Real detection requires camera or combined mode; simulate uses synthetic people")
    try:
        CameraConfig(args.camera_index, args.width, args.height, args.fps, args.backend)
    except ValueError as exc:
        parser.error(str(exc))
    for name in ("stale_after", "detection_stale_after"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            parser.error(f"--{name.replace('_', '-')} must be finite and positive")
    if args.baud <= 0 or args.detect_every <= 0:
        parser.error("--baud and --detect-every must be positive")
    if not math.isfinite(args.seconds) or args.seconds < 0:
        parser.error("--seconds must be finite and nonnegative")
    if not math.isfinite(args.confidence) or not 0 <= args.confidence <= 1:
        parser.error("--confidence must be between 0 and 1")
    return args


def simulated_frame(cv2, width, height, elapsed):
    import numpy as np
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    x = int(width * (0.5 + 0.15 * math.sin(elapsed)))
    cv2.rectangle(frame, (x - width // 12, height // 3),
                  (x + width // 12, height - 15), (80, 120, 180), -1)
    cv2.circle(frame, (x, height // 4), max(1, height // 15), (80, 120, 180), -1)
    return frame


def run(args):
    video = args.mode != "serial"
    cv2 = load_cv2() if video else None
    title = "Doorway Sentinel - Q / Esc to exit"
    try:
        with ExitStack() as stack:
            sensor = None
            if args.mode != "camera":
                sensor = stack.enter_context(SerialReader(
                    args.serial_port, args.baud, args.stale_after,
                    mock=args.mock_serial or args.mode == "simulate"))
            camera = None
            if args.mode in ("combined", "camera"):
                camera = stack.enter_context(Camera(CameraConfig(
                    args.camera_index, args.width, args.height, args.fps, args.backend), cv2))
            detector = None
            if args.detector != "none":
                from hub.detector import DetectionWorker, MobileNetSSD
                detector = stack.enter_context(DetectionWorker(
                    MobileNetSSD(args.models_dir, args.confidence, cv2)))
            started = time.monotonic()
            last_report = -float("inf")
            count = 0
            while args.seconds == 0 or time.monotonic() - started < args.seconds:
                tick = time.monotonic()
                detections, latency, detector_status = (), None, "off"
                frame = None
                if video:
                    frame = (camera.read() if camera else
                             simulated_frame(cv2, args.width, args.height, tick - started))
                    captured_at = time.monotonic()
                    count += 1
                    if detector:
                        if (count - 1) % args.detect_every == 0:
                            detector.submit(frame, captured_at)
                        result, detector_status = detector.snapshot(args.detection_stale_after)
                        if result:
                            detections, latency = result.detections, result.latency_ms
                        if detector_status.startswith("error"):
                            raise RuntimeError(detector_status)
                    if args.mode == "simulate":
                        detector_status = "simulated person (no inference)"
                snapshot = sensor.snapshot() if sensor else SensorSnapshot(None, "disabled")
                if args.headless or not video:
                    if tick - last_report >= 0.2:
                        reading = snapshot.measurement
                        print(json.dumps({
                            "mode": args.mode, "distance_cm": snapshot.distance_cm,
                            "sensor_status": snapshot.status,
                            "sensor_timestamp": reading.timestamp.isoformat() if reading else None,
                            "person_count": 1 if args.mode == "simulate" else len(detections),
                            "detector_status": detector_status, "inference_ms": latency,
                        }), flush=True)
                        last_report = tick
                else:
                    for detection in detections:
                        x1, y1, x2, y2 = detection.box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"person {detection.confidence:.2f}",
                                    (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5, (0, 255, 0), 1)
                    elapsed = max(time.monotonic() - started, 0.001)
                    source = "SIMULATION" if args.mode == "simulate" else f"Camera {args.camera_index}"
                    serial_source = "MOCK" if args.mock_serial or args.mode == "simulate" else "USB"
                    lines = [f"{source} | {frame.shape[1]}x{frame.shape[0]} | {count / elapsed:.1f} FPS",
                             f"{distance_label(snapshot)} [{serial_source}]" if sensor else "Sensor disabled",
                             f"Detection: {detector_status}"]
                    if latency is not None:
                        lines.append(f"CPU inference: {latency:.1f} ms")
                    for index, line in enumerate(lines):
                        position = (10, 25 + index * 24)
                        cv2.putText(frame, line, position, cv2.FONT_HERSHEY_SIMPLEX,
                                    0.52, (0, 0, 0), 3)
                        cv2.putText(frame, line, position, cv2.FONT_HERSHEY_SIMPLEX,
                                    0.52, (0, 255, 255), 1)
                    cv2.imshow(title, frame)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        break
                    if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                        break
                remaining = 1 / (args.fps if video else 5) - (time.monotonic() - tick)
                if remaining > 0:
                    time.sleep(remaining)
    finally:
        if cv2 is not None and not args.headless:
            cv2.destroyAllWindows()


def main(argv=None):
    args = parse_args(argv)
    try:
        if args.list_ports:
            for device, description in list_ports():
                print(f"{device}\t{description}")
            return 0
        run(args)
        return 0
    except KeyboardInterrupt:
        return 130
    except (CameraError, ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Hub stopped: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if exc.__class__.__module__.split(".")[0] != "cv2":
            raise
        print(f"OpenCV capture/display failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
