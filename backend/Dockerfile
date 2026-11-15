# ==============================================================================
# MAAR Backend — Multi-Stage Production Dockerfile
# ==============================================================================

# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /install

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production runtime
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 maar && \
    useradd -u 1001 -g maar -m -s /bin/bash maar

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application files
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Create persistent storage directories with correct ownership
RUN mkdir -p /app/data /app/uploads /app/exports && \
    chown -R maar:maar /app

USER maar

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite+aiosqlite:////app/data/maar.db \
    CHECKPOINT_DB_URL=/app/data/maar_checkpoints.db \
    UPLOAD_DIR=/app/uploads \
    EXPORT_DIR=/app/exports

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
