
from datetime import date, timedelta
from enum import Enum


class PaymentStatus(Enum):

    PAID = "Paid"          # full amount, on or before the due date
    PARTIAL = "Partial"    # some amount paid, but less than expected
    LATE = "Late"          # full amount paid, but after the due date
    MISSED = "Missed"      # due date has passed and nothing was paid
    PENDING = "Pending"    # due date has not passed yet, nothing paid so far


class Member:
    def __init__(self, member_id: int, name: str, phone_number: str):
        self.member_id = member_id
        self.name = name
        self.phone_number = phone_number
        self.join_date = date.today()

    def __repr__(self) -> str:
        return self.name


class Contribution:
    def __init__(self, member: Member, amount_expected: float):
        self.member = member
        self.amount_expected = amount_expected
        self.amount_paid = 0
        self.date_paid = None
        self.status = PaymentStatus.PENDING

    def log_payment(self, amount: float, due_date: date, payment_date: date = None) -> None:
        """Record a payment and update this contribution's status."""
        effective_date = payment_date or date.today()
        self.amount_paid = amount
        self.date_paid = effective_date

        if amount < self.amount_expected:
            # Paid something, but not the full expected amount.
            self.status = PaymentStatus.PARTIAL
        elif effective_date > due_date:
            # Paid in full, but after the due date.
            self.status = PaymentStatus.LATE
        else:
            self.status = PaymentStatus.PAID

    def mark_missed_if_overdue(self, due_date: date, today: date = None) -> None:
        """
        If the due date has passed and nothing has been paid at all,
        mark this contribution as MISSED instead of leaving it PENDING
        forever. Call this when displaying/refreshing a cycle's status.
        """
        today = today or date.today()
        if self.status == PaymentStatus.PENDING and today > due_date:
            self.status = PaymentStatus.MISSED

    def __repr__(self) -> str:
        return f"  - {self.member.name}: {self.status.value} ({self.amount_paid} FCFA)"


class Cycle:
    """One full round of a Njangi group: one recipient, all contributions."""

    def __init__(self, cycle_number: int, members: list, contribution_amount: float,
                 recipient: Member, due_date: date):
        self.cycle_number = cycle_number
        self.recipient = recipient
        self.due_date = due_date
        self.contributions = {
            m.member_id: Contribution(m, contribution_amount) for m in members
        }
        self.closed = False

    def record_payment(self, member_id: int, amount: float, payment_date: date = None) -> None:
        if member_id not in self.contributions:
            raise ValueError("Member not part of this cycle")
        self.contributions[member_id].log_payment(amount, self.due_date, payment_date)

    def refresh_overdue_statuses(self, today: date = None) -> None:
        """Update any still-PENDING contributions to MISSED if the due date has passed."""
        for contribution in self.contributions.values():
            contribution.mark_missed_if_overdue(self.due_date, today)

    def total_pool(self) -> float:
        return sum(c.amount_paid for c in self.contributions.values())

    def missing_members(self) -> list:
        """Members who have not yet paid in full (Pending, Partial, or Missed)."""
        return [
            c.member.name for c in self.contributions.values()
            if c.status in (PaymentStatus.PENDING, PaymentStatus.PARTIAL, PaymentStatus.MISSED)
        ]

    def is_fully_paid(self) -> bool:
        return all(c.status == PaymentStatus.PAID for c in self.contributions.values())

    def status_report(self) -> str:
        lines = [f"--- Cycle {self.cycle_number} (Recipient: {self.recipient.name}) ---"]
        for c in self.contributions.values():
            lines.append(f"{c}")
        lines.append(f"Total pool so far: {self.total_pool()} FCFA")
        return "\n".join(lines)

    def __repr__(self) -> str:
        status = "Closed" if self.closed else "Open"
        return f"Cycle {self.cycle_number} (Recipient: {self.recipient.name}, {status})"


class NjangiGroup:
    """A Njangi (tontine) savings group: members, rotation queue, and cycle history."""

    def __init__(self, group_name: str, contribution_amount: float, frequency_days: int = 30):
        self.group_name = group_name
        self.contribution_amount = contribution_amount
        self.frequency_days = frequency_days
        self.members = []
        self.rotation_queue = []
        self.cycles = []
        self.loans = []          # populated by loans.py functions (Task 6)
        self._next_member_id = 1
        self._next_loan_id = 1

    def add_member(self, name: str, phone_number: str) -> Member:
        m = Member(self._next_member_id, name, phone_number)
        self.members.append(m)
        self.rotation_queue.append(m)
        self._next_member_id += 1
        return m

    def start_new_cycle(self) -> Cycle:
        if not self.rotation_queue:
            raise ValueError("No members in rotation queue")
        recipient = self.rotation_queue.pop(0)
        self.rotation_queue.append(recipient)

        cycle_number = len(self.cycles) + 1
        due_date = date.today() + timedelta(days=self.frequency_days)

        c = Cycle(cycle_number, self.members, self.contribution_amount, recipient, due_date)
        self.cycles.append(c)
        return c

    def current_cycle(self) -> Cycle | None:
        return self.cycles[-1] if self.cycles else None

    def next_recipient(self) -> Member | None:
        return self.rotation_queue[0] if self.rotation_queue else None

    def group_summary(self) -> str:
        lines = [
            f"Group: {self.group_name}",
            f"Members: {len(self.members)}",
            f"Contribution per member: {self.contribution_amount} FCFA",
            f"Cycles completed: {sum(1 for c in self.cycles if c.closed)}",
            f"Next recipient in queue: {self.next_recipient().name if self.next_recipient() else 'None'}",
        ]
        return "\n".join(lines)