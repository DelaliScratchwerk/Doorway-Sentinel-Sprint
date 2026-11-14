import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hub.detector import Detection, DetectionResult, DetectionWorker, MobileNetSSD, decode_people


def test_person_filter_threshold_and_clipping():
    rows = [[0, 15, .60, -.1, .1, 1.1, .9],
            [0, 15, .59, 0, 0, 1, 1], [0, 7, .99, 0, 0, 1, 1],
            [0, 15, float("nan"), 0, 0, 1, 1], [0, 15, .9, .8, .8, .1, .1],
            [0, 15, 1.2, 0, 0, 1, 1]]
    assert decode_people(rows, 640, 480) == (Detection((0, 48, 639, 432), .60),)


def test_missing_detections():
    assert decode_people([], 640, 480) == ()


def test_stale_detections_are_hidden_even_if_inference_finished_recently():
    worker = DetectionWorker(Mock(), clock=lambda: 10)
    worker._result = DetectionResult((Detection((1, 2, 3, 4), .9),), 8, 20)
    assert worker.snapshot(stale_after=1)[0] is None
    assert worker.snapshot(stale_after=1)[1] == "stale"


def wait_until(predicate):
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if predicate():
            return
        threading.Event().wait(0.005)
    assert predicate()


def test_slow_inference_keeps_only_latest_pending_frame():
    entered, release = threading.Event(), threading.Event()
    seen = []
    class Frame:
        def __init__(self, identity):
            self.identity = identity
        def copy(self):
            return self
    def detect(frame):
        seen.append(frame.identity)
        if frame.identity == 1:
            entered.set()
            assert release.wait(1)
        return ()
    with DetectionWorker(SimpleNamespace(detect=detect)) as worker:
        worker.submit(Frame(1), time.monotonic())
        assert entered.wait(1)
        worker.submit(Frame(2), time.monotonic())
        worker.submit(Frame(3), time.monotonic())
        assert worker.snapshot()[1] == "warming up"  # Snapshot never waits on inference.
        release.set()
        wait_until(lambda: seen == [1, 3])
        wait_until(lambda: worker.snapshot()[0] is not None)
    assert not worker._thread.is_alive()


def test_worker_failure_visible_without_thread_traceback():
    detector = Mock()
    detector.detect.side_effect = RuntimeError("inference failed")
    with DetectionWorker(detector) as worker:
        worker.submit(Mock(), time.monotonic())
        wait_until(lambda: worker.snapshot()[1].startswith("error"))
        assert "inference failed" in worker.snapshot()[1]
    assert not worker._thread.is_alive()


def test_dnn_forces_cpu_and_uses_bgr_preprocessing(monkeypatch):
    monkeypatch.setattr("hub.detector.verify_models", lambda directory: None)
    cv2 = Mock()
    net = cv2.dnn.readNetFromCaffe.return_value
    net.forward.return_value.reshape.return_value = [[0, 15, .9, .1, .1, .9, .9]]
    detector = MobileNetSSD(cv2=cv2)
    cv2.setNumThreads.assert_called_once_with(0)
    net.setPreferableBackend.assert_called_once_with(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget.assert_called_once_with(cv2.dnn.DNN_TARGET_CPU)
    frame = SimpleNamespace(shape=(480, 640, 3))
    assert len(detector.detect(frame)) == 1
    kwargs = cv2.dnn.blobFromImage.call_args.kwargs
    assert kwargs["size"] == (300, 300)
    assert kwargs["swapRB"] is False
    assert kwargs["scalefactor"] == 1 / 127.5
