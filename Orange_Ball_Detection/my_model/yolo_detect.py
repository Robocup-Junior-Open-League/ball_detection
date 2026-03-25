import os
import sys
import argparse
import time
import math

import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--model', help='Path to YOLO model file', required=True)
parser.add_argument('--source', help='Image source ("usb0" for webcam)', required=True)
parser.add_argument('--thresh', help='Minimum confidence', default=0.5)
parser.add_argument('--resolution', help='Resolution in WxH', default=None)
args = parser.parse_args()

model_path = args.model
img_source = args.source
min_thresh = float(args.thresh)
user_res = args.resolution

if not os.path.exists(model_path):
    print('ERROR: Model path is invalid.')
    sys.exit(0)

# --- NVIDIA CUDA SETUP ---
print("Initializing NVIDIA CUDA acceleration...")
if torch.cuda.is_available():
    cuda_device = torch.device('cuda')
    # Print out the exact name of your NVIDIA card
    print(f"✅ Hardware Acceleration Enabled: Using NVIDIA GPU ({torch.cuda.get_device_name(0)})")
else:
    print("⚠️ NVIDIA CUDA not found! Falling back to CPU.")
    cuda_device = torch.device('cpu')

# Load model
print("Loading model...")
model = YOLO(model_path)
model.to(cuda_device)
labels = model.names
print("Model loaded successfully.")

# Setup Camera
usb_idx = int(img_source.replace('usb', ''))
cap = cv2.VideoCapture(usb_idx, cv2.CAP_DSHOW)

resize = False
if user_res:
    resize = True
    resW, resH = int(user_res.split('x')[0]), int(user_res.split('x')[1])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, resW)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resH)

bbox_colors = [(164,120,87), (68,148,228), (93,97,209), (178,182,133)]
avg_frame_rate = 0
frame_rate_buffer = []

print("Starting inference on NVIDIA GPU. Press 'q' to quit.")

while True:
    t_start = time.perf_counter()
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print('Camera disconnected.')
        break

    if resize:
        frame = cv2.resize(frame, (resW, resH))

    image_height, image_width = frame.shape[:2]

    # Run inference explicitly on the NVIDIA device
    results = model(frame, verbose=False, device=cuda_device)
    detections = results[0].boxes
    object_count = 0

    for i in range(len(detections)):
        conf = detections[i].conf.item()
        
        if conf > min_thresh:
            xyxy = detections[i].xyxy.cpu().numpy().squeeze().astype(int) 
            xmin, ymin, xmax, ymax = xyxy
            classidx = int(detections[i].cls.item())
            classname = labels[classidx]
            
            # --- YOUR EXACT TRIANGLE MATH ---
            # 1. Center of the ball
            x_center = (xmin + xmax) / 2.0
            y_center = (ymin + ymax) / 2.0
            
            # 2. Left middle side of the box
            x_left = float(xmin)
            
            # 3. The point on the bottom of the screen directly below the ball
            x_bottom = x_center
            y_bottom = float(image_height)

            # Calculate pixel lengths of the triangle sides
            # Opposite = Base (from center to left side)
            pixel_opposite = x_center - x_left 
            # Adjacent = Height (from center down to the bottom of the frame)
            pixel_adjacent = y_bottom - y_center 

            # Calculate tan(alpha) = Opposite / Adjacent
            if pixel_adjacent > 0:
                tan_alpha = pixel_opposite / pixel_adjacent
                
                # Your formula: 21mm / tan(alpha)
                if tan_alpha > 0:
                    distance_mm = 21.0 / tan_alpha
                else:
                    distance_mm = 0.0
            else:
                distance_mm = 0.0

            distance_cm = distance_mm / 10.0

            # --- VISUALIZATION DRAWING ---
            color = bbox_colors[classidx % len(bbox_colors)]
            cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), color, 2)
            
            # Draw the Triangle you described:
            # 1. Base (Center to Left Side) - Red Line
            cv2.line(frame, (int(x_center), int(y_center)), (int(x_left), int(y_center)), (0, 0, 255), 2)
            # 2. Height (Center straight down to bottom) - Blue Line
            cv2.line(frame, (int(x_center), int(y_center)), (int(x_bottom), int(y_bottom)), (255, 0, 0), 2)
            # 3. Hypotenuse (Left side down to the bottom corner) - Green Line
            cv2.line(frame, (int(x_left), int(y_center)), (int(x_bottom), int(y_bottom)), (0, 255, 0), 2)
            
            # Draw dots at the 3 corners of the triangle
            cv2.circle(frame, (int(x_center), int(y_center)), 5, (0, 255, 255), -1)   # Ball Center
            cv2.circle(frame, (int(x_left), int(y_center)), 5, (0, 255, 255), -1)     # Left Edge
            cv2.circle(frame, (int(x_bottom), int(y_bottom)), 5, (0, 255, 255), -1)   # Bottom Frame (Angle Alpha)

            # Draw labels
            label = f'{classname} | Dist: {distance_cm:.1f} cm'
            cv2.putText(frame, label, (xmin, ymin-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            object_count += 1

    # Draw FPS
    cv2.putText(frame, f'FPS: {avg_frame_rate:0.1f}', (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.imshow('RoboCup Vision (NVIDIA CUDA)', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

    # Calculate FPS
    t_stop = time.perf_counter()
    frame_rate_buffer.append(1/(t_stop - t_start))
    if len(frame_rate_buffer) > 15:
        frame_rate_buffer.pop(0)
    avg_frame_rate = np.mean(frame_rate_buffer)

cap.release()
cv2.destroyAllWindows()