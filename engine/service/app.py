"""
HTTP Server Implementation for Premiere AI Editor Local Engine.

Runs multithreaded loopback HTTP service with CORS, security validation,
and graceful shutdown.
"""

import json
import os
import signal
import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional
from .routes import RouteHandler
from ..security.auth import SecurityManager


class EngineRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP request handler routing requests to RouteHandler."""

    route_handler: RouteHandler = None
    server_instance: "EngineServer" = None

    def log_message(self, format, *args):
        # Silence default stderr logging to keep console clean
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Session-Token, Authorization")

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._handle_http("GET")

    def do_POST(self):
        self._handle_http("POST")

    def do_DELETE(self):
        self._handle_http("DELETE")

    def _handle_http(self, method: str):
        content_len = int(self.headers.get("Content-Length", 0))
        body_data = self.rfile.read(content_len) if content_len > 0 else None

        headers_dict = {k: v for k, v in self.headers.items()}
        status_code, response_data = self.route_handler.handle_request(
            method=method,
            path=self.path,
            headers=headers_dict,
            body_data=body_data,
        )

        resp_bytes = json.dumps(response_data, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(resp_bytes)

        # Trigger clean shutdown if requested
        if self.path == "/shutdown" and method == "POST" and status_code == 200:
            if self.server_instance:
                self.server_instance.stop()


class EngineServer:
    """Manages server lifecycle, PID file, and loopback socket."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8990,
        token_file: Optional[str] = None,
        models_dir: Optional[str] = None,
        pid_file: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.pid_file = pid_file

        self.security = SecurityManager(token_file=token_file)
        self.route_handler = RouteHandler(security_manager=self.security, models_dir=models_dir)

        EngineRequestHandler.route_handler = self.route_handler
        EngineRequestHandler.server_instance = self

        self.httpd: Optional[ThreadingHTTPServer] = None
        self.is_running = False

    def start(self):
        """Starts HTTP server and enters serve loop."""
        self._write_pid()
        self.httpd = ThreadingHTTPServer((self.host, self.port), EngineRequestHandler)
        self.is_running = True
        print(f"[Premiere AI Editor Engine] Listening on http://{self.host}:{self.port}")
        print(f"[Premiere AI Editor Engine] Session Token: {self.security.session_token[:8]}...")

        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stops server and cleans up pidfile."""
        if self.is_running and self.httpd:
            self.is_running = False
            self._remove_pid()
            print("[Premiere AI Editor Engine] Server stopping...")
            self.httpd.shutdown()

    def _write_pid(self):
        if self.pid_file:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(self.pid_file)), exist_ok=True)
                with open(self.pid_file, "w", encoding="utf-8") as f:
                    f.write(str(os.getpid()))
            except Exception:
                pass

    def _remove_pid(self):
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
            except Exception:
                pass
