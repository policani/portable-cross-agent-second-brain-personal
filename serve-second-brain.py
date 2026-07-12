#!/usr/bin/env python3
"""Run the portable Second Brain console locally with live reindexing."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import threading
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    """Serve this vault and expose a localhost-only index rebuild route."""

    def do_POST(self) -> None:
        if self.path.rstrip("/") == "/reindex":
            self.reindex()
            return
        self.send_error(404, "Not found")

    def reindex(self) -> None:
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / "brain.py"), "--index"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                timeout=600,
            )
            output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
            body = json.dumps({
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": output.strip(),
            }).encode("utf-8")
            self.send_response(200)
        except Exception as exc:  # noqa: BLE001 - return a useful local error
            body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        if self.path.endswith((".html", ".js", ".json")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        if "/reindex" in (self.path or ""):
            super().log_message(fmt, *args)


def find_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Second Brain console locally.")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    port = find_port(args.port)
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(ROOT)))
    url = f"http://127.0.0.1:{port}/index.html"
    print(f"Second Brain console: {url}")
    print("Refresh rebuilds brain-index.js and reloads this page. Ctrl+C stops the server.")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
