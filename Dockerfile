# ============================================================
# VIA — Autonomous AI Digital Enterprise Platform
# Production-grade Dockerfile (Multi-stage build)
# ============================================================

# ---------- Stage 1: Build dependencies ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build-time system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a virtual env
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: Production runtime ----------
FROM python:3.11-slim AS runtime

LABEL maintainer="VIA Team"
LABEL description="VIA — Autonomous AI Digital Enterprise Platform with 10 AI agents"
LABEL version="6.0.0"

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini && \
    rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual env from builder stage
COPY --from=builder /opt/venv /opt/venv

# Make sure the virtualenv Python/pip are first on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    APP_VERSION=6.0.0

# Create a non-root user for security
RUN groupadd --gid 1000 via && \
    useradd --uid 1000 --gid via --shell /bin/bash --create-home via

WORKDIR /app

# Copy application source code
COPY --chown=via:via . .

# Create required directories with correct ownership
RUN mkdir -p logs projects && \
    chown -R via:via logs projects

# Switch to non-root user
USER via

# Expose the API port
EXPOSE 8000

# Health check — verifies the API is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini as PID 1 for proper signal handling
ENTRYPOINT ["tini", "--"]

# Default command: run the FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
