from __future__ import annotations

from typing import Final

import cv2
import numpy as np
import requests


SUPPORTED_SCHEMES: Final[tuple[str, ...]] = ("http://", "https://")


class ImageDownloadError(RuntimeError):
    pass


def download_image(image_url: str, timeout_sec: float, max_bytes: int) -> tuple[np.ndarray, int]:
    normalized_url = image_url.strip()
    if not normalized_url.startswith(SUPPORTED_SCHEMES):
        raise ImageDownloadError("image_url must start with http:// or https://")

    content = bytearray()
    try:
        with requests.get(normalized_url, stream=True, timeout=timeout_sec) as response:
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise ImageDownloadError(f"image is too large, max allowed bytes is {max_bytes}")
    except requests.RequestException as exc:
        raise ImageDownloadError(f"failed to download image: {exc}") from exc

    if not content:
        raise ImageDownloadError("downloaded image content is empty")

    buffer = np.frombuffer(bytes(content), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ImageDownloadError("failed to decode image content")
    return image, len(content)
