#!/usr/bin/env python3
"""
Njangi Tracker - Loan Management Module
=======================================

This module implements the complete loan lifecycle for a Njangi group.

In traditional Njangi (ROSCA) systems, the primary purpose is rotating savings.
However, many modern groups also allow members to borrow from the accumulated
pool between cycles, subject to interest and eligibility rules. This module
provides a clean, object-oriented implementation of that capability.

Key Concepts
------------
- LoanStatus : Enumeration of all possible states a loan can be in
- Loan       : Rich domain object representing a single loan contract
- Helper functions that operate on a NjangiGroup's internal loan list

Business Rules Enforced
-----------------------
1. A member may have only one outstanding loan at a time
2. Loan amount must be positive
3. Requested amount cannot exceed currently available pool balance
4. Interest is calculated as a simple percentage of principal
5. Status transitions are strictly validated (no illegal jumps)

Status Lifecycle
----------------
    REQUESTED ──► APPROVED ──► ACTIVE ──► REPAID
         │
         └──────► REJECTED

Typical Usage
-------------
>>> from models import Member, NjangiGroup
>>> loan = request_loan(group, member, amount=50000.0, interest_rate=5.0)
>>> loan.approve()
>>> loan.disburse()
>>> loan.record_repayment(20000.0)
>>> print(loan.total_owed())

Author: Njangi Tracker Development Team
Version: 2.1.0 (Enhanced documentation, type hints, logging, validation)
Last Updated: 2026-09-28
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, TYPE_CHECKING

# Conditional import to avoid circular dependencies at type-checking time
if TYPE_CHECKING:
    from models import Member, NjangiGroup
else:
    from models import Member, NjangiGroup

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
logger = logging.getLogger("njangi.loans")


# =============================================================================
# Loan Status Enumeration
# =============================================================================

class LoanStatus(Enum):
    """
    Enumeration of all valid loan lifecycle states.

    Using an Enum instead of raw strings provides:
    - Compile-time safety against typos
    - Clear documentation of allowed values
    - Easy iteration and comparison
    """

    REQUESTED = "Requested"  # member has asked for a loan, not yet approved
    APPROVED = "Approved"    # approved but money not yet handed over
    ACTIVE = "Active"        # disbursed, member owes money
    REPAID = "Repaid"        # fully paid back
    REJECTED = "Rejected"    # request turned down

    def __str__(self) -> str:
        """Return the human-readable status string."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "LoanStatus":
        """
        Convert a string (e.g. from database) back into a LoanStatus.

        Parameters
        ----------
        value : str
            Status string such as "Requested" or "Active".

        Returns
        -------
        LoanStatus
            Matching enumeration member.

        Raises
        ------
        ValueError
            If the string does not match any known status.
        """
        for status in cls:
            if status.value.lower() == value.lower():
                return status
        raise ValueError(f"Unknown loan status: {value!r}")


# =============================================================================
# Loan Domain Object
# =============================================================================

