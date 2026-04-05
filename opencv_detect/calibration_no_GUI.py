import cv2
import numpy as np
import time
import sys

# --- KAMERA INITIALISIERUNG (Picamera2 mit Windows-Fallback) ---
RES_W, RES_H = 320, 240
GRID_W, GRID_H = 30, 30

picam2 = None
cap = None

try:
    from picamera2 import Picamera2
    picam2 = Picamera2()
    # GPU zwingen, das Bild sofort klein zu machen
    config = picam2.create_video_configuration(main={"size": (RES_W, RES_H), "format": "BGR888"})
    picam2.configure(config)
    picam2.start()
    print("[+] Picamera2 erfolgreich gestartet (Hardware-Modus).")
except Exception as e:
    print(f"[-] Picamera2 nicht gefunden. Wechsle zu USB-Webcam (Windows/Fallback)...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RES_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RES_H)
    if not cap.isOpened():
        print("FEHLER: Keine Kamera gefunden!")
        sys.exit(1)

def get_frame():
    """Liest ein Bild ein, egal welche Kamera gerade aktiv ist."""
    if picam2 is not None:
        return True, picam2.capture_array()
    elif cap is not None:
        ret, frame = cap.read()
        if ret:
            # Hardware-Ignoranz-Schutz für Webcams
            frame = cv2.resize(frame, (RES_W, RES_H), interpolation=cv2.INTER_NEAREST)
        return ret, frame
    return False, None

def extract_ball_pixels(frame, rough_lower, rough_upper):
    """Findet den Ball und gibt alle H, S und V Pixel innerhalb des Kreises zurück."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, rough_lower, rough_upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours: return None, None, None
        
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 50: return None, None, None
        
    ((cx, cy), radius) = cv2.minEnclosingCircle(largest)
    safe_radius = int(radius * 0.85) # Um 15% verkleinern
    
    if safe_radius <= 0: return None, None, None

    ball_mask = np.zeros(frame.shape[:2], dtype="uint8")
    cv2.circle(ball_mask, (int(cx), int(cy)), safe_radius, 255, -1)
    
    h_chan, s_chan, v_chan = cv2.split(hsv)
    return h_chan[ball_mask==255], s_chan[ball_mask==255], v_chan[ball_mask==255]

print("\n" + "="*55)
print(" RASPBERRY PI - INTERAKTIVE KALIBRIERUNG")
print("="*55)
time.sleep(1)

# Standard-Startwerte
rough_lower = np.array([0, 80, 80])
rough_upper = np.array([30, 255, 255])

# ==============================================================================
# PHASE 1: INTERAKTIVE VOR-KALIBRIERUNG
# ==============================================================================
while True:
    print("\n" + "-"*55)
    print(f"AKTUELLE GROBE HSV-WERTE:")
    print(f"LOWER: {rough_lower}")
    print(f"UPPER: {rough_upper}")
    input("\n>>> Halte den Ball vor die Kamera und druecke ENTER fuer ein Test-Foto... ")

    # Puffer leeren, damit wir ein aktuelles Bild haben
    for _ in range(5): get_frame()
    ret, frame = get_frame()
    
    if not ret:
        print("FEHLER: Konnte kein Bild aufnehmen!")
        continue

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, rough_lower, rough_upper)
    small_mask = cv2.resize(mask, (GRID_W, GRID_H), interpolation=cv2.INTER_NEAREST)
    
    sys.stdout.write("\033[H\033[J") # Terminal leeren
    print("--- TEST RADAR ---")
    for y in range(GRID_H):
        row_str = ""
        for x in range(GRID_W):
            row_str += "██" if small_mask[y, x] > 0 else "  "
        print(row_str)
    print("------------------")

    h_p, s_p, v_p = extract_ball_pixels(frame, rough_lower, rough_upper)
    if h_p is not None and len(h_p) > 0:
        print(f"[+] Ball erkannt! ({len(h_p)} Pixel im Zentrum)")
    else:
        print("[-] ACHTUNG: Ball wurde nicht sauber erkannt. Radar leer oder verrauscht.")

    print("\nBist du mit dem Radar zufrieden? (Zeigt es einen klaren Kreis?)")
    ans = input("Tippe 'j' fuer OK, oder 'n' um die HSV-Werte zu aendern: ").strip().lower()
    
    if ans == 'j' or ans == 'y':
        break
    else:
        print("\nGib die neuen Werte ein (3 Zahlen mit Leerzeichen getrennt, z.B. 5 100 100).")
        try:
            l_in = input("Neues LOWER HSV: ")
            u_in = input("Neues UPPER HSV: ")
            l_vals = [int(x) for x in l_in.split()]
            u_vals = [int(x) for x in u_in.split()]
            if len(l_vals) == 3 and len(u_vals) == 3:
                rough_lower = np.array(l_vals)
                rough_upper = np.array(u_vals)
                print("[+] Werte uebernommen!")
            else:
                print("[-] Fehlerhafte Eingabe. Behalte alte Werte.")
        except Exception:
            print("[-] Fehlerhafte Eingabe. Behalte alte Werte.")

# ==============================================================================
# PHASE 2: AUTOMATISCHE FEIN-KALIBRIERUNG (10 BILDER)
# ==============================================================================
print("\n" + "="*55)
print(" GROBE WERTE BESTAETIGT. STARTE FEIN-KALIBRIERUNG...")
print("="*55)
time.sleep(2)

medians_H, medians_S, medians_V = [], [], []
TOTAL_FRAMES = 10   
frames_taken = 0

try:
    while frames_taken < TOTAL_FRAMES:
        
        # --- LIVE-VORSCHAU PHASE (3 Sekunden) ---
        start_time = time.time()
        while time.time() - start_time < 3.0:
            ret, frame = get_frame()
            if not ret: continue
            
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, rough_lower, rough_upper)
            small_mask = cv2.resize(mask, (GRID_W, GRID_H), interpolation=cv2.INTER_NEAREST)
            
            sys.stdout.write("\033[H\033[J")
            print(f"FOTO {frames_taken + 1} VON {TOTAL_FRAMES} WIRD VORBEREITET...")
            countdown = 3.0 - (time.time() - start_time)
            print(f"Naechstes Bild in: {countdown:.1f} Sekunden (Bewege den Ball leicht)")
            print("-" * (GRID_W * 2))
            
            for y in range(GRID_H):
                row_str = ""
                for x in range(GRID_W):
                    row_str += "██" if small_mask[y, x] > 0 else "  "
                print(row_str)
            print("-" * (GRID_W * 2))
            time.sleep(0.1) 

        # --- FOTO SCHIESSEN ---
        for _ in range(5): get_frame() # Puffer leeren
        ret, frame = get_frame()
        
        h_p, s_p, v_p = extract_ball_pixels(frame, rough_lower, rough_upper)
        
        if h_p is not None and len(h_p) > 0:
            med_h, med_s, med_v = np.median(h_p), np.median(s_p), np.median(v_p)
            medians_H.append(med_h)
            medians_S.append(med_s)
            medians_V.append(med_v)
            frames_taken += 1
            print(f"\n[+] KLICK! Werte von {len(h_p)} Pixeln im Kreis analysiert (H:{med_h:.1f} S:{med_s:.1f} V:{med_v:.1f})")
            time.sleep(1.5)
        else:
            print("\n[!] FEHLER: Ball beim Klick nicht gefunden! Versuche es nochmal.")
            time.sleep(2)

    # --- FINALE BERECHNUNG ---
    sys.stdout.write("\033[H\033[J")
    final_h, final_s, final_v = int(np.mean(medians_H)), int(np.mean(medians_S)), int(np.mean(medians_V))

    # Toleranzen (Hier kannst du anpassen, wie strikt der Filter sein soll)
    tol_h, tol_s, tol_v = 10, 60, 60

    lower_bound = np.array([max(0, final_h - tol_h), max(0, final_s - tol_s), max(0, final_v - tol_v)])
    upper_bound = np.array([min(179, final_h + tol_h), min(255, final_s + tol_s), min(255, final_v + tol_v)])

    print("="*55)
    print(" KALIBRIERUNG ERFOLGREICH BEENDET!")
    print("="*55)
    print("Kopiere diese perfekten Werte in dein node_prod_vision.py Skript:\n")
    print(f"LOWER_ORANGE = ({lower_bound[0]}, {lower_bound[1]}, {lower_bound[2]})")
    print(f"UPPER_ORANGE = ({upper_bound[0]}, {upper_bound[1]}, {upper_bound[2]})\n")
    print("="*55)

finally:
    # Sauberes Beenden der Kameras (wichtig, damit sie beim nächsten Start nicht blockieren)
    if picam2 is not None:
        picam2.stop()
    if cap is not None:
        cap.release()