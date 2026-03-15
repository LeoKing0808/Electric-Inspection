from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    return Path(value).expanduser().resolve()


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    api_token: str | None
    audit_log_enabled: bool
    audit_log_dir: Path
    log_level: str
    log_max_bytes: int
    log_backup_count: int
    max_batch_size: int
    nest_weights: Path
    tower_weights: Path
    tower_threshold_file: Path
    nest_confidence: float
    nest_iou: float
    nest_imgsz: int
    tower_confidence: float
    tower_min_box_height: int
    image_download_timeout_sec: float
    max_image_bytes: int


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("POWER_INSPECTION_HOST", "0.0.0.0"),
        port=int(os.getenv("POWER_INSPECTION_PORT", "8000")),
        api_token=os.getenv("POWER_INSPECTION_API_TOKEN") or None,
        audit_log_enabled=_env_bool("POWER_INSPECTION_AUDIT_LOG_ENABLED", True),
        audit_log_dir=_env_path(
            "POWER_INSPECTION_AUDIT_LOG_DIR",
            ROOT_DIR / "var" / "logs",
        ),
        log_level=os.getenv("POWER_INSPECTION_LOG_LEVEL", "INFO").upper(),
        log_max_bytes=int(os.getenv("POWER_INSPECTION_LOG_MAX_BYTES", str(20 * 1024 * 1024))),
        log_backup_count=int(os.getenv("POWER_INSPECTION_LOG_BACKUP_COUNT", "5")),
        max_batch_size=int(os.getenv("POWER_INSPECTION_MAX_BATCH_SIZE", "16")),
        nest_weights=_env_path(
            "POWER_INSPECTION_NEST_WEIGHTS",
            ROOT_DIR / "models" / "nest_detection" / "best.pt",
        ),
        tower_weights=_env_path(
            "POWER_INSPECTION_TOWER_WEIGHTS",
            ROOT_DIR / "models" / "tower_tilt_detection" / "tower_detector" / "best.pt",
        ),
        tower_threshold_file=_env_path(
            "POWER_INSPECTION_TOWER_THRESHOLDS",
            ROOT_DIR / "models" / "tower_tilt_detection" / "thresholds" / "thresholds.json",
        ),
        nest_confidence=float(os.getenv("POWER_INSPECTION_NEST_CONF", "0.25")),
        nest_iou=float(os.getenv("POWER_INSPECTION_NEST_IOU", "0.45")),
        nest_imgsz=int(os.getenv("POWER_INSPECTION_NEST_IMGSZ", "640")),
        tower_confidence=float(os.getenv("POWER_INSPECTION_TOWER_CONF", "0.25")),
        tower_min_box_height=int(os.getenv("POWER_INSPECTION_TOWER_MIN_BOX_HEIGHT", "40")),
        image_download_timeout_sec=float(os.getenv("POWER_INSPECTION_DOWNLOAD_TIMEOUT", "15")),
        max_image_bytes=int(os.getenv("POWER_INSPECTION_MAX_IMAGE_BYTES", str(20 * 1024 * 1024))),
    )
