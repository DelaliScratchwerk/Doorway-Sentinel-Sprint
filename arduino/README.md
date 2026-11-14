# Ultrasonic streaming alternative

The original local sketch `Documents/Arduino/sketch_nov7a/sketch_nov7a.ino`
was inspected without changing it. It declares TRIG=D7, ECHO=D8, uses 9600
baud, and prints human-readable messages. The operator confirmed that this is
the working UNO R4 WiFi / Freenove shield v1.5 / P7 SONIC sketch.
Do not infer the P7 pin map solely from its connector number.

`Documents/Arduino/motion_detection_sim/motion_detection_sim.ino` is a separate
LED matrix animation and serial `M` command simulation, as confirmed by the
operator. Both original files remain untouched.

`ultrasonic_stream/ultrasonic_stream.ino` is a separate, documented alternative.
It preserves the confirmed TRIG=D7 / ECHO=D8 mapping and is ready for manual
verification and upload. Preserve the original diagnostic sketch separately.

Then select **Arduino UNO R4 WiFi** and its USB port in Arduino IDE and verify
and upload manually. Python never flashes firmware. No motors or servos are
controlled. Codex compiled this sketch successfully using the installed
Arduino CLI 1.5.1 and `arduino:renesas_uno:unor4wifi` core 1.6.0: 52,672
bytes flash and 6,740 bytes RAM. No upload or physical sensor test was
performed; those remain manual operator steps.

The output is one ASCII line at 9600 baud approximately every 200 ms:
positive centimeters up to 400.00, or lowercase `nan` when echo times out or
is outside that range. Echo timeout is 30 ms; the remaining delay keeps the
sample period near 5 Hz. No startup/debug messages enter the stream.

After upload, verify the output in Arduino Serial Monitor at 9600 baud, then
**close Serial Monitor/Plotter** before opening the port in Python. Save and
restore the working original sketch if troubleshooting is needed. Record
the upload and measured-distance checks in `docs/verification.md`.
