# Multi-stage Dockerfile for secure Invoice Generator
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and use non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better cache layering
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=5000

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create necessary directories
RUN mkdir -p logs uploads data static/uploads \
    && chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create a startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Invoice Generator..."\n\
echo "Initializing database..."\n\
python -c "from app import init_db; init_db()"\n\
echo "Database initialized successfully"\n\
echo "Starting application on port $PORT"\n\
if [ "$FLASK_ENV" = "production" ]; then\n\
    exec gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 app:app\n\
else\n\
    exec python app.py\n\
fi' > /app/start.sh \
    && chmod +x /app/start.sh \
    && chown appuser:appuser /app/start.sh

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# Expose port
EXPOSE $PORT

# Run the application
CMD ["/app/start.sh"]