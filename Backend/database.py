#we use the SQlite to store the Njangi Tracker data
import sqlite3
#sqlite3 is Python's build-in module for working in SQlite database
def connect_db():
#connect to database
    """
    Connect to the Njangi SQlite Database.
    If the database file doesn't exist,
    SQlite will create it automatically
    """
    connection = sqlite3.connect("njangi.db")
#connection represent our connection to the database
    return connection
#create the database table
def create_tables():
    """
    Create all the table needed for the Njangi Tracker,
    if they donot already exist.
    """
#this table stores informations about each njangi group
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups(
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contribution_amount REAL NOT NULL,
        frequency TEXT NOT NULL
        )
        """)
    #Create the member table
#This table stores informations about each member
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members(
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            FOREIGN KEY (group_id) REFERENCES groups(group_id)
        )
        """)
#create cycle table
#this table stores information about each cycle(round) of a njangi group
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycles(
            cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            cycle_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        )
        """)
#contribution table
# this table shows the contribution/records that each member has done in the Njangi cycle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contributions(
            contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            cycle_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_status TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members(member_id),
            FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
        )
        """)
#Loan tables
#This shows the loan obtain by a specific member of a Njangi group from the Njangi amount contributed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loans(
            loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            amount_repaid REAL NOT NULL DEFAULT 0,
            STATUS TEXT NOT NULL DEFAULT 'ACTIVE',
            FOREIGN KEY (member_id)
            REFERENCES members(member_id)
        )
        """) 
    connection.commit()
    connection.close()

#add a njangi group
def add_group(name, contribution_amount, frequency):
    """
    Add a new Njangi group to the database.
    Parameters:
    name (str): The name of the Njangi group
    contribution_amount (float): The amount each member contributes
    frequency (str): how often members contribute
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO groups (name, contribution_amount, frequency)
        VALUES (?, ?, ?)
        """, (name, contribution_amount, frequency))
#VALUES (?, ?, ?) is a safety way to send python values to SQLite
    connection.commit()
#get the ID created auomatically by the SQLite
    group_id = cursor.lastrowid
    connection.close()
    return group_id
def add_member(group_id, name, phone):
    """
    Add a member to an existing Njangi group
    Parameters:
        group_id (int): The ID of the Njangi group
        name (str): The name of the member
        phone (str): The phone number of the member
    """
    connection = connect_db()
    cursor = connection.cursor()
#insert the member
    cursor.execute("""
        INSERT INTO members (group_id, name, phone)
        VALUES (?, ?, ?)
        """, (group_id, name, phone))
    connection.commit()
    member_id = cursor.lastrowid
    connection.close()
    return member_id
def add_cycle(member_id, cycle_number, status="OPEN"):
    """
    Create a new cycle for a Njangi group;
    Parameters:
        member_id (int): The ID of the member
        cycle_number (int): The number of the cycle
        status (str): current status of the cycle (default is "OPEN")
        """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO cycles (member_id, cycle_number, status)
        VALUES (?, ?, ?)
        """, (member_id, cycle_number, status))
    connection.commit()
    cycle_id = cursor.lastrowid
    connection.close()
    return cycle_id
def add_contribution(member_id, cycle_id, amount):
    """
    Record a contribution made by a member
    The payment_status is automatically determined according the to the expected contribution amount.
    """
