# Use a minimal base image for Python
FROM python:3.12

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential build dependencies and clean up after installation
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
    # Additional Chrome dependencies for Remotion video rendering
    libcups2 \
    libpango-1.0-0 \
    libcairo2 \
    libatk-bridge2.0-0 \
    # Dependencies for Claude Code skills (PDF, DOCX, XLSX, PPTX processing)
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

# Verify Node.js and npm installation
RUN node --version && npm --version

# Install Claude Code CLI (required for Claude SDK)
RUN npm install -g @anthropic-ai/claude-code@2.0.53

# Verify Claude CLI installation
RUN claude --version

# Install Remotion CLI globally for video creation
RUN npm install -g @remotion/cli remotion

# Pre-install Chrome Headless Shell for Remotion (faster renders, ~500MB)
RUN npx remotion browser ensure

# Set up a working directory
WORKDIR /app

# Install Rust and Cargo for Rust-based Python dependencies
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip and install dependencies for a smooth build
RUN pip install --upgrade pip setuptools wheel maturin

# Install Python packages required by Claude Code skills
RUN pip install --no-cache-dir \
    # PDF processing
    pypdf \
    pdfplumber \
    reportlab \
    pytesseract \
    pdf2image \
    # DOCX/XLSX/PPTX processing
    openpyxl \
    defusedxml \
    "markitdown[pptx]" \
    # Data engineering & analytics
    pandas \
    numpy \
    matplotlib \
    seaborn \
    pyarrow \
    sqlalchemy \
    # Data science & ML
    scikit-learn \
    scipy \
    xgboost \
    joblib

# Copy and install Python dependencies
COPY ./requirements.txt ./requirements.txt
COPY ./inference/requirements.txt ./inference/requirements.txt
RUN pip install -r inference/requirements.txt

# Set environment variables
ENV PYTHONPATH=/app

# Set up a working directory
WORKDIR /app

# Copy only the necessary application files
COPY ./workflows ./services/workflows
COPY ./models ./services/models
COPY ./customer ./services/customer
COPY ./integration ./services/integration
COPY ./utils ./services/utils
COPY ./inference ./services/inference
COPY ./cache ./services/cache

# NOTE: Non-root user is intentionally disabled for the following reasons:
# 1. LibreOffice (used for document conversion) requires specific permissions for font cache and temp files
# 2. Tesseract OCR needs write access to /tmp for processing intermediate files
# 3. Claude Code CLI creates working directories that need write permissions
# 4. The container runs in an isolated environment with strict directory boundaries enforced at the application level
# 5. All file operations are sandboxed to /tmp/chicory/{project}/{agent}/ directories
# TODO: Investigate running as non-root with specific capabilities (CAP_CHOWN, CAP_FOWNER) in follow-up
# See: https://github.com/chicoryai/BrewHub/issues/XXX (to be created)
#RUN useradd -m appuser
#USER appuser

# Set the working directory for the service
WORKDIR /app/services/inference

# Grant execute permissions
RUN chmod +x ./entrypoint.sh

# Define the command to run the application
CMD ["./entrypoint.sh"]
