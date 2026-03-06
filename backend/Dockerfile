# ── AdaptiveAI Backend ──────────────────────────────────────
# Build:  docker build -t adaptiveai-backend .
# Run:    docker run -p 5000:5000 --env-file .env adaptiveai-backend
# ────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

# Install system deps (none needed for pure-Python stack)
# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Render uses $PORT env var)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

# Production: gunicorn with 2 workers (M0-friendly)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