#Get the expected contribution amount
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT groups.contribution_amount
        FROM groups
        JOIN members ON groups.group_id = members.group_id
        WHERE members.member_id = ?
        """, (member_id,))
    result = cursor.fetchone()
#check if the member exist
    if result is None:
        connection.close()
        print("Error: member not found")
        return None
    expected_amount = result[0]
#validate the amount
    if not validate_payment_amount(amount, expected_amount):
        connection.close()
        return None
    if amount == 0:
        payment_status = "Pending"
    elif amount < expected_amount:
        payment_status = "Partial"
    else:
        payment_status = "Paid"
    cursor.execute("""
    INSERT INTO contributions
    (member_id, cycle_id, amount, payment_status)
    VALUES(?, ?, ?, ?)
    """,(member_id, cycle_id, amount, payment_status))
    connection.commit()
    contribution_id = cursor.lastrowid
    connection.close()
    return contribution_id

def issue_loan(member_id, amount):
    """
    Issue a loan to a member.
    Parameters:
        member_id (int): ID of the member recieving the loan
        amount (float): Amount of the loan
    Returns:
        loan_id(int): ID of the newly created loan
    """
#A loan amount must be greater than zero
    if amount <= 0:
        print("Error: loan amount must be greater than zero.")
        return None
    connection = connect_db()
    cursor = connection.cursor()
#Check that the member exist
    cursor.execute("""
        SELECT member_id
        FROM members
        WHERE member_id = ?
    """,(member_id,))
    member = cursor.fetchone()
    if member is None:
        print("Error: member not found.")
        connection.close()
        return None
#Create the loan
    cursor.execute("""
        INSERT INTO loans (member_id, amount)
        VALUES (?, ?)
    """, (member_id, amount))
    connection.commit()
    loan_id = cursor.lastrowid
    connection.close()
    return loan_id

def repay_loan(loan_id, repayment_amount):
    """
    Repay part of the  existing laon.
    Parameters:
        loan_id (int): ID of the loan 
        repayment_amount (float): Amount the member wants to repay
    Returns:
        str: Update loan status
    """
#   repayment must be greater than zero
    if repayment_amount <= 0:
        print("Error: repayment amount must be greater than zero.")
        return None
    connection =connect_db()
    cursor = connection.cursor()
#Get the loan information
    cursor.execute("""
        SELECT amount, amount_repaid,status
        FROM loans
        WHERE loan_id = ?
    """, (loan_id,))
    loan = cursor.fetchone()
#Check if a loan exist
    if loan is None:
        print("Error: loan not found.")
        connection.close()
        return None
    amount = loan[0]
    amount_repaid = loan[1]
    status = loan[2]
#Check if the loan has already been fully repaid
    if status == "PAID":
        print("Error: this loan has already been paid.")
        connection.close()
        return None
#Calculate the remaining amount
    remaining_amount = amount - amount_repaid
#A repayment cannot be greater than what remains
    if repayment_amount > remaining_amount:
        print("Error: repayment cannot be greater than the remaining loan amount.")
        connection.close()
        return None
#Add the repayment
    new_amount_repaid = amount_repaid + repayment_amount
#Determine the new status
    if new_amount_repaid == amount:
        new_status = "PAID"
    else:
        new_status = "ACTIVE"
#Update the loan
    cursor.execute("""
        UPDATE loans
        SET amount_repaid = ?, status = ?
        WHERE loan_id = ?
    """, (new_amount_repaid, new_status, loan_id))
    connection.commit()
    connection.close()
    return new_status

def get_groups():
    """
    Get all Njangi groups from database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get the results from the database
    cursor.execute("SELECT * FROM groups")
#get all groups from the database
    groups = cursor.fetchall()
    conn.close()
    return groups
def get_members():
    """
    Get all the members from the database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    conn.close()
    return members
def get_members_by_group(group_id):
    """
    Get all members who belongs to a specific Njangi group.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get members that belong to a specific group using the group_id
    cursor.execute("SELECT * FROM members WHERE group_id = ?",
                   (group_id,)
                   )
    members = cursor.fetchall()
    conn.close()
    return members
def get_cycles():
    """
    Get all the cycles of the Njangi groups from the database.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cycles")
    cycles = cursor.fetchall()
    conn.close()
    return cycles

def get_cycles_by_group(group_id):
    """
    Get all the cycles that are belonging to a specific Njangi group.
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT cycles.*
        FROM cycles
        JOIN members
        ON cycles.member_id = members.member_id
        WHERE members.group_id = ?
    """, (group_id,))
    cycles = cursor.fetchall()
    connection.close()
    return cycles

def get_contributions():
    """
    Get all the contributions made by the members in the database.
    """
    conn = sqlite3.connect("njangi.db")
#Get the expected contribution amount
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contributions")
    contributions = cursor.fetchall()
    conn.close()
    return contributions
def get_contributions_by_cycle(cycle_id):
    """
    Get all contributions made in a specific cycle.
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
#get contributions from the selected cycle
    cursor.execute("SELECT * FROM contributions WHERE cycle_id = ?",
                   (cycle_id,)
                   )
    contributions = cursor.fetchall()
    conn.close()
    return contributions

def contribution_by_group(group_id):
    """
    Get all the contributions belonging to a specific Njangi group.
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT contributions. * FROM contributions
        JOIN members ON contributions.member_id = members.member_id
        WHERE members.group_id = ? """, (group_id,))
    contributions = cursor.fetchall()
    connection.close()
    return contributions

