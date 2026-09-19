#!/usr/bin/env python3
"""Njangi Tracker web server.

A small dependency-free Python backend using SQLite.  It serves the existing
HTML/CSS/JavaScript frontend and exposes JSON API routes for authentication,
members, contributions, cycles, loans, and password recovery.
"""
import hashlib
import http.server
import json
import os
import secrets
import smtplib
import socketserver
import sqlite3
import time
import urllib.parse
import re
from datetime import datetime, date
from email.message import EmailMessage
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = Path(os.environ.get("NJANGI_DB_PATH", str(BASE / "njangi_app.db")))
PORT = int(os.environ.get("PORT", "8000"))
SESSION_DAYS = int(os.environ.get("NJANGI_SESSION_DAYS", "7"))
RESET_MINUTES = int(os.environ.get("NJANGI_RESET_MINUTES", "10"))
RESET_MAX_ATTEMPTS = 5
RESET_REQUEST_LIMIT = 3
RESET_REQUEST_WINDOW = 15 * 60
LOAN_MIN_RELIABILITY = float(os.environ.get("NJANGI_LOAN_MIN_RELIABILITY", "70"))
LOAN_MIN_CYCLES = int(os.environ.get("NJANGI_LOAN_MIN_CYCLES", "1"))
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def load_env_file():
    """Load simple KEY=VALUE settings from .env without overwriting real env vars."""
    env_file = BASE / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def now_local():
    """Return Cameroon local time as YYYY-MM-DD HH:MM:SS."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Africa/Douala")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M:%S")


def today():
    return now_local()[:10]


def conn():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA busy_timeout=10000")
    return c


def ensure_schema():
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contribution_amount REAL NOT NULL DEFAULT 0,
            frequency TEXT NOT NULL DEFAULT 'Monthly',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(group_id) REFERENCES groups(id)
        );
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT NOT NULL,
            expected REAL NOT NULL DEFAULT 0,
            rotation_position INTEGER NOT NULL DEFAULT 1,
            enrolled INTEGER NOT NULL DEFAULT 1,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(group_id) REFERENCES groups(id)
        );
        CREATE TABLE IF NOT EXISTS cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            number INTEGER NOT NULL,
            target REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            recipient_id INTEGER,
            status TEXT NOT NULL DEFAULT 'OPEN',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(group_id) REFERENCES groups(id)
        );
        CREATE TABLE IF NOT EXISTS cycle_member_expected (
            cycle_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            expected REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(cycle_id, member_id),
            FOREIGN KEY(cycle_id) REFERENCES cycles(id) ON DELETE CASCADE,
            FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS loan_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            recorded_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(loan_id) REFERENCES loans(id) ON DELETE CASCADE,
            FOREIGN KEY(group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY(recorded_by) REFERENCES admins(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cycle_member_expected ON cycle_member_expected(cycle_id, member_id);
        CREATE INDEX IF NOT EXISTS idx_loan_payments_loan ON loan_payments(loan_id);
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            cycle_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Partial',
            FOREIGN KEY(group_id) REFERENCES groups(id),
            FOREIGN KEY(member_id) REFERENCES members(id),
            FOREIGN KEY(cycle_id) REFERENCES cycles(id)
        );
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            date_requested TEXT NOT NULL,
            amount_repaid REAL NOT NULL DEFAULT 0,
            interest_rate REAL NOT NULL DEFAULT 5,
            total_due REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(group_id) REFERENCES groups(id),
            FOREIGN KEY(member_id) REFERENCES members(id)
        );
        CREATE TABLE IF NOT EXISTS login_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            login_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            code_hash TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0,
            verified INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_members_group ON members(group_id);
        CREATE INDEX IF NOT EXISTS idx_loans_group ON loans(group_id);
        CREATE INDEX IF NOT EXISTS idx_reset_token ON reset_tokens(token);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);
        """
    )
    # Upgrade older databases created by the previous project version.
    for sql in (
        "ALTER TABLE reset_tokens ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE reset_tokens ADD COLUMN created_at REAL NOT NULL DEFAULT 0",
        "ALTER TABLE loans ADD COLUMN total_due REAL NOT NULL DEFAULT 0",
    ):
        try:
            c.execute(sql)
        except sqlite3.OperationalError:
            pass
    c.commit()
    c.close()


def valid_email(value):
    return bool(EMAIL_RE.fullmatch(str(value or "").strip().lower()))


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
    return salt.hex() + ":" + digest.hex()


def check_password(password, stored):
    try:
        salt_hex, digest = stored.split(":", 1)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 120000
        ).hex()
        return secrets.compare_digest(actual, digest)
    except Exception:
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def clean_member(row):
    data = dict(row)
    data.pop("password_hash", None)
    return data


def send_json(handler, payload, status=200):
    raw = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def error(handler, message, status=400):
    send_json(handler, {"ok": False, "error": message}, status)


def request_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if length > 1_000_000:
        raise ValueError("Request body is too large")
    raw = handler.rfile.read(length) or b"{}"
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def record_login(group_id, user_type, user_id, name, email):
    c = conn()
    c.execute(
        "INSERT INTO login_events(group_id,user_type,user_id,name,email,login_at) VALUES(?,?,?,?,?,?)",
        (group_id, user_type, user_id, name, email, now_local()),
    )
    c.commit()
    c.close()


