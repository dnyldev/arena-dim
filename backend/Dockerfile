# CPU-only image for the Beat Analysis Engine backend.
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: libsndfile for soundfile, ffmpeg for MP3/M4A decoding.
# No CUDA, no GPU libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU PyTorch first so dependency resolution never picks a CUDA wheel.
RUN pip install --upgrade pip && \
    pip install torch==2.3.1 torchaudio==2.3.1 \
        --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend/app /app/app

# Cache / weights volume
RUN mkdir -p /data/uploads /data/artifacts /data/checkpoints /root/.cache/torch
ENV DATA_DIR=/data \
    UPLOAD_DIR=/data/uploads \
    ARTIFACT_DIR=/data/artifacts \
    CHECKPOINT_DIR=/data/checkpoints \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
