from __future__ import annotations

from functools import lru_cache
import json
import logging
from typing import Any

from flask import Flask, Response, jsonify, request
import requests

from enterprise_image_adapter.config import AdapterSettings, load_settings
from enterprise_image_adapter.database import (
    AdapterConfigError,
    DatabaseImageRepository,
    ImageAdapterError,
    ImageNotFoundError,
)
from enterprise_image_adapter.signing import build_signed_image_url, verify_record_signature


def _error_response(message: str, status_code: int, **extra: Any) -> tuple[Response, int]:
    payload = {"status": "error", "message": message, **extra}
    return jsonify(payload), status_code


def _safe_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _extract_api_token() -> str | None:
    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    api_key = request.headers.get("X-API-Key", "").strip()
    return api_key or None


def _check_auth(settings: AdapterSettings) -> tuple[bool, str | None]:
    if not settings.api_token:
        return True, None

    token = _extract_api_token()
    if not token:
        return False, "missing api token"
    if token != settings.api_token:
        return False, "invalid api token"
    return True, None


def _coerce_record_id(value: Any) -> str | None:
    if value is None:
        return None
    record_id = str(value).strip()
    return record_id or None


def _parse_ttl(value: Any, default_ttl: int, max_ttl: int) -> int:
    if value in (None, ""):
        ttl = default_ttl
    else:
        ttl = int(value)
    if ttl <= 0:
        raise ValueError("expires_in_sec must be a positive integer")
    return min(ttl, max_ttl)


def _build_public_base_url(settings: AdapterSettings) -> str:
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return request.host_url.rstrip("/")


def _forward_to_inspection_service(
    settings: AdapterSettings,
    task_id: Any,
    image_url: str,
) -> tuple[dict[str, Any], int]:
    if not settings.inspection_api_url:
        raise AdapterConfigError("POWER_IMAGE_ADAPTER_INSPECTION_API_URL is required for inspect-from-db")

    headers = {"Content-Type": "application/json"}
    if settings.inspection_api_token:
        headers["Authorization"] = f"Bearer {settings.inspection_api_token}"

    try:
        response = requests.post(
            settings.inspection_api_url,
            headers=headers,
            json={"task_id": task_id, "image_url": image_url},
            timeout=settings.request_timeout_sec,
        )
    except requests.RequestException as exc:
        raise ImageAdapterError(f"failed to call inspection service: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ImageAdapterError(
            f"inspection service returned non-json response, status_code={response.status_code}"
        ) from exc

    return payload, response.status_code


@lru_cache(maxsize=1)
def _get_repository() -> DatabaseImageRepository:
    return DatabaseImageRepository(load_settings())


