from __future__ import annotations

import json
import logging
import threading
from logging.handlers import RotatingFileHandler
from typing import Any

from power_inspection.config import Settings


_AUDIT_LOCK = threading.Lock()


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_power_inspection_configured", False):
        return

    settings.audit_log_dir.mkdir(parents=True, exist_ok=True)
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        settings.audit_log_dir / "service.log",
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger._power_inspection_configured = True  # type: ignore[attr-defined]


def write_audit_log(settings: Settings, record: dict[str, Any]) -> None:
    if not settings.audit_log_enabled:
        return

    settings.audit_log_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with _AUDIT_LOCK:
        with (settings.audit_log_dir / "audit.log").open("a", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
