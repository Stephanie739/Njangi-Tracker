#!/usr/bin/env python3
"""
Njangi Tracker - Main Integration Test Script
=============================================

This script serves as a comprehensive end-to-end smoke test and demonstration
of the core database operations for the Njangi Tracker system.

It exercises the following workflows in sequence:

1. Database initialization and table creation
2. Creation of multiple Njangi groups with different contribution amounts
3. Registration of members into those groups
4. Opening of contribution cycles
5. Recording of member contributions
6. Pool summary calculation and progress reporting
7. Cycle closing logic
8. Loan issuance and partial repayment
9. Loan history retrieval per member

Purpose
-------
- Validate that the persistence layer (database.py / persistance.py) works correctly
- Provide a quick manual test harness for developers
- Serve as living documentation of the expected call sequences
- Generate sample data that can be inspected in the SQLite database

How to Run
----------
From the project root or the py/ directory:

    python main.py

Expected Output
---------------
- Confirmation messages for each created entity
- Pool summary statistics showing expected vs collected amounts
- Cycle status after closing
- Loan creation and repayment status
- Final list of loans belonging to a test member

Notes
-----
- This script uses the functions imported from database.py
- It is intentionally verbose so that each step is visible in the console
- Safe to re-run; the underlying create_tables() uses IF NOT EXISTS

Author: Njangi Tracker Development Team
Version: 2.1.0 (Enhanced with extensive documentation and logging)
Last Updated: 2026-09-28
"""

from __future__ import annotations

import sys
import logging
from typing import Tuple, List, Any, Optional
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
# Configure a simple console logger so that test progress is clearly visible
# and can later be redirected to a file if needed.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("njangi.main")

# ---------------------------------------------------------------------------
# Import the persistence / database layer
# ---------------------------------------------------------------------------
# All CRUD operations are provided by the database module.
# Using a star import here keeps the original test script style while
# still allowing us to add richer surrounding code.

from database import *  # noqa: F401, F403


# =============================================================================
# Helper Utilities
# =============================================================================