class Loan:
    """
    A loan taken by a member from the group's pooled funds, repaid with
    interest. Interest earned stays with the group (extra income shared
    across members at cycle end, or just left in the pool).

    Attributes
    ----------
    loan_id : int
        Unique identifier assigned by the group when the loan is created.
    member : Member
        The member who requested (and will repay) the loan.
    amount : float
        Principal amount requested, in FCFA.
    interest_rate : float
        Annualized simple interest rate as a percentage (default 5.0).
    status : LoanStatus
        Current lifecycle state.
    date_requested : date
        Calendar date when the request was submitted.
    date_approved : Optional[date]
        Calendar date when an administrator approved the loan (None until then).
    amount_repaid : float
        Cumulative amount already paid back by the member.
    """

    def __init__(
        self,
        loan_id: int,
        member: Member,
        amount: float,
        interest_rate: float = 5.0,
    ):
        """
        Construct a new Loan in the REQUESTED state.

        Parameters
        ----------
        loan_id : int
            Identifier allocated by the owning NjangiGroup.
        member : Member
            Borrower.
        amount : float
            Principal in FCFA. Must be positive.
        interest_rate : float, optional
            Simple interest percentage (default is 5.0%).
        """
        if amount <= 0:
            raise ValueError("Loan principal must be a positive number")
        if interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")

        self.loan_id = loan_id
        self.member = member
        self.amount = amount
        self.interest_rate = interest_rate
        self.status = LoanStatus.REQUESTED
        self.date_requested = date.today()
        self.date_approved: Optional[date] = None
        self.amount_repaid = 0.0

        # Extended metadata for richer reporting
        self.notes: str = ""
        self.approved_by: Optional[str] = None
        self.disbursed_at: Optional[datetime] = None

        logger.info(
            "Created loan request id=%s for member=%s amount=%.2f rate=%.2f%%",
            loan_id, member.name, amount, interest_rate,
        )

    def total_owed(self) -> float:
        """
        Principal + interest, minus whatever has already been repaid.

        Returns
        -------
        float
            Remaining balance rounded to 2 decimal places (FCFA cents).
        """
        principal_plus_interest = self.amount * (1 + self.interest_rate / 100)
        remaining = principal_plus_interest - self.amount_repaid
        return round(max(0.0, remaining), 2)

    def principal_plus_interest(self) -> float:
        """
        Return the full amount that will eventually be due (before any repayments).

        Returns
        -------
        float
            Principal multiplied by (1 + interest_rate/100).
        """
        return round(self.amount * (1 + self.interest_rate / 100), 2)

    def approve(self) -> None:
        """
        Transition the loan from REQUESTED to APPROVED.

        Raises
        ------
        ValueError
            If the current status is not REQUESTED.
        """
        if self.status != LoanStatus.REQUESTED:
            raise ValueError(f"Cannot approve a loan with status {self.status.value}")
        self.status = LoanStatus.APPROVED
        self.date_approved = date.today()
        logger.info("Loan %s approved on %s", self.loan_id, self.date_approved)

    def reject(self) -> None:
        """
        Transition the loan from REQUESTED to REJECTED.

        Raises
        ------
        ValueError
            If the current status is not REQUESTED.
        """
        if self.status != LoanStatus.REQUESTED:
            raise ValueError(f"Cannot reject a loan with status {self.status.value}")
        self.status = LoanStatus.REJECTED
        logger.info("Loan %s rejected", self.loan_id)

    def disburse(self) -> None:
        """
        Marks an approved loan as active (money considered handed over).

        Raises
        ------
        ValueError
            If the current status is not APPROVED.
        """
        if self.status != LoanStatus.APPROVED:
            raise ValueError(f"Cannot disburse a loan with status {self.status.value}")
        self.status = LoanStatus.ACTIVE
        self.disbursed_at = datetime.now()
        logger.info("Loan %s disbursed at %s", self.loan_id, self.disbursed_at)

    def record_repayment(self, amount: float) -> None:
        """
        Apply a repayment toward the outstanding balance.

        If the remaining balance reaches zero (or goes negative due to
        rounding), the loan is automatically marked REPAID.

        Parameters
        ----------
        amount : float
            Positive amount being paid now.

        Raises
        ------
        ValueError
            If the loan is not ACTIVE or the amount is not positive.
        """
        if self.status != LoanStatus.ACTIVE:
            raise ValueError(f"Cannot repay a loan with status {self.status.value}")
        if amount <= 0:
            raise ValueError("Repayment amount must be positive")

        self.amount_repaid += amount
        logger.info(
            "Recorded repayment of %.2f on loan %s (total repaid now %.2f)",
            amount, self.loan_id, self.amount_repaid,
        )

        if self.total_owed() <= 0:
            self.status = LoanStatus.REPAID
            logger.info("Loan %s fully repaid", self.loan_id)

    def is_outstanding(self) -> bool:
        """Return True if the loan still represents a claim on the member."""
        return self.status in (
            LoanStatus.REQUESTED,
            LoanStatus.APPROVED,
            LoanStatus.ACTIVE,
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"Loan({self.member.name}, {self.amount} FCFA, "
            f"{self.status.value}, owed: {self.total_owed()})"
        )

    def __str__(self) -> str:
        """User-friendly representation."""
        return (
            f"Loan #{self.loan_id} — {self.member.name}: "
            f"{self.amount:,.0f} FCFA @ {self.interest_rate}% "
            f"[{self.status.value}] (owed: {self.total_owed():,.2f})"
        )


