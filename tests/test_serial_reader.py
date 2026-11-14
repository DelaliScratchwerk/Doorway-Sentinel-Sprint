import threading
import time

import pytest

from hub.serial_reader import LineFramer, SerialReader, parse_distance


@pytest.mark.parametrize("line,expected", [(b"125.40\r\n", 125.4), (" 50 ", 50),
                                           ("0.1", 0.1), ("400", 400), ("1e2", 100)])
def test_parse_valid(line, expected):
    assert parse_distance(line) == expected


@pytest.mark.parametrize("line", ["", "garbage", "Distance: 25 cm", "-1", "0", "401",
                                  "inf", "-inf", "1e999", "1_000", b"\xff"])
def test_parse_invalid(line):
    with pytest.raises((ValueError, UnicodeError)):
        parse_distance(line)


def test_no_echo():
    assert parse_distance(b"nan\r\n") is None


def test_framing_fragmented_and_oversized_lines():
    framer = LineFramer(max_length=6)
    assert list(framer.feed(b"12.")) == []
    assert list(framer.feed(b"5\r\n40\n")) == [b"12.5\r", b"40"]
    assert list(framer.feed(b"x" * 100)) == []
    assert len(framer.buffer) == 0
    assert list(framer.feed(b"12\n35\n")) == [None, b"35"]


def test_snapshot_freshness_and_utc():
    now = [10.0]
    reader = SerialReader(mock=True, stale_after=1, clock=lambda: now[0])
    reader._consume(b"50")
    snapshot = reader.snapshot()
    assert snapshot.distance_cm == 50
    assert snapshot.measurement.timestamp.utcoffset().total_seconds() == 0
    now[0] = 11.0
    assert reader.snapshot().distance_cm == 50
    now[0] = 11.001
    assert reader.snapshot().status == "stale"
    assert reader.snapshot().distance_cm is None


@pytest.mark.parametrize("line,status", [(b"nan", "no echo"), (b"hello", "invalid"),
                                       (None, "invalid")])
def test_invalid_replaces_previous_valid(line, status):
    reader = SerialReader(mock=True)
    reader._consume(b"25")
    reader._consume(line)
    assert reader.snapshot().status == status
    assert reader.snapshot().distance_cm is None


def wait_until(predicate, timeout=1):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        threading.Event().wait(0.005)
    assert predicate(), "Worker did not reach expected state"


class FakeConnection:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.closed = False

    def read(self, size):
        chunk = next(self.chunks, b"")
        if isinstance(chunk, Exception):
            raise chunk
        threading.Event().wait(0.005)
        return chunk

    def close(self):
        self.closed = True


def test_disconnect_clears_reading_then_reconnects():
    first = FakeConnection([b"35\n", OSError("USB removed")])
    second = FakeConnection([b"80\n"])
    attempts = []
    def factory(*args, **kwargs):
        attempts.append(args)
        return first if len(attempts) == 1 else second
    with SerialReader(port="fake", serial_factory=factory, reconnect_delay=0.1) as reader:
        wait_until(lambda: reader.snapshot().status == "disconnected")
        assert reader.snapshot().distance_cm is None
        assert "USB removed" in reader.snapshot().error
        wait_until(lambda: reader.snapshot().distance_cm == 80)
    assert first.closed and second.closed
    assert not reader._thread.is_alive()


def test_missing_device_retries_and_can_stop():
    attempted = threading.Event()
    def factory(*args, **kwargs):
        attempted.set()
        raise OSError("missing")
    with SerialReader(port="absent", serial_factory=factory, reconnect_delay=0.01) as reader:
        assert attempted.wait(1)
        wait_until(lambda: reader.snapshot().status == "disconnected")
    assert not reader._thread.is_alive()


def test_timeout_does_not_erase_fresh_reading_but_eventually_stales():
    connection = FakeConnection([b"23", b".4\n"])
    with SerialReader(port="fake", serial_factory=lambda *a, **k: connection,
                      stale_after=0.1) as reader:
        wait_until(lambda: reader.snapshot().distance_cm == 23.4)
        wait_until(lambda: reader.snapshot().status == "stale")
        assert reader.snapshot().distance_cm is None


def test_mock_needs_no_serial_port():
    with SerialReader(mock=True) as reader:
        wait_until(lambda: reader.snapshot().distance_cm is not None)
    assert not reader._thread.is_alive()


def test_real_pyserial_loopback_without_hardware():
    serial = pytest.importorskip("serial")
    connection = serial.serial_for_url("loop://", timeout=0.05)
    with SerialReader(port="loop", serial_factory=lambda *a, **k: connection) as reader:
        connection.write(b"123.45\nnan\n48.2\n")
        wait_until(lambda: reader.snapshot().distance_cm == 48.2)
    assert not connection.is_open
