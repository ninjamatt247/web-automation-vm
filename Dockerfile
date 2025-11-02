# Multi-stage Docker build for web automation
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies and cron
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    cron \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN playwright install --with-deps chromium

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create necessary directories
RUN mkdir -p /app/logs /app/data/temp /app/data/archive

# Copy and setup cron job
COPY crontab /etc/cron.d/automation-cron
RUN chmod 0644 /etc/cron.d/automation-cron && \
    crontab /etc/cron.d/automation-cron && \
    touch /var/log/cron.log

# Make scripts executable
RUN chmod +x scripts/*.sh

# Healthcheck
HEALTHCHECK --interval=5m --timeout=3s \
  CMD python /app/scripts/healthcheck.py || exit 1

# Start cron and keep container running
CMD ["bash", "-c", "cron && tail -f /var/log/cron.log /app/logs/automation.log"]
