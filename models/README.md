# CPU detector assets

The optional detector uses **MobileNet-SSD (Caffe, VOC person class 15)**
through the installed OpenCV DNN module. Input is BGR, resized to 300x300,
scaled by 1/127.5 with mean 127.5. Default confidence threshold is 0.60.

The original model author is [chuanqi305](https://github.com/chuanqi305/MobileNet-SSD).
The downloader pins revision `bb17b6c3eef36d80be441ae8e5339be66e8e3b7a`,
retrieves `deploy.prototxt`, `mobilenet_iter_73000.caffemodel` (23,306,119
bytes), and `LICENSE`, then checks their SHA-256 hashes from `hub/models.py`.
The upstream license is MIT, copyright 2018 chuanqi305. The downloaded copy
of the license stays with the files. No weights are committed to Git.

```bash
source .venv/bin/activate
python -m hub.models
python -m hub.benchmark --runs 10
python -m hub.main --mode camera --camera-index 1 --detector mobilenet-ssd
```

Downloads are explicit, never automatic during preview or CI. `curl` with
HTTPS/TLS verification is required (provided by macOS). It is used because
the inspected Python.org 3.10 installation lacked a working default CA
configuration. TLS verification is never disabled. Failed downloads do not
replace existing files; SHA-256 is checked both at download and model load.

This is a compatibility-first baseline. [PyTorch's official release notice](https://pytorch.org/blog/pytorch2-2/)
states 2.2.x was the final macOS x64 release. The [Ultralytics installer](https://docs.ultralytics.com/quickstart/)
depends on PyTorch, so installing the latest YOLO stack is not an appropriate
unverified default on this Intel Mac. OpenCV DNN already loads and executes
the small MobileNet model without additional ML packages.

Inference uses the CPU. Internal OpenCV parallelism is disabled with
`setNumThreads(0)` to reduce contention with capture and display. Positive
thread limits were ignored by the installed GCD backend; this setting
reported one thread. Frames are submitted to a background worker every
third captured frame by default. Only the newest pending frame is retained;
results older than 1.5 seconds **from source-frame capture** are hidden.
The bounding boxes can still lag moving people; no tracking is implemented.

Use `--detect-every 5` to reduce load or `--detection-stale-after` to tune
expiry. Inference latency and display FPS are different measurements.
The benchmark uses a black synthetic frame and tests execution/performance,
not accuracy, recall or camera integration. Full simulation uses a drawn
person and synthetic distances; it does not prove model accuracy.
