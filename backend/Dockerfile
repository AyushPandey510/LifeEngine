# Dockerfile for Life Engine AI Backend
# Production-ready container

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for psycopg2 and faiss
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Create non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Create directory for FAISS indexes
RUN mkdir -p /app/faiss_indexes

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Run the application. Render provides PORT; local Docker falls back to 8000.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2}"]
