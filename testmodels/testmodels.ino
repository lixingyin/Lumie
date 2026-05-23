#include "WiFiS3.h"

// 1. CREATE YOUR PRIVATE ARDUINO WI-FI HERE
char local_ssid[] = "Lumie-Sensor-Bubble";
char local_pass[] = "123456789"; // Must be at least 8 characters long

int status = WL_IDLE_STATUS;
WiFiServer server(80); // Open standard web server port 80

// Simulated sensor value (replaces with your actual ultrasonic variable later)
float distanceCm = 42.5; 

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; } // Wait for serial monitor

  Serial.println("=== Launching Private Wi-Fi System ===");

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  // Start Broadcasting your own private local Wi-Fi bubble
  Serial.print("Broadcasting network name: ");
  Serial.println(local_ssid);
  
  status = WiFi.beginAP(local_ssid, local_pass);
  if (status != WL_AP_LISTENING) {
    Serial.println("Creating private Access Point failed!");
    while (true);
  }

  // Start the server framework so it listens for your phone's browser requests
  server.begin();

  Serial.println("\n=== Private Bubble Live! ===");
  Serial.println("1. Open your phone's Wi-Fi settings.");
  Serial.println("2. Connect to: 'Lumie-Sensor-Bubble'");
  Serial.println("3. Open Safari/Chrome and type in: http://192.168.4.1");
}

void loop() {
  // Listen for incoming connections from your phone
  WiFiClient client = server.available();
  
  if (client) {
    Serial.println("Phone connected to web server!");
    String currentLine = "";
    
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        
        if (c == '\n') {
          if (currentLine.length() == 0) {
            // Send standard HTTP response headers
            client.println("HTTP/1.1 200 OK");
            client.println("Content-type:text/html");
            client.println("Connection: close");
            client.println("Refresh: 2"); // Automatically auto-refreshes the phone screen every 2 seconds
            client.println();
            
            // Build the clean web page layout for your phone
            client.println("<!DOCTYPE HTML>");
            client.println("<html>");
            client.println("<head><title>Lumie Monitor</title></head>");
            client.println("<body style='font-family: Arial, sans-serif; text-align: center; margin-top: 60px; background-color: #f4f6f9;'>");
            client.println("<div style='display: inline-block; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>");
            client.println("<h1 style='color: #333;'>Lumie Sensor Hub</h1>");
            client.println("<p style='color: #666;'>Direct Microcontroller Stream</p>");
            client.println("<hr style='border: 0; border-top: 1px solid #eee; margin: 20px 0;'>");
            client.println("<div style='font-size: 28px; color: #007aff; margin: 20px 0;'>");
            client.print("Distance: <strong>");
            client.print(distanceCm); 
            client.println(" cm</strong>");
            client.println("</div>");
            client.println("</div>");
            client.println("</body>");
            client.println("</html>");
            break;
          } else {
            currentLine = "";
          }
        } else if (c != '\r') {
          currentLine += c;
        }
      }
    }
    client.stop();
    Serial.println("Phone disconnected.");
  }
}