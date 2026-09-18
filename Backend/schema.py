"""
Njangi Tracker — SQLite Schema
Person 1 — Task 2 (design and create SQLite database schema)

Just the table definitions. Nothing here reads or writes actual data —
that's Task 3, in persistence.py.
"""

import sqlite3

DB_PATH = "njangi.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Creates all tables if they don't already exist. Safe to call every
    time the app starts.

    Table design notes:
      - Every table (member, cycle, contribution, loan) carries group_id,
        directly or indirectly — this is what makes Task 5 (group data
        separation) possible: any query can filter WHERE group_id = ?
        and never see another group's data.
      - member's primary key is (member_id, group_id) rather than just
        member_id, since member_id is only assigned uniquely *within*
        a group (see NjangiGroup._next_member_id in models.py).
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS njangi_group (
            group_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name          TEXT NOT NULL UNIQUE,
            contribution_amount REAL NOT NULL,
            frequency_days      INTEGER NOT NULL DEFAULT 30
        );

        CREATE TABLE IF NOT EXISTS member (
            member_id      INTEGER NOT NULL,
            group_id       INTEGER NOT NULL,
            name           TEXT NOT NULL,
            phone_number   TEXT,
            join_date      TEXT NOT NULL,
            queue_position INTEGER,  -- NULL if not currently in rotation queue
            PRIMARY KEY (member_id, group_id),
            FOREIGN KEY (group_id) REFERENCES njangi_group(group_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cycle (
            cycle_pk       INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id       INTEGER NOT NULL,
            cycle_number   INTEGER NOT NULL,
            recipient_id   INTEGER NOT NULL,
            due_date       TEXT NOT NULL,
            closed         INTEGER NOT NULL DEFAULT 0,  -- 0/1 boolean
            UNIQUE (group_id, cycle_number),
            FOREIGN KEY (group_id) REFERENCES njangi_group(group_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS contribution (
            contribution_pk  INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_pk         INTEGER NOT NULL,
            member_id        INTEGER NOT NULL,
            group_id         INTEGER NOT NULL,
            amount_expected  REAL NOT NULL,
            amount_paid      REAL NOT NULL DEFAULT 0,
            date_paid        TEXT,
            status           TEXT NOT NULL DEFAULT 'Pending',
            FOREIGN KEY (cycle_pk) REFERENCES cycle(cycle_pk) ON DELETE CASCADE,
            FOREIGN KEY (member_id, group_id) REFERENCES member(member_id, group_id)
        );

        CREATE TABLE IF NOT EXISTS loan (
            loan_id          INTEGER NOT NULL,
            group_id         INTEGER NOT NULL,
            member_id        INTEGER NOT NULL,
            amount           REAL NOT NULL,
            interest_rate    REAL NOT NULL DEFAULT 5.0,
            status           TEXT NOT NULL DEFAULT 'Requested',
            date_requested   TEXT NOT NULL,
            date_approved    TEXT,
            amount_repaid    REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (loan_id, group_id),
            FOREIGN KEY (group_id) REFERENCES njangi_group(group_id) ON DELETE CASCADE,
            FOREIGN KEY (member_id, group_id) REFERENCES member(member_id, group_id)
        );
        """
    )
    conn.commit()