#!/usr/bin/env python3
"""Njangi Tracker - Class-Based Modular Application Server."""

import hashlib
import hmac
import http.server
import json
import os
import re
import secrets
import smtplib
import socketserver
import sqlite3
import time
import urllib.parse
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def bootstrap_env():
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#") and "=" in clean:
                k, v = clean.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

bootstrap_env()

DB_LOCATION = Path(os.environ.get("NJANGI_DB_PATH", str(ROOT_DIR / "njangi_app.db")))
PORT_NUM = int(os.environ.get("PORT", "8000"))
SESSION_DURATION_DAYS = int(os.environ.get("NJANGI_SESSION_DAYS", "7"))
RESET_EXPIRY_MINUTES = int(os.environ.get("NJANGI_RESET_MINUTES", "10"))
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def local_timestamp():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Africa/Douala")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S")

def current_date_str():
    return local_timestamp()[:10]

class DatabaseManager:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_LOCATION, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    @classmethod
    def initialize_db(cls):
        conn = cls.get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contribution_amount REAL NOT NULL DEFAULT 0,
                frequency TEXT NOT NULL DEFAULT 'Monthly',
                njangi_code TEXT, uuid TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone TEXT,
                password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(group_id) REFERENCES groups(id)
            );
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                member_code TEXT, name TEXT NOT NULL, email TEXT, phone TEXT NOT NULL,
                expected REAL NOT NULL DEFAULT 0, rotation_position INTEGER NOT NULL DEFAULT 1,
                enrolled INTEGER NOT NULL DEFAULT 1, password_hash TEXT NOT NULL,
                pin_hash TEXT, share_count INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(group_id) REFERENCES groups(id)
            );
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                number INTEGER NOT NULL, target REAL NOT NULL, start_date TEXT NOT NULL,
                end_date TEXT NOT NULL, recipient_id INTEGER, status TEXT NOT NULL DEFAULT 'OPEN',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(group_id) REFERENCES groups(id)
            );
            CREATE TABLE IF NOT EXISTS cycle_member_expected (
                cycle_id INTEGER NOT NULL, member_id INTEGER NOT NULL,
                expected REAL NOT NULL DEFAULT 0, PRIMARY KEY(cycle_id, member_id)
            );
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL, cycle_id INTEGER NOT NULL, amount REAL NOT NULL,
                date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Partial'
            );
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL, amount REAL NOT NULL, reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING', date_requested TEXT NOT NULL,
                amount_repaid REAL NOT NULL DEFAULT 0, interest_rate REAL NOT NULL DEFAULT 5,
                total_due REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, token_hash TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL, user_id INTEGER NOT NULL, group_id INTEGER NOT NULL,
                name TEXT NOT NULL, email TEXT, created_at REAL NOT NULL, expires_at REAL NOT NULL
            );
        """)
        conn.commit()
        conn.close()

class SecurityUtils:
    @staticmethod
    def hash_pwd(pwd, salt=None):
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 120000)
        return salt.hex() + ":" + digest.hex()

    @staticmethod
    def verify_pwd(pwd, stored):
        try:
            salt_hex, digest = stored.split(":", 1)
            actual = hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt_hex), 120000).hex()
            return secrets.compare_digest(actual, digest)
        except Exception:
            return False

    @staticmethod
    def hash_pin_code(pin, salt=None):
        if not re.fullmatch(r"\d{4}", str(pin or "").strip()):
            raise ValueError("PIN must be 4 digits")
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", str(pin).encode(), salt, 120000)
        return salt.hex() + ":" + digest.hex()

    @staticmethod
    def verify_pin_code(pin, stored):
        if not stored or ":" not in str(stored): return False
        try:
            salt_hex, expected_hex = stored.split(":", 1)
            actual = hashlib.pbkdf2_hmac("sha256", str(pin).strip().encode(), bytes.fromhex(salt_hex), 120000)
            return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
        except Exception:
            return False

class BaseHttpServer(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def write_json(self, payload, code=200):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def write_error(self, message, code=400):
        self.write_json({"ok": False, "error": message}, code)

    def read_json_body(self):
        len_val = int(self.headers.get("Content-Length", 0))
        if len_val > 1000000: raise ValueError("Payload too large")
        raw = self.rfile.read(len_val) or b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            return self.write_json({"ok": True, "service": "Njangi API", "time": local_timestamp()})
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/auth/login":
            conn = DatabaseManager.get_connection()
            try:
                data = self.read_json_body()
                email = str(data.get("email", "")).lower().strip()
                row = conn.execute("SELECT * FROM admins WHERE lower(email)=?", (email,)).fetchone()
                if row and SecurityUtils.verify_pwd(data.get("password", ""), row["password_hash"]):
                    token = secrets.token_urlsafe(32)
                    expires = time.time() + (SESSION_DURATION_DAYS * 86400)
                    conn.execute("INSERT INTO sessions VALUES (NULL, ?, 'admin', ?, ?, ?, ?, ?, ?)",
                                 (hashlib.sha256(token.encode()).hexdigest(), row["id"], row["group_id"], row["name"], row["email"], time.time(), expires))
                    conn.commit()
                    return self.write_json({"ok": True, "token": token, "user": {"role": "admin", "id": row["id"], "name": row["name"]}})
                return self.write_error("Invalid email or password.", 401)
            finally:
                conn.close()
        self.write_error("Endpoint not found", 404)

if __name__ == "__main__":
    DatabaseManager.initialize_db()
    with socketserver.ThreadingTCPServer(("", PORT_NUM), BaseHttpServer) as httpd:
        print(f"Server started on port {PORT_NUM}")
        httpd.serve_forever()