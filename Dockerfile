# HyperLiquidWalletTracker Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r hyperliquidwallettracker && useradd -r -g hyperliquidwallettracker hyperliquidwallettracker

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/config /app/logs /app/data && \
    chown -R hyperliquidwallettracker:hyperliquidwallettracker /app

# Switch to non-root user
USER hyperliquidwallettracker

# Expose metrics port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:9090/health')" || exit 1

# Default command
CMD ["python", "-m", "hyperliquidwallettracker.cli", "monitor"]
