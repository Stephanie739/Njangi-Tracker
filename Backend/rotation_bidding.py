def swap_member_positions(members_list, member_id_1, member_id_2):
    """
    Swaps the rotation positions between two consenting members.
    """
    m1 = next((m for m in members_list if m["member_id"] == member_id_1), None)
    m2 = next((m for m in members_list if m["member_id"] == member_id_2), None)

    if not m1 or not m2:
        return False, "One or both members not found."

    # Swap their assigned positions
    m1["position"], m2["position"] = m2.get("position"), m1.get("position")
    
    # Keep the members list sorted by rotation position
    members_list.sort(key=lambda m: m.get("position", 999))

    return True, f"Positions successfully swapped between {m1['name']} and {m2['name']}."


def resolve_rotation_auction(members_list, bids, base_pot_amount):
    """
    Evaluates bids for the current round.
    Highest bidder wins the pot early, minus their bid discount.
    The bid discount fee feeds into the cycle's dividend pool.
    
    bids: list of dicts -> [{"member_id": 2, "bid_amount": 2500.0}, ...]
    """
    if not bids:
        # Fallback to whoever is currently in Position #1
        current_winner = min(members_list, key=lambda m: m.get("position", 999))
        return {
            "winner_id": current_winner["member_id"],
            "winner_name": current_winner["name"],
            "winning_bid": 0.0,
            "net_payout": base_pot_amount,
            "dividend_pool_contribution": 0.0
        }

    # Sort bids descending
    valid_bids = [b for b in bids if b.get("bid_amount", 0) > 0]
    if not valid_bids:
        return False, "No valid bids submitted."

    highest_bid = max(valid_bids, key=lambda b: b["bid_amount"])
    winner = next((m for m in members_list if m["member_id"] == highest_bid["member_id"]), None)

    if not winner:
        return False, "Winning member not found."

    winning_discount = float(highest_bid["bid_amount"])
    net_payout = max(0.0, base_pot_amount - winning_discount)

    # Shift winner to current round position (#1)
    old_position = winner.get("position")
    for m in members_list:
        if m.get("position") < old_position:
            m["position"] += 1
    winner["position"] = 1
    members_list.sort(key=lambda m: m.get("position", 999))

    return True, {
        "winner_id": winner["member_id"],
        "winner_name": winner["name"],
        "winning_bid": winning_discount,
        "net_payout": net_payout,
        "dividend_pool_contribution": winning_discount
    }