# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    rclone \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data /config /scripts && \
    chown -R appuser:appuser /app /data /config /scripts

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Set PATH for user packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --chown=appuser:appuser scripts/ /app/scripts/
COPY --chown=appuser:appuser config/ /app/config/
COPY --chown=appuser:appuser cron/ /app/cron/

WORKDIR /app

# Switch to non-root user
USER appuser

# Add user packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command
CMD ["python", "scripts/crypto_news_scorer.py"]