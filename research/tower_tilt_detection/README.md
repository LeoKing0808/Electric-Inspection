# Tower Tilt Detection

This repository now includes a training-free tower tilt pipeline based on the current YOLO tower boxes.

## What it does

- Detects tower boxes from either:
  - existing YOLO label files, or
  - a trained Ultralytics YOLO model
- Estimates the tower centerline inside each box
- Outputs the apparent tilt angle relative to the image vertical axis
- Saves CSV/JSON results and optional annotated images

## Important limitation

The reported angle is **apparent tilt in the image plane**, not a calibrated physical lean angle.

It is affected by:

- camera tilt
- shooting angle
- perspective distortion
- partial occlusion

If you need true engineering tilt, you still need fixed-camera geometry, IMU/camera pose, or multi-view calibration.

## Quick start with the current dataset

Run directly from the existing labels:

```bash
python tower_tilt_detection.py ^
  --image-dir test/images ^
  --label-dir test/labels ^
  --output-dir runs/tilt_test ^
  --save-vis
```

Outputs:

- `runs/tilt_test/results.csv`
- `runs/tilt_test/results.json`
- `runs/tilt_test/visualizations/*.jpg`

## Recommended workflow for the current data

1. Train a tower detector:

```bash
python train_tower_detector.py --epochs 100 --imgsz 960 --batch 16
```

2. Calibrate apparent-tilt thresholds on `train + valid`:

```bash
python calibrate_tilt_thresholds.py
```

3. Run tilt inference on new images with the trained detector:

```bash
python tower_tilt_detection.py ^
  --image-dir path/to/images ^
  --model runs/detect/tower_detector/weights/best.pt ^
  --threshold-file runs/tilt_calibration/thresholds.json ^
  --output-dir runs/tilt_infer ^
  --save-vis
```

## Using a YOLO detector instead of labels

If you later train a detector, you can switch to model inference:

```bash
python tower_tilt_detection.py ^
  --image-dir path/to/images ^
  --model path/to/best.pt ^
  --threshold-file runs/tilt_calibration/thresholds.json ^
  --output-dir runs/tilt_infer ^
  --save-vis
```

After training, use the exported `best.pt` with the second command above.
