"""
Njangi Tracker — SQLite Schema
Step 1: Updated schema supporting phone numbers, 4-digit PIN hashes (pin_hash),
group memberships, unique njangi_code, multi-fund support, and RBAC roles.

This module only defines table structures. Data access lives in database.py /
server.py. Safe to call create_schema() on every app start.
"""

import sqlite3
from pathlib import Path

# Default path used by the py/ modules. The main web server (server.py) uses
# njangi_app.db; keep this separate so the two layers can coexist during migration.
DB_PATH = str(Path(__file__).resolve().parent.parent / "njangi.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a connection with foreign keys enabled."""
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """
    Create all tables if they do not already exist.

    Design notes
    ------------
    - groups.njangi_code  : human-readable public code (e.g. NJG-X7K9P)
    - groups.uuid         : system UUID for global ledger separation
    - members.pin_hash    : salted hash of the 4-digit PIN
    - members.phone       : primary login identifier for members
    - group_memberships   : supports multi-group membership for one user profile
    - roles               : President / Secretary / Treasurer / Auditor / Member
    - funds               : Main Pot, Social/Trouble Fund, Investment Fund
    """
    conn.executescript(
        """
        -- ============================================================
        -- GROUPS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS groups (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            name                  TEXT NOT NULL,
            njangi_code           TEXT NOT NULL UNIQUE,          -- e.g. NJG-X7K9P
            uuid                  TEXT NOT NULL UNIQUE,          -- system UUID
            contribution_amount   REAL NOT NULL DEFAULT 0,
            frequency             TEXT NOT NULL DEFAULT 'Monthly',
            frequency_days        INTEGER NOT NULL DEFAULT 30,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_groups_njangi_code
            ON groups(njangi_code);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_groups_uuid
            ON groups(uuid);

        -- ============================================================
        -- USERS (global profile — one person can belong to many groups)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS users (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            phone                 TEXT NOT NULL UNIQUE,          -- primary login key
            email                 TEXT UNIQUE,
            name                  TEXT NOT NULL,
            pin_hash              TEXT,                          -- 4-digit PIN (hashed)
            password_hash         TEXT,                          -- optional email/password
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at            TEXT
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_users_phone ON users(phone);

        -- ============================================================
        -- GROUP MEMBERSHIPS (many-to-many: user ↔ group + role + shares)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS group_memberships (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER NOT NULL,
            group_id              INTEGER NOT NULL,
            role                  TEXT NOT NULL DEFAULT 'Member'
                                  CHECK (role IN (
                                      'President', 'Secretary', 'Treasurer',
                                      'Auditor', 'Member'
                                  )),
            share_count           INTEGER NOT NULL DEFAULT 1,
            member_code           TEXT,                          -- e.g. MBR-000042
            rotation_position     INTEGER NOT NULL DEFAULT 0,
            enrolled              INTEGER NOT NULL DEFAULT 1,     -- 0/1
            status                TEXT NOT NULL DEFAULT 'Active'
                                  CHECK (status IN (
                                      'Pending', 'Active', 'Suspended', 'Left'
                                  )),
            join_date             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            UNIQUE (user_id, group_id)
        );

        CREATE INDEX IF NOT EXISTS idx_memberships_group
            ON group_memberships(group_id);
        CREATE INDEX IF NOT EXISTS idx_memberships_user
            ON group_memberships(user_id);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_memberships_member_code
            ON group_memberships(member_code) WHERE member_code IS NOT NULL;

        -- ============================================================
        -- FUNDS (multi-fund accounting inside one group)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS funds (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            name                  TEXT NOT NULL,                 -- Main, Social, Investment
            fund_type             TEXT NOT NULL
                                  CHECK (fund_type IN (
                                      'Main', 'Social', 'Investment'
                                  )),
            balance               REAL NOT NULL DEFAULT 0,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            UNIQUE (group_id, fund_type)
        );

        -- ============================================================
        -- CYCLES
        -- ============================================================
        CREATE TABLE IF NOT EXISTS cycles (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            number                INTEGER NOT NULL,
            target                REAL NOT NULL DEFAULT 0,
            start_date            TEXT NOT NULL,
            end_date              TEXT NOT NULL,
            recipient_membership_id INTEGER,                     -- who receives the pot
            status                TEXT NOT NULL DEFAULT 'OPEN'
                                  CHECK (status IN ('OPEN', 'CLOSED', 'PAID_OUT')),
            paid_out_at           TEXT,
            paid_out_amount       REAL NOT NULL DEFAULT 0,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            FOREIGN KEY (recipient_membership_id)
                REFERENCES group_memberships(id),
            UNIQUE (group_id, number)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_one_open_cycle
            ON cycles(group_id) WHERE status = 'OPEN';

        -- ============================================================
        -- CONTRIBUTIONS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS contributions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            membership_id         INTEGER NOT NULL,
            cycle_id              INTEGER NOT NULL,
            fund_id               INTEGER,                       -- which pot received it
            amount                REAL NOT NULL DEFAULT 0,
            amount_expected       REAL NOT NULL DEFAULT 0,
            date_paid             TEXT,
            status                TEXT NOT NULL DEFAULT 'Pending'
                                  CHECK (status IN (
                                      'Pending', 'Partial', 'Paid', 'Late'
                                  )),
            payment_method        TEXT DEFAULT 'Cash'
                                  CHECK (payment_method IN (
                                      'Cash', 'MTN_MoMo', 'Orange_Money', 'Bank'
                                  )),
            recorded_by           INTEGER,                       -- admin/treasurer user_id
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id)      REFERENCES groups(id),
            FOREIGN KEY (membership_id) REFERENCES group_memberships(id),
            FOREIGN KEY (cycle_id)      REFERENCES cycles(id) ON DELETE CASCADE,
            FOREIGN KEY (fund_id)       REFERENCES funds(id)
        );

        CREATE INDEX IF NOT EXISTS idx_contributions_cycle
            ON contributions(cycle_id);
        CREATE INDEX IF NOT EXISTS idx_contributions_membership
            ON contributions(membership_id);

        -- ============================================================
        -- LOANS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS loans (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            membership_id         INTEGER,                       -- py/ multi-group path
            member_id             INTEGER,                       -- server.py path (members.id)
            amount                REAL NOT NULL,
            interest_rate         REAL NOT NULL DEFAULT 5.0,
            total_due             REAL NOT NULL DEFAULT 0,
            amount_repaid         REAL NOT NULL DEFAULT 0,
            reason                TEXT,
            payback_months        INTEGER NOT NULL DEFAULT 1,     -- requested payback period
            status                TEXT NOT NULL DEFAULT 'Requested'
                                  CHECK (status IN (
                                      'Requested', 'Pending', 'PENDING',
                                      'Verified', 'Approved', 'APPROVED',
                                      'Disbursed', 'Active', 'ACTIVE',
                                      'Repaid', 'COMPLETED', 'Rejected', 'REJECTED',
                                      'Defaulted'
                                  )),
            date_requested        TEXT NOT NULL,
            date_verified         TEXT,
            date_approved         TEXT,
            date_disbursed        TEXT,
            verified_by           INTEGER,
            approved_by           INTEGER,
            disbursed_by          INTEGER,
            required_guarantors   INTEGER NOT NULL DEFAULT 1,     -- 1–3
            FOREIGN KEY (group_id) REFERENCES groups(id)
        );

        CREATE INDEX IF NOT EXISTS idx_loans_group ON loans(group_id);
        CREATE INDEX IF NOT EXISTS idx_loans_membership ON loans(membership_id);
        CREATE INDEX IF NOT EXISTS idx_loans_member ON loans(member_id);

        -- ============================================================
        -- GUARANTORS (loan_guarantors)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS loan_guarantors (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id               INTEGER NOT NULL,
            guarantor_membership_id INTEGER,                     -- py/ path
            guarantor_member_id   INTEGER,                       -- server.py members.id
            status                TEXT NOT NULL DEFAULT 'Pending'
                                  CHECK (status IN (
                                      'Pending', 'Accepted', 'Rejected'
                                  )),
            signed_at             TEXT,
            note                  TEXT,
            FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE,
            UNIQUE (loan_id, guarantor_member_id)
        );

        CREATE INDEX IF NOT EXISTS idx_guarantors_loan ON loan_guarantors(loan_id);

        -- ============================================================
        -- LOAN PAYMENTS
        -- ============================================================
        CREATE TABLE IF NOT EXISTS loan_payments (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id               INTEGER NOT NULL,
            group_id              INTEGER NOT NULL,
            amount                REAL NOT NULL,
            payment_date          TEXT NOT NULL,
            recorded_by           INTEGER,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id)  REFERENCES loans(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        );

        -- ============================================================
        -- LEDGER TRANSACTIONS (immutable financial audit trail)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS ledger_transactions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            fund_id               INTEGER,
            fund_type             TEXT NOT NULL DEFAULT 'MAIN_POT'
                                  CHECK (fund_type IN (
                                      'MAIN_POT', 'CAISSE_SOCIALE', 'INVESTMENT_PROJECT'
                                  )),
            member_id             INTEGER,
            loan_id               INTEGER,
            tx_type               TEXT NOT NULL
                                  CHECK (tx_type IN (
                                      'CONTRIBUTION', 'PAYOUT', 'LOAN_DISBURSE',
                                      'LOAN_REPAY', 'FINE', 'FEE', 'ADJUSTMENT',
                                      'SOCIAL_GRANT', 'INVESTMENT', 'MOMO_PAYMENT'
                                  )),
            direction             TEXT NOT NULL
                                  CHECK (direction IN ('IN', 'OUT')),
            amount                REAL NOT NULL,
            balance_after         REAL,
            reference             TEXT,
            description           TEXT,
            recorded_by           INTEGER,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ledger_group ON ledger_transactions(group_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_member ON ledger_transactions(member_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_loan ON ledger_transactions(loan_id);
        CREATE INDEX IF NOT EXISTS idx_ledger_type ON ledger_transactions(tx_type);

        -- ============================================================
        -- PAYOUT CYCLES & POT BIDS (rotation / bidding engine)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS payout_cycles (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            cycle_id              INTEGER,                       -- link to cycles table
            number                INTEGER NOT NULL,
            beneficiary_member_id INTEGER,
            pot_amount            REAL NOT NULL DEFAULT 0,
            status                TEXT NOT NULL DEFAULT 'OPEN'
                                  CHECK (status IN ('OPEN', 'BIDDING', 'AWARDED', 'DISBURSED', 'CLOSED')),
            bidding_opens         TEXT,
            bidding_closes        TEXT,
            awarded_at            TEXT,
            disbursed_at          TEXT,
            disbursed_by          INTEGER,
            winning_bid_id        INTEGER,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_payout_cycles_group ON payout_cycles(group_id);

        CREATE TABLE IF NOT EXISTS pot_bids (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            payout_cycle_id       INTEGER NOT NULL,
            group_id              INTEGER NOT NULL,
            member_id             INTEGER NOT NULL,
            discount_amount       REAL NOT NULL DEFAULT 0,       -- how much they discount from full pot
            bid_percent           REAL NOT NULL DEFAULT 0,       -- optional % discount
            status                TEXT NOT NULL DEFAULT 'Active'
                                  CHECK (status IN ('Active', 'Withdrawn', 'Won', 'Lost')),
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payout_cycle_id) REFERENCES payout_cycles(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            UNIQUE (payout_cycle_id, member_id)
        );

        CREATE INDEX IF NOT EXISTS idx_pot_bids_cycle ON pot_bids(payout_cycle_id);

        -- ============================================================
        -- ATTENDANCE & FINES
        -- ============================================================
        CREATE TABLE IF NOT EXISTS attendance (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            cycle_id              INTEGER,
            membership_id         INTEGER NOT NULL,
            meeting_date          TEXT NOT NULL,
            status                TEXT NOT NULL DEFAULT 'Present'
                                  CHECK (status IN (
                                      'Present', 'Late', 'Absent', 'Excused'
                                  )),
            recorded_by           INTEGER,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id)      REFERENCES groups(id),
            FOREIGN KEY (membership_id) REFERENCES group_memberships(id)
        );

        CREATE TABLE IF NOT EXISTS fines (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER NOT NULL,
            membership_id         INTEGER NOT NULL,
            amount                REAL NOT NULL,
            reason                TEXT NOT NULL,                 -- Late, Absent, LateContribution
            status                TEXT NOT NULL DEFAULT 'Unpaid'
                                  CHECK (status IN ('Unpaid', 'Paid', 'Waived')),
            issued_by             INTEGER,
            issued_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            paid_at               TEXT,
            FOREIGN KEY (group_id)      REFERENCES groups(id),
            FOREIGN KEY (membership_id) REFERENCES group_memberships(id)
        );

        -- ============================================================
        -- SESSIONS & SECURITY
        -- ============================================================
        CREATE TABLE IF NOT EXISTS sessions (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash            TEXT NOT NULL UNIQUE,
            user_id               INTEGER NOT NULL,
            membership_id         INTEGER,                       -- active group context
            role                  TEXT NOT NULL,
            group_id              INTEGER,
            created_at            REAL NOT NULL,
            expires_at            REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash);

        CREATE TABLE IF NOT EXISTS login_throttle (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            account_key           TEXT NOT NULL UNIQUE,          -- phone or email
            attempts              INTEGER NOT NULL DEFAULT 0,
            locked_until          REAL NOT NULL DEFAULT 0,
            updated_at            REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reset_tokens (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER NOT NULL,
            code_hash             TEXT NOT NULL,
            token                 TEXT NOT NULL UNIQUE,
            expires_at            REAL NOT NULL,
            used                  INTEGER NOT NULL DEFAULT 0,
            verified              INTEGER NOT NULL DEFAULT 0,
            attempts              INTEGER NOT NULL DEFAULT 0,
            created_at            REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_reset_token ON reset_tokens(token);

        -- ============================================================
        -- AUDIT LOG (for Auditor role + President oversight)
        -- ============================================================
        CREATE TABLE IF NOT EXISTS audit_log (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id              INTEGER,
            user_id               INTEGER,
            action                TEXT NOT NULL,
            entity_type           TEXT,
            entity_id             INTEGER,
            details               TEXT,
            created_at            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_audit_group ON audit_log(group_id);
        """
    )
    conn.commit()


def migrate_schema(conn: sqlite3.Connection) -> None:
    """
    Idempotent upgrades for older databases.
    Safe to call after create_schema().
    """
    upgrades = [
        "ALTER TABLE groups ADD COLUMN njangi_code TEXT",
        "ALTER TABLE groups ADD COLUMN uuid TEXT",
        "ALTER TABLE groups ADD COLUMN frequency_days INTEGER NOT NULL DEFAULT 30",
        "ALTER TABLE users ADD COLUMN pin_hash TEXT",
        "ALTER TABLE users ADD COLUMN password_hash TEXT",
        "ALTER TABLE group_memberships ADD COLUMN share_count INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE group_memberships ADD COLUMN member_code TEXT",
        "ALTER TABLE contributions ADD COLUMN fund_id INTEGER",
        "ALTER TABLE contributions ADD COLUMN payment_method TEXT DEFAULT 'Cash'",
        "ALTER TABLE loans ADD COLUMN total_due REAL NOT NULL DEFAULT 0",
        "ALTER TABLE loans ADD COLUMN payback_months INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE loans ADD COLUMN required_guarantors INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE loans ADD COLUMN member_id INTEGER",
        "ALTER TABLE loan_guarantors ADD COLUMN guarantor_member_id INTEGER",
        "ALTER TABLE loan_guarantors ADD COLUMN note TEXT",
        "ALTER TABLE cycles ADD COLUMN paid_out_at TEXT",
        "ALTER TABLE cycles ADD COLUMN paid_out_amount REAL NOT NULL DEFAULT 0",
    ]
    for sql in upgrades:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()


if __name__ == "__main__":
    connection = get_connection()
    create_schema(connection)
    migrate_schema(connection)
    connection.close()
    print(f"Schema created/updated successfully at {DB_PATH}")
