# First hands-on gate: Camo → OpenCV

Camo Camera on the iPhone SE (3rd generation) and the Camo Studio 2.9.0
preview already work, as reported by the operator. **The operator subsequently
verified live OpenCV video at index 1 using AVFoundation, 640x480, about 8.4 FPS.**
macOS authorization worked in that launching application. A lens-cover test
is still needed to confirm iPhone identity. A readable built-in camera does
not establish that Camo works. No frames are recorded by these commands.

From the repository root on macOS, activate the environment:

```bash
source .venv/bin/activate
python -m hub.camera --help
python -m hub.camera --list --backend avfoundation --max-index 5
```

Keep the iPhone connected and Camo Studio showing its live feed. macOS may
request camera permission for the launching application (Terminal, VS Code,
or Codex). Allow it in System Settings → Privacy & Security → Camera, then
restart that application if needed. A system permission prompt requires
operator action; the hub does not change privacy settings.

The list command opens candidate indices 0–5 sequentially in isolated
processes. Each gets up to 12 seconds, including startup. Increase
`--probe-timeout 30` if approving a permission prompt takes longer. Increase
`--max-index` if necessary. `readable: true` means an actual frame was read;
the JSON also reports its dimensions and capture backend. OpenCV does not
provide a portable mapping from index to camera name. Identify Camo visually.

For each readable candidate, substitute its index for `N`:

```bash
python -m hub.camera --preview --camera-index N --backend avfoundation --width 640 --height 480 --fps 10 --seconds 20
```

Confirm that the window shows the **iPhone view**, wave a hand in front of
the iPhone lens, and confirm that the movement appears live. Press Q or Esc
to exit early. The window displays index, actual dimensions, and approximate
capture/display FPS; this is not inference performance. Some devices ignore
requested resolution or FPS. Resources are released on normal exit, errors,
or Ctrl-C. A failed read is retried for up to three seconds; native backend
calls can themselves block. List probes have a hard process timeout; if a
preview stalls inside native capture, interrupt it from the terminal.

Record the selected index, actual dimensions, FPS, and outcome in
`docs/verification.md`. Re-probe after reconnecting devices or rebooting;
indices can change. A successful single-frame check alone does not prove
that this is Camo or that the feed remains live.

The reported `AVCaptureDeviceTypeExternal` deprecation warning did not block
the successful preview. Keep this separate from actual capture failures.

If the camera fails:

- Confirm the feed still works inside Camo Studio and check camera permission.
- Close other apps using the virtual camera, leaving Camo Studio running.
- Reconnect the phone and restart Camo Studio and the launching application.
- If another readable index is the built-in camera, test the remaining indices.
- If AVFoundation sees no Camo feed, record the error and investigate Camo's
  virtual-camera compatibility with this macOS installation before proceeding.

Do not flash Arduino firmware or install ML packages to troubleshoot this gate.

References: [OpenCV VideoCapture](https://docs.opencv.org/4.11.0/d8/dfe/classcv_1_1VideoCapture.html)
and the [pinned Intel macOS wheel](https://pypi.org/project/opencv-python/4.11.0.86/).
