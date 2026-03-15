from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import quote


def sign_record_id(record_id: str, expires_at: int, secret: str) -> str:
    payload = f"{record_id}:{expires_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_record_signature(record_id: str, expires_at: int, signature: str, secret: str) -> bool:
    if expires_at < int(time.time()):
        return False
    expected = sign_record_id(record_id, expires_at, secret)
    return hmac.compare_digest(expected, signature)


def build_signed_image_url(base_url: str, record_id: str, secret: str, expires_in_sec: int) -> tuple[str, int]:
    expires_at = int(time.time()) + max(1, int(expires_in_sec))
    signature = sign_record_id(record_id, expires_at, secret)
    quoted_record_id = quote(record_id, safe="")
    base = base_url.rstrip("/")
    image_url = f"{base}/api/v1/images/{quoted_record_id}?expires={expires_at}&signature={signature}"
    return image_url, expires_at
