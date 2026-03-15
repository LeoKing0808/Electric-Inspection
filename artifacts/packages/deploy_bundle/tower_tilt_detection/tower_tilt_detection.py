from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class BoxDetection:
    x1: int
    y1: int
    x2: int
    y2: int
    score: float
    source: str


@dataclass
class TiltResult:
    image_path: str
    tower_id: int
    source: str
    bbox_x1: int
    bbox_y1: int
    bbox_x2: int
    bbox_y2: int
    apparent_tilt_deg: float | None
    abs_apparent_tilt_deg: float | None
    confidence: float
    status: str
    centerline_points: int
    mean_residual_px: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate the apparent tilt of transmission towers from images. "
            "This is a training-free geometric method: it estimates the centerline "
            "inside each tower box and measures its angle relative to image vertical."
        )
    )
    parser.add_argument("--image-dir", type=Path, required=True, help="Directory containing images.")
    parser.add_argument(
        "--label-dir",
        type=Path,
        help="YOLO label directory matching --image-dir. Use this for the current dataset.",
    )
    parser.add_argument(
        "--model",
        type=Path,
        help="Optional Ultralytics YOLO model path. If set, detections come from the model instead of labels.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/tilt"),
        help="Directory for CSV/JSON results and annotated visualizations.",
    )
    parser.add_argument(
        "--conf-thres",
        type=float,
        default=0.25,
        help="Detection confidence threshold when --model is used.",
    )
    parser.add_argument(
        "--min-box-height",
        type=int,
        default=40,
        help="Ignore very small detections shorter than this height in pixels.",
    )
    parser.add_argument(
        "--warning-deg",
        type=float,
        default=4.0,
        help="Absolute tilt at or above this value is marked as warning.",
    )
    parser.add_argument(
        "--critical-deg",
        type=float,
        default=8.0,
        help="Absolute tilt at or above this value is marked as critical.",
    )
    parser.add_argument(
        "--threshold-file",
        type=Path,
        help="Optional JSON file produced by calibrate_tilt_thresholds.py.",
    )
    parser.add_argument(
        "--save-vis",
        action="store_true",
        help="Save annotated output images.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit for quick testing. 0 means no limit.",
    )
    args = parser.parse_args()
    if not args.label_dir and not args.model:
        parser.error("Provide either --label-dir or --model.")
    return args


def list_images(image_dir: Path) -> list[Path]:
    images = [path for path in sorted(image_dir.iterdir()) if path.suffix.lower() in IMAGE_EXTENSIONS]
    return images


def yolo_boxes_from_label(label_path: Path, image_shape: tuple[int, int, int]) -> list[BoxDetection]:
    image_h, image_w = image_shape[:2]
    detections: list[BoxDetection] = []
    if not label_path.exists():
        return detections

    with label_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            _, x_center, y_center, width, height = map(float, parts)
            x1 = int((x_center - width / 2.0) * image_w)
            y1 = int((y_center - height / 2.0) * image_h)
            x2 = int((x_center + width / 2.0) * image_w)
            y2 = int((y_center + height / 2.0) * image_h)
            detections.append(
                BoxDetection(
                    x1=max(0, x1),
                    y1=max(0, y1),
                    x2=min(image_w - 1, x2),
                    y2=min(image_h - 1, y2),
                    score=1.0,
                    source="label",
                )
            )
    return detections


def yolo_boxes_from_model(model_path: Path, image: np.ndarray, conf_thres: float) -> list[BoxDetection]:
    from ultralytics import YOLO

    model = yolo_boxes_from_model._cache.get(model_path)  # type: ignore[attr-defined]
    if model is None:
        model = YOLO(str(model_path))
        yolo_boxes_from_model._cache[model_path] = model  # type: ignore[attr-defined]

    result = model.predict(image, conf=conf_thres, verbose=False)[0]
    detections: list[BoxDetection] = []
    if result.boxes is None:
        return detections

    xyxy = result.boxes.xyxy.cpu().numpy().astype(int)
    confs = result.boxes.conf.cpu().numpy()
    for coords, score in zip(xyxy, confs):
        x1, y1, x2, y2 = coords.tolist()
        detections.append(BoxDetection(x1=x1, y1=y1, x2=x2, y2=y2, score=float(score), source="model"))
    return detections


yolo_boxes_from_model._cache = {}  # type: ignore[attr-defined]


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

    # Towers are mostly thin high-contrast structures. Track the centerline row by row.
    roi_h, roi_w = gray.shape
    top = int(roi_h * 0.12)
    bottom = int(roi_h * 0.90)
    prev_x = roi_w / 2.0
    points: list[tuple[float, float]] = []
    search_half = max(12, int(roi_w * 0.18))
    local_half = max(8, int(roi_w * 0.06))

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


