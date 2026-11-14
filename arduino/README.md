# Ultrasonic streaming alternative

The original local sketch `Documents/Arduino/sketch_nov7a/sketch_nov7a.ino`
was inspected without changing it. It declares TRIG=D7, ECHO=D8, uses 9600
baud, and prints human-readable messages. Confirmation that this is the
working UNO R4 WiFi / Freenove shield v1.5 / P7 SONIC sketch is pending.
Do not infer the P7 pin map solely from its connector number.

`ultrasonic_stream/ultrasonic_stream.ino` is a separate, documented alternative.
Its compile-time `PIN_MAPPING_CONFIRMED` guard is initially false. Compare
TRIG_PIN/ECHO_PIN against the actual working sketch, preserve that sketch,
correct the pins if needed, and set the guard true only after confirmation.

Then select **Arduino UNO R4 WiFi** and its USB port in Arduino IDE and verify
and upload manually. Python never flashes firmware. No motors or servos are
controlled. This firmware has not been compiled with the board toolchain or
tested on hardware by Codex.

The output is one ASCII line at 9600 baud approximately every 200 ms:
positive centimeters up to 400.00, or lowercase `nan` when echo times out or
is outside that range. Echo timeout is 30 ms; the remaining delay keeps the
sample period near 5 Hz. No startup/debug messages enter the stream.

After upload, verify the output in Arduino Serial Monitor at 9600 baud, then
**close Serial Monitor/Plotter** before opening the port in Python. Save and
restore the working original sketch if troubleshooting is needed. Record
the upload and measured-distance checks in `docs/verification.md`.
