

from datetime import date
from enum import Enum

from models import Member, NjangiGroup


class LoanStatus(Enum):

    REQUESTED = "Requested"  # member has asked for a loan, not yet approved
    APPROVED = "Approved"    # approved but money not yet handed over
    ACTIVE = "Active"        # disbursed, member owes money
    REPAID = "Repaid"        # fully paid back
    REJECTED = "Rejected"    # request turned down


class Loan:
    """
    A loan taken by a member from the group's pooled funds, repaid with
    interest. Interest earned stays with the group (extra income shared
    across members at cycle end, or just left in the pool).
    """

    def __init__(self, loan_id: int, member: Member, amount: float,
                 interest_rate: float = 5.0):
        self.loan_id = loan_id
        self.member = member
        self.amount = amount
        self.interest_rate = interest_rate
        self.status = LoanStatus.REQUESTED
        self.date_requested = date.today()
        self.date_approved = None
        self.amount_repaid = 0.0

    def total_owed(self) -> float:
        """Principal + interest, minus whatever has already been repaid."""
        principal_plus_interest = self.amount * (1 + self.interest_rate / 100)
        return round(principal_plus_interest - self.amount_repaid, 2)

    def approve(self) -> None:
        if self.status != LoanStatus.REQUESTED:
            raise ValueError(f"Cannot approve a loan with status {self.status.value}")
        self.status = LoanStatus.APPROVED
        self.date_approved = date.today()

    def reject(self) -> None:
        if self.status != LoanStatus.REQUESTED:
            raise ValueError(f"Cannot reject a loan with status {self.status.value}")
        self.status = LoanStatus.REJECTED

    def disburse(self) -> None:
        """Marks an approved loan as active (money considered handed over)."""
        if self.status != LoanStatus.APPROVED:
            raise ValueError(f"Cannot disburse a loan with status {self.status.value}")
        self.status = LoanStatus.ACTIVE

    def record_repayment(self, amount: float) -> None:
        if self.status != LoanStatus.ACTIVE:
            raise ValueError(f"Cannot repay a loan with status {self.status.value}")
        if amount <= 0:
            raise ValueError("Repayment amount must be positive")

        self.amount_repaid += amount
        if self.total_owed() <= 0:
            self.status = LoanStatus.REPAID

    def __repr__(self) -> str:
        return (f"Loan({self.member.name}, {self.amount} FCFA, "
                f"{self.status.value}, owed: {self.total_owed()})")


# ---------------------------------------------------------------------------
# Functions that operate on a NjangiGroup's `.loans` list.
# `group.loans` and `group._next_loan_id` are plain attributes that
# models.py's NjangiGroup already has (see models.py __init__), so this
# file just reads/writes them without needing NjangiGroup to know
# anything about loan logic itself.
# ---------------------------------------------------------------------------

def available_pool_balance(group: NjangiGroup) -> float:
    """
    Funds available for lending: total pool of the current cycle,
    minus whatever is already tied up in approved/active loans.
    """
    cycle = group.current_cycle()
    pool = cycle.total_pool() if cycle else 0
    committed = sum(
        loan.amount for loan in group.loans
        if loan.status in (LoanStatus.APPROVED, LoanStatus.ACTIVE)
    )
    return pool - committed


def request_loan(group: NjangiGroup, member: Member, amount: float,
                  interest_rate: float = 5.0) -> Loan:
    """
    A member requests a loan against the group's available pool.
    Business rules enforced here:
      - amount must be positive
      - member can't have more than one outstanding loan at a time
      - amount can't exceed what's currently available in the pool
    """
    if amount <= 0:
        raise ValueError("Loan amount must be positive")

    has_outstanding = any(
        loan.member.member_id == member.member_id
        and loan.status in (LoanStatus.REQUESTED, LoanStatus.APPROVED, LoanStatus.ACTIVE)
        for loan in group.loans
    )
    if has_outstanding:
        raise ValueError(f"{member.name} already has an outstanding loan")

    if amount > available_pool_balance(group):
        raise ValueError("Requested amount exceeds the group's available pool balance")

    loan = Loan(group._next_loan_id, member, amount, interest_rate)
    group.loans.append(loan)
    group._next_loan_id += 1
    return loan


def member_loans(group: NjangiGroup, member: Member) -> list:
    return [loan for loan in group.loans if loan.member.member_id == member.member_id]