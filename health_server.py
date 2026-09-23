import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import Config

logger = logging.getLogger(__name__)


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that only responds to GET /health."""

    def do_GET(self):  # noqa: N802 — required by BaseHTTPRequestHandler
        if self.path == "/health":
            payload = json.dumps({"status": "ok", "mode": "webhook"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            body = json.dumps({"error": "not found"}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    # Silence per-request log lines — the main bot logger is enough.
    def log_message(self, format, *args):  # noqa: A002
        pass


def start_health_server(
    host: str = Config.WEBHOOK_LISTEN,
    port: int = Config.HEALTH_PORT,
) -> HTTPServer:
    """Start a background health-check HTTP server.

    Returns the server instance (mainly for testing / graceful shutdown).
    """
    server = HTTPServer((host, port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server running on http://{host}:{port}/health")
    return server
