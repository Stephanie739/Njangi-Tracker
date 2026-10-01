"""
Njangi Tracker — Database access layer
Step 1: Updated to support phone numbers, pin_hash, group memberships,
unique njangi_code, and multi-group membership.

Strict separation: this module only talks to SQLite.
Business logic lives in model.py / controllers; HTTP lives in server.py.
"""

import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from schema import get_connection, create_schema, migrate_schema, DB_PATH


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def init_db(db_path: str = DB_PATH) -> None:
    """Create schema + run migrations. Call once at process start."""
    conn = get_connection(db_path)
    try:
        create_schema(conn)
        migrate_schema(conn)
    finally:
        conn.close()


def connect_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Backward-compatible alias used by older py/ modules."""
    return get_connection(db_path)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

def add_group(
    name: str,
    contribution_amount: float,
    frequency: str = "Monthly",
    frequency_days: int = 30,
    njangi_code: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """
    Insert a new Njangi group.
    Returns the new group id.
    Caller is responsible for generating a valid njangi_code (see model.generate_njangi_code).
    """
    if not njangi_code:
        raise ValueError("njangi_code is required")
    system_uuid = str(uuid.uuid4())
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO groups (name, njangi_code, uuid, contribution_amount, frequency, frequency_days)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name.strip(), njangi_code.upper().strip(), system_uuid, float(contribution_amount), frequency, int(frequency_days)),
        )
        group_id = cur.lastrowid
        # Seed the three standard funds
        for fund_type, fund_name in (
            ("Main", "Main Njangi Pot"),
            ("Social", "Trouble / Social Fund"),
            ("Investment", "Investment / Project Fund"),
        ):
            conn.execute(
                "INSERT INTO funds (group_id, name, fund_type, balance) VALUES (?, ?, ?, 0)",
                (group_id, fund_name, fund_type),
            )
        conn.commit()
        return int(group_id)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError(f"Group could not be created (duplicate code or name): {exc}") from exc
    finally:
        conn.close()


def get_group_by_code(njangi_code: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Look up a group by its public njangi_code. Returns a dict or None."""
    code = (njangi_code or "").strip().upper()
    if not code:
        return None
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM groups WHERE njangi_code = ?", (code,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_group_by_id(group_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM groups WHERE id = ?", (group_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_groups(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM groups ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Users (global profile)
# ---------------------------------------------------------------------------

def add_user(
    name: str,
    phone: str,
    pin_hash: Optional[str] = None,
    email: Optional[str] = None,
    password_hash: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """
    Create a global user profile.
    phone is the primary unique identifier for member login.
    """
    phone_clean = (phone or "").strip()
    if not phone_clean:
        raise ValueError("phone is required")
    if not name or not name.strip():
        raise ValueError("name is required")
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO users (phone, email, name, pin_hash, password_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                phone_clean,
                (email or "").strip().lower() or None,
                name.strip(),
                pin_hash,
                password_hash,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError(f"User with this phone or email already exists: {exc}") from exc
    finally:
        conn.close()


def get_user_by_phone(phone: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    phone_clean = (phone or "").strip()
    if not phone_clean:
        return None
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE phone = ?", (phone_clean,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_user_pin(user_id: int, pin_hash: str, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "UPDATE users SET pin_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pin_hash, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Group memberships
# ---------------------------------------------------------------------------

def add_membership(
    user_id: int,
    group_id: int,
    role: str = "Member",
    share_count: int = 1,
    member_code: Optional[str] = None,
    status: str = "Active",
    db_path: str = DB_PATH,
) -> int:
    """
    Link a user to a group with a role and share count.
    Supports multi-group membership (one user, many groups).
    """
    valid_roles = {"President", "Secretary", "Treasurer", "Auditor", "Member"}
    if role not in valid_roles:
        raise ValueError(f"role must be one of {valid_roles}")
    if share_count < 1:
        raise ValueError("share_count must be >= 1")
    conn = get_connection(db_path)
    try:
        # Auto-generate member_code if not supplied
        if not member_code:
            next_id = conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM group_memberships"
            ).fetchone()[0]
            member_code = f"MBR-{int(next_id):06d}"

        cur = conn.execute(
            """
            INSERT INTO group_memberships
                (user_id, group_id, role, share_count, member_code, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, group_id, role, int(share_count), member_code, status),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError(f"Membership already exists or constraint violation: {exc}") from exc
    finally:
        conn.close()


def get_memberships_for_user(user_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Return all groups a user belongs to (multi-group support)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT gm.*, g.name AS group_name, g.njangi_code, g.contribution_amount
            FROM group_memberships gm
            JOIN groups g ON g.id = gm.group_id
            WHERE gm.user_id = ?
            ORDER BY gm.join_date
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_members_by_group(group_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Return all members of a group with their user profile data."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT gm.*, u.name, u.phone, u.email
            FROM group_memberships gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = ?
            ORDER BY gm.rotation_position, gm.id
            """,
            (group_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_membership(user_id: int, group_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            """
            SELECT gm.*, u.name, u.phone, u.email
            FROM group_memberships gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.user_id = ? AND gm.group_id = ?
            """,
            (user_id, group_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def approve_membership(membership_id: int, db_path: str = DB_PATH) -> bool:
    """Move a pending self-registration request to Active."""
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "UPDATE group_memberships SET status = 'Active' WHERE id = ? AND status = 'Pending'",
            (membership_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Convenience helpers used by older code paths
# ---------------------------------------------------------------------------

def add_member(group_id: int, name: str, phone: str, share_count: int = 1,
               role: str = "Member", pin_hash: Optional[str] = None,
               db_path: str = DB_PATH) -> Tuple[int, int]:
    """
    High-level helper: create (or reuse) a user + membership in one call.
    Returns (user_id, membership_id).
    """
    existing = get_user_by_phone(phone, db_path=db_path)
    if existing:
        user_id = existing["id"]
        if pin_hash and not existing.get("pin_hash"):
            update_user_pin(user_id, pin_hash, db_path=db_path)
    else:
        user_id = add_user(name=name, phone=phone, pin_hash=pin_hash, db_path=db_path)

    membership_id = add_membership(
        user_id=user_id,
        group_id=group_id,
        role=role,
        share_count=share_count,
        status="Active",
        db_path=db_path,
    )
    return user_id, membership_id


# ---------------------------------------------------------------------------
# Sessions (lightweight token storage)
# ---------------------------------------------------------------------------

def create_session(
    user_id: int,
    token_hash: str,
    role: str,
    group_id: Optional[int],
    membership_id: Optional[int],
    created_at: float,
    expires_at: float,
    db_path: str = DB_PATH,
) -> int:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO sessions
                (token_hash, user_id, membership_id, role, group_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (token_hash, user_id, membership_id, role, group_id, created_at, expires_at),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_session_by_token_hash(token_hash: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(token_hash: str, db_path: str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Simple query helpers kept for compatibility with existing py/ modules
# ---------------------------------------------------------------------------

def get_members(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """All memberships across all groups (admin overview)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT gm.*, u.name, u.phone, u.email, g.name AS group_name, g.njangi_code
            FROM group_memberships gm
            JOIN users u ON u.id = gm.user_id
            JOIN groups g ON g.id = gm.group_id
            ORDER BY gm.id
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialised at {DB_PATH}")
