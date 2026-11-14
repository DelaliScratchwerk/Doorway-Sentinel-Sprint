// Alternative to the working sketch; upload manually through Arduino IDE.
// D7/D8 match Documents/Arduino/sketch_nov7a/sketch_nov7a.ino.
// Confirm that this is the tested P7 SONIC sketch before enabling upload.
constexpr bool PIN_MAPPING_CONFIRMED = false;
static_assert(PIN_MAPPING_CONFIRMED,
              "Confirm the working P7 SONIC TRIG/ECHO pins before uploading; see arduino/README.md");
constexpr int TRIG_PIN = 7;
constexpr int ECHO_PIN = 8;
constexpr unsigned long SAMPLE_PERIOD_MS = 200;
constexpr unsigned long ECHO_TIMEOUT_US = 30000;

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
}

void loop() {
  const unsigned long started = millis();
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  const unsigned long duration = pulseIn(ECHO_PIN, HIGH, ECHO_TIMEOUT_US);
  const float distanceCm = duration * 0.0343f / 2.0f;
  if (duration == 0 || distanceCm <= 0.0f || distanceCm > 400.0f) {
    Serial.println("nan");
  } else {
    Serial.println(distanceCm, 2);
  }

  const unsigned long elapsed = millis() - started;
  if (elapsed < SAMPLE_PERIOD_MS) {
    delay(SAMPLE_PERIOD_MS - elapsed);
  }
}
