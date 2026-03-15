from __future__ import annotations

from functools import lru_cache
import json
import time
from typing import Any

from flask import Flask, jsonify, request

from power_inspection.config import Settings, load_settings
from power_inspection.downloader import ImageDownloadError
from power_inspection.logging_utils import configure_logging, write_audit_log
from power_inspection.pipeline import ModelConfigError, PowerInspectionPipeline


def _error_response(message: str, task_id: Any = None, image_url: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "task_id": task_id,
        "image_url": image_url,
        "status": "error",
        "message": message,
    }
    return payload


def _safe_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    nested = result.get("results", {})
    nest = nested.get("nest_detection", {})
    tower = nested.get("tower_tilt_detection", {})
    tower_summary = tower.get("summary", {})
    return {
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "elapsed_ms": result.get("elapsed_ms"),
        "image_url": result.get("image_url"),
        "nest_count": nest.get("count", 0),
        "tower_count": tower.get("count", 0),
        "tower_warning": tower_summary.get("warning", 0),
        "tower_critical": tower_summary.get("critical", 0),
    }


def _extract_api_token() -> str | None:
    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()

    api_key = request.headers.get("X-API-Key", "").strip()
    return api_key or None


def _check_auth(settings: Settings) -> tuple[bool, str | None]:
    if not settings.api_token:
        return True, None

    token = _extract_api_token()
    if not token:
        return False, "missing api token"
    if token != settings.api_token:
        return False, "invalid api token"
    return True, None


@lru_cache(maxsize=1)
def _get_pipeline() -> PowerInspectionPipeline:
    settings = load_settings()
    return PowerInspectionPipeline(settings)


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False

    if settings is not None:
        _get_pipeline.cache_clear()

        @lru_cache(maxsize=1)
        def _settings_pipeline() -> PowerInspectionPipeline:
            return PowerInspectionPipeline(settings)

        pipeline_factory = _settings_pipeline
        active_settings = settings
    else:
        pipeline_factory = _get_pipeline
        active_settings = load_settings()

    configure_logging(active_settings)

    @app.get("/")
    def index() -> Any:
        return jsonify(
            {
                "service": "power_inspection",
                "status": "running",
                "supported_tasks": ["nest_detection", "tower_tilt_detection"],
                "inspect_endpoint": "/api/v1/inspect",
            }
        )

    @app.get("/healthz")
    def healthz() -> Any:
        try:
            pipeline_factory()
        except Exception as exc:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"service is not ready: {exc}",
                        "nest_weights": str(active_settings.nest_weights),
                        "tower_weights": str(active_settings.tower_weights),
                        "tower_threshold_file": str(active_settings.tower_threshold_file),
                    }
                ),
                500,
            )

        return jsonify(
            {
                "status": "ok",
                "models_loaded": True,
                "auth_enabled": bool(active_settings.api_token),
                "supported_tasks": ["nest_detection", "tower_tilt_detection"],
                "nest_weights": str(active_settings.nest_weights),
                "tower_weights": str(active_settings.tower_weights),
                "tower_threshold_file": str(active_settings.tower_threshold_file),
            }
        )

    @app.post("/api/v1/inspect")
    def inspect() -> Any:
        request_started_at = time.perf_counter()
        authorized, auth_error = _check_auth(active_settings)
        if not authorized:
            audit_payload = {
                "event": "unauthorized_request",
                "path": request.path,
                "remote_addr": request.remote_addr,
                "message": auth_error or "unauthorized",
            }
            app.logger.warning("unauthorized_request %s", _safe_json(audit_payload))
            write_audit_log(active_settings, audit_payload)
            return jsonify(_error_response(auth_error or "unauthorized")), 401

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            audit_payload = {
                "event": "invalid_request_body",
                "path": request.path,
                "remote_addr": request.remote_addr,
                "message": "request body must be a JSON object",
            }
            app.logger.warning("invalid_request_body %s", _safe_json(audit_payload))
            write_audit_log(active_settings, audit_payload)
            return jsonify(_error_response("request body must be a JSON object")), 400

        task_id = payload.get("task_id")
        image_url = str(payload.get("image_url") or "").strip()
        if task_id is None or (isinstance(task_id, str) and not task_id.strip()):
            audit_payload = {
                "event": "missing_task_id",
                "path": request.path,
                "remote_addr": request.remote_addr,
                "image_url": image_url or None,
            }
            app.logger.warning("missing_task_id %s", _safe_json(audit_payload))
            write_audit_log(active_settings, audit_payload)
            return jsonify(_error_response("task_id is required", task_id=task_id, image_url=image_url or None)), 400
        if not image_url:
            audit_payload = {
                "event": "missing_image_url",
                "path": request.path,
                "remote_addr": request.remote_addr,
                "task_id": task_id,
            }
            app.logger.warning("missing_image_url %s", _safe_json(audit_payload))
            write_audit_log(active_settings, audit_payload)
            return jsonify(_error_response("image_url is required", task_id=task_id)), 400

        try:
            result = pipeline_factory().inspect(task_id=task_id, image_url=image_url)
            summary = _summarize_result(result)
            summary["event"] = "inspection_success"
            summary["request_elapsed_ms"] = round((time.perf_counter() - request_started_at) * 1000.0, 2)
            app.logger.info("inspection_success %s", _safe_json(summary))
            write_audit_log(active_settings, summary)
        except ImageDownloadError as exc:
            audit_payload = {
                "event": "inspection_download_error",
                "task_id": task_id,
                "image_url": image_url,
                "message": str(exc),
            }
            app.logger.warning("inspection_download_error %s", _safe_json(audit_payload))
            write_audit_log(active_settings, audit_payload)
            return jsonify(_error_response(str(exc), task_id=task_id, image_url=image_url)), 400
        except ModelConfigError as exc:
            write_audit_log(
                active_settings,
                {
                    "event": "model_configuration_error",
                    "task_id": task_id,
                    "image_url": image_url,
                    "message": str(exc),
                },
            )
            app.logger.exception("model configuration error")
            return jsonify(_error_response(str(exc), task_id=task_id, image_url=image_url)), 500
        except Exception as exc:
            write_audit_log(
                active_settings,
                {
                    "event": "unexpected_inference_error",
                    "task_id": task_id,
                    "image_url": image_url,
                    "message": str(exc),
                },
            )
            app.logger.exception("unexpected inference error")
            return jsonify(_error_response(f"inference failed: {exc}", task_id=task_id, image_url=image_url)), 500
        return jsonify(result)

    return app
