from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from enterprise_image_adapter.config import AdapterSettings


class AdapterConfigError(RuntimeError):
    pass


class ImageAdapterError(RuntimeError):
    pass


class ImageNotFoundError(ImageAdapterError):
    pass


@dataclass(frozen=True)
class DatabaseImageRecord:
    image_bytes: bytes
    mime_type: str | None
    file_name: str | None


def _normalize_image_bytes(raw_value: Any, encoding: str) -> bytes:
    if raw_value is None:
        raise ImageAdapterError("image_data is null")

    if hasattr(raw_value, "read") and callable(raw_value.read):
        raw_value = raw_value.read()

    if isinstance(raw_value, bytes):
        return raw_value
    if isinstance(raw_value, bytearray):
        return bytes(raw_value)
    if isinstance(raw_value, memoryview):
        return raw_value.tobytes()

    if isinstance(raw_value, str):
        text_value = raw_value.strip()
        if encoding == "base64":
            try:
                return base64.b64decode(text_value, validate=True)
            except binascii.Error as exc:
                raise ImageAdapterError(f"failed to decode base64 image_data: {exc}") from exc
        if encoding == "hex":
            try:
                return bytes.fromhex(text_value)
            except ValueError as exc:
                raise ImageAdapterError(f"failed to decode hex image_data: {exc}") from exc
        if encoding == "binary":
            raise ImageAdapterError(
                "image_data is str while encoding=binary; use base64/hex or return a real BLOB column"
            )

    raise ImageAdapterError(
        f"unsupported image_data type {type(raw_value).__name__} for encoding={encoding}"
    )


class DatabaseImageRepository:
    def __init__(self, settings: AdapterSettings) -> None:
        if not settings.db_url:
            raise AdapterConfigError("POWER_IMAGE_ADAPTER_DB_URL is required")
        if not settings.image_query:
            raise AdapterConfigError("POWER_IMAGE_ADAPTER_IMAGE_QUERY is required")
        if settings.image_field_encoding not in {"binary", "base64", "hex"}:
            raise AdapterConfigError(
                "POWER_IMAGE_ADAPTER_IMAGE_FIELD_ENCODING must be one of: binary, base64, hex"
            )

        self.settings = settings
        self.engine: Engine = create_engine(settings.db_url, future=True, pool_pre_ping=True)
        self.image_query = text(settings.image_query)

    def ping(self) -> None:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise ImageAdapterError(f"database health check failed: {exc}") from exc

    def fetch_image(self, record_id: str) -> DatabaseImageRecord:
        try:
            with self.engine.connect() as connection:
                row = connection.execute(self.image_query, {"record_id": record_id}).mappings().first()
        except SQLAlchemyError as exc:
            raise ImageAdapterError(f"database query failed: {exc}") from exc

        if row is None:
            raise ImageNotFoundError(f"image record not found: {record_id}")

        image_bytes = _normalize_image_bytes(
            row.get("image_data"),
            self.settings.image_field_encoding,
        )
        if not image_bytes:
            raise ImageAdapterError(f"image data is empty for record_id={record_id}")

        mime_type = row.get("mime_type")
        file_name = row.get("file_name")
        return DatabaseImageRecord(
            image_bytes=image_bytes,
            mime_type=None if mime_type is None else str(mime_type),
            file_name=None if file_name is None else str(file_name),
        )
