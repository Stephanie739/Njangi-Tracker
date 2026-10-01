from datetime import date, timedelta 
from enum import Enum 
 
 
# Defines the different payment statuses that a contribution can have.
class PaymentStatus(Enum): 
 
    PAID = "Paid"          # Full amount was paid on or before the due date.
    PARTIAL = "Partial"    # Some amount was paid, but it is less than expected.
    LATE = "Late"          # Full amount was paid, but after the due date.
    MISSED = "Missed"      # Due date has passed and nothing was paid.
    PENDING = "Pending"    # Due date has not passed and no payment has been made.
 
 
# Represents a member of the Njangi group.
class Member: 
    def __init__(self, member_id: int, name: str, phone_number: str): 
        # Stores the unique ID of the member.
        self.member_id = member_id 
        
        # Stores the member's name.
        self.name = name 
        
        # Stores the member's phone number.
        self.phone_number = phone_number 
        
        # Automatically records the date when the member joins the group.
        self.join_date = date.today() 
 
    # Returns the member's name when the object is displayed.
    def __repr__(self) -> str: 
        return self.name 
 
 
# Represents the contribution made by one member during a cycle.
class Contribution: 
    def __init__(self, member: Member, amount_expected: float): 
        # Stores the member making the contribution.
        self.member = member 
        
        # Stores the amount that the member is expected to pay.
        self.amount_expected = amount_expected 
        
        # Initially, no money has been paid.
        self.amount_paid = 0 
        
        # Initially, there is no payment date.
        self.date_paid = None 
        
        # A new contribution starts with a Pending status.
        self.status = PaymentStatus.PENDING 
 
    # Records a payment and updates the payment status.
    def log_payment(self, amount: float, due_date: date, payment_date: date = None) -> None: 
        """Record a payment and update this contribution's status.""" 
        
        # Uses the provided payment date or today's date if no date is provided.
        effective_date = payment_date or date.today() 
        
        # Stores the amount that was paid.
        self.amount_paid = amount 
        
        # Stores the date on which the payment was made.
        self.date_paid = effective_date 
 
        # Checks if the member paid less than the expected amount.
        if amount < self.amount_expected: 
            # The contribution is marked as Partial.
            self.status = PaymentStatus.PARTIAL 
        
        # Checks if the full amount was paid after the due date.
        elif effective_date > due_date: 
            # The contribution is marked as Late.
            self.status = PaymentStatus.LATE 
        
        # If the full amount was paid on time.
        else: 
            self.status = PaymentStatus.PAID 
 
    # Checks whether a pending contribution has passed its due date.
    def mark_missed_if_overdue(self, due_date: date, today: date = None) -> None: 
        """ 
        If the due date has passed and nothing has been paid at all, 
        mark this contribution as MISSED instead of leaving it PENDING 
        forever. Call this when displaying/refreshing a cycle's status. 
        """ 
        
        # Uses the provided date or today's date if no date is provided.
        today = today or date.today() 
        
        # If the contribution is still pending and the due date has passed,
        # it is marked as missed.
        if self.status == PaymentStatus.PENDING and today > due_date: 
            self.status = PaymentStatus.MISSED 
 
    # Defines how a contribution is displayed.
    def __repr__(self) -> str: 
        return f"  - {self.member.name}: {self.status.value} ({self.amount_paid} FCFA)" 
 
 