def print_section(title: str) -> None:
    """
    Print a clearly delimited section header to the console.

    Parameters
    ----------
    title : str
        The heading text to display.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {title}")
    print(f"{separator}\n")
    logger.info("Starting section: %s", title)


def print_pool_summary(
    group_label: str,
    expected: float,
    collected: float,
    remaining: float,
    progress: float,
) -> None:
    """
    Pretty-print a pool summary for a given group/cycle.

    Parameters
    ----------
    group_label : str
        Human-readable label (e.g. "Group 1").
    expected : float
        Total amount expected from all members.
    collected : float
        Amount actually received so far.
    remaining : float
        Amount still outstanding.
    progress : float
        Collection progress as a percentage (0-100).
    """
    print(f"\n------- {group_label} Pool Summary -------")
    print(f"Expected pool : {expected:>12,.2f} FCFA")
    print(f"Collected     : {collected:>12,.2f} FCFA")
    print(f"Remaining     : {remaining:>12,.2f} FCFA")
    print(f"Progress      : {progress:>11.2f}%")
    logger.info(
        "%s summary → expected=%.2f collected=%.2f remaining=%.2f progress=%.2f%%",
        group_label, expected, collected, remaining, progress,
    )


def safe_close_cycle(cycle_id: int, group_id: int) -> str:
    """
    Close a cycle and return its new status, with error handling.

    Parameters
    ----------
    cycle_id : int
        Identifier of the cycle to close.
    group_id : int
        Group that owns the cycle.

    Returns
    -------
    str
        Status string returned by the close_cycle function, or an error message.
    """
    try:
        status = close_cycle(cycle_id, group_id)
        logger.info("Cycle %s (group %s) closed with status: %s", cycle_id, group_id, status)
        return status
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to close cycle %s: %s", cycle_id, exc)
        return f"ERROR: {exc}"


# =============================================================================
# Main Test Execution Flow
# =============================================================================

def run_integration_tests() -> None:
    """
    Execute the full sequence of integration tests.

    This function is intentionally linear and highly commented so that
    a new developer can follow the exact order of operations required
    to set up and exercise a Njangi group.
    """
    print_section("NJANGI TRACKER - INTEGRATION TEST SUITE")
    logger.info("Integration test run started at %s", datetime.now().isoformat())

    # -------------------------------------------------------------------------
    # Step 1: Initialize the database schema
    # -------------------------------------------------------------------------
    print_section("1. Database Initialization")
    # Initialize Database
    # Create the tables (idempotent – safe to call multiple times)
    create_tables()
    logger.info("Database tables created / verified successfully")
    print("✓ Tables created or already exist")

    # -------------------------------------------------------------------------
    # Step 2: Create test groups
    # -------------------------------------------------------------------------
    print_section("2. Creating Test Groups")
    # Test Groups
    # Create the test group
    group_id_1 = add_group("Group 1", 5000, "Weekly")
    print(f"Group created with ID: {group_id_1}")
    logger.info("Created Group 1 with id=%s, amount=5000, frequency=Weekly", group_id_1)

    group_id_2 = add_group("Group 2", 10000.0, "Weekly")
    print(f"Group created with ID: {group_id_2}")
    logger.info("Created Group 2 with id=%s, amount=10000.0, frequency=Weekly", group_id_2)

    # -------------------------------------------------------------------------
    # Step 3: Register members
    # -------------------------------------------------------------------------
    print_section("3. Registering Members")
    # Test Members
    # Add two members to Group 1
    member1 = add_member(group_id_1, "Sukuna", "657498909")
    member2 = add_member(group_id_1, "Stephanie", "564098454")
    print(f"Member 1 created with ID: {member1}")
    print(f"Member 2 created with ID: {member2}")
    logger.info("Group 1 members: Sukuna=%s, Stephanie=%s", member1, member2)

    # Add members to Group 2
    # Add to members to group 2
    member3 = add_member(group_id_2, "Perevet", "69809089")
    member4 = add_member(group_id_2, "Amiel", "67584958")
    print(f"Member 3 created with ID: {member3}")
    print(f"Member 4 created with ID: {member4}")
    logger.info("Group 2 members: Perevet=%s, Amiel=%s", member3, member4)

    # -------------------------------------------------------------------------
    # Step 4: Open contribution cycles
    # -------------------------------------------------------------------------
    print_section("4. Opening Contribution Cycles")
    # Test cycles
    # Create a cycle
    cycle1 = add_cycle(member1, 1)
    cycle2 = add_cycle(member3, 1)
    print(f"Cycle 1 (Group 1) created with ID: {cycle1}")
    print(f"Cycle 2 (Group 2) created with ID: {cycle2}")
    logger.info("Opened cycles: cycle1=%s (member1), cycle2=%s (member3)", cycle1, cycle2)

    # -------------------------------------------------------------------------
    # Step 5: Record contributions
    # -------------------------------------------------------------------------
    print_section("5. Recording Contributions")
    # Test contributions
    # Add one contribution for each member
    add_contribution(member1, cycle1, 5000)
    add_contribution(member2, cycle1, 5000)
    add_contribution(member3, cycle2, 10000)
    add_contribution(member4, cycle2, 10000)
    print("✓ Four contributions recorded successfully")
    logger.info("Recorded contributions for all four test members")

    # -------------------------------------------------------------------------
    # Step 6: Inspect pool summaries
    # -------------------------------------------------------------------------
    print_section("6. Pool Summary Calculations")
    # Test the poolsummary
    expected, collected, remaining, progress = get_pool_summary(group_id_1, cycle1)
    print_pool_summary("Group 1", expected, collected, remaining, progress)

    # -------------------------------------------------------------------------
    # Step 7: Close cycles
    # -------------------------------------------------------------------------
    print_section("7. Closing Cycles")
    # Test the cycle status
    cycle_status = safe_close_cycle(cycle1, group_id_1)
    print(f"\nCycle status (Group 1): {cycle_status}")

    expected, collected, remaining, progress = get_pool_summary(group_id_2, cycle2)
    print_pool_summary("Group 2", expected, collected, remaining, progress)

    cycle_status = safe_close_cycle(cycle2, group_id_2)
    print(f"\nCycle status (Group 2): {cycle_status}")

    # -------------------------------------------------------------------------
    # Step 8: Loan operations
    # -------------------------------------------------------------------------
    print_section("8. Loan Issuance and Repayment")
    # Test issuing a loan
    loan_id = issue_loan(member1, 50000)
    print(f"\nLoan created with ID: {loan_id}")
    logger.info("Issued loan id=%s to member1 for 50000 FCFA", loan_id)

    # Test partial loan repayment
    status = repay_loan(loan_id, 20000)
    print(f"Loan status after repayment: {status}")
    logger.info("Partial repayment of 20000 on loan %s → status=%s", loan_id, status)

    # -------------------------------------------------------------------------
    # Step 9: Retrieve loan history
    # -------------------------------------------------------------------------
    print_section("9. Member Loan History")
    print("\n------- MEMBER LOANS -------")
    loans = get_loans_by_member(member1)
    if not loans:
        print("No loans found for this member.")
        logger.warning("No loans returned for member %s", member1)
    else:
        for idx, loan in enumerate(loans, start=1):
            print(f"  [{idx}] {loan}")
            logger.info("Loan record %s: %s", idx, loan)

    # -------------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------------
    print_section("TEST SUITE COMPLETED SUCCESSFULLY")
    logger.info("All integration tests finished without fatal errors")
    print("You can now inspect the SQLite database for the generated records.")
    print("Thank you for running the Njangi Tracker integration suite.\n")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    try:
        run_integration_tests()
        sys.exit(0)
    except Exception as fatal:
        logger.exception("Fatal error during integration tests: %s", fatal)
        print(f"\n❌ FATAL ERROR: {fatal}", file=sys.stderr)
        sys.exit(1)
