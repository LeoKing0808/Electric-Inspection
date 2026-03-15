from __future__ import annotations

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
