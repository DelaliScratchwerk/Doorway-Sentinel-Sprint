"""CPU-only MobileNet-SSD detector with a latest-frame background worker."""

import math
from pathlib import Path
import threading
import time
from dataclasses import dataclass

from hub.camera import load_cv2
from hub.models import verify_models


@dataclass(frozen=True)
class Detection:
    box: tuple[int, int, int, int]
    confidence: float
    object_class: str = "person"


@dataclass(frozen=True)
class DetectionResult:
    detections: tuple[Detection, ...]
    captured_at: float
    latency_ms: float


def decode_people(rows, width, height, confidence=0.60):
    """Decode SSD [image_id, class_id, score, x1, y1, x2, y2] rows."""
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("Confidence must be between 0 and 1")
    detections = []
    for row in rows:
        if len(row) != 7 or not all(math.isfinite(float(v)) for v in row):
            continue
        _, category, score, x1, y1, x2, y2 = map(float, row)
        if category != 15 or not confidence <= score <= 1:
            continue
        left = max(0, min(width - 1, int(x1 * width)))
        top = max(0, min(height - 1, int(y1 * height)))
        right = max(0, min(width - 1, int(x2 * width)))
        bottom = max(0, min(height - 1, int(y2 * height)))
        if right > left and bottom > top:
            detections.append(Detection((left, top, right, bottom), score))
    return tuple(detections)


class MobileNetSSD:
    def __init__(self, models_dir="models", confidence=0.60, cv2=None):
        if not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        verify_models(models_dir)
        self.cv2 = cv2 if cv2 is not None else load_cv2()
        # GCD ignores positive limits on this Intel build; 0 disables internal
        # OpenCV parallel regions so inference leaves room for capture/display.
        self.cv2.setNumThreads(0)
        self.confidence = confidence
        root = Path(models_dir)
        self.net = self.cv2.dnn.readNetFromCaffe(
            str(root / "deploy.prototxt"), str(root / "mobilenet_iter_73000.caffemodel"))
        self.net.setPreferableBackend(self.cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(self.cv2.dnn.DNN_TARGET_CPU)

    def detect(self, frame):
        blob = self.cv2.dnn.blobFromImage(
            frame, scalefactor=1 / 127.5, size=(300, 300),
            mean=(127.5, 127.5, 127.5), swapRB=False, crop=False)
        self.net.setInput(blob)
        output = self.net.forward()
        return decode_people(output.reshape(-1, 7), frame.shape[1], frame.shape[0], self.confidence)


class DetectionWorker:
    def __init__(self, detector, clock=time.monotonic):
        self.detector, self.clock = detector, clock
        self._condition = threading.Condition()
        self._pending = None
        self._result = None
        self._error = None
        self._stopped = False
        self._thread = None

    def submit(self, frame, captured_at):
        # One replaceable pending frame; inference never builds an unbounded queue.
        image = frame.copy()
        with self._condition:
            if not self._stopped:
                self._pending = (image, captured_at)
                self._condition.notify()

    def snapshot(self, stale_after=1.5):
        with self._condition:
            result, error = self._result, self._error
        if error:
            return None, f"error: {error}"
        if result is None:
            return None, "warming up"
        if self.clock() - result.captured_at > stale_after:
            return None, "stale"
        return result, f"{len(result.detections)} person(s)"

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._stopped or self._pending is not None)
                if self._stopped:
                    return
                frame, captured_at = self._pending
                self._pending = None
            started = self.clock()
            try:
                detections = self.detector.detect(frame)
            except Exception as exc:
                with self._condition:
                    self._error = str(exc)
                return
            result = DetectionResult(tuple(detections), captured_at, (self.clock() - started) * 1000)
            with self._condition:
                self._result = result

    def __enter__(self):
        if self._thread is not None:
            raise RuntimeError("Detector already started")
        self._thread = threading.Thread(target=self._run, name="person-detector", daemon=True)
        self._thread.start()
        return self

    def close(self):
        with self._condition:
            self._stopped = True
            self._pending = None
            self._condition.notify()
        if self._thread:
            self._thread.join(timeout=2)

    def __exit__(self, *_):
        self.close()