def create_session(role, row):
    raw_token = secrets.token_urlsafe(32)
    created = time.time()
    expires = created + SESSION_DAYS * 86400
    c = conn()
    c.execute("DELETE FROM sessions WHERE expires_at < ?", (created,))
    c.execute(
        """INSERT INTO sessions(token_hash,role,user_id,group_id,name,email,created_at,expires_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            token_hash(raw_token),
            role,
            row["id"],
            row["group_id"],
            row["name"],
            row["email"],
            created,
            expires,
        ),
    )
    c.commit()
    c.close()
    return raw_token


def get_session(handler):
    auth_header = handler.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        return None
    c = conn()
    row = c.execute(
        "SELECT role,user_id,group_id,name,email FROM sessions WHERE token_hash=? AND expires_at>?",
        (token_hash(token), time.time()),
    ).fetchone()
    c.close()
    return dict(row) if row else None


def logout_session(handler):
    auth_header = handler.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if token:
        c = conn()
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
        c.commit()
        c.close()


def active_cycle(c, group_id):
    return c.execute(
        "SELECT * FROM cycles WHERE group_id=? AND status='OPEN' ORDER BY number DESC LIMIT 1",
        (group_id,),
    ).fetchone()


def member_cycle_status(c, member_id, cycle):
    if not cycle:
        return "Pending", 0.0, 0.0
    member = c.execute("SELECT expected FROM members WHERE id=?", (member_id,)).fetchone()
    expected = float(member["expected"] if member else 0)
    paid = float(
        c.execute(
            "SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE member_id=? AND cycle_id=?",
            (member_id, cycle["id"]),
        ).fetchone()["total"]
    )
    if expected > 0 and paid >= expected:
        return "Paid", paid, expected
    if paid > 0:
        return "Partial", paid, expected
    return "Pending", paid, expected


def reliability_for_member(c, member_id, group_id):
    """Calculate reliability from every CLOSED cycle in the member's group.

    On-time: expected amount fully paid and the final contribution date is on/before
    the cycle end date. Late: fully paid but final payment was after the deadline.
    Missed: the member did not fully pay the expected amount by cycle closure.
    """
    member = c.execute(
        "SELECT expected FROM members WHERE id=? AND group_id=?", (member_id, group_id)
    ).fetchone()
    if not member:
        return {"score": 0, "completed_cycles": 0, "on_time": 0, "late": 0, "missed": 0}
    cycles = c.execute(
        "SELECT id,end_date FROM cycles WHERE group_id=? AND status='CLOSED' ORDER BY number",
        (group_id,),
    ).fetchall()
    on_time = late = missed = 0
    for cycle in cycles:
        snapshot = c.execute(
            "SELECT expected FROM cycle_member_expected WHERE cycle_id=? AND member_id=?",
            (cycle["id"], member_id),
        ).fetchone()
        expected = float(snapshot["expected"] if snapshot else member["expected"] or 0)
        total = float(
            c.execute(
                "SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE member_id=? AND cycle_id=?",
                (member_id, cycle["id"]),
            ).fetchone()["total"]
        )
        last_payment = c.execute(
            "SELECT MAX(date) AS last_date FROM contributions WHERE member_id=? AND cycle_id=?",
            (member_id, cycle["id"]),
        ).fetchone()["last_date"]
        if expected > 0 and total >= expected:
            if last_payment and str(last_payment) <= str(cycle["end_date"]):
                on_time += 1
            else:
                late += 1
        else:
            missed += 1
    completed = on_time + late + missed
    # Score treats on-time as 100, late as 50, missed as 0.
    score = round(((on_time * 100) + (late * 50)) / completed) if completed else 0
    return {
        "score": score,
        "completed_cycles": completed,
        "on_time": on_time,
        "late": late,
        "missed": missed,
    }


def add_reliability(data, c, member_id, group_id):
    r = reliability_for_member(c, member_id, group_id)
    data["reliability"] = r
    return data


def dashboard(c, group_id):
    cycle = active_cycle(c, group_id)
    members = c.execute(
        "SELECT * FROM members WHERE group_id=? ORDER BY rotation_position,id", (group_id,)
    ).fetchall()
    total_pool = float(
        c.execute("SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE group_id=?", (group_id,)).fetchone()["total"]
    )
    cycle_total = float(
        c.execute(
            "SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE group_id=? AND cycle_id=?",
            (group_id, cycle["id"] if cycle else -1),
        ).fetchone()["total"]
    )
    expected_pool = sum(float(m["expected"] or 0) for m in members if m["enrolled"])
    paid_members = sum(
        1 for m in members if m["enrolled"] and member_cycle_status(c, m["id"], cycle)[0] == "Paid"
    )
    member_list = []
    for m in members:
        item = clean_member(m)
        status, paid, expected = member_cycle_status(c, m["id"], cycle)
        item.update({"status": status, "paid": paid, "expected": expected})
        add_reliability(item, c, m["id"], group_id)
        member_list.append(item)
    group = c.execute("SELECT * FROM groups WHERE id=?", (group_id,)).fetchone()
    target = float(cycle["target"] or 0) if cycle else 0
    progress = round(cycle_total / target * 100) if target > 0 else 0
    return {
        "group": dict(group) if group else {},
        "members": member_list,
        "active_cycle": dict(cycle) if cycle else None,
        "total_pool": total_pool,
        "cycle_collected": cycle_total,
        "cycle_expected": expected_pool,
        "progress": max(0, min(100, progress)),
        "members_paid": paid_members,
    }


def send_reset_email(email, code):
    host = os.getenv("NJANGI_SMTP_HOST", "smtp.gmail.com").strip()
    username = os.getenv("NJANGI_SMTP_USERNAME", "").strip()
    password = os.getenv("NJANGI_SMTP_PASSWORD", "")
    sender = os.getenv("NJANGI_SMTP_FROM", username).strip()
    port = int(os.getenv("NJANGI_SMTP_PORT", "587"))
    timeout = int(os.getenv("NJANGI_SMTP_TIMEOUT", "20"))
    no_auth = os.getenv("NJANGI_SMTP_NO_AUTH", "0") == "1"
    if not host or not sender or (not no_auth and (not username or not password)):
        return False, "SMTP email credentials are not configured."
    message = EmailMessage()
    message["Subject"] = "Njangi Tracker - Password Reset PIN"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "Hello,\n\n"
        f"Your Njangi Tracker password reset PIN is: {code}\n\n"
        f"This PIN expires in {RESET_MINUTES} minutes and can only be used once. "
        "If you did not request a password reset, ignore this email.\n\n"
        "Njangi Tracker"
    )
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                if not no_auth:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if not no_auth:
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(username, password)
                smtp.send_message(message)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def account_by_email(c, email):
    row = c.execute(
        "SELECT id,name,email,group_id FROM admins WHERE lower(email)=?", (email,)
    ).fetchone()
    if row:
        return "admin", row
    row = c.execute(
        "SELECT id,name,email,group_id FROM members WHERE lower(email)=?", (email,)
    ).fetchone()
    if row:
        return "member", row
    return None, None


def password_reset_forgot(handler, c):
    data = request_body(handler)
    email = str(data.get("email", "")).strip().lower()
    if not email or "@" not in email or len(email) > 254:
        return error(handler, "Please enter a valid email address.", 400)

    # Avoid revealing whether an account exists.
    generic = {
        "ok": True,
        "message": "If that email is registered, a 6-digit PIN has been sent.",
    }
    typ, account = account_by_email(c, email)
    if not account:
        return send_json(handler, generic)

    recent = c.execute(
        "SELECT COUNT(*) AS n FROM reset_tokens WHERE user_type=? AND user_id=? AND created_at>?",
        (typ, account["id"], time.time() - RESET_REQUEST_WINDOW),
    ).fetchone()["n"]
    if recent >= RESET_REQUEST_LIMIT:
        # Same public response prevents account enumeration.
        return send_json(handler, generic)

    c.execute(
        "UPDATE reset_tokens SET used=1 WHERE user_type=? AND user_id=? AND used=0",
        (typ, account["id"]),
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    token = secrets.token_urlsafe(32)
    created = time.time()
    expires = created + RESET_MINUTES * 60
    c.execute(
        """INSERT INTO reset_tokens(user_type,user_id,code_hash,token,expires_at,used,verified,attempts,created_at)
           VALUES(?,?,?,?,?,0,0,0,?)""",
        (typ, account["id"], hashlib.sha256(code.encode()).hexdigest(), token, expires, created),
    )
    c.commit()

    sent, mail_error = send_reset_email(email, code)
    if not sent:
        if os.getenv("NJANGI_DEV_SHOW_PIN", "0") == "1":
            # Local testing only: keep the token valid so the displayed PIN can be verified.
            return send_json(
                handler,
                {**generic, "sent": False, "reset_token": token, "dev_pin": code},
            )
        c.execute("UPDATE reset_tokens SET used=1 WHERE token=?", (token,))
        c.commit()
        # Keep the public response generic so the endpoint does not reveal whether
        # an email belongs to an account. The SMTP error is logged server-side.
        print("RESET EMAIL ERROR:", mail_error)
        return send_json(handler, generic)

    return send_json(
        handler,
        {
            **generic,
            "sent": True,
            "reset_token": token,
            "expires_in_minutes": RESET_MINUTES,
        },
    )


def password_reset_verify(handler, c):
    data = request_body(handler)
    token = str(data.get("reset_token", "")).strip()
    pin = str(data.get("pin", "")).strip()
    if not token or not pin.isdigit() or len(pin) != 6:
        return error(handler, "Enter the 6-digit PIN from your email.", 400)
    row = c.execute(
        "SELECT * FROM reset_tokens WHERE token=? AND used=0 ORDER BY id DESC LIMIT 1",
        (token,),
    ).fetchone()
    if not row or row["expires_at"] < time.time():
        return error(handler, "This PIN has expired. Request a new PIN.", 400)
    if row["attempts"] >= RESET_MAX_ATTEMPTS:
        c.execute("UPDATE reset_tokens SET used=1 WHERE id=?", (row["id"],))
        c.commit()
        return error(handler, "Too many incorrect PIN attempts. Request a new PIN.", 429)
    actual_hash = hashlib.sha256(pin.encode()).hexdigest()
    if not secrets.compare_digest(actual_hash, row["code_hash"]):
        c.execute("UPDATE reset_tokens SET attempts=attempts+1 WHERE id=?", (row["id"],))
        c.commit()
        remaining = max(0, RESET_MAX_ATTEMPTS - row["attempts"] - 1)
        return error(handler, f"Invalid PIN. {remaining} attempts remaining.", 400)
    c.execute("UPDATE reset_tokens SET verified=1 WHERE id=?", (row["id"],))
    c.commit()
    return send_json(handler, {"ok": True, "reset_token": token, "verified": True})


def password_reset_finish(handler, c):
    data = request_body(handler)
    token = str(data.get("reset_token", "")).strip()
    password = str(data.get("password", ""))
    if len(password) < 8:
        return error(handler, "Password must be at least 8 characters.", 400)
    row = c.execute(
        "SELECT * FROM reset_tokens WHERE token=? AND used=0 ORDER BY id DESC LIMIT 1",
        (token,),
    ).fetchone()
    if not row or row["expires_at"] < time.time() or not row["verified"]:
        return error(handler, "Your PIN verification is missing or expired. Request a new PIN.", 400)
    table = "admins" if row["user_type"] == "admin" else "members"
    c.execute(
        f"UPDATE {table} SET password_hash=? WHERE id=?",
        (hash_password(password), row["user_id"]),
    )
    c.execute("UPDATE reset_tokens SET used=1 WHERE id=?", (row["id"],))
    # Revoke all existing login sessions for that account after a password reset.
    c.execute(
        "DELETE FROM sessions WHERE role=? AND user_id=?",
        (row["user_type"], row["user_id"]),
    )
    c.commit()
    return send_json(handler, {"ok": True, "message": "Password changed successfully."})


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE), **kwargs)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def _headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")


    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def do_PATCH(self):
        self.route("PATCH")

    def do_DELETE(self):
        self.route("DELETE")

    def end_headers(self):
        self._headers()
        super().end_headers()

    def route(self, method):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path.startswith("/api/"):
                self.api(method, path)
            elif method == "GET":
                super().do_GET()
            else:
                error(self, "Method not allowed", 405)
        except json.JSONDecodeError:
            error(self, "Invalid JSON request.", 400)
        except (ValueError, KeyError) as exc:
            error(self, str(exc), 400)
        except Exception as exc:
            print("SERVER ERROR:", repr(exc))
            error(self, "Internal server error.", 500)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        blocked = path == "/.env" or path.endswith(".db") or path.startswith("/.git") or path.startswith("/py/") or path.endswith(".py")
        if blocked:
            return error(self, "Not found.", 404)
        return self.route("GET")

    def api(self, method, path):
        c = conn()
        try:
            session = get_session(self)

            # Public authentication and password recovery routes.
            if path == "/api/health" and method == "GET":
                return send_json(self, {"ok": True, "service": "Njangi Tracker", "time": now_local()})
            if path == "/api/auth/forgot" and method == "POST":
                return password_reset_forgot(self, c)
            if path == "/api/auth/verify-pin" and method == "POST":
                return password_reset_verify(self, c)
            if path == "/api/auth/reset" and method == "POST":
                return password_reset_finish(self, c)
            if path == "/api/auth/register" and method == "POST":
                data = request_body(self)
                name = str(data.get("name", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                phone = str(data.get("phone", "")).strip()
                password = str(data.get("password", ""))
                if not name or not valid_email(email) or len(password) < 8:
                    return error(self, "Name, valid email and password of at least 8 characters are required.")
                if c.execute("SELECT 1 FROM admins WHERE lower(email)=?", (email,)).fetchone() or c.execute("SELECT 1 FROM members WHERE lower(email)=?", (email,)).fetchone():
                    return error(self, "Email already registered.")
                group_name = str(data.get("group_name") or f"{name}'s Njangi Group").strip()
                amount = float(data.get("contribution_amount") or 25000)
                frequency = str(data.get("frequency") or "Monthly")
                c.execute("INSERT INTO groups(name,contribution_amount,frequency) VALUES(?,?,?)", (group_name, amount, frequency))
                gid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                c.execute("INSERT INTO admins(group_id,name,email,phone,password_hash) VALUES(?,?,?,?,?)", (gid, name, email, phone, hash_password(password)))
                aid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                c.commit()
                row = c.execute("SELECT id,group_id,name,email,phone FROM admins WHERE id=?", (aid,)).fetchone()
                token = create_session("admin", row)
                record_login(gid, "admin", aid, name, email)
                return send_json(self, {"ok": True, "token": token, "user": {"role": "admin", **dict(row)}})
            if path == "/api/auth/login" and method == "POST":
                data = request_body(self)
                email = str(data.get("email", "")).strip().lower()
                row = c.execute("SELECT * FROM admins WHERE lower(email)=?", (email,)).fetchone()
                if not row or not check_password(str(data.get("password", "")), row["password_hash"]):
                    return error(self, "Invalid email or password.", 401)
                token = create_session("admin", row)
                record_login(row["group_id"], "admin", row["id"], row["name"], row["email"])
                return send_json(self, {"ok": True, "token": token, "user": {"role": "admin", "id": row["id"], "group_id": row["group_id"], "name": row["name"], "email": row["email"]}})
            if path == "/api/member/login" and method == "POST":
                data = request_body(self)
                email = str(data.get("email", "")).strip().lower()
                row = c.execute("SELECT * FROM members WHERE lower(email)=? AND enrolled=1", (email,)).fetchone()
                if not row or not check_password(str(data.get("password", "")), row["password_hash"]):
                    return error(self, "Invalid email or password.", 401)
                token = create_session("member", row)
                record_login(row["group_id"], "member", row["id"], row["name"], row["email"])
                return send_json(self, {"ok": True, "token": token, "user": {"role": "member", "id": row["id"], "group_id": row["group_id"], "name": row["name"], "email": row["email"]}})
            if path == "/api/auth/logout" and method == "POST":
                logout_session(self)
                return send_json(self, {"ok": True})
            if path == "/api/members/public" and method == "GET":
                rows = c.execute("SELECT id,name,email,phone FROM members WHERE enrolled=1 ORDER BY name").fetchall()
                return send_json(self, {"ok": True, "members": [dict(x) for x in rows]})
            if path == "/api/auth/me" and method == "GET":
                return send_json(self, {"ok": bool(session), "user": session} if session else {"ok": False}, 200 if session else 401)

            if not session:
                return error(self, "Authentication required.", 401)
            gid = session["group_id"]
            role = session["role"]

            if path == "/api/dashboard" and method == "GET" and role == "admin":
                return send_json(self, {"ok": True, "data": dashboard(c, gid)})

            if path == "/api/members" and method == "GET" and role == "admin":
                return send_json(self, {"ok": True, "members": dashboard(c, gid)["members"]})

            if path == "/api/members" and method == "POST" and role == "admin":
                data = request_body(self)
                name = str(data.get("name", "")).strip()
                phone = str(data.get("phone", "")).strip()
                email = str(data.get("email", "")).strip().lower()
                if not name or not phone or not valid_email(email):
                    return error(self, "Name, phone and a valid email are required.")
                if c.execute("SELECT 1 FROM admins WHERE lower(email)=?", (email,)).fetchone() or c.execute("SELECT 1 FROM members WHERE lower(email)=?", (email,)).fetchone():
                    return error(self, "Email is already registered.")
                group = c.execute("SELECT contribution_amount FROM groups WHERE id=?", (gid,)).fetchone()
                expected = float(data.get("expected") or group["contribution_amount"])
                password = str(data.get("password") or "").strip()
                temporary = False
                if len(password) < 8:
                    password = secrets.token_urlsafe(9)
                    temporary = True
                c.execute(
                    """INSERT INTO members(group_id,name,email,phone,expected,rotation_position,enrolled,password_hash)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (gid, name, email, phone, expected, int(data.get("rotation_position") or 1), 1 if data.get("enrolled", True) else 0, hash_password(password)),
                )
                mid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                c.commit()
                member = c.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
                response = {"ok": True, "member": clean_member(member)}
                if temporary:
                    response["temporary_password"] = password
                return send_json(self, response)

            if path.startswith("/api/members/") and method in ("PUT", "DELETE") and role == "admin":
                try:
                    mid = int(path.split("/")[-1])
                except ValueError:
                    return error(self, "Invalid member ID.")
                row = c.execute("SELECT * FROM members WHERE id=? AND group_id=?", (mid, gid)).fetchone()
                if not row:
                    return error(self, "Member not found.", 404)
                if method == "DELETE":
                    c.execute("DELETE FROM members WHERE id=?", (mid,))
                    c.commit()
                    return send_json(self, {"ok": True})
                data = request_body(self)
                new_email = str(data.get("email", row["email"] or "")).strip().lower()
                if not valid_email(new_email):
                    return error(self, "A valid email is required for password recovery.")
                duplicate = c.execute("SELECT 1 FROM admins WHERE lower(email)=?", (new_email,)).fetchone() or c.execute("SELECT 1 FROM members WHERE lower(email)=? AND id!=?", (new_email, mid)).fetchone()
                if duplicate:
                    return error(self, "Email is already registered.")
                c.execute(
                    """UPDATE members SET name=?,email=?,phone=?,expected=?,rotation_position=?,enrolled=?
                       WHERE id=? AND group_id=?""",
                    (str(data.get("name", row["name"])).strip(), new_email, str(data.get("phone", row["phone"])).strip(), float(data.get("expected", row["expected"])), int(data.get("rotation_position", row["rotation_position"])), 1 if data.get("enrolled", row["enrolled"]) else 0, mid, gid),
                )
                c.commit()
                return send_json(self, {"ok": True, "member": clean_member(c.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone())})

            if path == "/api/cycles" and method == "GET" and role == "admin":
                cycles = []
                rows = c.execute("SELECT cy.*,m.name recipient_name FROM cycles cy LEFT JOIN members m ON m.id=cy.recipient_id WHERE cy.group_id=? ORDER BY cy.number DESC", (gid,)).fetchall()
                for row in rows:
                    item = dict(row)
                    item["collected"] = c.execute("SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE cycle_id=?", (row["id"],)).fetchone()["total"]
                    item["paid_members"] = c.execute("SELECT COUNT(DISTINCT member_id) AS n FROM contributions WHERE cycle_id=? AND status='Paid'", (row["id"],)).fetchone()["n"]
                    cycles.append(item)
                return send_json(self, {"ok": True, "cycles": cycles})

            if path == "/api/cycles" and method == "POST" and role == "admin":
                data = request_body(self)
                if active_cycle(c, gid):
                    return error(self, "Close the active cycle before creating another one.")
                number = int(data.get("number") or 1)
                target = float(data.get("target") or 0)
                start_date = str(data.get("start_date") or today())
                end_date = str(data.get("end_date") or start_date)
                recipient = data.get("recipient_id") or None
                if target <= 0 or start_date > end_date:
                    return error(self, "Enter a valid target and date range.")
                if c.execute("SELECT 1 FROM cycles WHERE group_id=? AND number=?", (gid, number)).fetchone():
                    return error(self, "That cycle number already exists in this group.")
                if recipient is not None:
                    recipient = int(recipient)
                    if not c.execute("SELECT 1 FROM members WHERE id=? AND group_id=? AND enrolled=1", (recipient, gid)).fetchone():
                        return error(self, "The selected recipient is not an enrolled member.")
                c.execute("INSERT INTO cycles(group_id,number,target,start_date,end_date,recipient_id,status) VALUES(?,?,?,?,?,?,'OPEN')", (gid, number, target, start_date, end_date, recipient))
                cid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                for member in c.execute("SELECT id,expected FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall():
                    c.execute("INSERT INTO cycle_member_expected(cycle_id,member_id,expected) VALUES(?,?,?)", (cid, member["id"], float(member["expected"] or 0)))
                c.commit()
                return send_json(self, {"ok": True, "cycle": dict(c.execute("SELECT * FROM cycles WHERE id=?", (cid,)).fetchone())})

            if path == "/api/cycles/close" and method == "POST" and role == "admin":
                cycle = active_cycle(c, gid)
                if not cycle:
                    return error(self, "No active cycle.")
                missing = []
                for member in c.execute("SELECT * FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall():
                    c.execute("INSERT OR IGNORE INTO cycle_member_expected(cycle_id,member_id,expected) VALUES(?,?,?)", (cycle["id"], member["id"], float(member["expected"] or 0)))
                    status, _, _ = member_cycle_status(c, member["id"], cycle)
                    if status != "Paid":
                        missing.append(member["name"])
                # A fully paid cycle may be closed early.  An incomplete cycle may be
                # closed once its deadline has passed so missed/late reliability can be recorded.
                if missing and cycle["end_date"] > today():
                    return error(self, "Cycle is not complete and its deadline has not passed: " + ", ".join(missing))
                c.execute("UPDATE cycles SET status='CLOSED' WHERE id=?", (cycle["id"],))
                c.commit()
                return send_json(self, {"ok": True, "message": "Cycle closed successfully.", "reliability_updated": True})

            if path == "/api/contributions" and method == "GET" and role == "admin":
                rows = c.execute("SELECT p.*,m.name member_name,cy.number cycle_number FROM contributions p JOIN members m ON m.id=p.member_id JOIN cycles cy ON cy.id=p.cycle_id WHERE p.group_id=? ORDER BY p.date DESC,p.id DESC", (gid,)).fetchall()
                return send_json(self, {"ok": True, "contributions": [dict(x) for x in rows]})

            if path == "/api/contributions" and method == "POST" and role == "admin":
                data = request_body(self)
                mid, cid, amount = int(data["member_id"]), int(data["cycle_id"]), float(data["amount"])
                cycle = c.execute("SELECT * FROM cycles WHERE id=? AND group_id=?", (cid, gid)).fetchone()
                member = c.execute("SELECT * FROM members WHERE id=? AND group_id=?", (mid, gid)).fetchone()
                if not cycle or not member or cycle["status"] != "OPEN" or amount <= 0:
                    return error(self, "Invalid active cycle, member, or amount.")
                status, paid, expected = member_cycle_status(c, mid, cycle)
                new_status = "Paid" if expected > 0 and paid + amount >= expected else "Partial"
                contribution_date = str(data.get("date") or today())
                if contribution_date > today():
                    return error(self, "Payment date cannot be in the future.")
                c.execute("INSERT INTO contributions(group_id,member_id,cycle_id,amount,date,status) VALUES(?,?,?,?,?,?)", (gid, mid, cid, amount, contribution_date, new_status))
                # Keep all contribution rows for the member/cycle consistent with the current total.
                total = paid + amount
                if expected > 0 and total >= expected:
                    c.execute("UPDATE contributions SET status='Paid' WHERE member_id=? AND cycle_id=?", (mid, cid))
                c.commit()
                return send_json(self, {"ok": True, "status": new_status})

            if path.startswith("/api/contributions/") and method == "DELETE" and role == "admin":
                pid = int(path.split("/")[-1])
                c.execute("DELETE FROM contributions WHERE id=? AND group_id=?", (pid, gid))
                c.commit()
                return send_json(self, {"ok": True})

            if path == "/api/history" and method == "GET" and role == "admin":
                rows = c.execute("SELECT p.*,m.name member_name,cy.number cycle_number FROM contributions p JOIN members m ON m.id=p.member_id JOIN cycles cy ON cy.id=p.cycle_id WHERE p.group_id=? ORDER BY p.date DESC,p.id DESC", (gid,)).fetchall()
                return send_json(self, {"ok": True, "history": [dict(x) for x in rows]})

            if path == "/api/loans" and method == "GET":
                if role == "admin":
                    rows = c.execute("SELECT l.*,m.name member_name,m.email FROM loans l JOIN members m ON m.id=l.member_id WHERE l.group_id=? ORDER BY l.id DESC", (gid,)).fetchall()
                else:
                    rows = c.execute("SELECT l.*,m.name member_name,m.email FROM loans l JOIN members m ON m.id=l.member_id WHERE l.group_id=? AND l.member_id=? ORDER BY l.id DESC", (gid, session["user_id"])).fetchall()
                output = []
                for loan in rows:
                    item = dict(loan)
                    principal = float(item["amount"] or 0)
                    rate = float(item["interest_rate"] or 0)
                    total_due = float(item["total_due"] or 0)
                    if total_due <= 0 and item["status"] in ("APPROVED", "ACTIVE", "COMPLETED"):
                        total_due = round(principal * (1 + rate / 100), 2)
                    elif total_due <= 0:
                        total_due = principal
                    repaid = float(item["amount_repaid"] or 0)
                    item["total_due"] = total_due
                    item["balance"] = max(0, round(total_due - repaid, 2))
                    item["interest_amount"] = round(max(0, total_due - principal), 2)
                    add_reliability(item, c, item["member_id"], gid)
                    output.append(item)
                return send_json(self, {"ok": True, "loans": output})

            if path == "/api/loans" and method == "POST":
                data = request_body(self)
                member_id = session["user_id"] if role == "member" else int(data.get("member_id") or 0)
                member = c.execute("SELECT * FROM members WHERE id=? AND group_id=? AND enrolled=1", (member_id, gid)).fetchone()
                amount = float(data.get("amount") or 0)
                reason = str(data.get("reason") or "").strip()
                if not member or amount <= 0 or not reason:
                    return error(self, "A valid member, amount, and reason are required.")
                if role == "member" and member_id != session["user_id"]:
                    return error(self, "You can only request a loan for yourself.", 403)
                outstanding = c.execute("SELECT 1 FROM loans WHERE member_id=? AND group_id=? AND status IN ('PENDING','APPROVED','ACTIVE')", (member_id, gid)).fetchone()
                if outstanding:
                    return error(self, "Member already has an outstanding loan.")
                rate = float(data.get("interest_rate") or 5)
                if rate < 0 or rate > 100:
                    return error(self, "Interest rate must be between 0 and 100 percent.")
                c.execute("INSERT INTO loans(group_id,member_id,amount,reason,status,date_requested,interest_rate,total_due,amount_repaid) VALUES(?,?,?,?,'PENDING',?,?,?,?)", (gid, member_id, amount, reason, now_local(), rate, 0, 0))
                loan_id = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                c.commit()
                return send_json(self, {"ok": True, "message": "Loan request submitted. Waiting for admin approval.", "loan_id": loan_id})

            if path.startswith("/api/loans/") and method == "PATCH" and role == "admin":
                try:
                    loan_id = int(path.split("/")[-1])
                except ValueError:
                    return error(self, "Invalid loan ID.")
                data = request_body(self)
                loan = c.execute("SELECT * FROM loans WHERE id=? AND group_id=?", (loan_id, gid)).fetchone()
                if not loan:
                    return error(self, "Loan not found.", 404)
                action = data.get("action")
                if action == "approve":
                    if loan["status"] != "PENDING":
                        return error(self, "Only pending loans can be approved.")
                    reliability = reliability_for_member(c, loan["member_id"], gid)
                    minimum_score = LOAN_MIN_RELIABILITY
                    minimum_cycles = LOAN_MIN_CYCLES
                    if reliability["completed_cycles"] < minimum_cycles:
                        return error(self, f"Loan cannot be approved yet. Member needs at least {minimum_cycles} completed cycle.", 409)
                    if reliability["score"] < minimum_score:
                        return error(self, f"Loan cannot be approved. Member reliability is {reliability['score']}%, below the required {minimum_score}%.", 409)
                    rate = float(data.get("interest_rate", loan["interest_rate"] or 5))
                    if rate < 0 or rate > 100:
                        return error(self, "Interest rate must be between 0 and 100 percent.")
                    # Available pool = contributions received minus unpaid balances on approved/active loans.
                    pool = float(c.execute("SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE group_id=?", (gid,)).fetchone()["total"])
                    outstanding_loans = 0.0
                    for ol in c.execute("SELECT amount,amount_repaid,total_due,interest_rate FROM loans WHERE group_id=? AND status IN ('APPROVED','ACTIVE')", (gid,)).fetchall():
                        due = float(ol["total_due"] or 0) or round(float(ol["amount"]) * (1 + float(ol["interest_rate"] or 0) / 100), 2)
                        outstanding_loans += max(0, due - float(ol["amount_repaid"] or 0))
                    available = max(0, pool - outstanding_loans)
                    if float(loan["amount"]) > available:
                        return error(self, f"Loan cannot be approved. Available loan pool is {round(available, 2):g} FCFA.", 409)
                    total_due = round(float(loan["amount"]) * (1 + rate / 100), 2)
                    c.execute("UPDATE loans SET status='APPROVED',interest_rate=?,total_due=? WHERE id=?", (rate, total_due, loan_id))
                    c.commit()
                    return send_json(self, {"ok": True, "message": "Loan approved.", "total_due": total_due, "reliability": reliability})
                if action == "reject":
                    if loan["status"] != "PENDING":
                        return error(self, "Only pending loans can be rejected.")
                    c.execute("UPDATE loans SET status='REJECTED' WHERE id=?", (loan_id,))
                    c.commit()
                    return send_json(self, {"ok": True, "message": "Loan rejected."})
                if action == "repay":
                    if loan["status"] not in ("APPROVED", "ACTIVE"):
                        return error(self, "Only approved or active loans can receive repayments.")
                    amount = float(data.get("amount") or 0)
                    total_due = float(loan["total_due"] or 0) or round(float(loan["amount"]) * (1 + float(loan["interest_rate"] or 0) / 100), 2)
                    current = float(loan["amount_repaid"] or 0)
                    balance = max(0, total_due - current)
                    if amount <= 0 or amount > balance:
                        return error(self, f"Repayment must be greater than zero and no more than {balance:g} FCFA.")
                    new_repaid = round(current + amount, 2)
                    status = "COMPLETED" if new_repaid >= total_due else "ACTIVE"
                    c.execute("UPDATE loans SET amount_repaid=?,total_due=?,status=? WHERE id=?", (new_repaid, total_due, status, loan_id))
                    c.execute("INSERT INTO loan_payments(loan_id,group_id,amount,payment_date,recorded_by) VALUES(?,?,?,?,?)", (loan_id, gid, amount, today(), session["user_id"]))
                    c.commit()
                    return send_json(self, {"ok": True, "message": "Repayment recorded.", "payment": {"amount": amount, "date": today()}, "balance": max(0, round(total_due - new_repaid, 2)), "status": status})
                return error(self, "Unknown loan action.")

            if path == "/api/login-activity" and method == "GET" and role == "admin":
                rows = c.execute("SELECT user_type,name,email,login_at FROM login_events WHERE group_id=? ORDER BY id DESC LIMIT 100", (gid,)).fetchall()
                return send_json(self, {"ok": True, "activity": [dict(x) for x in rows]})

            if path == "/api/member/dashboard" and method == "GET" and role == "member":
                cycle = active_cycle(c, gid)
                member = c.execute("SELECT * FROM members WHERE id=? AND group_id=?", (session["user_id"], gid)).fetchone()
                if not member:
                    return error(self, "Member account not found.", 404)
                status, paid, expected = member_cycle_status(c, member["id"], cycle)
                contributions = c.execute("SELECT p.*,m.name member_name,cy.number cycle_number FROM contributions p JOIN members m ON m.id=p.member_id JOIN cycles cy ON cy.id=p.cycle_id WHERE p.group_id=? AND p.member_id=? ORDER BY p.date DESC,p.id DESC LIMIT 50", (gid, member["id"])).fetchall()
                all_group_rows = c.execute("SELECT p.*,m.name member_name,cy.number cycle_number FROM contributions p JOIN members m ON m.id=p.member_id JOIN cycles cy ON cy.id=p.cycle_id WHERE p.group_id=? ORDER BY p.id DESC LIMIT 20", (gid,)).fetchall()
                loans = c.execute("SELECT * FROM loans WHERE member_id=? AND group_id=? ORDER BY id DESC", (member["id"], gid)).fetchall()
                cycle_total = float(c.execute("SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE group_id=? AND cycle_id=?", (gid, cycle["id"] if cycle else -1)).fetchone()["total"])
                expected_pool = sum(float(x["expected"] or 0) for x in c.execute("SELECT expected FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall())
                paid_members = sum(1 for x in c.execute("SELECT id FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall() if member_cycle_status(c, x["id"], cycle)[0] == "Paid")
                target = float(cycle["target"] or 0) if cycle else 0
                progress = round(cycle_total / target * 100) if target else 0
                loan_out = []
                for loan in loans:
                    item = dict(loan)
                    principal = float(item["amount"] or 0)
                    rate = float(item["interest_rate"] or 0)
                    due = float(item["total_due"] or 0) or (round(principal * (1 + rate / 100), 2) if item["status"] in ("APPROVED", "ACTIVE", "COMPLETED") else principal)
                    repaid = float(item["amount_repaid"] or 0)
                    item.update({"total_due": due, "balance": max(0, round(due - repaid, 2)), "interest_amount": round(max(0, due - principal), 2)})
                    add_reliability(item, c, member["id"], gid)
                    loan_out.append(item)
                member_data = clean_member(member)
                member_data.update({"status": status, "paid": paid, "expected": expected})
                add_reliability(member_data, c, member["id"], gid)
                return send_json(self, {"ok": True, "member": member_data, "active_cycle": dict(cycle) if cycle else None, "cycle_collected": cycle_total, "cycle_expected": expected_pool, "progress": max(0, min(100, progress)), "members_paid": paid_members, "contributions": [dict(x) for x in contributions], "group_recent_contributions": [dict(x) for x in all_group_rows], "loans": loan_out})

            if path == "/api/reliability" and method == "GET":
                if role == "admin":
                    members = c.execute("SELECT id,name,email FROM members WHERE group_id=? ORDER BY name", (gid,)).fetchall()
                    return send_json(self, {"ok": True, "members": [{**dict(m), **{"reliability": reliability_for_member(c, m["id"], gid)}} for m in members]})
                reliability = reliability_for_member(c, session["user_id"], gid)
                return send_json(self, {"ok": True, "reliability": reliability})

            return error(self, "Endpoint not found.", 404)
        finally:
            c.close()


def main():
    ensure_schema()
    with ReusableTCPServer(("", PORT), Handler) as server:
        print(f"Njangi Tracker running at http://127.0.0.1:{PORT}")
        print("Python backend + SQLite database")
        server.serve_forever()


if __name__ == "__main__":
    main()
