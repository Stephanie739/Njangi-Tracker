def update_reliability_score(current_score, payment_status, days_late=0):
    """
    Updates reliability score (0-100) based on payment behavior.
    """
    score = current_score

    if payment_status == "Paid" and days_late == 0:
        score += 5  # Bonus for prompt, full payment
    elif payment_status == "Paid" and days_late > 0:
        score -= min(15, days_late * 3)  # Mild penalty for late full payment
    elif payment_status == "Partial":
        score -= 15  # Incomplete payment penalty
    elif payment_status == "Pending" and days_late > 0:
        score -= 25  # Severe penalty for default/overdue

    return max(0, min(100, score))


def calculate_collateral_required(expected_amount, reliability_score, threshold=75, collateral_rate=0.20):
    """
    Determines collateral required in escrow.
    If reliability is below threshold (e.g., 75%), lock 20% collateral.
    """
    if reliability_score < threshold:
        return round(expected_amount * collateral_rate, 2)
    return 0.0


def apply_default_penalty(member, penalty_amount=2000.0):
    """
    Deducts penalties from locked collateral or flags penalty balance.
    """
    collateral = member.get("collateral_locked", 0.0)

    if collateral >= penalty_amount:
        member["collateral_locked"] -= penalty_amount
        deducted = penalty_amount
    else:
        deducted = collateral
        member["collateral_locked"] = 0.0
        member["outstanding_penalty"] = member.get("outstanding_penalty", 0.0) + (penalty_amount - deducted)

    member["reliability"] = update_reliability_score(member.get("reliability", 100), "Pending", days_late=7)

    return {
        "member_id": member["member_id"],
        "name": member["name"],
        "penalty_deducted": deducted,
        "remaining_collateral": member["collateral_locked"],
        "new_reliability": member["reliability"]
    }