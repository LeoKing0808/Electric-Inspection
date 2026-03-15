from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return float(value)


@dataclass(frozen=True)
class AdapterSettings:
    host: str
    port: int
    api_token: str | None
    public_base_url: str | None
    db_url: str | None
    image_query: str | None
    image_field_encoding: str
    signing_secret: str | None
    default_url_ttl_sec: int
    max_url_ttl_sec: int
    inspection_api_url: str | None
    inspection_api_token: str | None
    request_timeout_sec: float
    log_level: str


def load_settings() -> AdapterSettings:
    public_base_url = (os.getenv("POWER_IMAGE_ADAPTER_PUBLIC_BASE_URL") or "").strip() or None
    db_url = (os.getenv("POWER_IMAGE_ADAPTER_DB_URL") or "").strip() or None
    image_query = (os.getenv("POWER_IMAGE_ADAPTER_IMAGE_QUERY") or "").strip() or None
    signing_secret = (os.getenv("POWER_IMAGE_ADAPTER_SIGNING_SECRET") or "").strip() or None
    inspection_api_url = (os.getenv("POWER_IMAGE_ADAPTER_INSPECTION_API_URL") or "").strip() or None
    inspection_api_token = (os.getenv("POWER_IMAGE_ADAPTER_INSPECTION_API_TOKEN") or "").strip() or None

    return AdapterSettings(
        host=os.getenv("POWER_IMAGE_ADAPTER_HOST", "0.0.0.0"),
        port=_env_int("POWER_IMAGE_ADAPTER_PORT", 8001),
        api_token=(os.getenv("POWER_IMAGE_ADAPTER_API_TOKEN") or "").strip() or None,
        public_base_url=public_base_url,
        db_url=db_url,
        image_query=image_query,
        image_field_encoding=os.getenv("POWER_IMAGE_ADAPTER_IMAGE_FIELD_ENCODING", "binary").strip().lower(),
        signing_secret=signing_secret,
        default_url_ttl_sec=_env_int("POWER_IMAGE_ADAPTER_DEFAULT_URL_TTL_SEC", 300),
        max_url_ttl_sec=_env_int("POWER_IMAGE_ADAPTER_MAX_URL_TTL_SEC", 3600),
        inspection_api_url=inspection_api_url,
        inspection_api_token=inspection_api_token,
        request_timeout_sec=_env_float("POWER_IMAGE_ADAPTER_REQUEST_TIMEOUT", 120.0),
        log_level=os.getenv("POWER_IMAGE_ADAPTER_LOG_LEVEL", "INFO").upper(),
    )
