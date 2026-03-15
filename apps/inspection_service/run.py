from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from power_inspection import create_app
from power_inspection.config import load_settings


app = create_app()


if __name__ == "__main__":
    settings = load_settings()
    try:
        from waitress import serve
    except ImportError:
        app.run(host=settings.host, port=settings.port, debug=False, threaded=True)
    else:
        serve(app, host=settings.host, port=settings.port, threads=4)
