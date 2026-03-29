import cv2
import numpy as np
import time

def extract_ball_pixels(frame, rough_lower, rough_upper):
    """
    Findet den Ball anhand der groben Werte und gibt alle H, S und V Pixel zurück.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, rough_lower, rough_upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, None, None
        
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 100:
        return None, None, None
        
    # Schablone in Form des Balls erstellen
    ball_mask = np.zeros(frame.shape[:2], dtype="uint8")
    cv2.drawContours(ball_mask, [largest], -1, 255, -1)
    
    # Bild in HSV-Kanäle aufteilen und nur die Ball-Pixel extrahieren
    h_chan, s_chan, v_chan = cv2.split(hsv)
    return h_chan[ball_mask==255], s_chan[ball_mask==255], v_chan[ball_mask==255]

# --- KAMERA STARTEN ---
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

print("\n" + "="*55)
print(" RASPBERRY PI ZERO - REINE HSV-KALIBRIERUNG (10 BILDER)")
print("="*55)
time.sleep(2)

input(">>> Halte den Ball vor die Kamera und druecke ENTER... ")

# DEINE GROBEN STARTWERTE (Damit das Skript den Ball überhaupt erst findet)
rough_lower = np.array([3, 56, 220])
rough_upper = np.array([23, 165, 255])

medians_H, medians_S, medians_V = [], [], []
TOTAL_FRAMES = 10   
frames_taken = 0

print(f"\n[+] Starte Aufnahme von genau {TOTAL_FRAMES} Bildern...\n")

while frames_taken < TOTAL_FRAMES:
    # Puffer leeren, damit wir ein absolut aktuelles Bild bekommen
    for _ in range(5): cap.read() 
    
    ret, frame = cap.read()
    if not ret: 
        print("Fehler beim Lesen der Kamera!")
        break
    
    h_p, s_p, v_p = extract_ball_pixels(frame, rough_lower, rough_upper)
    
    if h_p is not None:
        # Median dieses Bildes berechnen und speichern
        med_h = np.median(h_p)
        med_s = np.median(s_p)
        med_v = np.median(v_p)
        
        medians_H.append(med_h)
        medians_S.append(med_s)
        medians_V.append(med_v)
        frames_taken += 1
        
        print(f"    [OK] Foto {frames_taken}/{TOTAL_FRAMES} im Kasten! (H:{med_h:.1f} S:{med_s:.1f} V:{med_v:.1f})")
        
        # 5 Sekunden Pause (außer nach dem allerletzten Bild)
        if frames_taken < TOTAL_FRAMES:
            print("         Bewege den Ball leicht. Naechstes Foto in:")
            for sec in range(5, 0, -1):
                print(f"         {sec} Sekunden... ", end="\r")
                time.sleep(1)
            print("         *Klick* ", end="\r")
            
    else:
        print(f"    [!] Kein Ball gefunden! Halte ihn ins Bild...{' '*10}", end="\r")
        time.sleep(0.5)

# Das finale Ergebnis berechnen (Durchschnitt aus den 10 Bildern)
if len(medians_H) > 0:
    final_h = np.mean(medians_H)
    final_s = np.mean(medians_S)
    final_v = np.mean(medians_V)

    # --- TOLERANZEN UM DEN PERFEKTEN MITTELWERT LEGEN ---
    tol_h = 8   # +/- 8 für den exakten Farbton Orange
    tol_s = 55  # +/- 55 für Sättigung (erlaubt Schatten)
    tol_v = 55  # +/- 55 für Helligkeit (erlaubt Reflexionen)

    final_h, final_s, final_v = int(final_h), int(final_s), int(final_v)

    # Grenzen berechnen und sicherstellen, dass sie in OpenCVs 0-255 (bzw 0-179 für H) bleiben
    final_lower = np.array([max(0, final_h - tol_h), max(0, final_s - tol_s), max(0, final_v - tol_v)])
    final_upper = np.array([min(179, final_h + tol_h), min(255, final_s + tol_s), min(255, final_v + tol_v)])

    print("\n\n" + "="*55)
    print(f" KALIBRIERUNG BEENDET!")
    print(f" Durchschnittliche Basiswerte: H={final_h}, S={final_s}, V={final_v}")
    print("-" * 55)
    print(f" KOPIERE DIESE WERTE IN DEIN HAUPTSKRIPT:")
    print(f" H_MIN = {final_lower[0]:<3} | H_MAX = {final_upper[0]:<3}")
    print(f" S_MIN = {final_lower[1]:<3} | S_MAX = {final_upper[1]:<3}")
    print(f" V_MIN = {final_lower[2]:<3} | V_MAX = {final_upper[2]:<3}")
    print("="*55 + "\n")

cap.release()