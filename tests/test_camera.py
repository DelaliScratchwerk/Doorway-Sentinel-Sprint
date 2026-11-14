import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from hub.camera import Camera, CameraConfig, CameraError, inspect_camera, main, preview, probe_index


@pytest.fixture
def cv2():
    frame = SimpleNamespace(size=640 * 480 * 3, shape=(480, 640, 3))
    capture = Mock()
    capture.isOpened.return_value = True
    capture.read.return_value = (True, frame)
    capture.getBackendName.return_value = "AVFOUNDATION"
    module = Mock(CAP_AVFOUNDATION=1200, CAP_ANY=0, CAP_PROP_FRAME_WIDTH=3,
                  CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_FPS=5)
    module.VideoCapture.return_value = capture
    return module


def test_selected_index_and_macos_backend(monkeypatch, cv2):
    monkeypatch.setattr("hub.camera.sys.platform", "darwin")
    report = inspect_camera(CameraConfig(3), cv2)
    cv2.VideoCapture.assert_called_once_with(3, cv2.CAP_AVFOUNDATION)
    assert report == {"index": 3, "readable": True, "width": 640,
                      "height": 480, "backend": "AVFOUNDATION"}
    cv2.VideoCapture.return_value.release.assert_called_once()


def test_unavailable_camera_released(cv2):
    cv2.VideoCapture.return_value.isOpened.return_value = False
    with pytest.raises(CameraError, match="could not be opened"):
        with Camera(CameraConfig(2), cv2):
            pytest.fail("Unavailable capture must not be used")
    cv2.VideoCapture.return_value.release.assert_called_once()


def test_disconnected_camera_released(cv2):
    cv2.VideoCapture.return_value.read.return_value = (False, None)
    with pytest.raises(CameraError, match="disconnected"):
        with Camera(CameraConfig(1), cv2) as camera:
            camera.read(timeout=0)
    cv2.VideoCapture.return_value.release.assert_called_once()


def test_transient_empty_frame_is_retried(cv2):
    frame = SimpleNamespace(size=10, shape=(10, 10, 3))
    cv2.VideoCapture.return_value.read.side_effect = [(False, None), (True, frame)]
    with Camera(CameraConfig(1), cv2) as camera:
        assert camera.read() is frame


def test_list_probe_timeout(monkeypatch):
    def stalled(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr("hub.camera.subprocess.run", stalled)
    assert probe_index(CameraConfig(4), timeout=0.1) == {
        "index": 4, "readable": False, "error": "Capture probe timed out."}


def test_native_probe_failure(monkeypatch):
    monkeypatch.setattr("hub.camera.subprocess.run", lambda *a, **k:
                        SimpleNamespace(returncode=-6, stdout="", stderr="camera busy"))
    assert probe_index(CameraConfig(2))["error"] == "camera busy"


def test_preview_exit_releases_camera_and_windows(cv2):
    cv2.waitKey.return_value = ord("q")
    preview(CameraConfig(2), cv2=cv2)
    cv2.VideoCapture.return_value.release.assert_called_once()
    cv2.destroyAllWindows.assert_called_once()


def test_preview_failure_releases_camera_and_windows(cv2):
    cv2.imshow.side_effect = RuntimeError("display unavailable")
    with pytest.raises(RuntimeError):
        preview(CameraConfig(2), cv2=cv2)
    cv2.VideoCapture.return_value.release.assert_called_once()
    cv2.destroyAllWindows.assert_called_once()


def test_check_requires_explicit_index():
    with pytest.raises(SystemExit) as exc:
        main(["--check"])
    assert exc.value.code == 2


@pytest.mark.parametrize("kwargs", [{"index": -1}, {"index": 0, "width": 0},
                                      {"index": 0, "fps": float("nan")},
                                      {"index": 0, "fps": 0}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        CameraConfig(**kwargs)


def test_list_reports_each_index(monkeypatch, capsys):
    monkeypatch.setattr("hub.camera.load_cv2", lambda: None)
    indices = []
    def probe(config, timeout):
        indices.append(config.index)
        return {"index": config.index, "readable": config.index == 2}
    monkeypatch.setattr("hub.camera.probe_index", probe)
    assert main(["--list", "--max-index", "3"]) == 0
    assert indices == [0, 1, 2, 3]
    assert len(capsys.readouterr().out.splitlines()) == 4


def test_list_fails_when_no_camera_readable(monkeypatch):
    monkeypatch.setattr("hub.camera.load_cv2", lambda: None)
    monkeypatch.setattr("hub.camera.probe_index", lambda c, t: {"index": c.index, "readable": False})
    assert main(["--list", "--max-index", "0"]) == 1
