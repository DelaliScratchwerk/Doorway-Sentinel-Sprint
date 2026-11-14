"""Synthetic CPU inference benchmark; does not measure person-detection accuracy."""

import argparse
import json
import statistics
import time

from hub.camera import load_cv2
from hub.detector import MobileNetSSD


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args(argv)
    if args.runs <= 0:
        parser.error("--runs must be positive")
    import numpy as np
    cv2 = load_cv2()
    detector = MobileNetSSD(args.models_dir, cv2=cv2)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detector.detect(frame)  # warmup, excluded
    timings = []
    for _ in range(args.runs):
        started = time.perf_counter()
        detector.detect(frame)
        timings.append((time.perf_counter() - started) * 1000)
    print(json.dumps({"input": "synthetic black 640x480, resized to 300x300",
                      "backend": "OpenCV DNN CPU", "opencv_threads": cv2.getNumThreads(),
                      "runs": args.runs, "median_ms": round(statistics.median(timings), 2),
                      "min_ms": round(min(timings), 2), "max_ms": round(max(timings), 2),
                      "accuracy_tested": False}))


if __name__ == "__main__":
    main()
