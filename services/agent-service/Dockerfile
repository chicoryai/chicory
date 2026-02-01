FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Claude Code skill dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy .claude directory (contains CLAUDE.md system prompt template)
COPY .claude/ ./.claude/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Create workspace directory with proper permissions
RUN mkdir -p /data/workspaces && chown -R appuser:appuser /data/workspaces

# Create .claude directory for Claude SDK session storage (will be mounted from EFS)
RUN mkdir -p /home/appuser/.claude && chown -R appuser:appuser /home/appuser/.claude

USER appuser

# Expose port
EXPOSE 8083

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8083/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8083"]
