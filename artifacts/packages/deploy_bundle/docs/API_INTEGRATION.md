# API Integration Guide

## Endpoint

```text
POST /api/v1/inspect
```

Example public URL:

```text
https://inspection.example.com/api/v1/inspect
```

## Request Headers

Always send:

```text
Content-Type: application/json
```

If auth is enabled, send one of:

```text
Authorization: Bearer your-token
```

or

```text
X-API-Key: your-token
```

## Request Body

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/path/image.jpg"
}
```

Fields:

- `task_id`: caller-side unique task identifier, returned unchanged
- `image_url`: downloadable image URL visible to the model server

## Success Response

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/path/image.jpg",
  "status": "success",
  "message": "ok",
  "elapsed_ms": 734.15,
  "image": {
    "width": 1120,
    "height": 1494,
    "download_bytes": 276304
  },
  "results": {
    "nest_detection": {
      "task_name": "nest_detection",
      "count": 1,
      "class_counts": {
        "nest": 1
      },
      "detections": []
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
      "detections": []
    }
  }
}
```

## Error Response

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/path/image.jpg",
  "status": "error",
  "message": "missing api token"
}
```

## Python Example

```python
import requests

url = "https://inspection.example.com/api/v1/inspect"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your-token",
}
payload = {
    "task_id": "task-20260315-001",
    "image_url": "https://files.example.com/path/image.jpg",
}
response = requests.post(url, headers=headers, json=payload, timeout=120)
response.raise_for_status()
print(response.json())
```

## curl Example

```bash
curl -X POST "https://inspection.example.com/api/v1/inspect" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-token" \
  -d '{
    "task_id": "task-20260315-001",
    "image_url": "https://files.example.com/path/image.jpg"
  }'
```

## Integration Checklist

- The caller can reach the API domain or IP
- The model server can reach the provided `image_url`
- The caller sends a unique `task_id`
- The caller sends a valid token if auth is enabled
