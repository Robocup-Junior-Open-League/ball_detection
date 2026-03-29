import cv2
import numpy as np
import math
import time

# ==========================================
# 1. KONFIGURATION & KONSTANTEN
# ==========================================

# --- KAMERA SPEZIFIKATIONEN (Raspberry Pi Cam V2) ---
BW_DEG = 62.2               # Horizontaler Bildwinkel in Grad
RES_WIDTH = 640             # Auflösung Breite
RES_HEIGHT = 480            # Auflösung Höhe
CENTER_X = RES_WIDTH / 2.0  # Die "Nase" des Roboters

# --- FARB-FILTER (HSV) ---
# Trage hier die exakten Werte ein, die ihr mit dem Slider-Skript gefunden habt!
# Beispiel-Werte für ein typisches Orange:
LOWER_ORANGE = np.array([3, 54, 205])
UPPER_ORANGE = np.array([19, 154, 255])

# --- STEUERUNG ---
DEADZONE_PIXELS = 40        # Toleranzbereich in der Mitte (in Pixeln)
MIN_RADIUS = 5              # Minimaler Ball-Radius (filtert Rauschen)

# ==========================================
# 2. INITIALISIERUNG
# ==========================================

print("Starte Headless Vision System (RCJ Main Loop)...")

# Kamera starten
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RES_HEIGHT)

# Timer für die 1-Sekunden-Ausgabe
last_print_time = time.time()

# ==========================================
# 3. HAUPTSCHLEIFE (Main Loop)
# ==========================================

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("FEHLER: Kameraverbindung verloren!")
            break

        # 1. Bildverarbeitung
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_frame, LOWER_ORANGE, UPPER_ORANGE)
        
        # Rauschfilter (Erosion & Dilation)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # 2. Konturen finden
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Standard-Werte, falls kein Ball gefunden wird
        command = "NO BALL"
        distance_cm = 0.0

        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)
            ((x_center, y_center), radius) = cv2.minEnclosingCircle(largest_contour)

            if radius > MIN_RADIUS:
                
                # --- ABSTANDSBERECHNUNG (FOV-Methode) ---
                opx = radius * 2.0
                Ow_deg = (BW_DEG / RES_WIDTH) * opx
                Ow_rad = math.radians(Ow_deg)
                
                if Ow_rad > 0:
                    distance_mm = 21.0 / math.tan(Ow_rad / 2.0)
                    distance_cm = distance_mm / 10.0
                else:
                    distance_cm = 0.0

                # --- LENK-LOGIK ---
                error_x = x_center - CENTER_X
                
                if error_x < -DEADZONE_PIXELS:
                    command = "LEFT"
                elif error_x > DEADZONE_PIXELS:
                    command = "RIGHT"
                else:
                    command = "FORWARD"

        # 3. Ausgabe (nur einmal pro Sekunde, um die Konsole nicht zu überfluten)
        current_time = time.time()
        if current_time - last_print_time >= 1.0:
            if command == "NO BALL":
                print("Status: NO BALL")
            else:
                print(f"Status: {command} | Distanz: {distance_cm:.1f} cm")
            
            last_print_time = current_time

except KeyboardInterrupt:
    print("\nProgramm durch Benutzer beendet (Strg+C).")

# ==========================================
# 4. AUFRÄUMEN
# ==========================================
cap.release()
print("Kamera geschlossen. System gestoppt.")