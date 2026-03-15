from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a YOLO tower detector on the current dataset."
    )
    parser.add_argument("--data", type=Path, default=Path("data.yaml"), help="Dataset yaml path.")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics model or checkpoint path.")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs.")
    parser.add_argument("--imgsz", type=int, default=960, help="Training image size.")
    parser.add_argument("--batch", type=int, default=16, help="Batch size.")
    parser.add_argument(
        "--device",
        default="auto",
        help='Training device, for example "0", "cpu", or "auto".',
    )
    parser.add_argument("--project", default="runs/detect", help="Ultralytics project directory.")
    parser.add_argument("--name", default="tower_detector", help="Run name.")
    parser.add_argument("--workers", type=int, default=0, help="Data loader workers.")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience.")
    parser.add_argument("--cache", action="store_true", help="Cache images in RAM/disk when possible.")
    parser.add_argument("--plots", action="store_true", help="Enable Ultralytics training plots.")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the latest checkpoint in the run directory.",
    )
    return parser.parse_args()


def resolve_device(device: str) -> str:
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "0"
    return "cpu"


def main() -> None:
    args = parse_args()
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    device = resolve_device(args.device)
    model = YOLO(args.model)
    model.train(
        data=str(args.data.resolve()),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=str(Path(args.project).resolve()),
        name=args.name,
        workers=args.workers,
        patience=args.patience,
        cache=args.cache,
        plots=args.plots,
        resume=args.resume,
    )
    print(f"Training complete. Device={device} run={Path(args.project) / args.name}")


if __name__ == "__main__":
    main()
