# 🤖 RoboCup Junior - Vision System (OpenCV & AI)

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![YOLO](https://img.shields.io/badge/AI-YOLO-orange.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Zero-red.svg)

This repository contains the visual detection system for our RoboCup Junior Soccer (Open League) robot. The goal is to detect the orange golf ball reliably and with extremely low latency.

Because our main robot relies on a heavily resource-constrained **Raspberry Pi Zero**, we split our vision research into two distinct approaches:
1. A highly hardware-optimized **OpenCV Pipeline** (our primary competition code).
2. A custom-trained **YOLO AI Model** (for validation, PC testing, and future hardware upgrades).

---

## ⚙️ Installation & Setup

To make setting up the project on a new PC or the Raspberry Pi as easy as possible, we use a central `requirements.txt` file.

You can install all necessary libraries with a single command:

```bash
pip install -r requirements.txt
```

---

## 🏎️ Approach 1: OpenCV (Competition Mode)
Folder: `opencv_detect/`

This is our main competition codebase. It is designed to run completely "headless" (no graphical user interface) on the Raspberry Pi Zero. By heavily downscaling the camera stream (e.g., to `160x120` or `160x90`), it requires minimal CPU resources while maintaining high FPS.

**Key Features**

* **Custom Weights:** Scripts to quickly adapt to the specific lighting conditions of the competition field.
* **Adaptive EMA Smoothing:** An intelligent, lightweight filter that aggressively removes sensor noise but reacts instantly to fast ball movements.
* **SSH/JSON Telemetry:** Broadcasts the calculated distance and steering commands directly to the main `robus-core` redis database.

**Quick Start** 

1. **Run Calibration:** Run the headless calibration script to find the perfect HSV values for the current room lighting:

```bash
python opencv_detect/calibration_no_GUI.py
```

2. **Start Detection:**

Update the HSV bounds in the main script and start the tracking node:

```bash
python opencv_detect/detection_main.py
```

---

## 🧠 Approach 2: YOLO AI Model (Research) ##

Folder: `yolo_model/`

To push the boundaries of our object detection, we trained a custom Neural Network. We annotated hundreds of images of the official orange RoboCup golf ball using Label Studio and trained a YOLO model.

While this model is currently too computationally heavy to run at high framerates on a Pi Zero, it provides incredibly robust detection on a PC—even with occluded balls or severe lighting reflections.

**Key Features**

* **Custom Weights:** The fully trained models are available as `best.pt` and `last.pt` inside `yolo_model/Orange_Ball_Detection/my_model/train/weights/`.
* **Training Data:** Includes `args.yaml`, confusion matrices, and precision-recall curves inside the `train/` directory.
* **Label Studio Backup:** Raw annotations and the Label Studio SQLite database are included for full transparency.

**Quick Start**

To test the AI model live using your PC webcam:

```bash
python yolo_model/Orange_Ball_Detection/my_model/yolo_detect.py
```

(Ensure the path to `best.pt` is set correctly inside the script).

---

## 🏆 Team Documentation ##

This repository is part of our Technical Description Paper (TDP) for the Austrian Open.