def create_app(settings: AdapterSettings | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False

    if settings is not None:
        _get_repository.cache_clear()

        @lru_cache(maxsize=1)
        def _settings_repository() -> DatabaseImageRepository:
            return DatabaseImageRepository(settings)

        repository_factory = _settings_repository
        active_settings = settings
    else:
        repository_factory = _get_repository
        active_settings = load_settings()

    logging.basicConfig(
        level=getattr(logging, active_settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    @app.get("/")
    def index() -> Any:
        return jsonify(
            {
                "service": "enterprise_image_adapter",
                "status": "running",
                "supported_endpoints": [
                    "/healthz",
                    "/api/v1/image-url",
                    "/api/v1/images/<record_id>",
                    "/api/v1/inspect-from-db",
                ],
            }
        )

    @app.get("/healthz")
    def healthz() -> Any:
        try:
            repository_factory().ping()
        except Exception as exc:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"adapter is not ready: {exc}",
                        "db_url_configured": bool(active_settings.db_url),
                        "image_query_configured": bool(active_settings.image_query),
                        "inspection_forwarding_enabled": bool(active_settings.inspection_api_url),
                    }
                ),
                500,
            )

        return jsonify(
            {
                "status": "ok",
                "db_connected": True,
                "auth_enabled": bool(active_settings.api_token),
                "image_query_configured": bool(active_settings.image_query),
                "inspection_forwarding_enabled": bool(active_settings.inspection_api_url),
            }
        )

    @app.post("/api/v1/image-url")
    def create_image_url() -> Any:
        authorized, auth_error = _check_auth(active_settings)
        if not authorized:
            app.logger.warning("adapter_unauthorized %s", _safe_json({"message": auth_error}))
            return _error_response(auth_error or "unauthorized", 401)

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error_response("request body must be a JSON object", 400)

        record_id = _coerce_record_id(payload.get("record_id"))
        if not record_id:
            return _error_response("record_id is required", 400)

        try:
            expires_in_sec = _parse_ttl(
                payload.get("expires_in_sec"),
                active_settings.default_url_ttl_sec,
                active_settings.max_url_ttl_sec,
            )
            if not active_settings.signing_secret:
                raise AdapterConfigError("POWER_IMAGE_ADAPTER_SIGNING_SECRET is required")

            image_url, expires_at = build_signed_image_url(
                _build_public_base_url(active_settings),
                record_id,
                active_settings.signing_secret,
                expires_in_sec,
            )
        except (AdapterConfigError, ValueError) as exc:
            return _error_response(str(exc), 400)

        result = {
            "status": "success",
            "record_id": record_id,
            "image_url": image_url,
            "expires_at": expires_at,
        }
        app.logger.info("adapter_image_url_created %s", _safe_json(result))
        return jsonify(result)

    @app.get("/api/v1/images/<path:record_id>")
    def download_database_image(record_id: str) -> Any:
        expires_at = request.args.get("expires", type=int)
        signature = (request.args.get("signature") or "").strip()
        if not expires_at or not signature:
            return _error_response("expires and signature are required", 401)
        if not active_settings.signing_secret:
            return _error_response("POWER_IMAGE_ADAPTER_SIGNING_SECRET is required", 500)
        if not verify_record_signature(record_id, expires_at, signature, active_settings.signing_secret):
            return _error_response("invalid or expired signature", 401)

        try:
            image_record = repository_factory().fetch_image(record_id)
        except ImageNotFoundError as exc:
            return _error_response(str(exc), 404, record_id=record_id)
        except (AdapterConfigError, ImageAdapterError) as exc:
            return _error_response(str(exc), 500, record_id=record_id)

        response = Response(
            image_record.image_bytes,
            mimetype=image_record.mime_type or "application/octet-stream",
        )
        if image_record.file_name:
            response.headers["Content-Disposition"] = f'inline; filename="{image_record.file_name}"'
        return response

    @app.post("/api/v1/inspect-from-db")
    def inspect_from_db() -> Any:
        authorized, auth_error = _check_auth(active_settings)
        if not authorized:
            return _error_response(auth_error or "unauthorized", 401)

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _error_response("request body must be a JSON object", 400)

        task_id = payload.get("task_id")
        if task_id is None or (isinstance(task_id, str) and not task_id.strip()):
            return _error_response("task_id is required", 400)

        record_id = _coerce_record_id(payload.get("record_id"))
        if not record_id:
            return _error_response("record_id is required", 400, task_id=task_id)

        try:
            expires_in_sec = _parse_ttl(
                payload.get("expires_in_sec"),
                active_settings.default_url_ttl_sec,
                active_settings.max_url_ttl_sec,
            )
            if not active_settings.signing_secret:
                raise AdapterConfigError("POWER_IMAGE_ADAPTER_SIGNING_SECRET is required")

            image_url, expires_at = build_signed_image_url(
                _build_public_base_url(active_settings),
                record_id,
                active_settings.signing_secret,
                expires_in_sec,
            )
            response_payload, status_code = _forward_to_inspection_service(active_settings, task_id, image_url)
        except (AdapterConfigError, ValueError) as exc:
            return _error_response(str(exc), 400, task_id=task_id, record_id=record_id)
        except ImageAdapterError as exc:
            return _error_response(str(exc), 502, task_id=task_id, record_id=record_id)

        app.logger.info(
            "adapter_inspect_forwarded %s",
            _safe_json(
                {
                    "task_id": task_id,
                    "record_id": record_id,
                    "expires_at": expires_at,
                    "status_code": status_code,
                }
            ),
        )
        return jsonify(response_payload), status_code

    return app
