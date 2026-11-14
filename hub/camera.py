"""Independent OpenCV camera check. Does not record frames or require Arduino."""

import argparse
import importlib
import json
import math
import subprocess
import sys
import time
from dataclasses import dataclass


class CameraError(RuntimeError):
    """An actionable capture failure."""


def load_cv2():
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise CameraError(
            "OpenCV is unavailable. Activate .venv and run "
            "python -m pip install --only-binary=:all: -r requirements.txt"
        ) from exc


@dataclass(frozen=True)
class CameraConfig:
    index: int
    width: int = 640
    height: int = 480
    fps: float = 10.0
    backend: str = "auto"

    def __post_init__(self):
        if self.index < 0 or self.width <= 0 or self.height <= 0:
            raise ValueError("Camera index must be >= 0; dimensions must be positive.")
        if not math.isfinite(self.fps) or self.fps <= 0:
            raise ValueError("FPS must be finite and positive.")
        if self.backend not in ("auto", "avfoundation", "any"):
            raise ValueError("Unsupported camera backend.")


class Camera:
    def __init__(self, config, cv2=None):
        self.config = config
        self.cv2 = cv2 if cv2 is not None else load_cv2()
        self.capture = None

    def __enter__(self):
        cv2 = self.cv2
        backend = self.config.backend
        if backend == "auto":
            backend = "avfoundation" if sys.platform == "darwin" else "any"
        api = cv2.CAP_AVFOUNDATION if backend == "avfoundation" else cv2.CAP_ANY
        try:
            self.capture = cv2.VideoCapture(self.config.index, api)
            if not self.capture.isOpened():
                raise CameraError(f"Camera index {self.config.index} could not be opened.")
            # Backends may ignore these requests; report actual frame dimensions.
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.capture.set(cv2.CAP_PROP_FPS, self.config.fps)
            return self
        except BaseException:
            self.close()
            raise

    def read(self, timeout=3.0):
        deadline = time.monotonic() + timeout
        while True:
            ok, frame = self.capture.read()
            if ok and frame is not None and frame.size > 0:
                return frame
            if time.monotonic() >= deadline:
                raise CameraError("No readable frames: camera may be busy or disconnected.")
            time.sleep(0.05)

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def __exit__(self, *_):
        self.close()


def inspect_camera(config, cv2=None):
    with Camera(config, cv2) as camera:
        frame = camera.read()
        return {
            "index": config.index,
            "readable": True,
            "width": int(frame.shape[1]),
            "height": int(frame.shape[0]),
            "backend": camera.capture.getBackendName(),
        }


def probe_index(config, timeout=12.0):
    """Isolate each native capture probe so a stalled backend can be terminated."""
    command = [
        sys.executable, "-m", "hub.camera", "--check", "--camera-index", str(config.index),
        "--width", str(config.width), "--height", str(config.height),
        "--fps", str(config.fps), "--backend", config.backend,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"index": config.index, "readable": False, "error": "Capture probe timed out."}
    try:
        report = json.loads(result.stdout)
        if result.returncode == 0 and report.get("readable") is True:
            return report
    except (ValueError, AttributeError):
        pass
    detail = result.stderr.strip() or result.stdout.strip() or "Capture process failed."
    return {"index": config.index, "readable": False, "error": detail[-1500:]}


def preview(config, seconds=0.0, cv2=None):
    cv2 = cv2 if cv2 is not None else load_cv2()
    title = f"Doorway Sentinel - camera {config.index} (Q / Esc to exit)"
    try:
        with Camera(config, cv2) as camera:
            started = time.monotonic()
            count = 0
            while seconds == 0 or time.monotonic() - started < seconds:
                tick = time.monotonic()
                frame = camera.read()
                count += 1
                elapsed = max(time.monotonic() - started, 0.001)
                label = f"index {config.index} | {frame.shape[1]}x{frame.shape[0]} | {count / elapsed:.1f} FPS"
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, (0, 255, 0), 1)
                cv2.imshow(title, frame)
                delay = max(1, int((1 / config.fps - (time.monotonic() - tick)) * 1000))
                if cv2.waitKey(delay) & 0xFF in (ord("q"), 27):
                    break
                if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
    finally:
        cv2.destroyAllWindows()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="Probe candidate indices in separate processes")
    mode.add_argument("--check", action="store_true", help="Read one frame and print JSON; no window")
    mode.add_argument("--preview", action="store_true", help="Show live frames; Q / Esc exits")
    parser.add_argument("--camera-index", type=int, help="Explicit index required for check or preview")
    parser.add_argument("--max-index", type=int, default=5, help="Last candidate for --list, inclusive (default: 5)")
    parser.add_argument("--backend", choices=("auto", "avfoundation", "any"), default="auto")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--seconds", type=float, default=0, help="Preview duration; 0 runs until closed")
    parser.add_argument("--probe-timeout", type=float, default=12, help="Seconds per isolated list probe")
    args = parser.parse_args(argv)
    if not args.list and args.camera_index is None:
        parser.error("--camera-index is required; do not assume Camo is index 0")
    if args.max_index < 0 or not math.isfinite(args.seconds) or args.seconds < 0:
        parser.error("--max-index and --seconds must be nonnegative and finite")
    if not math.isfinite(args.probe_timeout) or args.probe_timeout <= 0:
        parser.error("--probe-timeout must be finite and positive")
    try:
        config = CameraConfig(args.camera_index if args.camera_index is not None else 0,
                              args.width, args.height, args.fps, args.backend)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        if args.list:
            load_cv2()  # Fail once with installation advice rather than once per index.
            reports = []
            for index in range(args.max_index + 1):
                candidate = CameraConfig(index, args.width, args.height, args.fps, args.backend)
                report = probe_index(candidate, args.probe_timeout)
                reports.append(report)
                print(json.dumps(report), flush=True)
            return 0 if any(r["readable"] for r in reports) else 1
        if args.check:
            print(json.dumps(inspect_camera(config)))
        else:
            preview(config, args.seconds)
        return 0
    except KeyboardInterrupt:
        return 130
    except (CameraError, OSError, RuntimeError) as exc:
        print(f"Camera check failed: {exc}", file=sys.stderr)
        print("Keep Camo Studio open; check macOS Camera permissions for the launching app. "
              "See camera/README.md.", file=sys.stderr)
        return 1
    except Exception as exc:
        # Native OpenCV errors have a separate exception type, loaded only at runtime.
        if exc.__class__.__module__.split(".")[0] != "cv2":
            raise
        print(f"OpenCV capture/display failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
