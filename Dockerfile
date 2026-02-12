# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (gcc for any pip packages that need compiling)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY fastapi_backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fastapi_backend/ .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
  && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check (NO curl needed) - runs inside the container
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
