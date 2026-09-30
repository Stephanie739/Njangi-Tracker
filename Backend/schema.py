```python
# Njangi Tracker — SQLite Database Schema
# Person 1 — Task 2
# Design and create the SQLite database schema.
#
# This file only creates the database tables.
# It does not add, read, update, or delete data.
# Those operations are handled by persistence.py.

import sqlite3


# Name of the SQLite database file.
DB_PATH = "njangi.db"


# Open a connection to the SQLite database.
def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:

    # Connect to the database.
    conn = sqlite3.connect(db_path)

    # Turn on foreign key support.
    # This makes sure related records are valid.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# Create all database tables.
def create_schema(conn: sqlite3.Connection) -> None:

    # Run all table creation commands.
    # IF NOT EXISTS prevents errors if the tables already exist.
    conn.executescript(
        """

        CREATE TABLE IF NOT EXISTS njangi_group (
            # Unique ID for each Njangi group.
            group_id            INTEGER PRIMARY KEY AUTOINCREMENT,

            # Name of the Njangi group.
            # Each group must have a different name.
            group_name          TEXT NOT NULL UNIQUE,

            # Amount each member should contribute.
            contribution_amount REAL NOT NULL,

            # Number of days between contributions.
            # The default is 30 days.
            frequency_days      INTEGER NOT NULL DEFAULT 30
        );

        CREATE TABLE IF NOT EXISTS member (
            # Member ID.
            # It is unique only within a group.
            member_id      INTEGER NOT NULL,

            # ID of the group the member belongs to.
            group_id       INTEGER NOT NULL,

            # Member's name.
            name           TEXT NOT NULL,

            # Member's phone number.
            # It can be empty.
            phone_number   TEXT,

            # Date the member joined.
            join_date      TEXT NOT NULL,

            # Position of the member in the rotation queue.
            # NULL means the member is not currently in the queue.
            queue_position INTEGER,

            # A member is identified by member_id + group_id.
            PRIMARY KEY (member_id, group_id),

            # Connect the member to its group.
            # Deleting the group also deletes its members.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cycle (
            # Internal ID for the cycle.
            cycle_pk       INTEGER PRIMARY KEY AUTOINCREMENT,

            # ID of the group that owns the cycle.
            group_id       INTEGER NOT NULL,

            # Number of the cycle.
            cycle_number   INTEGER NOT NULL,

            # ID of the member receiving the money.
            recipient_id   INTEGER NOT NULL,

            # Date when the cycle is due.
            due_date       TEXT NOT NULL,

            # Shows whether the cycle is closed.
            # 0 = not closed
            # 1 = closed
            closed         INTEGER NOT NULL DEFAULT 0,

            # A group cannot have the same cycle number twice.
            UNIQUE (group_id, cycle_number),

            # Connect the cycle to its group.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS contribution (
            # Unique ID for the contribution.
            contribution_pk  INTEGER PRIMARY KEY AUTOINCREMENT,

            # ID of the cycle.
            cycle_pk         INTEGER NOT NULL,

            # ID of the member making the contribution.
            member_id        INTEGER NOT NULL,

            # ID of the member's group.
            # This helps keep group data separate.
            group_id         INTEGER NOT NULL,

            # Amount the member is expected to pay.
            amount_expected  REAL NOT NULL,

            # Amount the member has actually paid.
            # Starts at 0.
            amount_paid      REAL NOT NULL DEFAULT 0,

            # Date the payment was made.
            # NULL means no payment has been made.
            date_paid        TEXT,

            # Current payment status.
            # Default is Pending.
            status           TEXT NOT NULL DEFAULT 'Pending',

            # Connect the contribution to a cycle.
            # Deleting the cycle deletes its contributions.
            FOREIGN KEY (cycle_pk)
                REFERENCES cycle(cycle_pk)
                ON DELETE CASCADE,

            # Make sure the member belongs to the group.
            FOREIGN KEY (member_id, group_id)
                REFERENCES member(member_id, group_id)
        );

        CREATE TABLE IF NOT EXISTS loan (
            # Loan ID.
            # It is unique only within a group.
            loan_id          INTEGER NOT NULL,

            # ID of the group that owns the loan.
            group_id         INTEGER NOT NULL,

            # ID of the member who requested the loan.
            member_id        INTEGER NOT NULL,

            # Amount borrowed.
            amount           REAL NOT NULL,

            # Loan interest rate.
            # Default is 5%.
            interest_rate    REAL NOT NULL DEFAULT 5.0,

            # Current loan status.
            # Default is Requested.
            status            TEXT NOT NULL DEFAULT 'Requested',

            # Date the loan was requested.
            date_requested   TEXT NOT NULL,

            # Date the loan was approved.
            # NULL means it has not been approved yet.
            date_approved    TEXT,

            # Amount already repaid by the member.
            # Starts at 0.
            amount_repaid    REAL NOT NULL DEFAULT 0,

            # A loan is identified by loan_id + group_id.
            PRIMARY KEY (loan_id, group_id),

            # Connect the loan to its group.
            # Deleting the group also deletes its loans.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE,

            # Make sure the member belongs to the same group.
            FOREIGN KEY (member_id, group_id)
                REFERENCES member(member_id, group_id)
        );
        """
    )

    # Save the changes to the database.
    conn.commit()
```
