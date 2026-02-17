// --- Pin Mapping ---
const int redPin = 5;   
const int greenPin = 6; 
const int bluePin = 3;  
const int powerPin = 4;

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

  digitalWrite(powerPin, HIGH); 
  updateLEDs(0, 0, 0); 
  
  Serial.println("Lumie Hardware Ready. Waiting for commands...");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    // RGB Command
    if (input.startsWith("RGB:")) {
      int r, g, b;
      if (sscanf(input.substring(4).c_str(), "%d,%d,%d", &r, &g, &b) == 3) {
        fadeDuration = 0; // Cancel any active fade
        curR = r; curG = g; curB = b;
        updateLEDs(r, g, b);
      }
    } 
    // Gradient Command
    else if (input.startsWith("GRAD:")) {
      int r1, g1, b1, r2, g2, b2, d;
      if (sscanf(input.substring(5).c_str(), "%d,%d,%d,%d,%d,%d,%d", 
                 &r1, &g1, &b1, &r2, &g2, &b2, &d) == 7) {
        startR = r1; startG = g1; startB = b1;
        targetR = r2; targetG = g2; targetB = b2;
        fadeDuration = d;
        fadeStartTime = millis();
        updateLEDs(startR, startG, startB);
      }
    }
    else if (input == "LIGHT_OFF") {
      fadeDuration = 0;
      updateLEDs(0, 0, 0);
    }
  }

  // 2. The Transition Engine
  if (fadeDuration > 0) {
    unsigned long elapsed = millis() - fadeStartTime;
    
    if (elapsed < (unsigned long)fadeDuration) {
      float progress = (float)elapsed / (float)fadeDuration;
      
      curR = startR + (targetR - startR) * progress;
      curG = startG + (targetG - startG) * progress;
      curB = startB + (targetB - startB) * progress;
      
      updateLEDs((int)curR, (int)curG, (int)curB);
    } else {
      curR = targetR; curG = targetG; curB = targetB;
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