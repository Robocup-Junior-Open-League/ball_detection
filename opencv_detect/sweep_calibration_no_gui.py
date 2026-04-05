import cv2
import numpy as np
import sys
import time
import tty
import termios
import select
from picamera2 import Picamera2

# =============================================================================
#  HIER DEINE STARTWERTE EINGEBEN
# =============================================================================
LOWER_START = np.array([5, 150, 200])
UPPER_START = np.array([22, 255, 255])

# Sweep-Bereich: +/- um die Startwerte
SWEEP_RANGE = 20
SWEEP_STEP  = 2
# =============================================================================

GRID_W, GRID_H = 40, 20

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (320, 240)}
))
picam2.start()
time.sleep(1)

def get_frame():
    frame = picam2.capture_array()
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Fix: RGB→BGR

def show_radar(lower, upper, label):
    frame = get_frame()
    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask  = cv2.inRange(hsv, lower, upper)
    hits  = int(np.sum(mask > 0))
    small = cv2.resize(mask, (GRID_W, GRID_H), interpolation=cv2.INTER_NEAREST)

    sys.stdout.write("\033[H\033[J")
    print("=" * (GRID_W * 2))
    print(f" HSV TUNER — {label}")
    print("=" * (GRID_W * 2))
    print(f" Lower: H={lower[0]:3d}  S={lower[1]:3d}  V={lower[2]:3d}")
    print(f" Upper: H={upper[0]:3d}  S={upper[1]:3d}  V={upper[2]:3d}")
    print(f" Pixel erkannt: {hits:5d}   {'✓ BALL GEFUNDEN' if hits > 200 else '✗ kein Ball'}")
    print("-" * (GRID_W * 2))
    for y in range(GRID_H):
        row = ""
        for x in range(GRID_W):
            row += "██" if small[y, x] > 0 else "  "
        print(row)
    print("-" * (GRID_W * 2))
    print(" [SPACE/ENTER] = Approve   [s] = Skip   [q] = Beenden")
    print("=" * (GRID_W * 2))
    return hits

def wait_for_key():
    """Wartet auf Tastendruck, gibt Zeichen zurück."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def sweep_param(name, lower, upper, channel, is_lower, center):
    """Sweept einen Parameter um den Startwert. Gibt approved Wert zurück."""
    values = list(range(
        max(0, center - SWEEP_RANGE),
        min(255 if channel > 0 else 179, center + SWEEP_RANGE + 1),
        SWEEP_STEP
    ))

    approved = center
    for val in values:
        if is_lower:
            lower[channel] = val
        else:
            upper[channel] = val

        show_radar(lower, upper, f"Sweep {name}: {val}")
        time.sleep(0.25)

        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        if rlist:
            key = wait_for_key()
            if key in (' ', '\r', '\n'):
                approved = val
                print(f"\n✓ {name} = {val} approved!")
                time.sleep(0.5)
                return approved
            elif key == 's':
                return center  # Skip → Startwert behalten
            elif key == 'q':
                return None

    # Kein Approve während Sweep → besten Wert (center) behalten
    print(f"\n→ Kein Approve — behalte Startwert {center}")
    time.sleep(1)
    return center


# ── Phase 0: Startwerte anzeigen ──────────────────────────────────────────────
lower = LOWER_START.copy()
upper = UPPER_START.copy()

print("Zeige Startwerte — drücke ENTER zum Starten des Sweeps...")
show_radar(lower, upper, "STARTWERTE")
input()

# ── Sweep ─────────────────────────────────────────────────────────────────────
phases = [
    ("Lower-H", 0, True,  LOWER_START[0]),
    ("Upper-H", 0, False, UPPER_START[0]),
    ("Lower-S", 1, True,  LOWER_START[1]),
    ("Lower-V", 2, True,  LOWER_START[2]),
]

for name, channel, is_lower, center in phases:
    result = sweep_param(name, lower, upper, channel, is_lower, center)
    if result is None:
        picam2.stop()
        sys.exit()
    if is_lower:
        lower[channel] = result
    else:
        upper[channel] = result

# ── Ergebnis ──────────────────────────────────────────────────────────────────
sys.stdout.write("\033[H\033[J")
print("=" * 55)
print(" ✓ KALIBRIERUNG ABGESCHLOSSEN!")
print("=" * 55)
print(f"\nLOWER_ORANGE = ({lower[0]}, {lower[1]}, {lower[2]})")
print(f"UPPER_ORANGE = ({upper[0]}, {upper[1]}, {upper[2]})\n")

with open("hsv_approved.txt", "w") as f:
    f.write(f"LOWER_ORANGE = ({lower[0]}, {lower[1]}, {lower[2]})\n")
    f.write(f"UPPER_ORANGE = ({upper[0]}, {upper[1]}, {upper[2]})\n")
print("Gespeichert in: hsv_approved.txt")
print("=" * 55)

show_radar(lower, upper, "FINALES ERGEBNIS")
input("\nDrücke ENTER zum Beenden.")
picam2.stop()
