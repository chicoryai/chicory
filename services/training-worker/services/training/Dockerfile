# =============================================================================
# Training Worker Dockerfile
# Optimized for fast builds and small image size
# Last updated: 2026-01-26
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with build tools
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build dependencies (needed for compiling some packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (needed for tiktoken and some other packages)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements files
COPY ./requirements.txt ./requirements.txt
COPY ./training/requirements.txt ./training/requirements.txt

# Install Python dependencies
# Using --no-cache-dir to reduce layer size
RUN pip install --no-cache-dir -r training/requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal image with only runtime dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install only runtime dependencies (no build tools)
# Combined into single layer, removed Chromium/Playwright deps (not used)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # For file type detection
    libmagic1 \
    # For PDF processing (unstructured, pdf2image)
    poppler-utils \
    # For OCR (tesseract)
    tesseract-ocr \
    # For image processing (pillow, opencv)
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    # For graphviz (eralchemy)
    graphviz \
    # For gitpython (GitHub integration)
    git \
    # General utilities
    curl \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY ./workflows ./services/workflows
COPY ./customer ./services/customer
COPY ./integration ./services/integration
COPY ./utils ./services/utils
COPY ./training ./services/training

# Set working directory for service
WORKDIR /app/services/training

# Make entrypoint executable
RUN chmod +x ./entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

ENTRYPOINT ["/app/services/training/entrypoint.sh"]
