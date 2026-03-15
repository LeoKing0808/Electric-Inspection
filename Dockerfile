FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app/src
ENV POWER_INSPECTION_HOST=0.0.0.0
ENV POWER_INSPECTION_PORT=8000
ENV POWER_INSPECTION_AUDIT_LOG_DIR=/app/var/logs

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r /app/requirements.txt

COPY apps /app/apps
COPY config /app/config
COPY deploy /app/deploy
COPY models /app/models
COPY src /app/src

EXPOSE 8000

CMD ["python", "apps/inspection_service/run.py"]