def get_cycle_total(cycle_id):
    """
    Calculate the total amount contributed during a specific cycle.
    """
    conn = connect_db()
    cursor = conn.cursor()
#Add together all contributions belonging to this cycle
    cursor.execute("""
        SELECT SUM(amount)
        FROM contributions
        WHERE cycle_id = ?
    """, (cycle_id,))
#Get the result
    result = cursor.fetchone()
    conn.close()
#if there are no contributions, SUM return None
    if result[0] is None:
        return 0
    return result[0]

def get_expected_pool(group_id):
    """
    Calculate the total expected amount of a Njangi group.
    Expected pool = number of members * contribution amount
    """
    conn = connect_db()
    cursor = conn.cursor()
#Get the contribution amount and the number of member
    cursor.execute("""
        SELECT groups.contribution_amount, COUNT(members.member_id)
        FROM groups
        LEFT JOIN members
        ON groups.group_id = members.group_id
        WHERE groups.group_id = ?
        GROUP BY groups.group_id
    """,(group_id,))
    result = cursor.fetchone()
    conn.close()
#Check if group exist
    if result is None:
        result = 0

    contribution_amount = result[0]
    number_of_members = result[1]
#calculate the pool expected
    expected_pool = contribution_amount * number_of_members
    return expected_pool

def get_pool_summary(group_id, cycle_id):
    """
    Get summary of the Njangi pool.
    Returns:
        expected_pool = total amount expected
        collected_pool = amount collected actually
        remaining_pool = amount still missing
        progress = percentage of the pool collected
    """
#Get the expected total
    expected_pool = get_expected_pool(group_id)
#Get the amount actually collected
    collected_pool = get_cycle_total(cycle_id)
#Calculate the remaining amount
    remaining_pool = expected_pool - collected_pool
#Calculate the percentage collected
    if expected_pool == 0:
        progress = 0
    else:
        progress = (collected_pool / expected_pool) * 100
    return expected_pool, collected_pool,remaining_pool,progress

def close_cycle(cycle_id, group_id):
    """
    Close a Njangi cycle once the expected contribution has been fully paid*
    """
#Get the amount expected amount for the group
    expected_pool =  get_expected_pool(group_id)
#Get the amount actually collected in this cycle
    collected_pool = get_cycle_total(cycle_id)
#Check if the cycle is fully paid
    if collected_pool >= expected_pool:
        connection = connect_db()
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE cycles
            SET status = 'CLOSED'
            WHERE cycle_id = ?
        """, (cycle_id,))
        connection.commit()
        connection.close()
        return "CLOSED"
    else:
        return "OPEN"
    
def get_pending_contributions():
    """
    Get all the contributions that are still pending(not paid).
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM contributions 
        WHERE payment_status = 'Pending'
    """)
    contributions = cursor.fetchall()
    conn.close()
    return contributions

def update_contribution_status(contribution_id, amount, status):
    """
    Update the payment status of a contribution
    """
    conn = sqlite3.connect("njangi.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE contributions
        SET amount = ?, payment_status = ?
        WHERE contribution_id = ?
        """, (amount, status, contribution_id)
        )
    conn.commit()
    conn.close()

def update_contribution_payment(contribution_id, amount, expected_amount):
    """
    Update a contribution and automatically determine its payment status.
    """
#validate the payment amount first
    if not validate_payment_amount(amount, expected_amount):
        return None
    # Check the amount paid
    if amount == 0:
        payment_status = "Pending"
    elif amount < expected_amount:
        payment_status = "Partial"
    else:
        payment_status = "Paid"

    # Connect to the database
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE contributions
        SET amount = ?, payment_status = ?
        WHERE contribution_id = ?
        """,(amount, payment_status, contribution_id))
    connection.commit()
    connection.close()
    return payment_status
def validate_payment_amount(amount, expected_amount):
    """
    Check whether a contribution amount is valid.
    Returns:
    True   -> payment is valid
    False  -> payment is invalid
    """
#A payment cannot be negative 
    if amount < 0:
        print("Error: payment amount cannot be negative.")
        return False
#A payment cannot be greater than the expected cntribution
    if amount > expected_amount:
        print("Error: payment cannot be greater than the expected contribtion.")
        return False
    #If all payment pass, the payment is valid
    return True

def get_loans_by_member(member_id):
    """
    Get all the loans belonging to a spacific member.
    """
    connection = connect_db()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM loans
        WHERE member_id = ?
    """, (member_id,))
    loans = cursor.fetchall()
    connection.close()
    return loans
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
