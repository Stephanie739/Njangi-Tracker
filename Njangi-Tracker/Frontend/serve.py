#!/usr/bin/env python3
"""Tiny static file server for the Njangi Tracker frontend (development).

Usage:  python serve.py [port]        (default port 5500)

The frontend is plain HTML/CSS/JS, so any static host works in production
(Render Static Site, Netlify, GitHub Pages, Nginx...).  This script only
exists so you can run it locally with no extra tools.
"""
import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("FRONTEND_PORT", "5500"))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("", PORT), Handler) as httpd:
        print(f"Njangi Tracker frontend running at http://127.0.0.1:{PORT}")
        print("It expects the backend API at http://127.0.0.1:8000/api (see js/config.js)")
        httpd.serve_forever()
