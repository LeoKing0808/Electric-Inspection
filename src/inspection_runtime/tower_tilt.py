from __future__ import annotations

import math
import os
from dataclasses import dataclass

import cv2
import numpy as np


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


@dataclass
class BoxDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    source: str


def robust_polyfit(y_coords: np.ndarray, x_coords: np.ndarray) -> tuple[float, float, np.ndarray]:
    slope, intercept = np.polyfit(y_coords, x_coords, deg=1)
    for _ in range(3):
        predicted = slope * y_coords + intercept
        residuals = np.abs(predicted - x_coords)
        median = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - median))) or 1.0
        keep = residuals <= median + 2.5 * mad
        if int(keep.sum()) < 8:
            break
        slope, intercept = np.polyfit(y_coords[keep], x_coords[keep], deg=1)
        y_coords = y_coords[keep]
        x_coords = x_coords[keep]
    return float(slope), float(intercept), np.stack([x_coords, y_coords], axis=1)


def estimate_apparent_tilt(
    image: np.ndarray,
    detection: BoxDetection,
) -> tuple[float | None, float, np.ndarray | None, np.ndarray | None, int, float | None]:
    image_h, image_w = image.shape[:2]
    box_w = detection.x2 - detection.x1
    box_h = detection.y2 - detection.y1
    if box_w <= 4 or box_h <= 4:
        return None, 0.0, None, None, 0, None

    margin_x = int(box_w * 0.08)
    margin_y = int(box_h * 0.05)
    x1 = max(0, detection.x1 - margin_x)
    y1 = max(0, detection.y1 - margin_y)
    x2 = min(image_w - 1, detection.x2 + margin_x)
    y2 = min(image_h - 1, detection.y2 + margin_y)
    roi = image[y1:y2, x1:x2]
    if roi.size == 0:
        return None, 0.0, None, None, 0, None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    roi_h, roi_w = gray.shape
    top = int(roi_h * 0.12)
    bottom = int(roi_h * 0.90)
    prev_x = roi_w / 2.0
    points: list[tuple[float, float]] = []
    search_half = max(12, int(roi_w * 0.18))
    local_half = max(8, int(roi_w * 0.06))

    # Towers are mostly thin high-contrast structures. Track the centerline row by row.
    for y in range(bottom - 1, top, -3):
        band_y1 = max(0, y - 2)
        band_y2 = min(roi_h, y + 3)
        band = edges[band_y1:band_y2]
        xs = np.where(band > 0)[1]
        if xs.size == 0:
            continue

        candidate = xs[(xs >= prev_x - search_half) & (xs <= prev_x + search_half)]
        if candidate.size < 4:
            candidate = xs

        center = float(np.median(candidate))
        close = candidate[(candidate >= center - local_half) & (candidate <= center + local_half)]
        if close.size == 0:
            close = candidate

        tracked_x = float(np.mean(close))
        prev_x = 0.75 * prev_x + 0.25 * tracked_x
        points.append((tracked_x, float(y)))

    if len(points) < 8:
        return None, 0.0, None, None, 0, None

    coords = np.array(points, dtype=np.float32)
    x_coords = coords[:, 0]
    y_coords = coords[:, 1]
    slope, intercept, inlier_points = robust_polyfit(y_coords, x_coords)
    fit_y = inlier_points[:, 1]
    fit_x = inlier_points[:, 0]
    predicted_x = slope * fit_y + intercept
    residuals = np.abs(predicted_x - fit_x)
    mean_residual = float(np.mean(residuals))

    angle_deg = math.degrees(math.atan2(slope, 1.0))
    coverage = float((fit_y.max() - fit_y.min()) / max(roi_h, 1))
    aspect_ratio = box_h / max(box_w, 1)
    residual_limit = max(6.0, roi_w * 0.08)
    confidence = (
        0.35 * min(1.0, len(inlier_points) / 30.0)
        + 0.25 * min(1.0, coverage / 0.55)
        + 0.20 * min(1.0, aspect_ratio / 1.8)
        + 0.20 * max(0.0, 1.0 - mean_residual / residual_limit)
    )
    confidence = float(max(0.0, min(1.0, confidence)))

    line_points = np.array(
        [
            [int(slope * top + intercept), int(top)],
            [int(slope * bottom + intercept), int(bottom)],
        ],
        dtype=np.int32,
    )
    line_points[:, 0] += x1
    line_points[:, 1] += y1
    return angle_deg, confidence, line_points, coords, int(len(inlier_points)), mean_residual


def classify_tilt(angle_deg: float | None, confidence: float, warning_deg: float, critical_deg: float) -> str:
    if angle_deg is None or confidence < 0.35:
        return "unreliable"
    absolute = abs(angle_deg)
    if absolute >= critical_deg:
        return "critical"
    if absolute >= warning_deg:
        return "warning"
    return "normal"
