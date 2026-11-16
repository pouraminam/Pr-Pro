#!/usr/bin/env python3
"""
Premiere AI Editor - Local Processing Service Entry Point.

Usage:
    python -m engine.main [--port 8990] [--token-file <path>] [--models-dir <path>]
"""

import argparse
import os
import sys
import urllib.request
from pathlib import Path
from .service.app import EngineServer


def is_already_running(host: str, port: int) -> bool:
    """Checks if an engine instance is already healthy on this port."""
    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PremiereAIEditor-Launcher"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Premiere AI Editor Local Processing Engine")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8990, help="Port to listen on (default: 8990)")
    parser.add_argument("--token-file", help="Path to file where session token will be stored")
    parser.add_argument("--models-dir", help="Directory where Whisper models are stored")
    parser.add_argument("--pid-file", help="Path to write process ID file")

    args = parser.parse_args()

    # Determine default paths if not provided
    if os.name == "nt":
        app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        base_dir = Path(app_data) / "PremiereAIEditor"
    else:
        base_dir = Path.home() / ".cache" / "premiere_ai_editor"

    base_dir.mkdir(parents=True, exist_ok=True)

    token_file = args.token_file or str(base_dir / "session.token")
    pid_file = args.pid_file or str(base_dir / "engine.pid")
    models_dir = args.models_dir or str(base_dir / "models")

    # Check for already running instance
    if is_already_running(args.host, args.port):
        print(f"[Premiere AI Editor Engine] Already running on http://{args.host}:{args.port}")
        sys.exit(0)

    server = EngineServer(
        host=args.host,
        port=args.port,
        token_file=token_file,
        models_dir=models_dir,
        pid_file=pid_file,
    )

    server.start()


if __name__ == "__main__":
    main()
