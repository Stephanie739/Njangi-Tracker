#!/usr/bin/env python3
"""
Njangi Tracker - Domain Model Classes
=====================================

This module defines the core object-oriented domain models for the Njangi Tracker
application. Njangi (also known as tontine or ROSCA - Rotating Savings and Credit
Association) is a traditional informal savings system widely practiced in Cameroon
and across West and Central Africa.

These classes represent the fundamental entities that make up a Njangi group:

1. NjangiGroup  - The savings group itself (name, contribution amount, frequency)
2. Member       - An individual participant in a group
3. Cycle        - A single round of the rotation where one member receives the pool
4. Contribution - A payment made by a member toward a specific cycle

Design Principles
-----------------
- Simple data-holder classes with clear constructors
- Explicit attributes for easy serialization and database mapping
- Self-documenting attribute names that match the database schema
- Ready for extension with validation methods and business rules

Future Enhancements
-------------------
- Add __repr__ and __str__ methods for better debugging
- Add validation in setters or properties
- Add methods for calculating reliability scores
- Add methods for determining next recipient in rotation
- Support for multi-group membership

Author: Njangi Tracker Development Team
Last Updated: 2026-09-28
Version: 2.1.0 (Enhanced documentation and structure)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# Constants and Configuration
# =============================================================================

DEFAULT_CONTRIBUTION_FREQUENCY = "Weekly"
SUPPORTED_FREQUENCIES = ("Daily", "Weekly", "Bi-Weekly", "Monthly")
DEFAULT_PAYMENT_STATUS = "Pending"
VALID_PAYMENT_STATUSES = ("Pending", "Partial", "Paid", "Overdue", "Waived")
DEFAULT_CYCLE_STATUS = "Open"
VALID_CYCLE_STATUSES = ("Open", "Closed", "Cancelled", "Pending")


# =============================================================================
# NjangiGroup Class
# =============================================================================

class NjangiGroup:
    """
    Represents a Njangi savings group.

    A NjangiGroup is the central organizing unit. It defines:
    - Who the members are
    - How much each member contributes per cycle
    - How frequently contributions are collected (Weekly, Monthly, etc.)

    Attributes
    ----------
    group_id : int
        Unique identifier for the group (usually from database AUTOINCREMENT).
    name : str
        Human-readable name of the group (e.g., "Family Savings 2026").
    contribution_amount : float
        Fixed amount each member is expected to contribute per cycle (in FCFA).
    frequency : str
        How often cycles occur. Common values: "Weekly", "Monthly".

    Example
    -------
    >>> group = NjangiGroup(1, "Douala Youth Njangi", 5000.0, "Weekly")
    >>> print(group.name)
    Douala Youth Njangi
    """

    def __init__(self, group_id: int, name: str, contribution_amount: float, frequency: str):
        """
        Initialize a new NjangiGroup instance.

        Parameters
        ----------
        group_id : int
            Unique identifier assigned by the persistence layer.
        name : str
            Display name of the group. Should be unique within the system.
        contribution_amount : float
            The standard contribution amount in FCFA (Central African CFA franc).
        frequency : str
            Contribution frequency. Recommended values are in SUPPORTED_FREQUENCIES.
        """
        # Core identity attributes
        self.group_id = group_id
        self.name = name
        self.contribution_amount = contribution_amount
        self.frequency = frequency

        # Optional extended attributes (can be populated later)
        self.created_at: Optional[str] = None
        self.member_count: int = 0
        self.is_active: bool = True

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"NjangiGroup(group_id={self.group_id}, name='{self.name}', "
            f"contribution_amount={self.contribution_amount}, frequency='{self.frequency}')"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"{self.name} ({self.contribution_amount} FCFA / {self.frequency})"

    def expected_pool_size(self, member_count: int) -> float:
        """
        Calculate the expected total pool for a full cycle.

        Parameters
        ----------
        member_count : int
            Number of active members expected to contribute.

        Returns
        -------
        float
            Total expected collection amount in FCFA.
        """
        return self.contribution_amount * member_count


# =============================================================================
# Member Class
# =============================================================================

class Member:
    """
    Represents an individual member of a Njangi group.

    Each member belongs to exactly one group in the current data model
    (composite key of member_id + group_id in the database). Members make
    contributions and can receive the pooled funds when it is their turn
    in the rotation.

    Attributes
    ----------
    member_id : int
        Identifier unique within the group.
    group_id : int
        Foreign key linking the member to their NjangiGroup.
    name : str
        Full name of the member.
    phone : str
        Contact phone number (Cameroon format preferred, e.g. 6XX XXX XXX).

    Example
    -------
    >>> member = Member(1, 1, "Sukuna", "657498909")
    >>> print(member.name)
    Sukuna
    """

    def __init__(self, member_id: int, group_id: int, name: str, phone: str):
        """
        Initialize a new Member instance.

        Parameters
        ----------
        member_id : int
            Local identifier within the group (not globally unique).
        group_id : int
            The group this member belongs to.
        name : str
            Member's display name.
        phone : str
            Phone number used for notifications and contact.
        """
        self.member_id = member_id
        self.group_id = group_id
        self.name = name
        self.phone = phone

        # Extended attributes for richer member profiles
        self.join_date: Optional[str] = None
        self.queue_position: Optional[int] = None
        self.reliability_score: float = 100.0
        self.total_contributed: float = 0.0
        self.is_active: bool = True

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Member(member_id={self.member_id}, group_id={self.group_id}, "
            f"name='{self.name}', phone='{self.phone}')"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"{self.name} ({self.phone})"

    def full_identifier(self) -> str:
        """
        Return a composite identifier useful for logging and uniqueness checks.

        Returns
        -------
        str
            String in the form "group_id:member_id".
        """
        return f"{self.group_id}:{self.member_id}"


# =============================================================================
# Cycle Class
# =============================================================================

class Cycle:
    """
    Represents a single contribution cycle (round) in a Njangi group.

    In a classic Njangi, each cycle has one designated recipient who receives
    the entire collected pool. Cycles are numbered sequentially within a group.
    A cycle remains "Open" while contributions are being collected and becomes
    "Closed" once the pool has been distributed.

    Attributes
    ----------
    cycle_id : int
        Unique identifier for this cycle record.
    member_id : int
        The member who is the designated recipient of this cycle's pool.
    cycle_number : int
        Sequential number of this cycle within its group (1, 2, 3, ...).
    status : str
        Current lifecycle status: typically "Open" or "Closed".

    Example
    -------
    >>> cycle = Cycle(1, 1, 1, "Open")
    >>> print(cycle.status)
    Open
    """

    def __init__(self, cycle_id: int, member_id: int, cycle_number: int, status: str):
        """
        Initialize a new Cycle instance.

        Parameters
        ----------
        cycle_id : int
            Primary key of the cycle record.
        member_id : int
            ID of the member receiving the pool this round.
        cycle_number : int
            Order of this cycle in the group's history.
        status : str
            Lifecycle status. Prefer values from VALID_CYCLE_STATUSES.
        """
        self.cycle_id = cycle_id
        self.member_id = member_id
        self.cycle_number = cycle_number
        self.status = status

        # Extended tracking attributes
        self.due_date: Optional[str] = None
        self.closed_at: Optional[str] = None
        self.total_collected: float = 0.0
        self.expected_total: float = 0.0

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Cycle(cycle_id={self.cycle_id}, member_id={self.member_id}, "
            f"cycle_number={self.cycle_number}, status='{self.status}')"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"Cycle #{self.cycle_number} ({self.status}) → Member {self.member_id}"

    def is_open(self) -> bool:
        """Return True if the cycle is still accepting contributions."""
        return self.status == "Open"

    def is_closed(self) -> bool:
        """Return True if the cycle has been finalized."""
        return self.status == "Closed"

    def progress_percentage(self) -> float:
        """
        Calculate collection progress as a percentage.

        Returns
        -------
        float
            Percentage of expected amount that has been collected (0-100).
            Returns 0.0 if expected_total is zero to avoid division by zero.
        """
        if self.expected_total <= 0:
            return 0.0
        return min(100.0, (self.total_collected / self.expected_total) * 100.0)


# =============================================================================
# Contribution Class
# =============================================================================

class Contribution:
    """
    Represents a single contribution (payment) made by a member toward a cycle.

    Contributions track how much a member has paid (or is expected to pay)
    for a particular cycle. Partial payments are supported via the amount
    and payment_status fields.

    Attributes
    ----------
    contribution_id : int
        Unique identifier for this contribution record.
    member_id : int
        The member who made (or should make) this contribution.
    cycle_id : int
        The cycle this contribution belongs to.
    amount : float
        The amount paid or expected (in FCFA).
    payment_status : str
        Status of the payment: Pending, Partial, Paid, Overdue, etc.

    Example
    -------
    >>> contrib = Contribution(1, 1, 1, 5000.0, "Paid")
    >>> print(contrib.amount)
    5000.0
    """

    def __init__(
        self,
        contribution_id: int,
        member_id: int,
        cycle_id: int,
        amount: float,
        payment_status: str,
    ):
        """
        Initialize a new Contribution instance.

        Parameters
        ----------
        contribution_id : int
            Primary key of the contribution.
        member_id : int
            Member who owns this contribution obligation.
        cycle_id : int
            Cycle this payment is associated with.
        amount : float
            Monetary value in FCFA.
        payment_status : str
            Current status. Prefer values from VALID_PAYMENT_STATUSES.
        """
        self.contribution_id = contribution_id
        self.member_id = member_id
        self.cycle_id = cycle_id
        self.amount = amount
        self.payment_status = payment_status

        # Extended payment tracking
        self.date_paid: Optional[str] = None
        self.amount_expected: Optional[float] = None
        self.notes: str = ""
        self.recorded_by: Optional[int] = None

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"Contribution(contribution_id={self.contribution_id}, "
            f"member_id={self.member_id}, cycle_id={self.cycle_id}, "
            f"amount={self.amount}, payment_status='{self.payment_status}')"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"Contribution {self.contribution_id}: {self.amount} FCFA ({self.payment_status})"

    def is_fully_paid(self) -> bool:
        """Return True if the contribution has been marked as fully paid."""
        return self.payment_status == "Paid"

    def is_pending(self) -> bool:
        """Return True if no payment has been recorded yet."""
        return self.payment_status == "Pending"

    def remaining_balance(self) -> float:
        """
        Calculate remaining amount if amount_expected is set.

        Returns
        -------
        float
            Difference between expected and paid amounts, or 0.0 if not applicable.
        """
        if self.amount_expected is None:
            return 0.0
        return max(0.0, self.amount_expected - self.amount)


# =============================================================================
# Utility Functions for Model Construction
# =============================================================================

def create_group_from_dict(data: Dict[str, Any]) -> NjangiGroup:
    """
    Factory function to create a NjangiGroup from a dictionary (e.g. database row).

    Parameters
    ----------
    data : dict
        Dictionary containing at least group_id, name, contribution_amount, frequency.

    Returns
    -------
    NjangiGroup
        Fully constructed group instance.
    """
    group = NjangiGroup(
        group_id=data["group_id"],
        name=data["name"],
        contribution_amount=float(data["contribution_amount"]),
        frequency=data.get("frequency", DEFAULT_CONTRIBUTION_FREQUENCY),
    )
    group.created_at = data.get("created_at")
    group.is_active = bool(data.get("is_active", True))
    return group


def create_member_from_dict(data: Dict[str, Any]) -> Member:
    """
    Factory function to create a Member from a dictionary.

    Parameters
    ----------
    data : dict
        Dictionary containing member_id, group_id, name, phone.

    Returns
    -------
    Member
        Fully constructed member instance.
    """
    member = Member(
        member_id=data["member_id"],
        group_id=data["group_id"],
        name=data["name"],
        phone=data.get("phone", data.get("phone_number", "")),
    )
    member.join_date = data.get("join_date")
    member.queue_position = data.get("queue_position")
    member.reliability_score = float(data.get("reliability_score", 100.0))
    return member


# End of model.py
# This module provides the foundational domain objects used throughout
# the Njangi Tracker application. Higher-level business logic lives in
# database.py, persistance.py, loans.py, and the main server.py module.
