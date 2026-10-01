#!/usr/bin/env python3
"""
Njangi Tracker — SQLite Schema Definition Module
================================================

Person 1 — Task 2 (design and create SQLite database schema)

This module contains **only** the table definitions and the helper that
creates them. Nothing here reads or writes actual business data —
that responsibility belongs to Task 3 (persistance.py / database.py).

Design Goals
------------
1. Multi-group isolation  
   Every table that holds member-specific data carries a group_id
   (directly or via foreign key). This makes Task 5 (group data
   separation) trivial: any query can simply filter
   WHERE group_id = ? and will never see another group's rows.

2. Composite primary keys where needed  
   A member_id is only unique *inside* a group. Therefore the member
   table uses PRIMARY KEY (member_id, group_id). The same pattern is
   used for loans.

3. Referential integrity  
   Foreign-key constraints are declared and PRAGMA foreign_keys = ON
   is enabled so that deleting a group cascades cleanly and orphan
   rows cannot be inserted.

4. Idempotent creation  
   All statements use CREATE TABLE IF NOT EXISTS so the function can
   be called safely on every application start.

Tables Overview
---------------
njangi_group
    Root entity. Holds the group name, standard contribution amount
    and frequency (in days).

member
    Participants. Composite PK (member_id, group_id). Tracks join date
    and optional queue position for the rotation order.

cycle
    One contribution round. Identified by (group_id, cycle_number).
    Records who the recipient is and whether the cycle is closed.

contribution
    Individual payment obligations / receipts linked to a cycle and
    a member. Supports partial payments via amount_paid vs
    amount_expected.

loan
    Money borrowed from the group pool. Composite PK (loan_id, group_id).
    Tracks interest, status and cumulative repayments.

Author: Njangi Tracker Development Team
Version: 2.1.0 (Enhanced documentation, type hints, constants)
Last Updated: 2026-09-28
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional, Union

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("njangi.schema")

# ---------------------------------------------------------------------------
# Configuration Constants
# ---------------------------------------------------------------------------

# Default database file name (can be overridden by callers)
DB_PATH: str = "njangi.db"

# Default contribution frequency in days (30 ≈ monthly)
DEFAULT_FREQUENCY_DAYS: int = 30

# Default interest rate applied to new loans (percent)
DEFAULT_INTEREST_RATE: float = 5.0

# Canonical status strings used across the application
CONTRIBUTION_STATUS_PENDING = "Pending"
CONTRIBUTION_STATUS_PARTIAL = "Partial"
CONTRIBUTION_STATUS_PAID = "Paid"
LOAN_STATUS_REQUESTED = "Requested"
LOAN_STATUS_APPROVED = "Approved"
LOAN_STATUS_ACTIVE = "Active"
LOAN_STATUS_REPAID = "Repaid"
LOAN_STATUS_REJECTED = "Rejected"


# =============================================================================
# Connection Helper
# =============================================================================

def get_connection(db_path: Union[str, Path] = DB_PATH) -> sqlite3.Connection:
    """
    Open a SQLite connection with foreign-key enforcement enabled.

    Parameters
    ----------
    db_path : str or Path, optional
        Filesystem path to the SQLite database file.
        Defaults to the module-level DB_PATH constant.

    Returns
    -------
    sqlite3.Connection
        An open connection with row_factory left at the default
        (callers may set it to sqlite3.Row if they prefer).

    Notes
    -----
    - PRAGMA foreign_keys = ON is executed immediately so that all
      subsequent statements on this connection respect constraints.
    - The connection is *not* closed by this function; the caller is
      responsible for closing it (preferably via a context manager).
    """
    path_str = str(db_path)
    logger.debug("Opening SQLite connection to %s", path_str)
    conn = sqlite3.connect(path_str)
    conn.execute("PRAGMA foreign_keys = ON")
    # Optional performance pragmas that are safe for a small multi-user app
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


# =============================================================================
# Schema Creation
# =============================================================================

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
      - cycle uses a surrogate cycle_pk so that contributions can
        reference a single integer; uniqueness of (group_id, cycle_number)
        is still enforced by a UNIQUE constraint.
      - loan follows the same composite-key pattern as member.

    Parameters
    ----------
    conn : sqlite3.Connection
        An open connection (preferably obtained from get_connection()).

    Side Effects
    ------------
    - Executes a multi-statement script that creates five tables.
    - Commits the transaction so the schema is durable.
    - Logs a success message at INFO level.
    """
    logger.info("Creating / verifying Njangi database schema …")

    conn.executescript(
        """
        -- ================================================================
        -- njangi_group : root entity for each savings circle
        -- ================================================================
        CREATE TABLE IF NOT EXISTS njangi_group (
            group_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name          TEXT NOT NULL UNIQUE,
            contribution_amount REAL NOT NULL,
            frequency_days      INTEGER NOT NULL DEFAULT 30
            -- frequency_days stores the interval between cycles
            -- (7 = weekly, 14 = bi-weekly, 30 ≈ monthly, etc.)
        );

        -- ================================================================
        -- member : participants belonging to a group
        -- Composite primary key because member_id is local to the group
        -- ================================================================
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

        -- Index to speed up "list all members of a group" queries
        CREATE INDEX IF NOT EXISTS idx_member_group
            ON member(group_id);

        -- ================================================================
        -- cycle : one contribution round inside a group
        -- ================================================================
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

        CREATE INDEX IF NOT EXISTS idx_cycle_group
            ON cycle(group_id);

        -- ================================================================
        -- contribution : individual payment records linked to a cycle
        -- ================================================================
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

        CREATE INDEX IF NOT EXISTS idx_contribution_cycle
            ON contribution(cycle_pk);
        CREATE INDEX IF NOT EXISTS idx_contribution_member
            ON contribution(member_id, group_id);

        -- ================================================================
        -- loan : money borrowed from the group pool
        -- ================================================================
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

        CREATE INDEX IF NOT EXISTS idx_loan_group
            ON loan(group_id);
        CREATE INDEX IF NOT EXISTS idx_loan_member
            ON loan(member_id, group_id);
        """
    )
    conn.commit()
    logger.info("Schema creation / verification completed successfully")


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """
    Dangerously drop every table defined by this schema.

    Intended only for test fixtures and development reset scripts.
    Never call this in production.

    Parameters
    ----------
    conn : sqlite3.Connection
        Open connection with sufficient privileges.
    """
    logger.warning("Dropping all Njangi schema tables (destructive operation)")
    conn.executescript(
        """
        DROP TABLE IF EXISTS loan;
        DROP TABLE IF EXISTS contribution;
        DROP TABLE IF EXISTS cycle;
        DROP TABLE IF EXISTS member;
        DROP TABLE IF EXISTS njangi_group;
        """
    )
    conn.commit()
    logger.warning("All tables dropped")


def schema_version(conn: sqlite3.Connection) -> str:
    """
    Return a simple version identifier for the current schema.

    Useful for future migration tooling. Currently hard-coded because
    the schema is still small; later this can read a dedicated
    schema_meta table.

    Returns
    -------
    str
        Version string of the form "major.minor".
    """
    return "2.1"


# =============================================================================
# Convenience entry point for command-line use
# =============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    print(f"Creating schema in {target} …")
    with get_connection(target) as connection:
        create_schema(connection)
    print("Done.")
