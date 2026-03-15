# Power Inspection Service

This project combines two existing models into one HTTP service:

- `nest_detection`: bird nest detection on power towers
- `tower_tilt_detection`: tower body tilt estimation

The service accepts:

```json
{
  "task_id": "task-001",
  "image_url": "https://example.com/demo.jpg"
}
```

The service returns JSON with:

- the original `task_id`
- nest detection results
- tower tilt detection results
- image metadata and elapsed time

## Project Layout

- `nest_detection/`: original bird nest model and desktop demo
- `tower_tilt_detection/`: original tower tilt training and inference code
- `power_inspection/`: new unified service layer
- `run_service.py`: service entry point

## Environment Setup

Install a PyTorch build that matches your server first, then install the rest:

```bash
pip install -r requirements.txt
```

If your server already has `torch`, `opencv-python`, and `ultralytics`, you can start directly.

## Start Service

Run from the project root:

```bash
python run_service.py
```

Default bind:

- `host=0.0.0.0`
- `port=8000`

You can override them with environment variables:

```bash
set POWER_INSPECTION_HOST=0.0.0.0
set POWER_INSPECTION_PORT=8000
python run_service.py
```

Optional auth:

```bash
set POWER_INSPECTION_API_TOKEN=replace-with-a-long-random-token
python run_service.py
```

Logs are written to `logs/service.log` and `logs/audit.log` by default.

Docker quick start:

```bash
docker compose up -d --build
```

## API

### Health Check

```bash
curl http://127.0.0.1:8000/healthz
```

### Inspection API

```bash
curl -X POST http://127.0.0.1:8000/api/v1/inspect ^
  -H "Content-Type: application/json" ^
  -d "{\"task_id\":\"task-001\",\"image_url\":\"https://example.com/demo.jpg\"}"
```

If auth is enabled, send either `Authorization: Bearer <token>` or `X-API-Key: <token>`.

## Example Response

```json
{
  "task_id": "task-001",
  "image_url": "https://example.com/demo.jpg",
  "status": "success",
  "message": "ok",
  "elapsed_ms": 512.67,
  "image": {
    "width": 1280,
    "height": 720,
    "download_bytes": 183245
  },
  "results": {
    "nest_detection": {
      "task_name": "nest_detection",
      "count": 1,
      "class_counts": {
        "nest": 1
      },
      "detections": [
        {
          "nest_id": 1,
          "class_id": 0,
          "class_name": "nest",
          "confidence": 0.9342,
          "bbox": {
            "x1": 322,
            "y1": 108,
            "x2": 418,
            "y2": 186
          }
        }
      ]
    },
    "tower_tilt_detection": {
      "task_name": "tower_tilt_detection",
      "count": 1,
      "warning_threshold_deg": 12.0058,
      "critical_threshold_deg": 20.384,
      "summary": {
        "normal": 1,
        "warning": 0,
        "critical": 0,
        "unreliable": 0
      },
      "detections": [
        {
          "tower_id": 1,
          "status": "normal",
          "detector_confidence": 0.9721,
          "tilt_confidence": 0.9012,
          "apparent_tilt_deg": 4.3281,
          "abs_apparent_tilt_deg": 4.3281,
          "centerline_points": 116,
          "mean_residual_px": 5.3312,
          "bbox": {
            "x1": 104,
            "y1": 51,
            "x2": 537,
            "y2": 703
          }
        }
      ]
    }
  }
}
```

## Default Model Files

The service uses the bundled weights by default:

- nest detection: `nest_detection/weights/best.pt`
- tower tilt detection: `tower_tilt_detection/runs/detect/tower_detector/weights/best.pt`
- tower thresholds: `tower_tilt_detection/runs/tilt_calibration/thresholds.json`

If deployment paths differ, override them with environment variables:

```bash
set POWER_INSPECTION_NEST_WEIGHTS=D:\models\nest_best.pt
set POWER_INSPECTION_TOWER_WEIGHTS=D:\models\tower_best.pt
set POWER_INSPECTION_TOWER_THRESHOLDS=D:\models\thresholds.json
python run_service.py
```

## Deployment Files

- `deploy/nginx/power_inspection.conf`: Nginx reverse proxy example
- `deploy/systemd/power-inspection.service`: Linux systemd service example
- `deploy/systemd/power-inspection.env.example`: Linux environment file example
- `deploy/windows/start_service.ps1`: Windows startup script
- `deploy/windows/start_service.bat`: Windows batch wrapper
- `Dockerfile`: container image build file
- `docker-compose.yml`: container startup example
- `.env.example`: shared environment template
- `docs/DEPLOYMENT.md`: deployment guide
- `docs/API_INTEGRATION.md`: third-party integration guide

## Implemented Tasks

- bird nest detection
- tower tilt detection

To add more inspection tasks later, extend `power_inspection/pipeline.py` and append new task results under `results`.
