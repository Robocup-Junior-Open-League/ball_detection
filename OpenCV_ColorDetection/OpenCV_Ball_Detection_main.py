import cv2
import numpy as np
import json
import time
import sys
import math

# --- KAMERA & KONSTANTEN ---
cap = cv2.VideoCapture(0)
frame_w, frame_h = 320, 240
cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_w)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_h)

Bw_deg = 62.2  # FOV der Pi Kamera
DEADZONE_PIXELS = 20

# Das Raster für die JSON-Übertragung
GRID_W = 40
GRID_H = 20

# Deine ermittelten HSV-Werte
h_min, h_max = 3, 23
s_min, s_max = 56, 165
v_min, v_max = 220, 255
lower_bound = np.array([h_min, s_min, v_min])
upper_bound = np.array([h_max, s_max, v_max])

print("Starte Telemetrie-Radar... (STRG+C zum Beenden)")
time.sleep(2)

try:
    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. Hochauflösende Maske erstellen
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Rauschen leicht filtern
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=1)

        # --- TELEMETRIE VARIABLEN INITIALISIEREN ---
        dist_cm = 0.0
        error_x = 0
        error_y = 0  # <--- NEU: Y-Positionsabweichung
        command = "SUCHE"
        quality_pct = 0.0

        # 2. PRÄZISE BERECHNUNGEN (auf dem Originalbild)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            if area > 50:
                ((cx, cy), radius) = cv2.minEnclosingCircle(largest_contour)
                
                # A) Distanz berechnen (-2.1 cm Radius-Korrektur)
                opx = radius * 2.0
                Ow_rad = math.radians((Bw_deg / frame_w) * opx)
                if Ow_rad > 0:
                    dist_cm = max(0.0, (21.0 / math.tan(Ow_rad / 2.0)) / 10.0 - 2.1)
                
                # B) Lenk-Positionierung berechnen (X und Y)
                error_x = int(cx - (frame_w / 2.0))
                error_y = int(cy - (frame_h / 2.0)) # <--- NEU: Y-Abweichung zur Mitte
                
                if error_x < -DEADZONE_PIXELS: command = "LINKS"
                elif error_x > DEADZONE_PIXELS: command = "RECHTS"
                else: command = "GERADEAUS"
                
                # C) Prozentanteil (Qualität) berechnen
                circle_area = math.pi * (radius ** 2)
                if circle_area > 0:
                    quality_pct = min(100.0, (area / circle_area) * 100.0)

        # 3. AUF RASTER VEREINFACHEN (für die Übertragung)
        small_mask = cv2.resize(mask, (GRID_W, GRID_H), interpolation=cv2.INTER_NEAREST)
        y_coords, x_coords = np.where(small_mask > 0)
        
        # 4. JSON ZUSAMMENBAUEN
        payload = {
            "telemetry": {
                "status": command,
                "distance_cm": round(dist_cm, 1),
                "error_x": error_x,
                "error_y": error_y,  # <--- NEU: Y mit ins JSON gepackt
                "quality_pct": round(quality_pct, 1)
            },
            "pixels": {}
        }
        
        for i in range(len(x_coords)):
            payload["pixels"][f"p{i+1}"] = [int(x_coords[i]), int(y_coords[i])]

        json_output = json.dumps(payload)

        # ==========================================
        # LIVE TERMINAL OUTPUT (Das SSH-Radar)
        # ==========================================
        sys.stdout.write("\033[H\033[J") # Terminal sauber wischen
        
        print(f"JSON Payload: {len(json_output)} Bytes gesendet.")
        print("-" * (GRID_W * 2))

        # Das ASCII-Radar zeichnen
        for y in range(GRID_H):
            row_str = ""
            for x in range(GRID_W):
                if small_mask[y, x] > 0:
                    row_str += "██"
                else:
                    row_str += "  "
            print(row_str)
            
        print("-" * (GRID_W * 2))
        
        # Die Telemetrie-Daten direkt unterm Radar anzeigen (mit Error-Y)
        if command != "SUCHE":
            print(f" [!] BALL ERKANNT | Qualitaet: {quality_pct:.1f}%")
            print(f" ->  Cmd: {command:<10} | Dist: {dist_cm:>5.1f} cm | Err_X: {error_x:>4} px | Err_Y: {error_y:>4} px")
        else:
            print(" [?] SUCHE BALL...")

        time.sleep(0.1) # Max. 10 FPS reichen für das Radar völlig

except KeyboardInterrupt:
    print("\nRadar beendet.")
finally:
    cap.release()