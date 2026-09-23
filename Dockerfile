FROM python:3.11-slim

# Keep Python output unbuffered so logs stream in real time.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Run as a non-root user for security.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/bot_data \
    && chown -R appuser:appuser /app
USER appuser

# Webhook port (WEBHOOK_PORT) and health-check port (HEALTH_PORT).
# These are the in-container defaults; override via env at runtime.
EXPOSE 8443 8081

# Container health check hits the bot's /health endpoint.
# Only meaningful in webhook mode (where the health server runs).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.getenv('HEALTH_PORT','8081')}/health\", timeout=3)" || exit 1

CMD ["python", "bot.py"]
