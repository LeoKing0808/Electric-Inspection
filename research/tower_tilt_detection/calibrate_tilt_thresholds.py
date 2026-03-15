from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from tower_tilt_detection import (
    IMAGE_EXTENSIONS,
    classify_tilt,
    estimate_apparent_tilt,
    list_images,
    yolo_boxes_from_label,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Estimate apparent-tilt distribution on labeled data and output recommended "
            "warning/critical thresholds for the current dataset."
        )
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "valid"],
        help="Dataset splits to use, for example train valid.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Dataset root directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/tilt_calibration/thresholds.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.65,
        help="Discard weaker geometric fits when computing the baseline.",
    )
    parser.add_argument(
        "--min-box-height",
        type=int,
        default=40,
        help="Ignore tiny boxes when computing the baseline.",
    )
    return parser.parse_args()


def find_image_for_label(image_dir: Path, stem: str) -> Path | None:
    for ext in IMAGE_EXTENSIONS:
        candidate = image_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.array(values, dtype=np.float32), q))


def main() -> None:
    args = parse_args()
    all_angles: list[float] = []
    split_stats: dict[str, dict[str, float | int]] = {}

    for split in args.splits:
        image_dir = args.root / split / "images"
        label_dir = args.root / split / "labels"
        split_angles: list[float] = []
        for image_path in list_images(image_dir):
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            label_path = label_dir / f"{image_path.stem}.txt"
            detections = yolo_boxes_from_label(label_path, image.shape)
            detections = [
                det
                for det in detections
                if (det.y2 - det.y1) >= args.min_box_height and (det.x2 - det.x1) > 4
            ]
            for det in detections:
                angle_deg, confidence, _, _, _, _ = estimate_apparent_tilt(image, det)
                if angle_deg is None or confidence < args.min_confidence:
                    continue
                split_angles.append(abs(float(angle_deg)))

        split_angles.sort()
        all_angles.extend(split_angles)
        split_stats[split] = {
            "samples": len(split_angles),
            "median_abs_deg": round(percentile(split_angles, 50), 4),
            "p90_abs_deg": round(percentile(split_angles, 90), 4),
            "p95_abs_deg": round(percentile(split_angles, 95), 4),
            "p97_abs_deg": round(percentile(split_angles, 97), 4),
            "p99_abs_deg": round(percentile(split_angles, 99), 4),
        }

    all_angles.sort()
    warning_deg = percentile(all_angles, 90)
    critical_deg = percentile(all_angles, 97)
    if critical_deg < warning_deg:
        critical_deg = warning_deg

    payload = {
        "note": (
            "These thresholds are calibrated from the current dataset's apparent image-plane tilt "
            "distribution. They are not physical lean thresholds."
        ),
        "splits": split_stats,
        "global": {
            "samples": len(all_angles),
            "median_abs_deg": round(percentile(all_angles, 50), 4),
            "p90_abs_deg": round(percentile(all_angles, 90), 4),
            "p95_abs_deg": round(percentile(all_angles, 95), 4),
            "p97_abs_deg": round(percentile(all_angles, 97), 4),
            "p99_abs_deg": round(percentile(all_angles, 99), 4),
        },
        "recommended_thresholds": {
            "warning_deg": round(warning_deg, 4),
            "critical_deg": round(critical_deg, 4),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved calibration to {args.output}")
    print(
        f"Recommended thresholds: warning>={warning_deg:.2f} deg, critical>={critical_deg:.2f} deg"
    )


if __name__ == "__main__":
    main()
