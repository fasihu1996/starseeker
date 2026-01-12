#include <WiFiS3.h>
#include <Servo.h>
#include "arduino_secrets.h"

// WiFi
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;
int status = WL_IDLE_STATUS;
WiFiServer server(80);

// Servos
Servo altServo;
Servo aziServo;
const int ALT_PIN = 3;
const int AZI_PIN = 4;
const int LASER_PIN = 6;

// optional: limit angles
const int ALT_MIN_ANGLE = 0;
const int ALT_MAX_ANGLE = 180;
const int AZI_MIN_ANGLE = -90;
const int AZI_MAX_ANGLE = 90;

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; }
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW);

  // Attach servos
  altServo.attach(ALT_PIN);
  aziServo.attach(AZI_PIN);
  altServo.write(0);
  aziServo.write(0);

  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
    while (true);
  }

  String fv = WiFi.firmwareVersion();
  if (fv < WIFI_FIRMWARE_LATEST_VERSION) {
    Serial.println("Please upgrade the firmware");
  }

  // Connect to WiFi
  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to WPA SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(3000);
  }

  delay(3000);
  server.begin();
  printWiFiStatus();
}

void loop() {
  WiFiClient client = server.available();
  if (client) {
    Serial.println("new client");
    String currentLine = "";
    String request = "";

    while (client.connected()) {
      delayMicroseconds(10);
      if (client.available()) {
        char c = client.read();
        request += c;      // collect the full HTTP request header
        Serial.write(c);

        if (c == '\n') {
          // End of headers (blank line)
          if (currentLine.length() == 0) {
            // Parse rotation from request line (first line)
            handleRequest(request);

            // Simple HTTP response
            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: text/plain");
            client.println("Connection: close");
            client.println();
            client.println("OK");
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
    Serial.println("client disconnected");
  }
}

void handleRequest(const String& request) {
  // Find the first line: "GET /?alt=XX&azi=YY HTTP/1.1"
  int firstLineEnd = request.indexOf('\r');
  if (firstLineEnd < 0) return;
  String firstLine = request.substring(0, firstLineEnd);
  Serial.print("First line: ");
  Serial.println(firstLine);

  // Find the path part after "GET "
  int getPos = firstLine.indexOf("GET ");
  if (getPos < 0) return;
  int pathStart = getPos + 4;  // after "GET "
  int pathEnd = firstLine.indexOf(' ', pathStart);
  if (pathEnd < 0) return;
  String path = firstLine.substring(pathStart, pathEnd);
  // path should look like "/?alt=30&azi=120" or "/alt=30&azi=120"
  Serial.print("Path: ");
  Serial.println(path);

  // Strip leading '/'
  if (path.startsWith("/")) {
    path = path.substring(1);
  }

  // now path: "?alt=30&azi=120" or "alt=30&azi=120"
  if (path.startsWith("?")) {
    path = path.substring(1);
  }

  // Parse query params
  int altIndex = path.indexOf("alt=");
  int aziIndex = path.indexOf("az=");

  float altVal = NAN;
  float azVal = NAN;

  if (altIndex >= 0) {
    int altValueStart = altIndex + 4;
    int altValueEnd = path.indexOf('&', altValueStart);
    if (altValueEnd < 0) altValueEnd = path.length();
    String altStr = path.substring(altValueStart, altValueEnd);
    altVal = altStr.toFloat();
  }

  if (aziIndex >= 0) {
    int aziValueStart = aziIndex + 3;
    int aziValueEnd = path.indexOf('&', aziValueStart);
    if (aziValueEnd < 0) aziValueEnd = path.length();
    String aziStr = path.substring(aziValueStart, aziValueEnd);
    azVal = aziStr.toFloat();
  }

  Serial.print("Parsed alt: ");
  Serial.print(altVal);
  Serial.print("  az: ");
  Serial.println(azVal);

  // If values valid, move servos (you can clamp or map as needed)
  if (!isnan(altVal)) {
    int altAngle = constrain((int)altVal, ALT_MIN_ANGLE, ALT_MAX_ANGLE);
    Serial.print("Setting ALT servo to ");
    Serial.println(altAngle);
    altServo.write(altAngle);
  }

  if (!isnan(azVal)) {
    int aziAngle = constrain((int)azVal, AZI_MIN_ANGLE, AZI_MAX_ANGLE);
    Serial.print("Setting AZI servo to ");
    Serial.println(aziAngle);
    aziServo.write(aziAngle);
    digitalWrite(LASER_PIN, HIGH);
  }
}

void printWiFiStatus() {
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);
  Serial.print("Send commands to: http://");
  Serial.println(ip);
}
