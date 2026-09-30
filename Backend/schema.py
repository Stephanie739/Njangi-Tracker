```python
"""
Njangi Tracker — SQLite Database Schema

Person 1 — Task 2
Design and create the SQLite database schema.

This file is responsible ONLY for creating the database tables.

It does NOT:
- Add members
- Add contributions
- Create loans
- Read existing records
- Update or delete records

Those operations are handled by persistence.py.

The main purpose of this file is to define how our data
will be stored in the SQLite database.
"""

import sqlite3


# Name of the SQLite database file.
# SQLite will create this file automatically if it does not exist.
DB_PATH = "njangi.db"


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Open a connection to the SQLite database.

    A connection is needed before we can create tables
    or work with the database.

    Parameters:
        db_path: The name/path of the database file.
                 By default, it uses "njangi.db".

    Returns:
        A SQLite database connection.
    """

    # Connect to the SQLite database.
    conn = sqlite3.connect(db_path)

    # Turn on foreign-key checking.
    #
    # Foreign keys make sure that records are connected
    # correctly.
    #
    # For example:
    # A member cannot belong to a group that does not exist.
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create all the database tables.

    IF NOT EXISTS means the tables will only be created
    if they do not already exist.

    This makes it safe to call this function every time
    the application starts.
    """

    # executescript() allows us to run several SQL commands
    # at the same time.
    conn.executescript(
        """

        ----------------------------------------------------------------
        -- 1. NJANGI GROUP TABLE
        ----------------------------------------------------------------
        -- This table stores information about each Njangi group.
        --
        -- Example:
        -- group_id = 1
        -- group_name = "Unity Njangi"
        -- contribution_amount = 10000
        -- frequency_days = 30
        --
        -- One group can have many members, cycles and loans.
        ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS njangi_group (
            -- Unique ID for each Njangi group.
            -- AUTOINCREMENT automatically creates the next ID.
            group_id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Name of the Njangi group.
            -- NOT NULL means a group must have a name.
            -- UNIQUE means two groups cannot have the same name.
            group_name TEXT NOT NULL UNIQUE,

            -- Amount each member is expected to contribute.
            contribution_amount REAL NOT NULL,

            -- Number of days between contributions/cycles.
            -- Default is 30 days.
            frequency_days INTEGER NOT NULL DEFAULT 30
        );


        ----------------------------------------------------------------
        -- 2. MEMBER TABLE
        ----------------------------------------------------------------
        -- Stores all members belonging to Njangi groups.
        --
        -- A member belongs to one group.
        -- A group can have many members.
        ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS member (

            -- Member number.
            --
            -- This number is unique only inside a particular group.
            -- For example:
            --
            -- Group 1 can have member 1.
            -- Group 2 can also have member 1.
            member_id INTEGER NOT NULL,

            -- The group this member belongs to.
            group_id INTEGER NOT NULL,

            -- Member's full name.
            name TEXT NOT NULL,

            -- Member's phone number.
            -- It can be empty, therefore there is no NOT NULL.
            phone_number TEXT,

            -- Date the member joined the group.
            -- We store dates as TEXT in SQLite.
            join_date TEXT NOT NULL,

            -- Position of the member in the rotation queue.
            --
            -- NULL means the member is currently not
            -- waiting in the queue.
            queue_position INTEGER,

            -- A member is identified by BOTH member_id and group_id.
            --
            -- This allows different groups to have members
            -- with the same member_id.
            PRIMARY KEY (member_id, group_id),

            -- Connect the member to an existing group.
            --
            -- If the group is deleted, all its members
            -- are automatically deleted as well.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE
        );


        ----------------------------------------------------------------
        -- 3. CYCLE TABLE
        ----------------------------------------------------------------
        -- A cycle represents one contribution/rotation period.
        --
        -- Example:
        -- Cycle 1 -> Member 1 receives the money.
        -- Cycle 2 -> Member 2 receives the money.
        ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS cycle (

            -- Internal database ID for the cycle.
            -- It is automatically generated.
            cycle_pk INTEGER PRIMARY KEY AUTOINCREMENT,

            -- The group that owns this cycle.
            group_id INTEGER NOT NULL,

            -- Human-readable cycle number.
            -- Example: 1, 2, 3, etc.
            cycle_number INTEGER NOT NULL,

            -- ID of the member who receives the money
            -- during this cycle.
            recipient_id INTEGER NOT NULL,

            -- Date when the cycle is due.
            due_date TEXT NOT NULL,

            -- Shows whether the cycle has been completed.
            --
            -- SQLite does not have a real BOOLEAN type,
            -- so we use:
            -- 0 = False / Not closed
            -- 1 = True / Closed
            closed INTEGER NOT NULL DEFAULT 0,

            -- A group cannot have two cycles with
            -- the same cycle number.
            --
            -- Example:
            -- Group 1 can have Cycle 1.
            -- Group 2 can also have Cycle 1.
            UNIQUE (group_id, cycle_number),

            -- Connect the cycle to its group.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE
        );


        ----------------------------------------------------------------
        -- 4. CONTRIBUTION TABLE
        ----------------------------------------------------------------
        -- Stores the payments/contributions made by members
        -- for a particular cycle.
        --
        -- One cycle can have many contributions.
        ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS contribution (

            -- Unique ID for this contribution record.
            contribution_pk INTEGER PRIMARY KEY AUTOINCREMENT,

            -- The cycle this contribution belongs to.
            cycle_pk INTEGER NOT NULL,

            -- The member who is making the contribution.
            member_id INTEGER NOT NULL,

            -- The group the member belongs to.
            --
            -- Keeping group_id here makes it easier to separate
            -- data belonging to different Njangi groups.
            group_id INTEGER NOT NULL,

            -- Amount the member is supposed to pay.
            amount_expected REAL NOT NULL,

            -- Amount the member has actually paid.
            --
            -- Default is 0 because a new contribution
            -- has not been paid yet.
            amount_paid REAL NOT NULL DEFAULT 0,

            -- Date the payment was made.
            --
            -- NULL means the member has not paid yet.
            date_paid TEXT,

            -- Current payment status.
            --
            -- Example:
            -- Pending
            -- Paid
            -- Late
            status TEXT NOT NULL DEFAULT 'Pending',

            -- Connect this contribution to a cycle.
            --
            -- If the cycle is deleted, its contributions
            -- are also deleted automatically.
            FOREIGN KEY (cycle_pk)
                REFERENCES cycle(cycle_pk)
                ON DELETE CASCADE,

            -- Make sure the member actually belongs
            -- to the specified group.
            FOREIGN KEY (member_id, group_id)
                REFERENCES member(member_id, group_id)
        );


        ----------------------------------------------------------------
        -- 5. LOAN TABLE
        ----------------------------------------------------------------
        -- Stores loans requested or taken by members.
        ----------------------------------------------------------------

        CREATE TABLE IF NOT EXISTS loan (

            -- Loan number.
            --
            -- Like member_id, the loan ID is unique
            -- only inside a particular group.
            loan_id INTEGER NOT NULL,

            -- Group that owns the loan.
            group_id INTEGER NOT NULL,

            -- Member who requested the loan.
            member_id INTEGER NOT NULL,

            -- Original amount borrowed.
            amount REAL NOT NULL,

            -- Interest rate for the loan.
            --
            -- Default is 5%.
            interest_rate REAL NOT NULL DEFAULT 5.0,

            -- Current loan status.
            --
            -- Example:
            -- Requested
            -- Approved
            -- Paid
            -- Rejected
            status TEXT NOT NULL DEFAULT 'Requested',

            -- Date when the loan was requested.
            date_requested TEXT NOT NULL,

            -- Date when the loan was approved.
            --
            -- NULL means the loan has not been approved yet.
            date_approved TEXT,

            -- Total amount the member has already repaid.
            --
            -- Starts at 0 because nothing has been paid
            -- when the loan is first created.
            amount_repaid REAL NOT NULL DEFAULT 0,

            -- A loan is identified by BOTH loan_id and group_id.
            --
            -- This allows different groups to have
            -- the same loan number.
            PRIMARY KEY (loan_id, group_id),

            -- Connect the loan to its Njangi group.
            --
            -- Deleting the group also deletes its loans.
            FOREIGN KEY (group_id)
                REFERENCES njangi_group(group_id)
                ON DELETE CASCADE,

            -- Make sure the member taking the loan
            -- belongs to the same group.
            FOREIGN KEY (member_id, group_id)
                REFERENCES member(member_id, group_id)
        );

        """
    )

    # Save all the table changes to the database.
    conn.commit()
```

