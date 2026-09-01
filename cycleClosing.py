

from models import Cycle, NjangiGroup


def close_cycle(cycle: Cycle) -> bool:
    """
    Close a cycle if every member has paid their contribution in full.
    Returns True if the cycle was closed, False if it's not ready yet
    (someone is still Pending, Partial, Late, or Missed).
    """
    if cycle.is_fully_paid():
        cycle.closed = True
        return True
    return False


def close_and_advance(group: NjangiGroup) -> dict:
    """
    Closes the group's current cycle (if ready) and immediately starts
    the next one, so the group can keep running without a separate
    manual step. Returns a small report dict describing what happened.

    Raises ValueError if the current cycle isn't fully paid yet.
    """
    cycle = group.current_cycle()
    if cycle is None:
        raise ValueError("Group has no active cycle to close")

    if not cycle.is_fully_paid():
        missing = cycle.missing_members()
        raise ValueError(f"Cannot close cycle {cycle.cycle_number}: still owed by {missing}")

    close_cycle(cycle)
    next_cycle = group.start_new_cycle()

    return {
        "closed_cycle": cycle,
        "recipient": cycle.recipient,
        "next_cycle": next_cycle,
    }