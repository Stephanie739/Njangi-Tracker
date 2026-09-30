from flask import Flask, render_template, jsonify, request
from cycleClosing import calculate_dividends
from reliability_collateral import (
    update_reliability_score,
    calculate_collateral_required,
    apply_default_penalty
)
from rotation_bidding import swap_member_positions, resolve_rotation_auction

app = Flask(__name__)

# In-memory member store with rotation positions
members = [
    {
        "member_id": 1,
        "name": "Alice Dupont",
        "phone_number": "+237670000001",
        "position": 1,
        "expected": 10000.0,
        "paid": 0.0,
        "balance": 10000.0,
        "status": "Pending",
        "reliability": 100,
        "collateral_locked": 0.0
    },
    {
        "member_id": 2,
        "name": "Bob Ndongo",
        "phone_number": "+237670000002",
        "position": 2,
        "expected": 10000.0,
        "paid": 0.0,
        "balance": 10000.0,
        "status": "Pending",
        "reliability": 100,
        "collateral_locked": 0.0
    },
    {
        "member_id": 3,
        "name": "Charlie Tabi",
        "phone_number": "+237670000003",
        "position": 3,
        "expected": 10000.0,
        "paid": 0.0,
        "balance": 10000.0,
        "status": "Pending",
        "reliability": 100,
        "collateral_locked": 0.0
    }
]

@app.route('/')
@app.route('/members')
def index():
    return render_template('members.html')

@app.route('/api/members', methods=['GET'])
def get_members():
    return jsonify({
        "status": "success",
        "members": sorted(members, key=lambda m: m.get("position", 999))
    })

@app.route('/api/contributions', methods=['POST'])
def record_contribution():
    data = request.get_json() or {}
    member_id = data.get('member_id')
    amount = float(data.get('amount', 0))

    target = next((m for m in members if m['member_id'] == member_id), None)
    if not target:
        return jsonify({'error': 'Member not found'}), 404

    target['paid'] += amount
    target['balance'] = max(0.0, target['expected'] - target['paid'])

    # Proportional reliability based on payment completion
    if target['expected'] > 0:
        ratio = target['paid'] / target['expected']
        target['reliability'] = max(0, min(100, round(ratio * 100)))
    else:
        target['reliability'] = 100

    # Status assignment
    if target['balance'] == 0:
        target['status'] = 'Paid'
    elif target['paid'] > 0:
        target['status'] = 'Partial'
    else:
        target['status'] = 'Pending'

    return jsonify({'status': 'success', 'member': target})

@app.route('/api/cycle/close', methods=['POST'])
def close_cycle():
    data = request.get_json() or {}
    pool_amount = float(data.get('pool_amount', 5000.0))
    min_reliability = int(data.get('min_reliability', 70))

    result = calculate_dividends(members, total_dividend_pool=pool_amount, min_reliability=min_reliability)
    return jsonify({
        "status": "success",
        "summary": result
    })

@app.route('/api/members/<int:member_id>/collateral', methods=['GET'])
def get_member_collateral(member_id):
    target = next((m for m in members if m['member_id'] == member_id), None)
    if not target:
        return jsonify({'error': 'Member not found'}), 404

    collateral_due = calculate_collateral_required(
        expected_amount=target.get('expected', 10000.0),
        reliability_score=target.get('reliability', 100)
    )

    return jsonify({
        'status': 'success',
        'member_id': member_id,
        'name': target['name'],
        'reliability': target.get('reliability', 100),
        'collateral_required': collateral_due,
        'collateral_locked': target.get('collateral_locked', 0.0)
    })

@app.route('/api/members/<int:member_id>/penalize', methods=['POST'])
def penalize_member(member_id):
    target = next((m for m in members if m['member_id'] == member_id), None)
    if not target:
        return jsonify({'error': 'Member not found'}), 404

    data = request.get_json() or {}
    penalty_fee = float(data.get('penalty_amount', 2000.0))

    summary = apply_default_penalty(target, penalty_amount=penalty_fee)
    return jsonify({'status': 'success', 'summary': summary})

@app.route('/api/rotation/swap', methods=['POST'])
def swap_slots():
    data = request.get_json() or {}
    m1_id = data.get('member_id_1')
    m2_id = data.get('member_id_2')

    if not m1_id or not m2_id:
        return jsonify({'error': 'Both member_id_1 and member_id_2 are required'}), 400

    success, message = swap_member_positions(members, int(m1_id), int(m2_id))
    if not success:
        return jsonify({'error': message}), 400

    return jsonify({
        'status': 'success',
        'message': message,
        'members': members
    })

@app.route('/api/rotation/auction', methods=['POST'])
def run_auction():
    data = request.get_json() or {}
    bids = data.get('bids', [])
    base_pot = float(data.get('base_pot', 30000.0))

    success, result = resolve_rotation_auction(members, bids, base_pot)
    if not success:
        return jsonify({'error': result}), 400

    return jsonify({
        'status': 'success',
        'auction_result': result,
        'members': members
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)