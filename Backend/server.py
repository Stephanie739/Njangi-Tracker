#!/usr/bin/env python3
"""Njangi Tracker web server.

A small dependency-free Python backend using SQLite.  It serves the existing
HTML/CSS/JavaScript frontend and exposes JSON API routes for authentication,
members, contributions, cycles, loans, and password recovery.
"""
import hashlib
import hmac
import http.server
import json
import os
import secrets
import smtplib
import socketserver
import sqlite3
import threading
import time
import urllib.parse
import re
from datetime import datetime, date, timedelta
from email.message import EmailMessage
from pathlib import Path

BASE = Path(__file__).resolve().parent


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

# Read configuration only after .env has been loaded.
DB = Path(os.environ.get("NJANGI_DB_PATH", str(BASE / "njangi_app.db")))
PORT = int(os.environ.get("PORT", "8000"))
SESSION_DAYS = int(os.environ.get("NJANGI_SESSION_DAYS", "7"))
RESET_MINUTES = int(os.environ.get("NJANGI_RESET_MINUTES", "10"))
RESET_MAX_ATTEMPTS = 5
RESET_REQUEST_LIMIT = 3
RESET_REQUEST_WINDOW = 15 * 60
LOAN_MIN_RELIABILITY = float(os.environ.get("NJANGI_LOAN_MIN_RELIABILITY", "70"))
LOAN_MIN_CYCLES = int(os.environ.get("NJANGI_LOAN_MIN_CYCLES", "1"))
LOGIN_MAX_ATTEMPTS = int(os.environ.get("NJANGI_LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCK_SECONDS = int(os.environ.get("NJANGI_LOGIN_LOCK_SECONDS", str(15 * 60)))
CYCLE_REMINDER_DAYS = int(os.environ.get("NJANGI_CYCLE_REMINDER_DAYS", "3"))
NOTIFY_CHECK_SECONDS = int(os.environ.get("NJANGI_NOTIFY_CHECK_SECONDS", "3600"))
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


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
            njangi_code TEXT,
            uuid TEXT,
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
            member_code TEXT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT NOT NULL,
            expected REAL NOT NULL DEFAULT 0,
            rotation_position INTEGER NOT NULL DEFAULT 1,
            enrolled INTEGER NOT NULL DEFAULT 1,
            password_hash TEXT NOT NULL,
            pin_hash TEXT,
            share_count INTEGER NOT NULL DEFAULT 1,
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
        CREATE TABLE IF NOT EXISTS loan_guarantors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            guarantor_member_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            signed_at TEXT,
            note TEXT,
            FOREIGN KEY(loan_id) REFERENCES loans(id) ON DELETE CASCADE,
            FOREIGN KEY(guarantor_member_id) REFERENCES members(id),
            UNIQUE(loan_id, guarantor_member_id)
        );
        CREATE INDEX IF NOT EXISTS idx_guarantors_loan ON loan_guarantors(loan_id);
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            member_id INTEGER,
            loan_id INTEGER,
            tx_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_after REAL,
            reference TEXT,
            description TEXT,
            recorded_by INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(group_id) REFERENCES groups(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ledger_group ON ledger_transactions(group_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_loan ON ledger_transactions(loan_id);
        CREATE TABLE IF NOT EXISTS payout_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            cycle_id INTEGER,
            number INTEGER NOT NULL,
            beneficiary_member_id INTEGER,
            pot_amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'OPEN',
            bidding_opens TEXT,
            bidding_closes TEXT,
            awarded_at TEXT,
            disbursed_at TEXT,
            disbursed_by INTEGER,
            winning_bid_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(group_id) REFERENCES groups(id)
        );
        CREATE INDEX IF NOT EXISTS idx_payout_cycles_group ON payout_cycles(group_id);
        CREATE TABLE IF NOT EXISTS pot_bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payout_cycle_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            discount_amount REAL NOT NULL DEFAULT 0,
            bid_percent REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(payout_cycle_id) REFERENCES payout_cycles(id) ON DELETE CASCADE,
            FOREIGN KEY(group_id) REFERENCES groups(id),
            UNIQUE(payout_cycle_id, member_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pot_bids_cycle ON pot_bids(payout_cycle_id);
        CREATE TABLE IF NOT EXISTS momo_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            cycle_id INTEGER,
            amount REAL NOT NULL,
            provider TEXT NOT NULL,
            external_ref TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'PENDING',
            contribution_id INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            paid_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_momo_ref ON momo_pending(external_ref);
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
        CREATE TABLE IF NOT EXISTS login_throttle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_key TEXT NOT NULL UNIQUE,
            attempts INTEGER NOT NULL DEFAULT 0,
            locked_until REAL NOT NULL DEFAULT 0,
            updated_at REAL NOT NULL DEFAULT 0
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
        CREATE UNIQUE INDEX IF NOT EXISTS uq_one_open_cycle ON cycles(group_id) WHERE status='OPEN';
        """
    )
    # Upgrade older databases created by the previous project version.
    for sql in (
        "ALTER TABLE reset_tokens ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE reset_tokens ADD COLUMN created_at REAL NOT NULL DEFAULT 0",
        "ALTER TABLE loans ADD COLUMN total_due REAL NOT NULL DEFAULT 0",
        "ALTER TABLE cycles ADD COLUMN paid_out_at TEXT",
        "ALTER TABLE cycles ADD COLUMN paid_out_amount REAL NOT NULL DEFAULT 0",
        "ALTER TABLE cycles ADD COLUMN paid_out_by INTEGER",
        "ALTER TABLE cycles ADD COLUMN reminder_sent INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE members ADD COLUMN pin_hash TEXT",
        "ALTER TABLE members ADD COLUMN share_count INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE groups ADD COLUMN njangi_code TEXT",
        "ALTER TABLE groups ADD COLUMN uuid TEXT",
        "ALTER TABLE loans ADD COLUMN payback_months INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE loans ADD COLUMN required_guarantors INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE loans ADD COLUMN approved_by INTEGER",
        "ALTER TABLE loans ADD COLUMN date_approved TEXT",
        "ALTER TABLE ledger_transactions ADD COLUMN fund_type TEXT NOT NULL DEFAULT 'MAIN_POT'",
    ):
        try:
            c.execute(sql)
        except sqlite3.OperationalError:
            pass
    # Login-system migration: every member gets a stable Member ID.
    # This removes the need to type a Njangi group name at member login and
    # lets the same email address be used in different Njangi groups safely.
    try:
        c.execute("ALTER TABLE members ADD COLUMN member_code TEXT")
    except sqlite3.OperationalError:
        pass
    rows = c.execute("SELECT id FROM members WHERE member_code IS NULL OR TRIM(member_code)='' ORDER BY id").fetchall()
    for row in rows:
        c.execute("UPDATE members SET member_code=? WHERE id=?", (f"MBR-{int(row['id']):06d}", row["id"]))
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_members_member_code ON members(member_code)")
    except sqlite3.IntegrityError:
        # Rebuild any duplicate legacy codes deterministically.
        rows = c.execute("SELECT id FROM members ORDER BY id").fetchall()
        for row in rows:
            c.execute("UPDATE members SET member_code=? WHERE id=?", (f"MBR-{int(row['id']):06d}", row["id"]))
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_members_member_code ON members(member_code)")

    ensure_group_codes(c)
    try:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_groups_njangi_code ON groups(njangi_code) WHERE njangi_code IS NOT NULL")
    except sqlite3.OperationalError:
        pass
    c.commit()
    c.close()


def valid_email(value):
    return bool(EMAIL_RE.fullmatch(str(value or "").strip().lower()))


def normalize_member_code(value):
    return re.sub(r"\\s+", "", str(value or "").strip().upper())


def make_member_code(member_id):
    return f"MBR-{int(member_id):06d}"


# ---------------------------------------------------------------------------
# Step 2 / 3 helpers — njangi_code generation + PIN hashing
# (mirrors py/model.py so the web server stays self-contained)
# ---------------------------------------------------------------------------
_NJANGI_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_njangi_code(prefix="NJG"):
    """Human-readable public code e.g. NJG-X7K9P (excludes 0,O,1,I)."""
    body = "".join(secrets.choice(_NJANGI_ALPHABET) for _ in range(5))
    return f"{(prefix or 'NJG').strip().upper()}-{body}"


def hash_pin(pin, salt=None):
    """Salted PBKDF2-HMAC-SHA256 hash of a 4-digit PIN. Format: salt_hex:digest_hex"""
    cleaned = str(pin or "").strip()
    if not re.fullmatch(r"\d{4}", cleaned):
        raise ValueError("PIN must be exactly 4 digits")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", cleaned.encode(), salt, 120000)
    return salt.hex() + ":" + digest.hex()


def verify_pin(pin, stored):
    """Constant-time PIN verification. Returns False on any malformation."""
    if not stored or ":" not in str(stored):
        return False
    cleaned = str(pin or "").strip()
    if not re.fullmatch(r"\d{4}", cleaned):
        return False
    try:
        salt_hex, expected_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", cleaned.encode(), salt, 120000)
    return hmac.compare_digest(actual, expected)


def normalize_phone(phone):
    return re.sub(r"[\s\-().]", "", str(phone or "").strip())


def ensure_group_codes(c):
    """Back-fill njangi_code / uuid for any groups that still lack them."""
    import uuid as _uuid
    rows = c.execute("SELECT id FROM groups WHERE njangi_code IS NULL OR TRIM(njangi_code)=''").fetchall()
    for row in rows:
        for _ in range(20):
            code = generate_njangi_code()
            try:
                c.execute(
                    "UPDATE groups SET njangi_code=?, uuid=COALESCE(uuid, ?) WHERE id=?",
                    (code, str(_uuid.uuid4()), row["id"]),
                )
                break
            except sqlite3.IntegrityError:
                continue



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
    snap = c.execute(
        "SELECT expected FROM cycle_member_expected WHERE cycle_id=? AND member_id=?", (cycle["id"], member_id)
    ).fetchone()
    if snap:
        expected = float(snap["expected"] or 0)
    else:
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
        if not cycle:
            expected = float(m["expected"] or 0)
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


def smtp_configured():
    """True when enough SMTP settings exist to attempt a send."""
    host, username, password, sender, port, timeout, no_auth = _smtp_credentials()
    return bool(host and sender and (no_auth or (username and password)))


def _smtp_credentials():
    """Load SMTP settings from .env.

    Supported keys (aliases accepted):
      NJANGI_SMTP_HOST
      NJANGI_SMTP_PORT          (default 587 → STARTTLS)
      NJANGI_SMTP_USERNAME  or  NJANGI_SMTP_USER
      NJANGI_SMTP_PASSWORD  or  NJANGI_SMTP_PASS
      NJANGI_SMTP_FROM
    """
    host = os.getenv("NJANGI_SMTP_HOST", "smtp.gmail.com").strip()
    username = (
        os.getenv("NJANGI_SMTP_USERNAME", "")
        or os.getenv("NJANGI_SMTP_USER", "")
    ).strip()
    password = (
        os.getenv("NJANGI_SMTP_PASSWORD", "")
        or os.getenv("NJANGI_SMTP_PASS", "")
    ).replace(" ", "").strip()
    sender = os.getenv("NJANGI_SMTP_FROM", username).strip()
    port = int(os.getenv("NJANGI_SMTP_PORT", "587"))
    timeout = int(os.getenv("NJANGI_SMTP_TIMEOUT", "20"))
    no_auth = os.getenv("NJANGI_SMTP_NO_AUTH", "0") == "1"
    return host, username, password, sender, port, timeout, no_auth


def send_email(to, subject, body, allow_sender_fallback=True):
    """Send one email via SMTP with STARTTLS (port 587) or SSL (port 465).

    Returns (ok: bool, error_message: str).

    Preferred recipient = `to` (looked up from members/admins table by the route).
    If that address is missing/invalid or the first attempt fails, optionally
    fall back to NJANGI_SMTP_FROM so mail still arrives somewhere usable.
    """
    host, username, password, sender, port, timeout, no_auth = _smtp_credentials()
    if not host or not sender or (not no_auth and (not username or not password)):
        msg = (
            "SMTP not configured. Set NJANGI_SMTP_HOST, NJANGI_SMTP_USERNAME "
            "(or NJANGI_SMTP_USER), NJANGI_SMTP_PASSWORD (or NJANGI_SMTP_PASS), "
            "and NJANGI_SMTP_FROM in .env"
        )
        print(f"[SMTP ERROR] {msg}")
        return False, msg

    preferred = str(to or "").strip().lower()
    fallback = sender.strip().lower() if sender else ""

    candidates = []
    if preferred and valid_email(preferred):
        candidates.append(preferred)
    if allow_sender_fallback and fallback and valid_email(fallback) and fallback not in candidates:
        candidates.append(fallback)

    if not candidates:
        msg = f"No valid recipient (requested={to!r}, sender={sender!r})"
        print(f"[SMTP ERROR] {msg}")
        return False, msg

    last_error = "Unknown SMTP error"
    for idx, to_email in enumerate(candidates):
        is_fallback = idx > 0
        body_use = body
        if is_fallback:
            print(f"[SMTP] Primary recipient failed or missing — falling back TO {to_email}")
            body_use = (
                body
                + f"\n\n---\n[System note] Original intended recipient was: {preferred or '(none)'}.\n"
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to_email
        message.set_content(body_use)

        print(f"[SMTP] Preparing mail FROM {sender} TO {to_email} | subject={subject!r}")
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                    if not no_auth:
                        smtp.login(username, password)
                    smtp.send_message(message)
            else:
                # Default path: port 587 + STARTTLS (Gmail / most providers)
                with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                    smtp.ehlo()
                    if not no_auth:
                        smtp.starttls()
                        smtp.ehlo()
                        smtp.login(username, password)
                    smtp.send_message(message)
            print(f"[SMTP SUCCESS] Sent email FROM {sender} TO {to_email}")
            return True, ""
        except smtplib.SMTPAuthenticationError as exc:
            last_error = f"Authentication failed: {exc}"
            print(f"[SMTP ERROR] Auth failed for user={username!r} FROM {sender} TO {to_email}: {exc}")
        except smtplib.SMTPConnectError as exc:
            last_error = f"Connection failed: {exc}"
            print(f"[SMTP ERROR] Connect failed host={host}:{port} TO {to_email}: {exc}")
        except smtplib.SMTPException as exc:
            last_error = f"SMTP error: {exc}"
            print(f"[SMTP ERROR] SMTPException FROM {sender} TO {to_email}: {exc}")
        except OSError as exc:
            last_error = f"Network error: {exc}"
            print(f"[SMTP ERROR] Network/OS error host={host}:{port}: {exc}")
        except Exception as exc:
            last_error = str(exc)
            print(f"[SMTP ERROR] Unexpected error FROM {sender} TO {to_email}: {exc!r}")

    print(f"[SMTP ERROR] All recipients failed. Last error: {last_error}")
    return False, last_error


def send_reset_email(email, code):
    """Email the 6-digit recovery PIN to the resolved member/admin address."""
    to_email = str(email or "").strip().lower()
    body = (
        "Hello,\n\n"
        f"Your Njangi Tracker password reset PIN is: {code}\n\n"
        f"This PIN expires in {RESET_MINUTES} minutes and can only be used once. "
        "If you did not request a password reset, ignore this email.\n\n"
        "Njangi Tracker"
    )
    print(f"[RESET PIN] Dispatching recovery PIN (preferred TO {to_email or 'n/a'})")
    return send_email(to_email, "Njangi Tracker - Password Reset PIN", body, allow_sender_fallback=True)


def notify(email, subject, body):
    """Best-effort notification (background thread). Falls back to NJANGI_SMTP_FROM."""
    to_email = str(email or "").strip().lower()
    if not smtp_configured():
        return False

    def _send():
        ok, mail_error = send_email(to_email, subject, body, allow_sender_fallback=True)
        if not ok:
            print(f"[SMTP ERROR] notify failed preferred TO {to_email}: {mail_error}")

    threading.Thread(target=_send, daemon=True).start()
    return True


def throttle_key(role, identifier):
    """Stable, privacy-preserving key for tracking failed logins of one account."""
    return hashlib.sha256(f"{role}:{identifier.strip().lower()}".encode()).hexdigest()


def login_lock_remaining(c, key):
    row = c.execute("SELECT locked_until FROM login_throttle WHERE account_key=?", (key,)).fetchone()
    if row and row["locked_until"] > time.time():
        return int(row["locked_until"] - time.time())
    return 0


def lock_message(seconds):
    mins = max(1, (int(seconds) + 59) // 60)
    return f"Too many failed login attempts. Try again in {mins} minute(s)."


def record_failed_login(c, key):
    now = time.time()
    c.execute(
        """INSERT INTO login_throttle(account_key,attempts,locked_until,updated_at) VALUES(?,1,0,?)
           ON CONFLICT(account_key) DO UPDATE SET attempts=attempts+1, updated_at=?""",
        (key, now, now),
    )
    row = c.execute("SELECT attempts FROM login_throttle WHERE account_key=?", (key,)).fetchone()
    if row and row["attempts"] >= LOGIN_MAX_ATTEMPTS:
        c.execute(
            "UPDATE login_throttle SET locked_until=?, attempts=0 WHERE account_key=?",
            (now + LOGIN_LOCK_SECONDS, key),
        )
    c.commit()


def clear_login_throttle(c, key):
    c.execute("DELETE FROM login_throttle WHERE account_key=?", (key,))
    c.commit()


def account_for_password_reset(c, email, account_type, group_name="", member_code=""):
    """Resolve exactly one resettable account from the database.

    Admins  → looked up by email (globally unique).
    Members → looked up by Member ID (MBR-000123). The email stored on that
              member row is what the recovery PIN is sent to.
    """
    email = (email or "").strip().lower()
    account_type = (account_type or "").strip().lower()

    if account_type == "admin":
        if not email:
            return account_type, None
        rows = c.execute(
            "SELECT id, name, email, group_id FROM admins WHERE lower(email)=?",
            (email,),
        ).fetchall()
    elif account_type == "member":
        code = normalize_member_code(member_code)
        rows = []
        # 1) Preferred: stable Member ID
        if re.fullmatch(r"MBR-\d{6}", code):
            rows = c.execute(
                "SELECT id, name, email, group_id, member_code FROM members "
                "WHERE member_code=? AND enrolled=1",
                (code,),
            ).fetchall()
        # 2) Fallback: email only (if form omitted / mistyped Member ID)
        if not rows and email:
            rows = c.execute(
                "SELECT id, name, email, group_id, member_code FROM members "
                "WHERE lower(email)=? AND enrolled=1",
                (email,),
            ).fetchall()
        # 3) Optional soft-check: if form email was given and differs from DB,
        #    still accept the Member-ID match (DB email is the delivery target).
        if email and rows and re.fullmatch(r"MBR-\d{6}", code):
            db_emails = {str(r["email"] or "").strip().lower() for r in rows}
            if email not in db_emails:
                print(
                    f"[RESET] Form email {email!r} differs from DB email(s) {db_emails}; "
                    "using Member ID match and DB email for delivery."
                )
    else:
        return None, None

    if len(rows) != 1:
        print(
            f"[RESET] Account lookup failed type={account_type!r} "
            f"member_code={member_code!r} email={email!r} matches={len(rows)}"
        )
        return account_type, None
    return account_type, rows[0]


def password_reset_forgot(handler, c):
    """POST /api/auth/forgot — generate 6-digit PIN, store token, email recipient.

    Body JSON:
      {
        "account_type": "member" | "admin",
        "email": "user@example.com",
        "member_code": "MBR-000123"   // required for members
      }
    """
    data = request_body(handler)
    email = str(data.get("email", "")).strip().lower()
    account_type = str(data.get("account_type", "")).strip().lower()
    member_code = normalize_member_code(data.get("member_code"))

    if account_type not in ("admin", "member"):
        return error(handler, "Choose whether this is an admin or member account.", 400)
    if account_type == "member" and not re.fullmatch(r"MBR-\d{6}", member_code) and not email:
        return error(handler, "Enter your Member ID (e.g. MBR-000123) or the email on your account.", 400)
    if account_type == "admin" and (not email or not valid_email(email)):
        return error(handler, "Please enter a valid email address.", 400)
    if email and not valid_email(email):
        return error(handler, "Please enter a valid email address.", 400)

    generic = {
        "ok": True,
        "message": "If that account is registered, a 6-digit PIN has been sent.",
    }
    dev_pin_mode = os.getenv("NJANGI_DEV_SHOW_PIN", "0") == "1"

    if not smtp_configured() and not dev_pin_mode:
        print("[SMTP ERROR] Password reset requested but SMTP is not configured.")
        return error(
            handler,
            "Password-reset email is not set up on this server yet. The site owner must add the SMTP settings "
            "(see DEPLOYMENT.md) or ask an administrator to reset your password.",
            503,
        )

    typ, account = account_for_password_reset(c, email, account_type, member_code=member_code)
    if not account:
        # Do not reveal whether the account exists.
        if dev_pin_mode:
            return send_json(handler, {**generic, "reset_token": secrets.token_urlsafe(32)})
        return send_json(handler, generic)

    # Rate-limit repeated requests
    recent = c.execute(
        "SELECT COUNT(*) AS n FROM reset_tokens WHERE user_type=? AND user_id=? AND created_at>?",
        (typ, account["id"], time.time() - RESET_REQUEST_WINDOW),
    ).fetchone()["n"]
    if recent >= RESET_REQUEST_LIMIT:
        print(f"[RESET] Rate limit hit for {typ}:{account['id']}")
        return send_json(handler, generic)

    # Invalidate prior unused tokens for this account
    c.execute(
        "UPDATE reset_tokens SET used=1 WHERE user_type=? AND user_id=? AND used=0",
        (typ, account["id"]),
    )

    # Generate 6-digit PIN + opaque reset token (expires in RESET_MINUTES, default 10)
    code = f"{secrets.randbelow(1_000_000):06d}"
    token = secrets.token_urlsafe(32)
    created = time.time()
    expires = created + RESET_MINUTES * 60

    # Always log PIN to terminal (fail-safe if Gmail is slow/blocked)
    acct_label = account["member_code"] if "member_code" in account.keys() else account["id"]
    db_email = str(account["email"] or "").strip().lower()
    form_email = email
    target_email = db_email if valid_email(db_email) else form_email
    print(f"[RECOVERY PIN] PIN for {acct_label} / {target_email or form_email or 'n/a'} is: {code}")

    c.execute(
        """INSERT INTO reset_tokens(
               user_type, user_id, code_hash, token, expires_at, used, verified, attempts, created_at
           ) VALUES (?,?,?,?,?,0,0,0,?)""",
        (typ, account["id"], hashlib.sha256(code.encode()).hexdigest(), token, expires, created),
    )
    c.commit()

    if not valid_email(target_email):
        print(f"[SMTP ERROR] Account {typ}:{account['id']} has no valid email on file "
              f"(db={db_email!r}, form={form_email!r})")
        if dev_pin_mode:
            return send_json(handler, {
                **generic, "sent": False, "reset_token": token, "dev_pin": code
            })
        # Still return generic success; PIN is in the terminal log.
        return send_json(handler, {**generic, "reset_token": token})

    print(f"[RESET PIN] Sending 6-digit PIN TO {target_email} "
          f"(account={typ}:{account['id']}, member_code={acct_label})")
    sent, mail_error = send_reset_email(target_email, code)
    if not sent:
        print(f"[SMTP ERROR] Recovery email failed TO {target_email}: {mail_error}")
        if dev_pin_mode:
            return send_json(handler, {
                **generic, "sent": False, "reset_token": token, "dev_pin": code
            })
        # Keep the token usable — operator can read PIN from terminal.
        return send_json(handler, {**generic, "reset_token": token})

    sender = os.getenv("NJANGI_SMTP_FROM") or os.getenv("NJANGI_SMTP_USERNAME") or os.getenv("NJANGI_SMTP_USER") or ""
    print(f"[SMTP SUCCESS] Sent recovery PIN FROM {sender} TO {target_email}")
    return send_json(handler, {
        **generic,
        "sent": True,
        "reset_token": token,
    })


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
    return send_json(
        handler,
        {
            "ok": True,
            "reset_token": token,
            "verified": True,
            "role": row["user_type"],
        },
    )


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
    return send_json(
        handler,
        {
            "ok": True,
            "message": "Password changed successfully.",
            "role": row["user_type"],
        },
    )


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
        # Logout writes through its own connection; handle it before starting
        # the request transaction so two writers never wait on each other.
        if path == "/api/auth/logout" and method == "POST":
            logout_session(self)
            return send_json(self, {"ok": True})
        c = conn()
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            # Serialize read-check-then-write sequences so concurrent requests
            # cannot race each other (double-open cycles, over-approved loans...).
            c.execute("BEGIN IMMEDIATE")
        try:
            session = get_session(self)

            # Public authentication and password recovery routes.
            if path == "/api/health" and method == "GET":
                return send_json(self, {"ok": True, "service": "Njangi Tracker", "time": now_local(), "email_configured": smtp_configured()})

            if path == "/api/v1/payments/momo/webhook" and method == "POST":
                data = request_body(self)
                # Accept both MTN and Orange-style payloads
                external_ref = str(
                    data.get("external_ref")
                    or data.get("financialTransactionId")
                    or data.get("txnid")
                    or data.get("transaction_id")
                    or data.get("reference")
                    or ""
                ).strip()
                status_raw = str(data.get("status") or data.get("transaction_status") or "").upper()
                amount = float(data.get("amount") or data.get("amount_paid") or 0)
                provider = str(data.get("provider") or data.get("network") or "MTN").upper()
                if "ORANGE" in provider:
                    provider = "ORANGE"
                else:
                    provider = "MTN"
                phone = normalize_phone(data.get("phone") or data.get("msisdn") or data.get("payer") or "")
                if not external_ref:
                    return error(self, "external_ref / transaction_id required.", 400)
                # Idempotent: already processed?
                existing = c.execute(
                    "SELECT * FROM momo_pending WHERE external_ref=?", (external_ref,)
                ).fetchone()
                success_statuses = {"SUCCESS", "SUCCESSFUL", "SUCCESSFULLY", "COMPLETED", "PAID", "TS"}
                is_success = status_raw in success_statuses or str(data.get("success") or "").lower() in ("true", "1", "yes")
                if existing and existing["status"] == "PAID":
                    return send_json(self, {"ok": True, "message": "Already processed.", "contribution_id": existing["contribution_id"]})
                if not is_success:
                    if existing:
                        c.execute("UPDATE momo_pending SET status=? WHERE id=?", (status_raw or "FAILED", existing["id"]))
                        c.commit()
                    return send_json(self, {"ok": True, "message": "Non-success status recorded.", "status": status_raw})
                # Resolve member by phone or pending row
                member = None
                cycle = None
                group_id = None
                if existing:
                    member = c.execute("SELECT * FROM members WHERE id=?", (existing["member_id"],)).fetchone()
                    group_id = existing["group_id"]
                    if existing["cycle_id"]:
                        cycle = c.execute("SELECT * FROM cycles WHERE id=?", (existing["cycle_id"],)).fetchone()
                    amount = amount or float(existing["amount"])
                if not member and phone:
                    member = c.execute(
                        "SELECT * FROM members WHERE phone=? AND enrolled=1 ORDER BY id DESC LIMIT 1", (phone,)
                    ).fetchone()
                    if member:
                        group_id = member["group_id"]
                if not member:
                    return error(self, "Unable to match payment to a member.", 404)
                if not cycle:
                    cycle = active_cycle(c, group_id)
                if not cycle:
                    return error(self, "No open cycle to apply payment to.", 404)
                if amount <= 0:
                    return error(self, "Invalid payment amount.", 400)
                # Record contribution as Paid
                c.execute(
                    """INSERT INTO contributions (group_id, member_id, cycle_id, amount, date, status)
                       VALUES (?,?,?,?,?,'Paid')""",
                    (group_id, member["id"], cycle["id"], amount, today()),
                )
                contrib_id = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                c.execute(
                    """INSERT INTO ledger_transactions
                       (group_id, member_id, fund_type, tx_type, direction, amount, reference, description, recorded_by)
                       VALUES (?, ?, 'MAIN_POT', 'MOMO_PAYMENT', 'IN', ?, ?, ?, NULL)""",
                    (group_id, member["id"], amount, external_ref, f"{provider} MoMo payment for cycle #{cycle['number']}"),
                )
                if existing:
                    c.execute(
                        "UPDATE momo_pending SET status='PAID', paid_at=?, contribution_id=?, amount=? WHERE id=?",
                        (now_local(), contrib_id, amount, existing["id"]),
                    )
                else:
                    c.execute(
                        """INSERT INTO momo_pending
                           (group_id, member_id, cycle_id, amount, provider, external_ref, status, contribution_id, paid_at)
                           VALUES (?,?,?,?,?,?,'PAID',?,?)""",
                        (group_id, member["id"], cycle["id"], amount, provider, external_ref, contrib_id, now_local()),
                    )
                c.commit()
                return send_json(self, {
                    "ok": True,
                    "message": "Payment applied.",
                    "contribution_id": contrib_id,
                    "member_id": member["id"],
                    "amount": amount,
                    "provider": provider,
                })


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
                if c.execute("SELECT 1 FROM admins WHERE lower(email)=?", (email,)).fetchone():
                    return error(self, "That email is already registered as an administrator.")
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
                key = throttle_key("admin", email)
                locked = login_lock_remaining(c, key)
                if locked:
                    return error(self, lock_message(locked), 429)
                row = c.execute("SELECT * FROM admins WHERE lower(email)=?", (email,)).fetchone()
                if not row or not check_password(str(data.get("password", "")), row["password_hash"]):
                    record_failed_login(c, key)
                    c.commit()
                    return error(self, "Invalid email or password.", 401)
                clear_login_throttle(c, key)
                c.commit()
                token = create_session("admin", row)
                record_login(row["group_id"], "admin", row["id"], row["name"], row["email"])
                return send_json(self, {"ok": True, "token": token, "user": {"role": "admin", "id": row["id"], "group_id": row["group_id"], "name": row["name"], "email": row["email"]}})
            if path == "/api/member/login" and method == "POST":
                data = request_body(self)
                member_code = normalize_member_code(data.get("member_code"))
                if not re.fullmatch(r"MBR-\d{6}", member_code):
                    return error(self, "Enter your 6-character Member ID, for example MBR-000123.", 400)
                key = throttle_key("member", member_code)
                locked = login_lock_remaining(c, key)
                if locked:
                    return error(self, lock_message(locked), 429)
                row = c.execute(
                    "SELECT * FROM members WHERE member_code=? AND enrolled=1",
                    (member_code,),
                ).fetchone()
                if not row or not check_password(str(data.get("password", "")), row["password_hash"]):
                    record_failed_login(c, key)
                    c.commit()
                    return error(self, "Invalid Member ID or password.", 401)
                clear_login_throttle(c, key)
                c.commit()
                token = create_session("member", row)
                record_login(row["group_id"], "member", row["id"], row["name"], row["email"])
                return send_json(self, {
                    "ok": True,
                    "token": token,
                    "user": {
                        "role": "member",
                        "id": row["id"],
                        "member_code": row["member_code"],
                        "group_id": row["group_id"],
                        "name": row["name"],
                        "email": row["email"],
                    },
                })
            # ================================================================
            # Step 3 — Core API endpoints under /api/v1/
            # ================================================================

            # POST /api/v1/auth/member-login  (phone + 4-digit PIN)
            if path == "/api/v1/auth/member-login" and method == "POST":
                data = request_body(self)
                phone = normalize_phone(data.get("phone") or data.get("member_code") or "")
                pin = str(data.get("pin") or data.get("password") or "").strip()
                if not phone:
                    return error(self, "Phone number is required.", 400)
                if not re.fullmatch(r"\d{4}", pin):
                    return error(self, "PIN must be exactly 4 digits.", 400)
                key = throttle_key("member_pin", phone)
                locked = login_lock_remaining(c, key)
                if locked:
                    return error(self, lock_message(locked), 429)
                # Prefer pin_hash; fall back to password_hash for legacy accounts
                row = c.execute(
                    "SELECT * FROM members WHERE phone=? AND enrolled=1 ORDER BY id LIMIT 1",
                    (phone,),
                ).fetchone()
                if not row:
                    # Also allow login with member_code if phone lookup failed
                    code = normalize_member_code(data.get("member_code") or data.get("phone") or "")
                    if re.fullmatch(r"MBR-\d{6}", code):
                        row = c.execute(
                            "SELECT * FROM members WHERE member_code=? AND enrolled=1",
                            (code,),
                        ).fetchone()
                ok = False
                if row:
                    pin_hash = row["pin_hash"] if "pin_hash" in row.keys() else None
                    if pin_hash:
                        ok = verify_pin(pin, pin_hash)
                    else:
                        # Legacy: treat submitted value as password
                        ok = check_password(pin, row["password_hash"])
                if not ok:
                    record_failed_login(c, key)
                    c.commit()
                    return error(self, "Invalid phone number or PIN.", 401)
                clear_login_throttle(c, key)
                c.commit()
                token = create_session("member", row)
                record_login(row["group_id"], "member", row["id"], row["name"], row["email"])
                return send_json(self, {
                    "ok": True,
                    "token": token,
                    "user": {
                        "role": "member",
                        "id": row["id"],
                        "member_code": row["member_code"],
                        "group_id": row["group_id"],
                        "name": row["name"],
                        "email": row["email"],
                        "phone": row["phone"],
                    },
                })

            # GET /api/v1/groups/lookup?code=NJG-XXXXX
            if path == "/api/v1/groups/lookup" and method == "GET":
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                code = (qs.get("code") or [""])[0].strip().upper()
                if not code:
                    return error(self, "Query parameter 'code' is required.", 400)
                ensure_group_codes(c)
                c.commit()
                row = c.execute(
                    "SELECT id, name, njangi_code, contribution_amount, frequency, created_at FROM groups WHERE njangi_code=?",
                    (code,),
                ).fetchone()
                if not row:
                    return error(self, "No group found for that Njangi code.", 404)
                member_count = c.execute(
                    "SELECT COUNT(*) AS n FROM members WHERE group_id=? AND enrolled=1",
                    (row["id"],),
                ).fetchone()["n"]
                return send_json(self, {
                    "ok": True,
                    "group": {
                        "id": row["id"],
                        "name": row["name"],
                        "njangi_code": row["njangi_code"],
                        "contribution_amount": row["contribution_amount"],
                        "frequency": row["frequency"],
                        "member_count": member_count,
                        "created_at": row["created_at"],
                    },
                })

            # POST /api/v1/groups/<group_id>/members  (Admin adds member with name, phone, share_count)
            m = re.fullmatch(r"/api/v1/groups/(\d+)/members", path)
            if m and method == "POST":
                if not session or session.get("role") != "admin":
                    return error(self, "Admin authentication required.", 401)
                try:
                    target_gid = int(m.group(1))
                except ValueError:
                    return error(self, "Invalid group ID.", 400)
                if int(session["group_id"]) != target_gid:
                    return error(self, "You can only add members to your own group.", 403)
                data = request_body(self)
                name = str(data.get("name", "")).strip()
                phone = normalize_phone(data.get("phone") or "")
                share_count = int(data.get("share_count") or data.get("shares") or 1)
                if not name:
                    return error(self, "Name is required.", 400)
                if not phone:
                    return error(self, "Phone number is required.", 400)
                if share_count < 1:
                    return error(self, "share_count must be at least 1.", 400)
                # Password / PIN from admin form (do NOT auto-generate unless empty)
                password = str(data.get("password") or "").strip()
                pin = str(data.get("pin") or "").strip()
                pin_hash_val = None
                temporary_password = None
                if pin:
                    if not re.fullmatch(r"\d{4}", pin):
                        return error(self, "PIN must be exactly 4 digits.", 400)
                    try:
                        pin_hash_val = hash_pin(pin)
                    except ValueError as exc:
                        return error(self, str(exc), 400)
                elif re.fullmatch(r"\d{4}", password):
                    # Treat a 4-digit password as PIN as well
                    try:
                        pin_hash_val = hash_pin(password)
                        pin = password
                    except ValueError:
                        pass
                email = str(data.get("email") or "").strip().lower()
                if email and not valid_email(email):
                    return error(self, "Invalid email address.", 400)
                exists = c.execute(
                    "SELECT 1 FROM members WHERE group_id=? AND phone=?",
                    (target_gid, phone),
                ).fetchone()
                if exists:
                    return error(self, "A member with this phone number already exists in the group.", 409)
                group = c.execute("SELECT contribution_amount FROM groups WHERE id=?", (target_gid,)).fetchone()
                if not group:
                    return error(self, "Group not found.", 404)
                expected = float(data.get("expected") or group["contribution_amount"]) * share_count
                if not password:
                    password = secrets.token_urlsafe(9)
                    temporary_password = password
                c.execute(
                    """INSERT INTO members
                       (group_id, member_code, name, email, phone, expected, rotation_position,
                        enrolled, password_hash, pin_hash, share_count)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        target_gid, None, name, email or None, phone, expected,
                        int(data.get("rotation_position") or 1),
                        1 if data.get("enrolled", True) else 0,
                        hash_password(password),
                        pin_hash_val,
                        share_count,
                    ),
                )
                mid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                member_code = make_member_code(mid)
                c.execute("UPDATE members SET member_code=? WHERE id=?", (member_code, mid))
                c.commit()
                member = c.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
                resp = {
                    "ok": True,
                    "member": clean_member(member),
                    "member_login_id": member_code,
                    "phone": phone,
                    "share_count": share_count,
                }
                if temporary_password:
                    resp["temporary_password"] = temporary_password
                if pin:
                    resp["pin_set"] = True
                new_member_email = str(email or "").strip().lower()
                if valid_email(new_member_email):
                    if temporary_password:
                        creds_line = f"Temporary password: {temporary_password}\n"
                    elif pin:
                        creds_line = f"PIN: {pin}\n"
                    elif password:
                        creds_line = "Password/PIN: the one set by your group administrator.\n"
                    else:
                        creds_line = ""
                    body = (
                        f"Hello {name},\n\n"
                        f"You have been added to the Njangi group.\n\n"
                        f"Member ID: {member_code}\n"
                        f"{creds_line}"
                        f"Sign in at the member portal with your Member ID (or phone) and password/PIN.\n\n"
                        f"Njangi Tracker"
                    )
                    print(f"[MEMBER CREATED] Sending welcome email directly to {new_member_email}")
                    ok_mail, mail_err = send_email(
                        new_member_email,
                        "Njangi Tracker - Your Member Account",
                        body,
                    )
                    if ok_mail:
                        print(f"[SMTP SUCCESS] Sent welcome email FROM {os.getenv('NJANGI_SMTP_FROM', os.getenv('NJANGI_SMTP_USERNAME', ''))} TO {new_member_email}")
                    else:
                        print(f"[MEMBER CREATED] Welcome email FAILED for {new_member_email}: {mail_err}")
                return send_json(self, resp)

            # GET /api/v1/members/dashboard  (member savings, payout status, loan balance)
            if path == "/api/v1/members/dashboard" and method == "GET":
                if not session or session.get("role") != "member":
                    return error(self, "Member authentication required.", 401)
                gid = session["group_id"]
                mid = session["user_id"]
                member = c.execute(
                    "SELECT * FROM members WHERE id=? AND group_id=?", (mid, gid)
                ).fetchone()
                if not member:
                    return error(self, "Member not found.", 404)
                cycle = c.execute(
                    "SELECT * FROM cycles WHERE group_id=? AND status='OPEN' ORDER BY number DESC LIMIT 1",
                    (gid,),
                ).fetchone()
                # Savings = sum of contributions paid by this member
                savings_row = c.execute(
                    "SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE member_id=? AND group_id=?",
                    (mid, gid),
                ).fetchone()
                savings = float(savings_row["total"] or 0)
                # Active loan balance
                loan_row = c.execute(
                    """SELECT COALESCE(SUM(total_due - amount_repaid),0) AS balance
                       FROM loans WHERE member_id=? AND group_id=?
                       AND status IN ('Approved','Disbursed','Active','PENDING')""",
                    (mid, gid),
                ).fetchone()
                loan_balance = float(loan_row["balance"] or 0)
                # Payout status for current cycle
                payout_status = "Not applicable"
                if cycle:
                    if cycle["recipient_id"] == mid:
                        if cycle["status"] == "PAID_OUT" or (cycle["paid_out_amount"] or 0) > 0:
                            payout_status = "Paid out"
                        else:
                            payout_status = "Pending payout (you are the recipient)"
                    else:
                        payout_status = "Waiting for cycle"
                status, paid, expected = member_cycle_status(c, mid, cycle) if cycle else ("N/A", 0, float(member["expected"] or 0))
                return send_json(self, {
                    "ok": True,
                    "member": {
                        "id": member["id"],
                        "name": member["name"],
                        "member_code": member["member_code"],
                        "phone": member["phone"],
                        "email": member["email"],
                    },
                    "savings": savings,
                    "loan_balance": loan_balance,
                    "payout_status": payout_status,
                    "current_cycle": {
                        "id": cycle["id"] if cycle else None,
                        "number": cycle["number"] if cycle else None,
                        "status": cycle["status"] if cycle else None,
                        "contribution_status": status,
                        "paid": paid,
                        "expected": expected,
                    } if cycle else None,
                })

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
                same_group_admin = c.execute("SELECT 1 FROM admins WHERE group_id=? AND lower(email)=?", (gid, email)).fetchone()
                same_group_member = c.execute("SELECT 1 FROM members WHERE group_id=? AND lower(email)=?", (gid, email)).fetchone()
                if same_group_admin or same_group_member:
                    return error(self, "That email is already used by an account in this Njangi group.")
                group = c.execute("SELECT contribution_amount FROM groups WHERE id=?", (gid,)).fetchone()
                expected = float(data.get("expected") or group["contribution_amount"])
                password = str(data.get("password") or data.get("pin") or "").strip()
                temporary = False
                pin_hash_val = None
                if password:
                    # User-provided password/PIN: hash as-is (PIN may be 4 digits)
                    if re.fullmatch(r"\d{4}", password):
                        try:
                            pin_hash_val = hash_pin(password)
                        except ValueError:
                            pin_hash_val = None
                    # Always store password_hash so email/password login still works
                    pwd_hash = hash_password(password)
                else:
                    # Only auto-generate when the admin left the field empty
                    password = secrets.token_urlsafe(9)
                    temporary = True
                    pwd_hash = hash_password(password)
                try:
                    c.execute(
                        """INSERT INTO members(group_id,member_code,name,email,phone,expected,rotation_position,enrolled,password_hash,pin_hash,share_count)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (gid, None, name, email, phone, expected, int(data.get("rotation_position") or 1), 1 if data.get("enrolled", True) else 0, pwd_hash, pin_hash_val, int(data.get("share_count") or 1)),
                    )
                except sqlite3.OperationalError:
                    c.execute(
                        """INSERT INTO members(group_id,member_code,name,email,phone,expected,rotation_position,enrolled,password_hash)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (gid, None, name, email, phone, expected, int(data.get("rotation_position") or 1), 1 if data.get("enrolled", True) else 0, pwd_hash),
                    )
                mid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                member_code = make_member_code(mid)
                c.execute("UPDATE members SET member_code=? WHERE id=?", (member_code, mid))
                c.commit()
                member = c.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone()
                response = {"ok": True, "member": clean_member(member), "member_login_id": member_code}
                if temporary:
                    response["temporary_password"] = password
                # Welcome / credentials email → member's own email only (never admin/env fallback)
                new_member_email = str(email or "").strip().lower()
                if valid_email(new_member_email):
                    creds_line = (
                        f"Temporary password: {password}\n"
                        if temporary
                        else "Password/PIN: the one set by your group administrator.\n"
                    )
                    body = (
                        f"Hello {name},\n\n"
                        f"You have been added to the Njangi group.\n\n"
                        f"Member ID: {member_code}\n"
                        f"{creds_line}"
                        f"Sign in at the member portal with your Member ID (or phone) and password/PIN.\n\n"
                        f"Njangi Tracker"
                    )
                    print(f"[MEMBER CREATED] Sending welcome email directly to {new_member_email}")
                    ok_mail, mail_err = send_email(
                        new_member_email,
                        "Njangi Tracker - Your Member Account",
                        body,
                    )
                    if ok_mail:
                        print(f"[SMTP SUCCESS] Sent welcome email FROM {os.getenv('NJANGI_SMTP_FROM', os.getenv('NJANGI_SMTP_USERNAME', ''))} TO {new_member_email}")
                    else:
                        print(f"[MEMBER CREATED] Welcome email FAILED for {new_member_email}: {mail_err}")
                else:
                    print(f"[MEMBER CREATED] No valid email for member {member_code}; skipped welcome email")
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
                    has_history = c.execute(
                        "SELECT 1 FROM contributions WHERE member_id=? UNION SELECT 1 FROM loans WHERE member_id=? UNION SELECT 1 FROM cycle_member_expected WHERE member_id=? LIMIT 1",
                        (mid, mid, mid),
                    ).fetchone()
                    if has_history:
                        return error(self, "This member has financial history and cannot be deleted. Deactivate the member instead by turning off Enrolled.", 409)
                    c.execute("DELETE FROM members WHERE id=? AND group_id=?", (mid, gid))
                    c.commit()
                    return send_json(self, {"ok": True})
                data = request_body(self)
                new_email = str(data.get("email", row["email"] or "")).strip().lower()
                if not valid_email(new_email):
                    return error(self, "A valid email is required for password recovery.")
                duplicate = c.execute("SELECT 1 FROM admins WHERE group_id=? AND lower(email)=?", (gid, new_email)).fetchone() or c.execute("SELECT 1 FROM members WHERE group_id=? AND lower(email)=? AND id!=?", (gid, new_email, mid)).fetchone()
                if duplicate:
                    return error(self, "That email is already used by another account in this Njangi group.")
                c.execute(
                    """UPDATE members SET name=?,email=?,phone=?,expected=?,rotation_position=?,enrolled=?
                       WHERE id=? AND group_id=?""",
                    (str(data.get("name", row["name"])).strip(), new_email, str(data.get("phone", row["phone"])).strip(), float(data.get("expected", row["expected"])), int(data.get("rotation_position", row["rotation_position"])), 1 if data.get("enrolled", row["enrolled"]) else 0, mid, gid),
                )
                c.commit()
                return send_json(self, {"ok": True, "member": clean_member(c.execute("SELECT * FROM members WHERE id=?", (mid,)).fetchone())})

            if path == "/api/auth/change-password" and method == "POST":
                data = request_body(self)
                current = str(data.get("current_password", ""))
                new = str(data.get("new_password", ""))
                if len(new) < 8:
                    return error(self, "New password must be at least 8 characters.")
                table = "admins" if role == "admin" else "members"
                row = c.execute(f"SELECT password_hash FROM {table} WHERE id=?", (session["user_id"],)).fetchone()
                if not row or not check_password(current, row["password_hash"]):
                    return error(self, "Your current password is incorrect.", 403)
                c.execute(f"UPDATE {table} SET password_hash=? WHERE id=?", (hash_password(new), session["user_id"]))
                c.commit()
                return send_json(self, {"ok": True, "message": "Password changed."})

            if path == "/api/alerts" and method == "GET" and role == "admin":
                alerts = []
                cycle = active_cycle(c, gid)
                pending = c.execute("SELECT COUNT(*) AS n FROM loans WHERE group_id=? AND status='PENDING'", (gid,)).fetchone()["n"]
                if pending:
                    alerts.append({"level": "warn", "text": f"{pending} loan request(s) waiting for your decision", "href": "loans.html"})
                if cycle:
                    days_left = (date.fromisoformat(cycle["end_date"]) - date.fromisoformat(today())).days
                    unpaid = [m["name"] for m in c.execute("SELECT id,name FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall()
                              if member_cycle_status(c, m["id"], cycle)[0] != "Paid"]
                    if days_left < 0:
                        alerts.append({"level": "danger", "text": f"Cycle #{cycle['number']} is {abs(days_left)} day(s) past its deadline", "href": "cycles.html"})
                    elif days_left <= CYCLE_REMINDER_DAYS:
                        alerts.append({"level": "warn", "text": f"Cycle #{cycle['number']} closes in {days_left} day(s)", "href": "cycles.html"})
                    if unpaid:
                        alerts.append({"level": "info", "text": f"{len(unpaid)} member(s) still owe this cycle: " + ", ".join(unpaid[:4]) + ("..." if len(unpaid) > 4 else ""), "href": "contributions.html"})
                    elif c.execute("SELECT 1 FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchone():
                        alerts.append({"level": "ok", "text": f"Everyone has paid for cycle #{cycle['number']} - you can close it", "href": "cycles.html"})
                else:
                    alerts.append({"level": "info", "text": "No active cycle. Create one to start collecting.", "href": "cycles.html"})
                owed = c.execute("SELECT id FROM cycles WHERE group_id=? AND status='CLOSED' AND paid_out_at IS NULL", (gid,)).fetchall()
                if owed:
                    alerts.append({"level": "warn", "text": f"{len(owed)} closed cycle(s) have no payout recorded", "href": "cycles.html"})
                if not smtp_configured():
                    alerts.append({"level": "info", "text": "Email is not configured: members will not receive notifications or reset PINs", "href": "#"})
                return send_json(self, {"ok": True, "alerts": alerts})

            if path.startswith("/api/members/") and path.endswith("/reset-password") and method == "POST" and role == "admin":
                try:
                    mid = int(path.split("/")[-2])
                except ValueError:
                    return error(self, "Invalid member ID.")
                row = c.execute("SELECT * FROM members WHERE id=? AND group_id=?", (mid, gid)).fetchone()
                if not row:
                    return error(self, "Member not found.", 404)
                temp = secrets.token_urlsafe(9)
                c.execute("UPDATE members SET password_hash=? WHERE id=?", (hash_password(temp), mid))
                c.execute("DELETE FROM sessions WHERE role='member' AND user_id=?", (mid,))
                c.commit()
                return send_json(self, {"ok": True, "member_login_id": row["member_code"], "temporary_password": temp})

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
                try:
                    c.execute("INSERT INTO cycles(group_id,number,target,start_date,end_date,recipient_id,status) VALUES(?,?,?,?,?,?,'OPEN')", (gid, number, target, start_date, end_date, recipient))
                except sqlite3.IntegrityError:
                    return error(self, "A cycle is already open for this group. Close it before creating another.", 409)
                cid = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                for member in c.execute("SELECT id,expected FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall():
                    c.execute("INSERT INTO cycle_member_expected(cycle_id,member_id,expected) VALUES(?,?,?)", (cid, member["id"], float(member["expected"] or 0)))
                c.commit()
                group_row = c.execute("SELECT name FROM groups WHERE id=?", (gid,)).fetchone()
                group_name = group_row["name"] if group_row else "your Njangi group"
                for m in c.execute("SELECT name,email FROM members WHERE group_id=? AND enrolled=1", (gid,)).fetchall():
                    notify(
                        m["email"],
                        f"Njangi Tracker - Cycle #{number} Opened",
                        f"Hello {m['name']},\n\nCycle #{number} in {group_name} is now open "
                        f"({start_date} to {end_date}). Target pool: {target:g} FCFA.\n\nNjangi Tracker",
                    )
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

            if path == "/api/cycles/payout" and method == "POST" and role == "admin":
                data = request_body(self)
                try:
                    cid = int(data.get("cycle_id") or 0)
                except (TypeError, ValueError):
                    return error(self, "Invalid cycle ID.")
                cycle = c.execute("SELECT * FROM cycles WHERE id=? AND group_id=?", (cid, gid)).fetchone()
                if not cycle:
                    return error(self, "Cycle not found.", 404)
                if cycle["status"] != "CLOSED":
                    return error(self, "Only closed cycles can be paid out.", 409)
                if cycle["paid_out_at"]:
                    return error(self, "This cycle already has a recorded payout.", 409)
                amount = float(data.get("amount") or 0)
                if amount <= 0:
                    amount = float(c.execute("SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE cycle_id=?", (cid,)).fetchone()["total"])
                if amount <= 0:
                    return error(self, "There is nothing to pay out for this cycle.")
                pay_date = str(data.get("date") or today())
                if pay_date > today():
                    return error(self, "Payout date cannot be in the future.")
                c.execute(
                    "UPDATE cycles SET paid_out_at=?,paid_out_amount=?,paid_out_by=? WHERE id=?",
                    (pay_date, amount, session["user_id"], cid),
                )
                c.commit()
                if cycle["recipient_id"]:
                    rec = c.execute("SELECT name,email FROM members WHERE id=?", (cycle["recipient_id"],)).fetchone()
                    if rec:
                        notify(
                            rec["email"],
                            f"Njangi Tracker - Payout for Cycle #{cycle['number']}",
                            f"Hello {rec['name']},\n\nA payout of {amount:g} FCFA for cycle #{cycle['number']} "
                            f"was recorded on {pay_date}.\n\nNjangi Tracker",
                        )
                return send_json(self, {"ok": True, "message": "Payout recorded."})

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
                # Admin-selected status (explicit). Default Paid if omitted.
                requested_status = str(data.get("status") or "Paid").strip().title()
                if requested_status not in ("Paid", "Partial", "Pending"):
                    return error(self, "status must be Paid, Partial, or Pending.", 400)
                _, paid, expected = member_cycle_status(c, mid, cycle)
                remaining = max(0.0, expected - paid) if expected > 0 else 0.0
                if expected > 0 and amount > remaining and requested_status != "Pending":
                    return error(self, f"Payment is higher than the remaining {remaining:g} FCFA for this member in the cycle.")
                contribution_date = str(data.get("date") or today())
                if contribution_date > today():
                    return error(self, "Payment date cannot be in the future.")
                c.execute(
                    "INSERT INTO contributions(group_id,member_id,cycle_id,amount,date,status) VALUES(?,?,?,?,?,?)",
                    (gid, mid, cid, amount, contribution_date, requested_status),
                )
                c.commit()
                if valid_email(member["email"] or ""):
                    notify(
                        member["email"],
                        f"Njangi Tracker - Payment Recorded (Cycle #{cycle['number']})",
                        f"Hello {member['name']},\n\nYour payment of {amount:g} FCFA for cycle "
                        f"#{cycle['number']} was recorded on {contribution_date} (status: {requested_status}). "
                        f"Total paid this cycle: {round(paid + amount, 2):g} FCFA.\n\nNjangi Tracker",
                    )
                return send_json(self, {"ok": True, "status": requested_status})

            if path.startswith("/api/contributions/") and method == "DELETE" and role == "admin":
                pid = int(path.split("/")[-1])
                payment = c.execute("SELECT p.id,cy.status FROM contributions p JOIN cycles cy ON cy.id=p.cycle_id WHERE p.id=? AND p.group_id=?", (pid, gid)).fetchone()
                if not payment:
                    return error(self, "Contribution not found.", 404)
                if payment["status"] == "CLOSED":
                    return error(self, "Closed-cycle contributions cannot be deleted because they affect reliability history.", 409)
                c.execute("DELETE FROM contributions WHERE id=? AND group_id=?", (pid, gid))
                c.commit()
                return send_json(self, {"ok": True})

            if path == "/api/history" and method == "GET" and role == "admin":
                rows = c.execute("SELECT p.*,m.name member_name,cy.number cycle_number FROM contributions p JOIN members m ON m.id=p.member_id JOIN cycles cy ON cy.id=p.cycle_id WHERE p.group_id=? ORDER BY p.date DESC,p.id DESC", (gid,)).fetchall()
                return send_json(self, {"ok": True, "history": [dict(x) for x in rows]})

            # ================================================================
            # Step — Loans & Financial Ledger (v1)
            # ================================================================

            # POST /api/v1/loans/apply  — member applies (amount + payback period)
            if path == "/api/v1/loans/apply" and method == "POST":
                if not session:
                    return error(self, "Authentication required.", 401)
                data = request_body(self)
                member_id = session["user_id"] if session.get("role") == "member" else int(data.get("member_id") or 0)
                if session.get("role") == "member" and member_id != session["user_id"]:
                    return error(self, "You can only apply for a loan for yourself.", 403)
                gid = session["group_id"]
                member = c.execute(
                    "SELECT * FROM members WHERE id=? AND group_id=? AND enrolled=1",
                    (member_id, gid),
                ).fetchone()
                amount = float(data.get("amount") or 0)
                reason = str(data.get("reason") or "").strip()
                payback_months = int(data.get("payback_months") or data.get("payback_period") or 1)
                required_guarantors = int(data.get("required_guarantors") or 1)
                guarantor_ids = data.get("guarantor_ids") or data.get("guarantors") or []
                if not isinstance(guarantor_ids, list):
                    guarantor_ids = []
                guarantor_ids = [int(x) for x in guarantor_ids if str(x).isdigit()]
                if not member or amount <= 0 or not reason:
                    return error(self, "A valid member, amount, and reason are required.", 400)
                if payback_months < 1 or payback_months > 36:
                    return error(self, "Payback period must be between 1 and 36 months.", 400)
                if required_guarantors < 1 or required_guarantors > 3:
                    return error(self, "required_guarantors must be between 1 and 3.", 400)
                outstanding = c.execute(
                    "SELECT 1 FROM loans WHERE member_id=? AND group_id=? AND status IN ('PENDING','APPROVED','ACTIVE')",
                    (member_id, gid),
                ).fetchone()
                if outstanding:
                    return error(self, "You already have an outstanding loan request or active loan.", 409)
                rate = float(data.get("interest_rate") or 5)
                if rate < 0 or rate > 100:
                    return error(self, "Interest rate must be between 0 and 100 percent.", 400)
                # Validate nominated guarantors belong to same group and are not the borrower
                for gid_g in guarantor_ids:
                    if gid_g == member_id:
                        return error(self, "You cannot nominate yourself as guarantor.", 400)
                    gmem = c.execute(
                        "SELECT id FROM members WHERE id=? AND group_id=? AND enrolled=1",
                        (gid_g, gid),
                    ).fetchone()
                    if not gmem:
                        return error(self, f"Guarantor member id {gid_g} is not a valid enrolled member of this group.", 400)
                c.execute(
                    """INSERT INTO loans
                       (group_id, member_id, amount, reason, status, date_requested,
                        interest_rate, total_due, amount_repaid, payback_months, required_guarantors)
                       VALUES (?,?,?,?,'PENDING',?,?,0,0,?,?)""",
                    (gid, member_id, amount, reason, now_local(), rate, payback_months, required_guarantors),
                )
                loan_id = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                for gid_g in guarantor_ids:
                    try:
                        c.execute(
                            "INSERT INTO loan_guarantors (loan_id, guarantor_member_id, status) VALUES (?,?, 'Pending')",
                            (loan_id, gid_g),
                        )
                    except sqlite3.IntegrityError:
                        pass
                # Ledger: application recorded as zero-amount adjustment for audit
                c.execute(
                    """INSERT INTO ledger_transactions
                       (group_id, member_id, loan_id, tx_type, direction, amount, description, recorded_by)
                       VALUES (?,?,?,'ADJUSTMENT','IN',0,?,?)""",
                    (gid, member_id, loan_id, f"Loan application #{loan_id}: {amount:g} FCFA, {payback_months} mo", session["user_id"]),
                )
                c.commit()
                return send_json(self, {
                    "ok": True,
                    "message": "Loan application submitted. Awaiting guarantor sign-off and admin approval.",
                    "loan_id": loan_id,
                    "payback_months": payback_months,
                    "required_guarantors": required_guarantors,
                    "guarantors_nominated": len(guarantor_ids),
                })

            # POST /api/v1/loans/<loan_id>/guarantee  — guarantor digitally signs
            m_g = re.fullmatch(r"/api/v1/loans/(\d+)/guarantee", path)
            if m_g and method == "POST":
                if not session:
                    return error(self, "Authentication required.", 401)
                try:
                    loan_id = int(m_g.group(1))
                except ValueError:
                    return error(self, "Invalid loan ID.", 400)
                data = request_body(self)
                decision = str(data.get("decision") or data.get("status") or "Accepted").strip().title()
                if decision not in ("Accepted", "Rejected"):
                    return error(self, "decision must be 'Accepted' or 'Rejected'.", 400)
                note = str(data.get("note") or "").strip()[:500]
                gid = session["group_id"]
                loan = c.execute(
                    "SELECT * FROM loans WHERE id=? AND group_id=?", (loan_id, gid)
                ).fetchone()
                if not loan:
                    return error(self, "Loan not found.", 404)
                if loan["status"] not in ("PENDING", "Pending", "Requested"):
                    return error(self, "Only pending loans can receive guarantor decisions.", 409)
                # Guarantor is the logged-in member (or admin acting for testing)
                guarantor_id = session["user_id"] if session.get("role") == "member" else int(data.get("guarantor_member_id") or 0)
                if not guarantor_id:
                    return error(self, "Guarantor identity required.", 400)
                if guarantor_id == loan["member_id"]:
                    return error(self, "Borrower cannot guarantee their own loan.", 400)
                # Ensure a pending guarantor row exists (create if admin nominated on the fly)
                row = c.execute(
                    "SELECT * FROM loan_guarantors WHERE loan_id=? AND guarantor_member_id=?",
                    (loan_id, guarantor_id),
                ).fetchone()
                if not row:
                    # Auto-create if under the required count
                    count = c.execute(
                        "SELECT COUNT(*) AS n FROM loan_guarantors WHERE loan_id=?", (loan_id,)
                    ).fetchone()["n"]
                    req = int(loan["required_guarantors"] or 1) if "required_guarantors" in loan.keys() else 1
                    if count >= req and session.get("role") != "admin":
                        return error(self, "You are not nominated as a guarantor for this loan.", 403)
                    c.execute(
                        "INSERT INTO loan_guarantors (loan_id, guarantor_member_id, status) VALUES (?,?, 'Pending')",
                        (loan_id, guarantor_id),
                    )
                c.execute(
                    "UPDATE loan_guarantors SET status=?, signed_at=?, note=? WHERE loan_id=? AND guarantor_member_id=?",
                    (decision, now_local(), note or None, loan_id, guarantor_id),
                )
                # Count accepted
                accepted = c.execute(
                    "SELECT COUNT(*) AS n FROM loan_guarantors WHERE loan_id=? AND status='Accepted'",
                    (loan_id,),
                ).fetchone()["n"]
                required = int(loan["required_guarantors"] or 1) if "required_guarantors" in loan.keys() else 1
                c.commit()
                return send_json(self, {
                    "ok": True,
                    "message": f"Guarantor decision recorded: {decision}.",
                    "loan_id": loan_id,
                    "decision": decision,
                    "accepted_count": accepted,
                    "required_guarantors": required,
                    "guarantees_complete": accepted >= required,
                })

            # POST /api/v1/loans/<loan_id>/approve  — admin approves or rejects
            m_a = re.fullmatch(r"/api/v1/loans/(\d+)/approve", path)
            if m_a and method == "POST":
                if not session or session.get("role") != "admin":
                    return error(self, "Admin authentication required.", 401)
                try:
                    loan_id = int(m_a.group(1))
                except ValueError:
                    return error(self, "Invalid loan ID.", 400)
                data = request_body(self)
                action = str(data.get("action") or data.get("decision") or "approve").strip().lower()
                if action not in ("approve", "reject"):
                    return error(self, "action must be 'approve' or 'reject'.", 400)
                gid = session["group_id"]
                loan = c.execute(
                    "SELECT * FROM loans WHERE id=? AND group_id=?", (loan_id, gid)
                ).fetchone()
                if not loan:
                    return error(self, "Loan not found.", 404)
                if loan["status"] not in ("PENDING", "Pending", "Requested"):
                    return error(self, "Only pending loans can be approved or rejected.", 409)

                if action == "reject":
                    c.execute(
                        "UPDATE loans SET status='REJECTED', approved_by=?, date_approved=? WHERE id=?",
                        (session["user_id"], now_local(), loan_id),
                    )
                    c.execute(
                        """INSERT INTO ledger_transactions
                           (group_id, member_id, loan_id, tx_type, direction, amount, description, recorded_by)
                           VALUES (?,?,?,'ADJUSTMENT','OUT',0,?,?)""",
                        (gid, loan["member_id"], loan_id, f"Loan #{loan_id} rejected", session["user_id"]),
                    )
                    c.commit()
                    mem = c.execute("SELECT name,email FROM members WHERE id=?", (loan["member_id"],)).fetchone()
                    if mem and mem["email"]:
                        notify(mem["email"], "Njangi Tracker - Loan Update",
                               f"Hello {mem['name']},\n\nYour loan request of {float(loan['amount']):g} FCFA was not approved.\n\nNjangi Tracker")
                    return send_json(self, {"ok": True, "message": "Loan rejected.", "status": "REJECTED"})

                # --- approve path ---
                required = int(loan["required_guarantors"] or 1) if "required_guarantors" in loan.keys() else 1
                accepted = c.execute(
                    "SELECT COUNT(*) AS n FROM loan_guarantors WHERE loan_id=? AND status='Accepted'",
                    (loan_id,),
                ).fetchone()["n"]
                # Allow admin override via force=true
                force = bool(data.get("force"))
                if accepted < required and not force:
                    return error(
                        self,
                        f"Guarantor sign-off incomplete ({accepted}/{required}). "
                        "Wait for guarantors or pass force=true to override.",
                        409,
                    )
                reliability = reliability_for_member(c, loan["member_id"], gid)
                if not force:
                    if reliability["completed_cycles"] < LOAN_MIN_CYCLES:
                        return error(self, f"Member needs at least {LOAN_MIN_CYCLES} completed cycle(s).", 409)
                    if reliability["score"] < LOAN_MIN_RELIABILITY:
                        return error(
                            self,
                            f"Member reliability is {reliability['score']}%, below the required {LOAN_MIN_RELIABILITY}%.",
                            409,
                        )
                rate = float(data.get("interest_rate", loan["interest_rate"] or 5))
                if rate < 0 or rate > 100:
                    return error(self, "Interest rate must be between 0 and 100 percent.", 400)
                pool = float(c.execute(
                    "SELECT COALESCE(SUM(amount),0) AS total FROM contributions WHERE group_id=?", (gid,)
                ).fetchone()["total"])
                outstanding_loans = 0.0
                for ol in c.execute(
                    "SELECT amount,amount_repaid,total_due,interest_rate FROM loans WHERE group_id=? AND status IN ('APPROVED','ACTIVE')",
                    (gid,),
                ).fetchall():
                    due = float(ol["total_due"] or 0) or round(float(ol["amount"]) * (1 + float(ol["interest_rate"] or 0) / 100), 2)
                    outstanding_loans += max(0, due - float(ol["amount_repaid"] or 0))
                available = max(0, pool - outstanding_loans)
                if float(loan["amount"]) > available and not force:
                    return error(self, f"Available loan pool is {round(available, 2):g} FCFA.", 409)
                total_due = round(float(loan["amount"]) * (1 + rate / 100), 2)
                c.execute(
                    """UPDATE loans SET status='APPROVED', interest_rate=?, total_due=?,
                       approved_by=?, date_approved=? WHERE id=?""",
                    (rate, total_due, session["user_id"], now_local(), loan_id),
                )
                # Ledger: loan disbursement OUT
                c.execute(
                    """INSERT INTO ledger_transactions
                       (group_id, member_id, loan_id, tx_type, direction, amount, description, recorded_by)
                       VALUES (?,?,?,'LOAN_DISBURSE','OUT',?,?,?)""",
                    (gid, loan["member_id"], loan_id, float(loan["amount"]),
                     f"Loan #{loan_id} approved/disbursed at {rate:g}% (total due {total_due:g})",
                     session["user_id"]),
                )
                c.commit()
                mem = c.execute("SELECT name,email FROM members WHERE id=?", (loan["member_id"],)).fetchone()
                if mem and mem["email"]:
                    notify(
                        mem["email"],
                        "Njangi Tracker - Loan Approved",
                        f"Hello {mem['name']},\n\nYour loan of {float(loan['amount']):g} FCFA has been approved "
                        f"at {rate:g}% interest. Total due: {total_due:g} FCFA. "
                        f"Payback period: {loan['payback_months'] if 'payback_months' in loan.keys() else 1} month(s).\n\nNjangi Tracker",
                    )
                return send_json(self, {
                    "ok": True,
                    "message": "Loan approved.",
                    "status": "APPROVED",
                    "total_due": total_due,
                    "reliability": reliability,
                    "guarantors_accepted": accepted,
                })


            # ================================================================
            # Payout Rotation & Bidding Engine
            # ================================================================

            # POST /api/v1/payouts/bid
            if path == "/api/v1/payouts/bid" and method == "POST":
                if not session:
                    return error(self, "Authentication required.", 401)
                data = request_body(self)
                gid = session["group_id"]
                member_id = session["user_id"] if session.get("role") == "member" else int(data.get("member_id") or 0)
                if session.get("role") == "member":
                    member_id = session["user_id"]
                discount = float(data.get("discount_amount") or data.get("discount") or 0)
                bid_percent = float(data.get("bid_percent") or 0)
                if discount < 0 or bid_percent < 0:
                    return error(self, "Discount cannot be negative.", 400)
                # Active payout cycle in BIDDING or OPEN
                pc = c.execute(
                    "SELECT * FROM payout_cycles WHERE group_id=? AND status IN ('OPEN','BIDDING') ORDER BY number DESC LIMIT 1",
                    (gid,),
                ).fetchone()
                if not pc:
                    # Auto-create from current open contribution cycle
                    cy = active_cycle(c, gid)
                    if not cy:
                        return error(self, "No open cycle available for bidding.", 404)
                    next_num = (c.execute("SELECT COALESCE(MAX(number),0) FROM payout_cycles WHERE group_id=?", (gid,)).fetchone()[0] or 0) + 1
                    pot = float(c.execute("SELECT COALESCE(SUM(amount),0) FROM contributions WHERE cycle_id=?", (cy["id"],)).fetchone()[0] or 0)
                    c.execute(
                        """INSERT INTO payout_cycles (group_id, cycle_id, number, pot_amount, status, bidding_opens)
                           VALUES (?,?,?,?,'BIDDING',?)""",
                        (gid, cy["id"], next_num, pot, now_local()),
                    )
                    pc_id = c.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                    pc = c.execute("SELECT * FROM payout_cycles WHERE id=?", (pc_id,)).fetchone()
                if pc["status"] not in ("OPEN", "BIDDING"):
                    return error(self, "Bidding is closed for this payout cycle.", 409)
                if discount > float(pc["pot_amount"] or 0):
                    return error(self, "Discount cannot exceed pot amount.", 400)
                member = c.execute("SELECT id FROM members WHERE id=? AND group_id=? AND enrolled=1", (member_id, gid)).fetchone()
                if not member:
                    return error(self, "Member not found in this group.", 404)
                try:
                    c.execute(
                        """INSERT INTO pot_bids (payout_cycle_id, group_id, member_id, discount_amount, bid_percent, status)
                           VALUES (?,?,?,?,?,'Active')
                           ON CONFLICT(payout_cycle_id, member_id) DO UPDATE SET
                             discount_amount=excluded.discount_amount,
                             bid_percent=excluded.bid_percent,
                             status='Active',
                             created_at=CURRENT_TIMESTAMP""",
                        (pc["id"], gid, member_id, discount, bid_percent),
                    )
                except sqlite3.OperationalError:
                    # SQLite without UPSERT support on older versions – delete+insert
                    c.execute("DELETE FROM pot_bids WHERE payout_cycle_id=? AND member_id=?", (pc["id"], member_id))
                    c.execute(
                        """INSERT INTO pot_bids (payout_cycle_id, group_id, member_id, discount_amount, bid_percent, status)
                           VALUES (?,?,?,?,?,'Active')""",
                        (pc["id"], gid, member_id, discount, bid_percent),
                    )
                if pc["status"] == "OPEN":
                    c.execute("UPDATE payout_cycles SET status='BIDDING' WHERE id=?", (pc["id"],))
                c.commit()
                bid = c.execute(
                    "SELECT * FROM pot_bids WHERE payout_cycle_id=? AND member_id=?", (pc["id"], member_id)
                ).fetchone()
                return send_json(self, {
                    "ok": True,
                    "message": "Bid submitted.",
                    "bid": dict(bid) if bid else None,
                    "payout_cycle_id": pc["id"],
                    "pot_amount": pc["pot_amount"],
                })

            # GET /api/v1/payouts/schedule
            if path == "/api/v1/payouts/schedule" and method == "GET":
                if not session:
                    return error(self, "Authentication required.", 401)
                gid = session["group_id"]
                cycles_rows = c.execute(
                    "SELECT * FROM cycles WHERE group_id=? ORDER BY number", (gid,)
                ).fetchall()
                payouts = c.execute(
                    "SELECT * FROM payout_cycles WHERE group_id=? ORDER BY number DESC", (gid,)
                ).fetchall()
                schedule = []
                for cy in cycles_rows:
                    recipient = None
                    if cy["recipient_id"]:
                        m = c.execute("SELECT id,name,member_code FROM members WHERE id=?", (cy["recipient_id"],)).fetchone()
                        recipient = dict(m) if m else None
                    schedule.append({
                        "cycle_id": cy["id"],
                        "number": cy["number"],
                        "status": cy["status"],
                        "start_date": cy["start_date"],
                        "end_date": cy["end_date"],
                        "target": cy["target"],
                        "recipient": recipient,
                        "paid_out_at": cy["paid_out_at"] if "paid_out_at" in cy.keys() else None,
                        "paid_out_amount": cy["paid_out_amount"] if "paid_out_amount" in cy.keys() else 0,
                    })
                current = None
                if payouts:
                    p = payouts[0]
                    bids = c.execute(
                        """SELECT b.*, m.name member_name FROM pot_bids b
                           JOIN members m ON m.id=b.member_id
                           WHERE b.payout_cycle_id=? ORDER BY b.discount_amount DESC""",
                        (p["id"],),
                    ).fetchall()
                    beneficiary = None
                    if p["beneficiary_member_id"]:
                        bm = c.execute("SELECT id,name,member_code FROM members WHERE id=?", (p["beneficiary_member_id"],)).fetchone()
                        beneficiary = dict(bm) if bm else None
                    current = {
                        "payout_cycle_id": p["id"],
                        "number": p["number"],
                        "status": p["status"],
                        "pot_amount": p["pot_amount"],
                        "beneficiary": beneficiary,
                        "bids": [dict(b) for b in bids],
                        "disbursed_at": p["disbursed_at"],
                    }
                return send_json(self, {"ok": True, "schedule": schedule, "current_payout": current})

            # POST /api/v1/payouts/disburse
            if path == "/api/v1/payouts/disburse" and method == "POST":
                if not session or session.get("role") != "admin":
                    return error(self, "Admin authentication required.", 401)
                data = request_body(self)
                gid = session["group_id"]
                pc_id = data.get("payout_cycle_id")
                if pc_id:
                    pc = c.execute("SELECT * FROM payout_cycles WHERE id=? AND group_id=?", (int(pc_id), gid)).fetchone()
                else:
                    pc = c.execute(
                        "SELECT * FROM payout_cycles WHERE group_id=? AND status IN ('OPEN','BIDDING','AWARDED') ORDER BY number DESC LIMIT 1",
                        (gid,),
                    ).fetchone()
                if not pc:
                    return error(self, "No disbursable payout cycle found.", 404)
                if pc["status"] == "DISBURSED":
                    return error(self, "This pot has already been disbursed.", 409)
                # Winner = highest discount bid, or explicit beneficiary, or cycle recipient
                winner_id = data.get("beneficiary_member_id") or pc["beneficiary_member_id"]
                winning_bid = None
                if not winner_id:
                    winning_bid = c.execute(
                        """SELECT * FROM pot_bids WHERE payout_cycle_id=? AND status='Active'
                           ORDER BY discount_amount DESC, created_at ASC LIMIT 1""",
                        (pc["id"],),
                    ).fetchone()
                    if winning_bid:
                        winner_id = winning_bid["member_id"]
                if not winner_id:
                    cy = c.execute("SELECT recipient_id FROM cycles WHERE id=?", (pc["cycle_id"],)).fetchone() if pc["cycle_id"] else None
                    winner_id = cy["recipient_id"] if cy else None
                if not winner_id:
                    return error(self, "No beneficiary determined. Assign a recipient or accept a bid first.", 400)
                discount = float(winning_bid["discount_amount"]) if winning_bid else 0.0
                amount = max(0, float(pc["pot_amount"] or 0) - discount)
                # Mark bids
                c.execute("UPDATE pot_bids SET status='Lost' WHERE payout_cycle_id=? AND status='Active'", (pc["id"],))
                if winning_bid:
                    c.execute("UPDATE pot_bids SET status='Won' WHERE id=?", (winning_bid["id"],))
                c.execute(
                    """UPDATE payout_cycles SET status='DISBURSED', beneficiary_member_id=?,
                       disbursed_at=?, disbursed_by=?, winning_bid_id=?, pot_amount=? WHERE id=?""",
                    (winner_id, now_local(), session["user_id"], winning_bid["id"] if winning_bid else None, amount, pc["id"]),
                )
                # Mirror onto contribution cycle if linked
                if pc["cycle_id"]:
                    c.execute(
                        """UPDATE cycles SET status='CLOSED', paid_out_at=?, paid_out_amount=?, paid_out_by=?, recipient_id=?
                           WHERE id=?""",
                        (now_local(), amount, session["user_id"], winner_id, pc["cycle_id"]),
                    )
                c.execute(
                    """INSERT INTO ledger_transactions
                       (group_id, member_id, fund_type, tx_type, direction, amount, description, recorded_by)
                       VALUES (?,?, 'MAIN_POT', 'PAYOUT', 'OUT', ?, ?, ?)""",
                    (gid, winner_id, amount, f"Pot disbursement payout_cycle #{pc['id']} to member {winner_id}", session["user_id"]),
                )
                c.commit()
                winner = c.execute("SELECT id,name,member_code,phone FROM members WHERE id=?", (winner_id,)).fetchone()
                return send_json(self, {
                    "ok": True,
                    "message": "Pot disbursed.",
                    "amount": amount,
                    "discount": discount,
                    "beneficiary": dict(winner) if winner else None,
                    "payout_cycle_id": pc["id"],
                })

            # ================================================================
            # Multi-Fund balances
            # ================================================================

            if path == "/api/v1/funds/balances" and method == "GET":
                if not session:
                    return error(self, "Authentication required.", 401)
                gid = session["group_id"]
                balances = {}
                for ft in ("MAIN_POT", "CAISSE_SOCIALE", "INVESTMENT_PROJECT"):
                    row = c.execute(
                        """SELECT
                             COALESCE(SUM(CASE WHEN direction='IN' THEN amount ELSE 0 END),0) AS inflow,
                             COALESCE(SUM(CASE WHEN direction='OUT' THEN amount ELSE 0 END),0) AS outflow
                           FROM ledger_transactions WHERE group_id=? AND fund_type=?""",
                        (gid, ft),
                    ).fetchone()
                    balances[ft] = {
                        "inflow": float(row["inflow"]),
                        "outflow": float(row["outflow"]),
                        "balance": float(row["inflow"]) - float(row["outflow"]),
                    }
                return send_json(self, {"ok": True, "funds": balances})

            # POST /api/v1/funds/transfer or social grant
            if path == "/api/v1/funds/grant" and method == "POST":
                if not session or session.get("role") != "admin":
                    return error(self, "Admin authentication required.", 401)
                data = request_body(self)
                gid = session["group_id"]
                amount = float(data.get("amount") or 0)
                member_id = int(data.get("member_id") or 0)
                fund_type = str(data.get("fund_type") or "CAISSE_SOCIALE").upper()
                if fund_type not in ("CAISSE_SOCIALE", "INVESTMENT_PROJECT", "MAIN_POT"):
                    return error(self, "Invalid fund_type.", 400)
                if amount <= 0 or not member_id:
                    return error(self, "amount and member_id required.", 400)
                desc = str(data.get("description") or f"{fund_type} grant").strip()
                c.execute(
                    """INSERT INTO ledger_transactions
                       (group_id, member_id, fund_type, tx_type, direction, amount, description, recorded_by)
                       VALUES (?,?,?, 'SOCIAL_GRANT', 'OUT', ?, ?, ?)""",
                    (gid, member_id, fund_type, amount, desc, session["user_id"]),
                )
                c.commit()
                return send_json(self, {"ok": True, "message": "Grant recorded.", "fund_type": fund_type, "amount": amount})

            # ================================================================
            # Mobile Money webhook
            # ================================================================

            # POST /api/v1/payments/momo/initiate — create pending MoMo intent
            if path == "/api/v1/payments/momo/initiate" and method == "POST":
                if not session:
                    return error(self, "Authentication required.", 401)
                data = request_body(self)
                gid = session["group_id"]
                member_id = session["user_id"] if session.get("role") == "member" else int(data.get("member_id") or 0)
                amount = float(data.get("amount") or 0)
                provider = str(data.get("provider") or "MTN").upper()
                if amount <= 0:
                    return error(self, "amount must be positive.", 400)
                cycle = active_cycle(c, gid)
                if not cycle:
                    return error(self, "No open cycle.", 404)
                ref = f"NJG-{gid}-{member_id}-{secrets.token_hex(6).upper()}"
                c.execute(
                    """INSERT INTO momo_pending (group_id, member_id, cycle_id, amount, provider, external_ref, status)
                       VALUES (?,?,?,?,?,?,'PENDING')""",
                    (gid, member_id, cycle["id"], amount, provider, ref),
                )
                c.commit()
                return send_json(self, {
                    "ok": True,
                    "external_ref": ref,
                    "amount": amount,
                    "provider": provider,
                    "message": "Present this reference to the Mobile Money checkout. Webhook will mark paid.",
                })

            # ================================================================
            # Passbook PDF export
            # ================================================================

            m_pb = re.fullmatch(r"/api/v1/members/(\d+)/passbook/export", path)
            if m_pb and method == "GET":
                if not session:
                    return error(self, "Authentication required.", 401)
                try:
                    uid = int(m_pb.group(1))
                except ValueError:
                    return error(self, "Invalid member id.", 400)
                gid = session["group_id"]
                # Members may only export their own; admins any member in group
                if session.get("role") == "member" and session["user_id"] != uid:
                    return error(self, "You can only export your own passbook.", 403)
                member = c.execute(
                    "SELECT * FROM members WHERE id=? AND group_id=?", (uid, gid)
                ).fetchone()
                if not member:
                    return error(self, "Member not found.", 404)
                group = c.execute("SELECT * FROM groups WHERE id=?", (gid,)).fetchone()
                contribs = c.execute(
                    """SELECT p.*, cy.number cycle_number FROM contributions p
                       JOIN cycles cy ON cy.id=p.cycle_id
                       WHERE p.member_id=? AND p.group_id=? ORDER BY p.date, p.id""",
                    (uid, gid),
                ).fetchall()
                loans = c.execute(
                    "SELECT * FROM loans WHERE member_id=? AND group_id=? ORDER BY id", (uid, gid)
                ).fetchall()
                # Fines table may not exist on older DBs
                fines = []
                try:
                    fines = c.execute(
                        "SELECT * FROM fines WHERE membership_id=? OR member_id=? ORDER BY id",
                        (uid, uid),
                    ).fetchall()
                except sqlite3.OperationalError:
                    pass

                # Build PDF with reportlab
                try:
                    from reportlab.lib.pagesizes import A4
                    from reportlab.lib.units import mm
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.colors import HexColor
                    import io
                    buf = io.BytesIO()
                    pdf = canvas.Canvas(buf, pagesize=A4)
                    W, H = A4
                    y = H - 25 * mm
                    green = HexColor("#1a7a4c")
                    pdf.setFillColor(green)
                    pdf.setFont("Helvetica-Bold", 16)
                    pdf.drawString(20 * mm, y, "Njangi Tracker — Digital Passbook")
                    y -= 8 * mm
                    pdf.setFillColor(HexColor("#222222"))
                    pdf.setFont("Helvetica", 10)
                    pdf.drawString(20 * mm, y, f"Group: {group['name'] if group else '-'}")
                    y -= 5 * mm
                    pdf.drawString(20 * mm, y, f"Member: {member['name']}  |  ID: {member['member_code']}  |  Phone: {member['phone']}")
                    y -= 5 * mm
                    pdf.drawString(20 * mm, y, f"Generated: {now_local()}")
                    y -= 10 * mm
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawString(20 * mm, y, "Contribution History")
                    y -= 6 * mm
                    pdf.setFont("Helvetica", 9)
                    pdf.drawString(20 * mm, y, "Date")
                    pdf.drawString(45 * mm, y, "Cycle")
                    pdf.drawString(65 * mm, y, "Amount")
                    pdf.drawString(95 * mm, y, "Status")
                    y -= 5 * mm
                    total_paid = 0.0
                    for row in contribs:
                        if y < 25 * mm:
                            pdf.showPage()
                            y = H - 20 * mm
                        pdf.drawString(20 * mm, y, str(row["date"] or "-"))
                        pdf.drawString(45 * mm, y, f"#{row['cycle_number']}")
                        pdf.drawString(65 * mm, y, f"{float(row['amount']):,.0f} FCFA")
                        pdf.drawString(95 * mm, y, str(row["status"]))
                        total_paid += float(row["amount"] or 0)
                        y -= 5 * mm
                    y -= 3 * mm
                    pdf.setFont("Helvetica-Bold", 10)
                    pdf.drawString(20 * mm, y, f"Total contributions: {total_paid:,.0f} FCFA")
                    y -= 10 * mm
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawString(20 * mm, y, "Loans")
                    y -= 6 * mm
                    pdf.setFont("Helvetica", 9)
                    if not loans:
                        pdf.drawString(20 * mm, y, "No loans on record.")
                        y -= 5 * mm
                    for ln in loans:
                        if y < 25 * mm:
                            pdf.showPage()
                            y = H - 20 * mm
                        bal = max(0, float(ln["total_due"] or ln["amount"]) - float(ln["amount_repaid"] or 0))
                        pdf.drawString(20 * mm, y, f"{ln['date_requested']}  {float(ln['amount']):,.0f} FCFA  status={ln['status']}  balance={bal:,.0f}")
                        y -= 5 * mm
                    y -= 8 * mm
                    pdf.setFont("Helvetica-Bold", 12)
                    pdf.drawString(20 * mm, y, "Fines")
                    y -= 6 * mm
                    pdf.setFont("Helvetica", 9)
                    if not fines:
                        pdf.drawString(20 * mm, y, "No fines on record.")
                    else:
                        for f in fines:
                            pdf.drawString(20 * mm, y, f"{f['issued_at'] if 'issued_at' in f.keys() else ''}  {float(f['amount']):,.0f} FCFA  {f['reason']}  {f['status']}")
                            y -= 5 * mm
                    pdf.setFont("Helvetica", 8)
                    pdf.setFillColor(HexColor("#666666"))
                    pdf.drawString(20 * mm, 12 * mm, "Njangi Tracker — official member passbook export. Keep for your records.")
                    pdf.save()
                    pdf_bytes = buf.getvalue()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="passbook_{member["member_code"]}.pdf"')
                    self.send_header("Content-Length", str(len(pdf_bytes)))
                    self.end_headers()
                    self.wfile.write(pdf_bytes)
                    return
                except Exception as exc:
                    return error(self, f"PDF generation failed: {exc}", 500)

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
                    mem = c.execute("SELECT name,email FROM members WHERE id=?", (loan["member_id"],)).fetchone()
                    if mem:
                        notify(
                            mem["email"],
                            "Njangi Tracker - Loan Approved",
                            f"Hello {mem['name']},\n\nYour emergency loan of {float(loan['amount']):g} FCFA "
                            f"has been approved at {rate:g}% interest. Total due: {total_due:g} FCFA.\n\nNjangi Tracker",
                        )
                    return send_json(self, {"ok": True, "message": "Loan approved.", "total_due": total_due, "reliability": reliability})
                if action == "reject":
                    if loan["status"] != "PENDING":
                        return error(self, "Only pending loans can be rejected.")
                    c.execute("UPDATE loans SET status='REJECTED' WHERE id=?", (loan_id,))
                    c.commit()
                    mem = c.execute("SELECT name,email FROM members WHERE id=?", (loan["member_id"],)).fetchone()
                    if mem:
                        notify(
                            mem["email"],
                            "Njangi Tracker - Loan Update",
                            f"Hello {mem['name']},\n\nYour emergency loan request of {float(loan['amount']):g} "
                            f"FCFA was not approved. Contact your group administrator for details.\n\nNjangi Tracker",
                        )
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
                    mem = c.execute("SELECT name,email FROM members WHERE id=?", (loan["member_id"],)).fetchone()
                    if mem:
                        notify(
                            mem["email"],
                            "Njangi Tracker - Loan Repayment Recorded",
                            f"Hello {mem['name']},\n\nA repayment of {amount:g} FCFA on your loan was recorded. "
                            f"Remaining balance: {max(0, round(total_due - new_repaid, 2)):g} FCFA.\n\nNjangi Tracker",
                        )
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
                if not cycle:
                    expected = float(member["expected"] or 0)
                member_data.update({"status": status, "paid": paid, "expected": expected})
                add_reliability(member_data, c, member["id"], gid)
                grp = c.execute("SELECT name FROM groups WHERE id=?", (gid,)).fetchone()
                return send_json(self, {"ok": True, "group_name": grp["name"] if grp else "", "member": member_data, "active_cycle": dict(cycle) if cycle else None, "cycle_collected": cycle_total, "cycle_expected": expected_pool, "progress": max(0, min(100, progress)), "members_paid": paid_members, "contributions": [dict(x) for x in contributions], "group_recent_contributions": [dict(x) for x in all_group_rows], "loans": loan_out})

            if path == "/api/reliability" and method == "GET":
                if role == "admin":
                    members = c.execute("SELECT id,name,email FROM members WHERE group_id=? ORDER BY name", (gid,)).fetchall()
                    return send_json(self, {"ok": True, "members": [{**dict(m), **{"reliability": reliability_for_member(c, m["id"], gid)}} for m in members]})
                reliability = reliability_for_member(c, session["user_id"], gid)
                return send_json(self, {"ok": True, "reliability": reliability})

            return error(self, "Endpoint not found.", 404)
        finally:
            c.close()


def send_cycle_reminders():
    """Email members with unpaid balances in OPEN cycles nearing the deadline (once per cycle)."""
    try:
        c = conn()
        soon = (date.fromisoformat(today()) + timedelta(days=CYCLE_REMINDER_DAYS)).isoformat()
        rows = c.execute(
            "SELECT * FROM cycles WHERE status='OPEN' AND reminder_sent=0 AND end_date>=? AND end_date<=?",
            (today(), soon),
        ).fetchall()
        for cycle in rows:
            members = c.execute(
                "SELECT id,name,email,expected FROM members WHERE group_id=? AND enrolled=1", (cycle["group_id"],)
            ).fetchall()
            for m in members:
                paid = float(
                    c.execute(
                        "SELECT COALESCE(SUM(amount),0) AS t FROM contributions WHERE member_id=? AND cycle_id=?",
                        (m["id"], cycle["id"]),
                    ).fetchone()["t"]
                )
                remaining = max(0.0, float(m["expected"] or 0) - paid)
                if remaining <= 0:
                    continue
                notify(
                    m["email"],
                    f"Njangi Tracker - Cycle #{cycle['number']} closes on {cycle['end_date']}",
                    f"Hello {m['name']},\n\nCycle #{cycle['number']} closes on {cycle['end_date']}. "
                    f"Your remaining contribution is {remaining:g} FCFA. Pay before the deadline to protect "
                    f"your reliability score.\n\nNjangi Tracker",
                )
            c.execute("UPDATE cycles SET reminder_sent=1 WHERE id=?", (cycle["id"],))
            c.commit()
        c.close()
    except Exception as exc:
        print("REMINDER ERROR:", repr(exc))


def reminder_loop():
    while True:
        time.sleep(NOTIFY_CHECK_SECONDS)
        send_cycle_reminders()


def main():
    ensure_schema()
    threading.Thread(target=reminder_loop, daemon=True).start()
    with ReusableTCPServer(("", PORT), Handler) as server:
        print(f"Njangi Tracker running at http://127.0.0.1:{PORT}")
        print("Python backend + SQLite database")
        if smtp_configured():
            print("Email: SMTP is configured.")
        else:
            print("Email: NOT configured. Copy .env.example to .env and fill in the SMTP settings "
                  "(or set NJANGI_DEV_SHOW_PIN=1 to see reset PINs on screen while testing locally).")
        server.serve_forever()


if __name__ == "__main__":
    main()
