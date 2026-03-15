from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
from ultralytics import YOLO

from power_inspection.config import Settings
from power_inspection.downloader import download_image
from tower_tilt_detection import BoxDetection, classify_tilt, estimate_apparent_tilt


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")


class ModelConfigError(RuntimeError):
    pass


def _assert_file_exists(path: Path, description: str) -> None:
    if not path.exists():
        raise ModelConfigError(f"{description} not found: {path}")


def _load_thresholds(threshold_file: Path) -> tuple[float, float]:
    payload = json.loads(threshold_file.read_text(encoding="utf-8"))
    recommended = payload.get("recommended_thresholds", {})
    warning_deg = float(recommended.get("warning_deg", 4.0))
    critical_deg = float(recommended.get("critical_deg", 8.0))
    if critical_deg < warning_deg:
        critical_deg = warning_deg
    return warning_deg, critical_deg


def _normalize_names(names: Any) -> dict[int, str]:
    if isinstance(names, dict):
        return {int(index): str(name) for index, name in names.items()}
    if isinstance(names, (list, tuple)):
        return {index: str(name) for index, name in enumerate(names)}
    return {}


class NestInspector:
    def __init__(self, weights_path: Path, confidence: float, iou: float, imgsz: int) -> None:
        _assert_file_exists(weights_path, "nest model weights")
        self.weights_path = weights_path
        self.confidence = confidence
        self.iou = iou
        self.imgsz = imgsz
        self._lock = threading.Lock()
        self._model = YOLO(str(weights_path), task="detect")
        self._names = _normalize_names(self._model.names)
        self._warm_up()

    def _warm_up(self) -> None:
        dummy = np.zeros((64, 64, 3), dtype=np.uint8)
        with self._lock:
            self._model.predict(dummy, conf=self.confidence, iou=self.iou, imgsz=self.imgsz, verbose=False)

    def predict(self, image: np.ndarray) -> dict[str, Any]:
        with self._lock:
            result = self._model.predict(
                image,
                conf=self.confidence,
                iou=self.iou,
                imgsz=self.imgsz,
                verbose=False,
            )[0]

        detections: list[dict[str, Any]] = []
        class_counts: dict[str, int] = {}
        if result.boxes is not None and len(result.boxes) > 0:
            xyxy = result.boxes.xyxy.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)
            for index, (coords, score, cls_id) in enumerate(zip(xyxy, confs, classes), start=1):
                x1, y1, x2, y2 = coords.tolist()
                class_name = self._names.get(cls_id, str(cls_id))
                detections.append(
                    {
                        "nest_id": index,
                        "class_id": int(cls_id),
                        "class_name": class_name,
                        "confidence": round(float(score), 4),
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    }
                )
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

        return {
            "task_name": "nest_detection",
            "count": len(detections),
            "class_counts": class_counts,
            "detections": detections,
        }


class TowerTiltInspector:
    def __init__(
        self,
        weights_path: Path,
        threshold_file: Path,
        confidence: float,
        min_box_height: int,
    ) -> None:
        _assert_file_exists(weights_path, "tower model weights")
        _assert_file_exists(threshold_file, "tower threshold file")
        self.weights_path = weights_path
        self.threshold_file = threshold_file
        self.confidence = confidence
        self.min_box_height = min_box_height
        self.warning_deg, self.critical_deg = _load_thresholds(threshold_file)
        self._lock = threading.Lock()
        self._model = YOLO(str(weights_path), task="detect")
        self._warm_up()

    def _warm_up(self) -> None:
        dummy = np.zeros((64, 64, 3), dtype=np.uint8)
        with self._lock:
            self._model.predict(dummy, conf=self.confidence, verbose=False)

    def _detect_boxes(self, image: np.ndarray) -> list[BoxDetection]:
        with self._lock:
            result = self._model.predict(image, conf=self.confidence, verbose=False)[0]

        detections: list[BoxDetection] = []
        if result.boxes is None or len(result.boxes) == 0:
            return detections

        xyxy = result.boxes.xyxy.cpu().numpy().astype(int)
        confs = result.boxes.conf.cpu().numpy()
        for coords, score in zip(xyxy, confs):
            x1, y1, x2, y2 = coords.tolist()
            if (y2 - y1) < self.min_box_height or (x2 - x1) <= 4:
                continue
            detections.append(
                BoxDetection(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    score=float(score),
                    source="model",
                )
            )
        return detections

    def predict(self, image: np.ndarray) -> dict[str, Any]:
        raw_detections = self._detect_boxes(image)
        detections: list[dict[str, Any]] = []
        summary = {"normal": 0, "warning": 0, "critical": 0, "unreliable": 0}

        for tower_id, detection in enumerate(raw_detections, start=1):
            angle_deg, tilt_confidence, _, _, point_count, mean_residual = estimate_apparent_tilt(image, detection)
            status = classify_tilt(angle_deg, tilt_confidence, self.warning_deg, self.critical_deg)
            summary[status] += 1
            detections.append(
                {
                    "tower_id": tower_id,
                    "status": status,
                    "detector_confidence": round(float(detection.score), 4),
                    "tilt_confidence": round(float(tilt_confidence), 4),
                    "apparent_tilt_deg": None if angle_deg is None else round(float(angle_deg), 4),
                    "abs_apparent_tilt_deg": None if angle_deg is None else round(abs(float(angle_deg)), 4),
                    "centerline_points": int(point_count),
                    "mean_residual_px": None if mean_residual is None else round(float(mean_residual), 4),
                    "bbox": {
                        "x1": int(detection.x1),
                        "y1": int(detection.y1),
                        "x2": int(detection.x2),
                        "y2": int(detection.y2),
                    },
                }
            )

        return {
            "task_name": "tower_tilt_detection",
            "count": len(detections),
            "warning_threshold_deg": round(self.warning_deg, 4),
            "critical_threshold_deg": round(self.critical_deg, 4),
            "summary": summary,
            "detections": detections,
        }


class PowerInspectionPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.nest_inspector = NestInspector(
            weights_path=settings.nest_weights,
            confidence=settings.nest_confidence,
            iou=settings.nest_iou,
            imgsz=settings.nest_imgsz,
        )
        self.tower_tilt_inspector = TowerTiltInspector(
            weights_path=settings.tower_weights,
            threshold_file=settings.tower_threshold_file,
            confidence=settings.tower_confidence,
            min_box_height=settings.tower_min_box_height,
        )

    def inspect(self, task_id: Any, image_url: str) -> dict[str, Any]:
        started = time.perf_counter()
        image, download_bytes = download_image(
            image_url=image_url,
            timeout_sec=self.settings.image_download_timeout_sec,
            max_bytes=self.settings.max_image_bytes,
        )
        image_height, image_width = image.shape[:2]

        nest_result = self.nest_inspector.predict(image)
        tower_tilt_result = self.tower_tilt_inspector.predict(image)

        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        return {
            "task_id": task_id,
            "image_url": image_url,
            "status": "success",
            "message": "ok",
            "elapsed_ms": elapsed_ms,
            "image": {
                "width": int(image_width),
                "height": int(image_height),
                "download_bytes": int(download_bytes),
            },
            "results": {
                "nest_detection": nest_result,
                "tower_tilt_detection": tower_tilt_result,
            },
        }
