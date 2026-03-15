# Deployment Guide

## 1. Server Requirements

- Python 3.10 or newer
- PyTorch build that matches the server CPU or GPU
- Access from the model server to the remote `image_url`
- Access from the caller to this API service

## 2. Install

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure

Set the base environment variables:

```bash
export POWER_INSPECTION_HOST=127.0.0.1
export POWER_INSPECTION_PORT=8000
export POWER_INSPECTION_API_TOKEN=replace-with-a-long-random-token
```

Optional model overrides:

```bash
export POWER_INSPECTION_NEST_WEIGHTS=/opt/power-inspection/nest_detection/weights/best.pt
export POWER_INSPECTION_TOWER_WEIGHTS=/opt/power-inspection/tower_tilt_detection/runs/detect/tower_detector/weights/best.pt
export POWER_INSPECTION_TOWER_THRESHOLDS=/opt/power-inspection/tower_tilt_detection/runs/tilt_calibration/thresholds.json
```

## 4. Start Service

Direct start:

```bash
python run_service.py
```

Linux background service:

1. Copy `deploy/systemd/power-inspection.service` to `/etc/systemd/system/`
2. Copy `deploy/systemd/power-inspection.env.example` to `/opt/power-inspection/deploy/systemd/power-inspection.env`
3. Adjust paths, user, and token
4. Run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable power-inspection
sudo systemctl start power-inspection
sudo systemctl status power-inspection
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\windows\start_service.ps1
```

## 5. Docker

Update `.env.example` with your own values, then run:

```bash
docker compose up -d --build
```

The provided container setup:

- exposes `8000`
- writes logs to `./logs`
- installs CPU PyTorch inside the image

## 6. Nginx Reverse Proxy

Use `deploy/nginx/power_inspection.conf` as a template.

Typical flow:

- caller -> Nginx 80/443
- Nginx -> local service `127.0.0.1:8000`

For internet-facing deployments, terminate HTTPS at Nginx.

## 7. Health Check

```bash
curl http://127.0.0.1:8000/healthz
```

Expected:

- `status=ok`
- `models_loaded=true`
- `auth_enabled=true` if token auth is enabled

## 8. Logs

Default log files:

```text
logs/service.log
logs/audit.log
```

`service.log` is for runtime events and exceptions.
`audit.log` is JSON-lines output for request outcomes.

## 9. Production Notes

- Keep the model service on an internal port and expose only Nginx
- Use a strong token if third parties can access the API
- Ensure the model server can fetch the remote image URL
- If the image source requires custom headers or signed URLs, extend `power_inspection/downloader.py`
- If inference concurrency grows, deploy one process per GPU or pin workers per machine
