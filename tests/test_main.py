from contextlib import contextmanager
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hub.main import distance_label, main, parse_args
from hub.serial_reader import Measurement, SensorSnapshot
from datetime import datetime, timezone


@pytest.mark.parametrize("argv", [[], ["--mode", "serial"],
    ["--mode", "camera", "--mock-serial"], ["--mode", "simulate", "--fps", "nan"],
    ["--mode", "simulate", "--seconds", "-1"],
    ["--mode", "simulate", "--detector", "mobilenet-ssd"],
    ["--mode", "camera", "--confidence", "1.1"],
    ["--mode", "camera", "--detect-every", "0"]])
def test_cli_rejects_ambiguous_or_invalid_config(argv):
    with pytest.raises(SystemExit) as exc:
        parse_args(argv)
    assert exc.value.code == 2


def test_initial_camera_index_one_is_configurable():
    assert parse_args(["--mode", "camera"]).camera_index == 1
    assert parse_args(["--mode", "camera", "--camera-index", "3"]).camera_index == 3


def test_stale_distance_is_never_displayed_as_numeric():
    reading = Measurement(datetime.now(timezone.utc), 30, 0)
    assert "30.0 cm" in distance_label(SensorSnapshot(reading, "valid"))
    assert "-- cm (stale)" in distance_label(SensorSnapshot(reading, "stale"))


@pytest.fixture
def video_env(monkeypatch):
    events = []
    cv2 = Mock()
    cv2.waitKey.return_value = ord("q")
    frame = SimpleNamespace(shape=(480, 640, 3))
    camera = Mock()
    camera.read.return_value = frame
    @contextmanager
    def capture(config, module):
        events.append(("camera-open", config.index))
        try:
            yield camera
        finally:
            events.append("camera-closed")
    @contextmanager
    def sensor(*args, **kwargs):
        events.append("sensor-open")
        try:
            yield SimpleNamespace(snapshot=lambda: SensorSnapshot(None, "disconnected"))
        finally:
            events.append("sensor-closed")
    monkeypatch.setattr("hub.main.load_cv2", lambda: cv2)
    monkeypatch.setattr("hub.main.Camera", capture)
    monkeypatch.setattr("hub.main.SerialReader", sensor)
    monkeypatch.setattr("hub.main.simulated_frame", lambda *args: frame)
    return cv2, camera, events


def test_combined_renders_despite_unavailable_serial(video_env):
    cv2, camera, events = video_env
    assert main(["--mock-serial"]) == 0
    camera.read.assert_called_once()
    cv2.imshow.assert_called_once()
    assert any("disconnected" in str(call) for call in cv2.putText.call_args_list)
    assert ("camera-open", 1) in events
    assert events[-2:] == ["camera-closed", "sensor-closed"]
    cv2.destroyAllWindows.assert_called_once()


def test_display_exception_closes_both_sources(video_env):
    cv2, _, events = video_env
    cv2.imshow.side_effect = RuntimeError("display failure")
    assert main(["--mock-serial"]) == 1
    assert events[-2:] == ["camera-closed", "sensor-closed"]
    cv2.destroyAllWindows.assert_called_once()


def test_simulation_opens_no_camera(video_env):
    cv2, _, events = video_env
    assert main(["--mode", "simulate"]) == 0
    assert not any(isinstance(e, tuple) and e[0] == "camera-open" for e in events)
    cv2.imshow.assert_called_once()


def test_serial_only_never_loads_opencv(monkeypatch, capsys):
    monkeypatch.setattr("hub.main.load_cv2", lambda: pytest.fail("serial must not load cv2"))
    assert main(["--mode", "serial", "--mock-serial", "--seconds", "0.25"]) == 0
    reports = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert any(r["distance_cm"] is not None for r in reports)
    assert all(r["mode"] == "serial" for r in reports)
