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


def calculate_dividends(members_data, total_dividend_pool, min_reliability=70):
    """
    Distributes the dividend pool proportionally among eligible members.
    Eligible: status == 'Paid' and reliability >= min_reliability.
    """
    eligible = [
        m for m in members_data
        if m.get("status") == "Paid" and m.get("reliability", 0) >= min_reliability
    ]

    if not eligible:
        return {
            "total_pool": total_dividend_pool,
            "distributed": 0.0,
            "retained_pool": total_dividend_pool,
            "payouts": []
        }

    total_paid = sum(m.get("paid", 0) for m in eligible)
    if total_paid == 0:
        return {
            "total_pool": total_dividend_pool,
            "distributed": 0.0,
            "retained_pool": total_dividend_pool,
            "payouts": []
        }

    payouts = []
    total_distributed = 0.0

    for m in eligible:
        ratio = m.get("paid", 0) / total_paid
        share = round(ratio * total_dividend_pool, 2)
        total_distributed += share
        payouts.append({
            "member_id": m.get("member_id"),
            "name": m.get("name"),
            "paid": m.get("paid"),
            "reliability": m.get("reliability"),
            "dividend_amount": share
        })

    return {
        "total_pool": total_dividend_pool,
        "distributed": total_distributed,
        "retained_pool": round(total_dividend_pool - total_distributed, 2),
        "payouts": payouts
    }