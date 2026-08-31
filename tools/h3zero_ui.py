"""Serve the bundled H3Zero UI through an authenticated local proxy.

The Modal endpoint uses proxy authorization headers, which a normal browser
cannot attach.  This server keeps those credentials on localhost: static UI
files are served from the H3Zero checkout and only /api requests are forwarded
to Modal with the required headers.
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / ".tools" / "h3zero" / "frontend" / "dist"
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


class Handler(BaseHTTPRequestHandler):
    server_version = "H3ZeroLocalUI/1.0"

    def do_GET(self):
        if self.path.startswith("/api"):
            self.proxy()
        else:
            self.static()

    def do_POST(self):
        self.proxy()

    def do_PUT(self):
        self.proxy()

    def do_DELETE(self):
        self.proxy()

    def do_PATCH(self):
        self.proxy()

    def static(self):
        request_path = self.path.split("?", 1)[0].lstrip("/") or "index.html"
        candidate = (DIST / request_path).resolve()
        try:
            candidate.relative_to(DIST.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            candidate = DIST / "index.html"
        if not candidate.is_file():
            self.send_error(503, "H3Zero frontend is not built")
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def proxy(self):
        target = urljoin(self.server.modal_url.rstrip("/") + "/", self.path.lstrip("/"))
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in HOP_BY_HOP and key.lower() != "host"
        }
        headers["Modal-Key"] = self.server.modal_key
        headers["Modal-Secret"] = self.server.modal_secret
        length = int(self.headers.get("Content-Length", "0"))
        body = LimitedReader(self.rfile, length) if length else None
        if length:
            headers["Content-Length"] = str(length)
        try:
            response = requests.request(
                self.command,
                target,
                headers=headers,
                data=body,
                stream=True,
                timeout=(30, 3600),
            )
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in HOP_BY_HOP and key.lower() != "content-encoding":
                    self.send_header(key, value)
            self.end_headers()
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    self.wfile.write(chunk)
        except (requests.RequestException, BrokenPipeError) as exc:
            if not self.wfile.closed:
                self.send_error(502, f"Modal proxy failed: {exc}")

    def log_message(self, fmt, *args):
        print(f"[h3zero-ui] {self.address_string()} - {fmt % args}")


class LimitedReader:
    """Expose exactly one HTTP request body, not the persistent socket."""

    def __init__(self, stream, remaining: int):
        self.stream = stream
        self.remaining = remaining

    def read(self, size: int = -1):
        if self.remaining <= 0:
            return b""
        if size < 0 or size > self.remaining:
            size = self.remaining
        chunk = self.stream.read(size)
        self.remaining -= len(chunk)
        return chunk


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    load_env(ROOT / ".env")
    modal_url = os.environ.get("AI_RENDER_H3ZERO_URL", "").strip()
    modal_key = os.environ.get("AI_RENDER_H3ZERO_MODAL_KEY", "").strip()
    modal_secret = os.environ.get("AI_RENDER_H3ZERO_MODAL_SECRET", "").strip()
    missing = [
        name
        for name, value in (
            ("AI_RENDER_H3ZERO_URL", modal_url),
            ("AI_RENDER_H3ZERO_MODAL_KEY", modal_key),
            ("AI_RENDER_H3ZERO_MODAL_SECRET", modal_secret),
        )
        if not value
    ]
    if missing:
        parser.error(f"missing in .env: {', '.join(missing)}")
    if not (DIST / "index.html").is_file():
        parser.error(f"frontend build not found: {DIST}")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.modal_url = modal_url
    server.modal_key = modal_key
    server.modal_secret = modal_secret
    print(f"H3Zero UI: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
