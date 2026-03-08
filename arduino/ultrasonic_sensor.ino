/*
 * HC-SR04 Ultrasonic Sensor → ROS2 Serial Bridge
 * ------------------------------------------------
 * Wiring:
 *   VCC  → 5V
 *   GND  → GND
 *   TRIG → D9
 *   ECHO → D10
 *
 * Output format (Serial, 115200 baud, ~20 Hz):
 *   DIST:123.45\n   (distance in centimetres, float)
 *   DIST:OUT_OF_RANGE\n  (when >400cm or reading fails)
 */

#define TRIG_PIN 9
#define ECHO_PIN 10
#define BAUD_RATE 115200
#define MEASURE_INTERVAL_MS 50   // 20 Hz

const float MAX_RANGE_CM = 400.0f;
const float MIN_RANGE_CM = 2.0f;

unsigned long lastMeasureTime = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {}           // Wait for USB serial on Leonardo / Micro (safe for Nano)
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
  delay(50);
}

float measureDistanceCm() {
  // Ensure trigger is LOW
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // 10µs HIGH pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Measure echo pulse width (timeout = 30ms → ~510 cm, beyond MAX)
  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);

  if (duration == 0) {
    return -1.0f;  // Timeout / no echo
  }

  // Speed of sound: 343 m/s → 0.0343 cm/µs, round-trip → /2
  float distance = (duration * 0.0343f) / 2.0f;
  return distance;
}

void loop() {
  unsigned long now = millis();
  if (now - lastMeasureTime >= MEASURE_INTERVAL_MS) {
    lastMeasureTime = now;

    float dist = measureDistanceCm();

    if (dist < 0 || dist > MAX_RANGE_CM) {
      Serial.println("DIST:OUT_OF_RANGE");
    } else if (dist < MIN_RANGE_CM) {
      Serial.println("DIST:TOO_CLOSE");
    } else {
      Serial.print("DIST:");
      Serial.println(dist, 2);  // 2 decimal places
    }
  }
}
