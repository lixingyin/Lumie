// --- Pin Mapping ---
const int redPin = 5;   
const int greenPin = 6; 
const int bluePin = 3;  
const int powerPin = 4;

const int trigPin = 10;  
const int echoPin = 11;

unsigned long lastSensorRead = 0;
const int sensorInterval = 200;

// --- Transition Variables ---
float curR = 0, curG = 0, curB = 0;
int startR, startG, startB;
int targetR, targetG, targetB;
unsigned long fadeStartTime;
int fadeDuration = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(redPin, OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin, OUTPUT);
  pinMode(powerPin, OUTPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  digitalWrite(powerPin, HIGH); 
  updateLEDs(0, 0, 0); 
  
  Serial.println("Lumie Hardware Ready. Waiting for commands...");
}

void loop() {
  // 1. Read Commands from Python
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    handleCommands(input);
  }

  // 2. The Transition Engine (LED Fading)
  updateFade();

  // 3. The Sensor Engine (New)
  if (millis() - lastSensorRead >= sensorInterval) {
    readUltrasonic();
    lastSensorRead = millis();
  }
}

void readUltrasonic() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 30000);
  int distance = (duration / 2) / 29.1;

  if (distance > 0 && distance < 100) { 
    Serial.print("DIST:");
    Serial.println(distance);
  }
}

void handleCommands(String input) {
  if (input.startsWith("RGB:")) {
    int r, g, b;
    if (sscanf(input.substring(4).c_str(), "%d,%d,%d", &r, &g, &b) == 3) {
      fadeDuration = 0;
      curR = r; curG = g; curB = b;
      updateLEDs(r, g, b);
    }
  } 
  else if (input.startsWith("GRAD:")) {
    int r1, g1, b1, r2, g2, b2, d;
    if (sscanf(input.substring(5).c_str(), "%d,%d,%d,%d,%d,%d,%d", 
               &r1, &g1, &b1, &r2, &g2, &b2, &d) == 7) {
      startR = r1; startG = g1; startB = b1;
      targetR = r2; targetG = g2; targetB = b2;
      fadeDuration = d;
      fadeStartTime = millis();
    }
  }
}

void updateFade() {
  if (fadeDuration > 0) {
    unsigned long elapsed = millis() - fadeStartTime;
    if (elapsed < (unsigned long)fadeDuration) {
      float progress = (float)elapsed / (float)fadeDuration;
      curR = startR + (targetR - startR) * progress;
      curG = startG + (targetG - startG) * progress;
      curB = startB + (targetB - startB) * progress;
      updateLEDs((int)curR, (int)curG, (int)curB);
    } else {
      updateLEDs(targetR, targetG, targetB);
      fadeDuration = 0; 
    }
  }
}

// Helper to handle the Inverted Logic 
// Assuming 255 is OFF and 0 is FULL ON
void updateLEDs(int r, int g, int b) {
  analogWrite(redPin, 255 - r);
  analogWrite(greenPin, 255 - g);
  analogWrite(bluePin, 255 - b);
}