# Inference Worker Dockerfile
# Handles ML inference for agentic workflows

FROM python:3.12

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app/packages/worker-common:/app/packages/python-common

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libexpat1 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libdrm2 \
    libxkbcommon0 \
    libasound2 \
    libnss3 \
    libx11-xcb1 \
    libxcursor1 \
    libxshmfence1 \
    libmagic1 \
    fonts-liberation \
    curl \
    unzip \
    libcups2 \
    libpango-1.0-0 \
    libcairo2 \
    libatk-bridge2.0-0 \
    poppler-utils \
    tesseract-ocr \
    pandoc \
    libreoffice \
    qpdf \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Claude SDK)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN node --version && npm --version

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@2.0.53
RUN claude --version

# Install Remotion CLI for video creation
RUN npm install -g @remotion/cli remotion
RUN npx remotion browser ensure

WORKDIR /app

# Install Rust (needed for some Python dependencies)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel maturin

# Install common Python packages for ML/data work
RUN pip install --no-cache-dir \
    pypdf \
    pdfplumber \
    reportlab \
    pytesseract \
    pdf2image \
    openpyxl \
    defusedxml \
    "markitdown[pptx]" \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    pyarrow \
    sqlalchemy \
    scikit-learn \
    scipy \
    xgboost \
    joblib

# Copy and install python-common package first (chicory-common)
COPY packages/python-common /app/packages/python-common
RUN pip install --no-cache-dir -e /app/packages/python-common

# Copy and install worker-common package
COPY packages/worker-common /app/packages/worker-common
RUN pip install --no-cache-dir -e /app/packages/worker-common

# Copy requirements and install
COPY services/inference-worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY services/inference-worker/ /app/

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "print('healthy')" || exit 1

CMD ["./entrypoint.sh"]