# Represents one complete cycle of the Njangi group.
class Cycle: 
    """One full round of a Njangi group: one recipient, all contributions.""" 
 
    def __init__(self, cycle_number: int, members: list, contribution_amount: float, 
                 recipient: Member, due_date: date): 
        
        # Stores the cycle number.
        self.cycle_number = cycle_number 
        
        # Stores the member who receives the Njangi payout for this cycle.
        self.recipient = recipient 
        
        # Stores the deadline for contributions.
        self.due_date = due_date 
        
        # Creates a contribution record for every member.
        self.contributions = { 
            m.member_id: Contribution(m, contribution_amount) for m in members 
        } 
        
        # Indicates whether the cycle has been closed.
        self.closed = False 
 
    # Records a member's payment for the current cycle.
    def record_payment(self, member_id: int, amount: float, payment_date: date = None) -> None: 
        
        # Checks whether the member belongs to this cycle.
        if member_id not in self.contributions: 
            raise ValueError("Member not part of this cycle") 
        
        # Records the payment for the specified member.
        self.contributions[member_id].log_payment(amount, self.due_date, payment_date) 
 
    # Updates pending contributions that have passed their due date.
    def refresh_overdue_statuses(self, today: date = None) -> None: 
        """Update any still-PENDING contributions to MISSED if the due date has passed.""" 
        
        # Goes through every contribution in the cycle.
        for contribution in self.contributions.values(): 
            
            # Checks whether the contribution should be marked as missed.
            contribution.mark_missed_if_overdue(self.due_date, today) 
 
    # Calculates the total amount collected in the cycle.
    def total_pool(self) -> float: 
        return sum(c.amount_paid for c in self.contributions.values()) 
 
    # Returns the members who have not paid the full expected amount.
    def missing_members(self) -> list: 
        """Members who have not yet paid in full (Pending, Partial, or Missed).""" 
        
        return [ 
            c.member.name for c in self.contributions.values() 
            if c.status in (PaymentStatus.PENDING, PaymentStatus.PARTIAL, PaymentStatus.MISSED) 
        ] 
 
    # Checks whether every member has fully paid.
    def is_fully_paid(self) -> bool: 
        return all(c.status == PaymentStatus.PAID for c in self.contributions.values()) 
 
    # Creates a text report showing the payment status of the cycle.
    def status_report(self) -> str: 
        
        # Creates the first line containing the cycle and recipient information.
        lines = [f"--- Cycle {self.cycle_number} (Recipient: {self.recipient.name}) ---"] 
        
        # Adds each member's contribution information to the report.
        for c in self.contributions.values(): 
            lines.append(f"{c}") 
        
        # Adds the total amount collected to the report.
        lines.append(f"Total pool so far: {self.total_pool()} FCFA") 
        
        # Combines all lines into one text report.
        return "\n".join(lines) 
 
    # Defines how the cycle is displayed.
    def __repr__(self) -> str: 
        
        # Determines whether the cycle is open or closed.
        status = "Closed" if self.closed else "Open" 
        
        return f"Cycle {self.cycle_number} (Recipient: {self.recipient.name}, {status})" 
 
 
# Represents the entire Njangi savings group.
class NjangiGroup: 
    """A Njangi (tontine) savings group: members, rotation queue, and cycle history.""" 
 
    def __init__(self, group_name: str, contribution_amount: float, frequency_days: int = 30): 
        
        # Stores the name of the Njangi group.
        self.group_name = group_name 
        
        # Stores the amount each member should contribute.
        self.contribution_amount = contribution_amount 
        
        # Stores the number of days between cycles.
        self.frequency_days = frequency_days 
        
        # Stores all members of the group.
        self.members = [] 
        
        # Stores members in the order in which they will receive the payout.
        self.rotation_queue = [] 
        
        # Stores all cycles belonging to the group.
        self.cycles = [] 
        
        # Stores the group's loans.
        self.loans = []          # populated by loans.py functions (Task 6) 
        
        # Keeps track of the next member ID.
        self._next_member_id = 1 
        
        # Keeps track of the next loan ID.
        self._next_loan_id = 1 
 
    # Adds a new member to the Njangi group.
    def add_member(self, name: str, phone_number: str) -> Member: 
        
        # Creates a new member using the next available ID.
        m = Member(self._next_member_id, name, phone_number) 
        
        # Adds the member to the group's member list.
        self.members.append(m) 
        
        # Adds the member to the rotation queue.
        self.rotation_queue.append(m) 
        
        # Increases the ID for the next member.
        self._next_member_id += 1 
        
        # Returns the newly created member.
        return m 
 
    # Starts a new Njangi cycle.
    def start_new_cycle(self) -> Cycle: 
        
        # Makes sure there is at least one member available.
        if not self.rotation_queue: 
            raise ValueError("No members in rotation queue") 
        
        # Takes the first member in the queue as the recipient.
        recipient = self.rotation_queue.pop(0) 
        
        # Places the recipient at the end of the queue for future cycles.
        self.rotation_queue.append(recipient) 
 
        # Determines the number of the new cycle.
        cycle_number = len(self.cycles) + 1 
        
        # Calculates the due date based on the group's frequency.
        due_date = date.today() + timedelta(days=self.frequency_days) 
 
        # Creates the new cycle.
        c = Cycle(cycle_number, self.members, self.contribution_amount, recipient, due_date) 
        
        # Adds the cycle to the group's cycle history.
        self.cycles.append(c) 
        
        # Returns the newly created cycle.
        return c 
 
    # Returns the current cycle, if one exists.
    def current_cycle(self) -> Cycle | None: 
        return self.cycles[-1] if self.cycles else None 
 
    # Returns the next member who will receive the Njangi payout.
    def next_recipient(self) -> Member | None: 
        return self.rotation_queue[0] if self.rotation_queue else None 
 
    # Generates a summary of the Njangi group.
    def group_summary(self) -> str: 
        
        # Creates the main information displayed in the group summary.
        lines = [ 
            f"Group: {self.group_name}", 
            f"Members: {len(self.members)}", 
            f"Contribution per member: {self.contribution_amount} FCFA", 
            f"Cycles completed: {sum(1 for c in self.cycles if c.closed)}", 
            f"Next recipient in queue: {self.next_recipient().name if self.next_recipient() else 'None'}", 
        ] 
        
        # Combines all summary lines into one string.
        return "\n".join(lines)