# =============================================================================
# Group-level Loan Helper Functions
# =============================================================================
# Functions that operate on a NjangiGroup's `.loans` list.
# `group.loans` and `group._next_loan_id` are plain attributes that
# models.py's NjangiGroup already has (see models.py __init__), so this
# file just reads/writes them without needing NjangiGroup to know
# anything about loan logic itself.
# =============================================================================

def available_pool_balance(group: NjangiGroup) -> float:
    """
    Funds available for lending: total pool of the current cycle,
    minus whatever is already tied up in approved/active loans.

    Parameters
    ----------
    group : NjangiGroup
        The group whose pool is being inspected.

    Returns
    -------
    float
        Amount still available for new loans (may be zero or negative
        if the pool has been over-committed – callers should check).
    """
    cycle = group.current_cycle()
    pool = cycle.total_pool() if cycle else 0.0
    committed = sum(
        loan.amount
        for loan in group.loans
        if loan.status in (LoanStatus.APPROVED, LoanStatus.ACTIVE)
    )
    available = pool - committed
    logger.debug(
        "Available pool for group %s: pool=%.2f committed=%.2f available=%.2f",
        getattr(group, "name", "?"), pool, committed, available,
    )
    return available


def request_loan(
    group: NjangiGroup,
    member: Member,
    amount: float,
    interest_rate: float = 5.0,
) -> Loan:
    """
    A member requests a loan against the group's available pool.

    Business rules enforced here:
      - amount must be positive
      - member can't have more than one outstanding loan at a time
      - amount can't exceed what's currently available in the pool

    Parameters
    ----------
    group : NjangiGroup
        Group that will fund the loan.
    member : Member
        Requesting member (must belong to the group).
    amount : float
        Desired principal.
    interest_rate : float, optional
        Interest percentage (default 5.0).

    Returns
    -------
    Loan
        Newly created loan object already appended to group.loans.

    Raises
    ------
    ValueError
        If any business rule is violated.
    """
    if amount <= 0:
        raise ValueError("Loan amount must be positive")

    has_outstanding = any(
        loan.member.member_id == member.member_id
        and loan.status in (
            LoanStatus.REQUESTED,
            LoanStatus.APPROVED,
            LoanStatus.ACTIVE,
        )
        for loan in group.loans
    )
    if has_outstanding:
        raise ValueError(f"{member.name} already has an outstanding loan")

    available = available_pool_balance(group)
    if amount > available:
        raise ValueError(
            f"Requested amount ({amount:.2f}) exceeds the group's "
            f"available pool balance ({available:.2f})"
        )

    loan = Loan(group._next_loan_id, member, amount, interest_rate)
    group.loans.append(loan)
    group._next_loan_id += 1

    logger.info(
        "Loan request accepted: id=%s member=%s amount=%.2f available_was=%.2f",
        loan.loan_id, member.name, amount, available,
    )
    return loan


def member_loans(group: NjangiGroup, member: Member) -> List[Loan]:
    """
    Return all loans (any status) belonging to a specific member.

    Parameters
    ----------
    group : NjangiGroup
        Group to search.
    member : Member
        Member whose loans are requested.

    Returns
    -------
    list[Loan]
        Possibly empty list of Loan objects.
    """
    result = [
        loan
        for loan in group.loans
        if loan.member.member_id == member.member_id
    ]
    logger.debug(
        "Found %d loan(s) for member %s in group %s",
        len(result), member.name, getattr(group, "name", "?"),
    )
    return result


def outstanding_loans(group: NjangiGroup) -> List[Loan]:
    """
    Return every loan in the group that is still outstanding.

    Parameters
    ----------
    group : NjangiGroup
        Group to inspect.

    Returns
    -------
    list[Loan]
        Loans whose status is REQUESTED, APPROVED or ACTIVE.
    """
    return [loan for loan in group.loans if loan.is_outstanding()]


def total_outstanding_principal(group: NjangiGroup) -> float:
    """
    Sum of principal amounts currently tied up in active/approved loans.

    Useful for high-level financial dashboards.
    """
    return sum(
        loan.amount
        for loan in group.loans
        if loan.status in (LoanStatus.APPROVED, LoanStatus.ACTIVE)
    )


# End of loans.py
# This module is intentionally free of any database or HTTP concerns.
# Persistence of Loan objects is handled by higher layers (persistance.py
# or server.py) which convert between these domain objects and SQLite rows.