def load_thresholds(args: argparse.Namespace) -> tuple[float, float]:
    warning_deg = args.warning_deg
    critical_deg = args.critical_deg
    if args.threshold_file:
        payload = json.loads(args.threshold_file.read_text(encoding="utf-8"))
        recommended = payload.get("recommended_thresholds", {})
        warning_deg = float(recommended.get("warning_deg", warning_deg))
        critical_deg = float(recommended.get("critical_deg", critical_deg))
    if critical_deg < warning_deg:
        critical_deg = warning_deg
    return warning_deg, critical_deg


def annotate_image(
    image: np.ndarray,
    detection: BoxDetection,
    angle_deg: float | None,
    confidence: float,
    status: str,
    line_points: np.ndarray | None,
) -> np.ndarray:
    annotated = image.copy()
    color = {
        "normal": (50, 200, 50),
        "warning": (0, 215, 255),
        "critical": (0, 80, 255),
        "unreliable": (180, 180, 180),
    }.get(status, (255, 255, 255))

    cv2.rectangle(annotated, (detection.x1, detection.y1), (detection.x2, detection.y2), color, 2)
    if line_points is not None:
        cv2.line(
            annotated,
            tuple(line_points[0].tolist()),
            tuple(line_points[1].tolist()),
            (255, 0, 0),
            2,
        )

    label = f"{status} conf={confidence:.2f}"
    if angle_deg is not None:
        label = f"{label} tilt={angle_deg:+.2f}deg"

    label_origin = (detection.x1, max(20, detection.y1 - 8))
    cv2.putText(annotated, label, label_origin, cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return annotated


def gather_detections(args: argparse.Namespace, image_path: Path, image: np.ndarray) -> list[BoxDetection]:
    if args.model:
        return yolo_boxes_from_model(args.model, image, args.conf_thres)

    label_path = args.label_dir / f"{image_path.stem}.txt"
    return yolo_boxes_from_label(label_path, image.shape)


def process_images(args: argparse.Namespace) -> list[TiltResult]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    vis_dir = args.output_dir / "visualizations"
    if args.save_vis:
        vis_dir.mkdir(parents=True, exist_ok=True)

    results: list[TiltResult] = []
    images = list_images(args.image_dir)
    if args.limit > 0:
        images = images[: args.limit]

    for image_path in images:
        image = cv2.imread(str(image_path))
        if image is None:
            continue

        detections = gather_detections(args, image_path, image)
        detections = [
            det
            for det in detections
            if (det.y2 - det.y1) >= args.min_box_height and (det.x2 - det.x1) > 4
        ]

        annotated = image.copy() if args.save_vis else None
        for tower_id, detection in enumerate(detections, start=1):
            angle_deg, confidence, line_points, _, point_count, mean_residual = estimate_apparent_tilt(image, detection)
            status = classify_tilt(angle_deg, confidence, args.warning_deg, args.critical_deg)
            result = TiltResult(
                image_path=str(image_path),
                tower_id=tower_id,
                source=detection.source,
                bbox_x1=detection.x1,
                bbox_y1=detection.y1,
                bbox_x2=detection.x2,
                bbox_y2=detection.y2,
                apparent_tilt_deg=None if angle_deg is None else round(angle_deg, 4),
                abs_apparent_tilt_deg=None if angle_deg is None else round(abs(angle_deg), 4),
                confidence=round(confidence, 4),
                status=status,
                centerline_points=point_count,
                mean_residual_px=None if mean_residual is None else round(mean_residual, 4),
            )
            results.append(result)

            if annotated is not None:
                annotated = annotate_image(annotated, detection, angle_deg, confidence, status, line_points)

        if annotated is not None:
            cv2.imwrite(str(vis_dir / image_path.name), annotated)

    return results


def write_outputs(output_dir: Path, results: Iterable[TiltResult]) -> None:
    results = list(results)
    csv_path = output_dir / "results.csv"
    json_path = output_dir / "results.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0]).keys()) if results else list(TiltResult.__dataclass_fields__.keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(result) for result in results], handle, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    warning_deg, critical_deg = load_thresholds(args)
    args.warning_deg = warning_deg
    args.critical_deg = critical_deg
    results = process_images(args)
    write_outputs(args.output_dir, results)

    total = len(results)
    reliable = sum(1 for item in results if item.status != "unreliable")
    warnings = sum(1 for item in results if item.status == "warning")
    critical = sum(1 for item in results if item.status == "critical")
    print(
        f"Processed {total} towers. reliable={reliable} warning={warnings} critical={critical}. "
        f"Results saved to {args.output_dir}"
    )
    print(f"Thresholds: warning>={warning_deg:.2f} deg, critical>={critical_deg:.2f} deg")
    print(
        "Note: the reported value is apparent tilt in the image plane, not a calibrated physical lean angle."
    )


if __name__ == "__main__":
    main()
