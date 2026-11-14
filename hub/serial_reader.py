"""Threaded, bounded USB serial input with monotonic freshness and mock data."""

import math
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone


MAX_DISTANCE_CM = 400.0
NUMERIC = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def parse_distance(line):
    """Return centimeters, None for nan; reject malformed/out-of-range lines."""
    if isinstance(line, bytes):
        line = line.decode("ascii")
    text = line.strip()
    if text.lower() == "nan":
        return None
    if not NUMERIC.fullmatch(text):
        raise ValueError("Expected numeric centimeters or nan")
    distance = float(text)
    if not math.isfinite(distance) or not 0 < distance <= MAX_DISTANCE_CM:
        raise ValueError("Distance must be positive and at most 400 cm")
    return distance


@dataclass(frozen=True)
class Measurement:
    timestamp: datetime
    distance_cm: float | None
    received_at: float


@dataclass(frozen=True)
class SensorSnapshot:
    measurement: Measurement | None
    status: str
    error: str | None = None

    @property
    def distance_cm(self):
        if self.status == "valid" and self.measurement is not None:
            return self.measurement.distance_cm
        return None


class LineFramer:
    """Retain fragmented lines; discard oversized lines through their newline."""

    def __init__(self, max_length=64):
        self.max_length = max_length
        self.buffer = bytearray()
        self.discarding = False

    def feed(self, chunk):
        for byte in chunk:
            if byte == 10:
                yield None if self.discarding else bytes(self.buffer)
                self.buffer.clear()
                self.discarding = False
            elif not self.discarding:
                self.buffer.append(byte)
                if len(self.buffer) > self.max_length:
                    self.buffer.clear()
                    self.discarding = True


def list_ports():
    from serial.tools import list_ports as ports
    return [(p.device, p.description) for p in ports.comports()]


class SerialReader:
    def __init__(self, port=None, baudrate=9600, stale_after=1.0, reconnect_delay=1.0,
                 mock=False, serial_factory=None, clock=time.monotonic):
        if not mock and not port:
            raise ValueError("Select a serial port or enable mock serial")
        if baudrate <= 0 or any(not math.isfinite(v) or v <= 0
                                for v in (stale_after, reconnect_delay)):
            raise ValueError("Baud rate, freshness and reconnect delay must be positive")
        self.port, self.baudrate, self.mock = port, baudrate, mock
        self.stale_after, self.reconnect_delay = stale_after, reconnect_delay
        self._factory, self._clock = serial_factory, clock
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._snapshot = SensorSnapshot(None, "waiting")

    def _set(self, measurement, status, error=None):
        with self._lock:
            self._snapshot = SensorSnapshot(measurement, status, error)

    def snapshot(self):
        with self._lock:
            result = self._snapshot
        if (result.measurement is not None and
                self._clock() - result.measurement.received_at > self.stale_after):
            return SensorSnapshot(None, "stale")
        return result

    def _consume(self, line):
        try:
            distance = parse_distance(line) if line is not None else None
            status = "no echo" if distance is None else "valid"
            if line is None:
                status = "invalid"
        except (ValueError, UnicodeError):
            distance, status = None, "invalid"
        reading = Measurement(datetime.now(timezone.utc), distance, self._clock())
        self._set(reading, status)

    def _run_mock(self):
        values = (b"150", b"120", b"90", b"65", b"48", b"30", b"nan", b"80")
        index = 0
        while not self._stop.is_set():
            self._consume(values[index % len(values)])
            index += 1
            self._stop.wait(0.2)

    def _run(self):
        if self.mock:
            self._run_mock()
            return
        # Import before starting the thread in start(), so missing pyserial is visible.
        factory = self._factory
        while not self._stop.is_set():
            connection = None
            try:
                connection = factory(self.port, baudrate=self.baudrate, timeout=0.1)
                self._set(None, "waiting")
                framer = LineFramer()
                while not self._stop.is_set():
                    chunk = connection.read(64)
                    for line in framer.feed(chunk):
                        self._consume(line)
            except (OSError, ValueError) as exc:
                self._set(None, "disconnected", str(exc))
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except OSError:
                        pass
            self._stop.wait(self.reconnect_delay)

    def start(self):
        if self._thread is not None:
            raise RuntimeError("Reader already started")
        if not self.mock and self._factory is None:
            import serial
            self._factory = serial.Serial
        self._thread = threading.Thread(target=self._run, name="ultrasonic-serial", daemon=True)
        self._thread.start()
        return self

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()
