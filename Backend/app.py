from flask import Flask, render_template, request, jsonify
from models import NjangiGroup, Contribution
from persistance import load_group, save_group, list_group_names

app = Flask(__name__)
DEFAULT_GROUP_NAME = "Njangi Group"


def get_or_create_group(name: str = DEFAULT_GROUP_NAME) -> NjangiGroup:
    """Helper to ensure group exists in SQLite."""
    group = load_group(name)
    if group is None:
        group = NjangiGroup(group_name=name, contribution_amount=10000.0, frequency_days=30)
        save_group(group)
    return group

# Page Route
@app.route('/members')
def members_page():
    return render_template('members.html')


# Get Members API
@app.route('/api/members', methods=['GET'])
def api_get_members():
    group_name = request.args.get('group', DEFAULT_GROUP_NAME)
    group = get_or_create_group(group_name)
    cycle = group.current_cycle()

    # Map rotation queue positions (1-indexed)
    queue_map = {m.member_id: idx + 1 for idx, m in enumerate(group.rotation_queue)}

    result = []
    for m in group.members:
        paid = 0.0
        expected = group.contribution_amount
        status_str = "Pending"

        if cycle and m.member_id in cycle.contributions:
            contrib = cycle.contributions[m.member_id]
            paid = contrib.amount_paid
            expected = contrib.amount_expected
            status_str = contrib.status.value

        result.append({
            "id": str(m.member_id),
            "name": m.name,
            "phone": m.phone_number,
            "expected": expected,
            "paid": paid,
            "rotationPosition": queue_map.get(m.member_id, len(result) + 1),
            "enrolled": m.member_id in queue_map,
            "status": status_str
        })

    return jsonify(result), 200


#
# Add Member Route
@app.route('/api/members', methods=['POST'])
def api_add_member():
    data = request.get_json() or {}

    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    group_name = data.get('group', DEFAULT_GROUP_NAME)

    # Acceptance Criteria validation
    if not name:
        return jsonify({'error': 'Member name is required.'}), 400
    if not phone:
        return jsonify({'error': 'Phone number is required.'}), 400

    group = get_or_create_group(group_name)

    # handles member list and rotation queue
    new_member = group.add_member(name=name, phone_number=phone)

    # If a cycle is currently open, enroll the new member into it
    current_cyc = group.current_cycle()
    if current_cyc and not current_cyc.closed:
        current_cyc.contributions[new_member.member_id] = Contribution(
            new_member, group.contribution_amount
        )

    #database persistence
    save_group(group)

    return jsonify({
        "id": str(new_member.member_id),
        "name": new_member.name,
        "phone": new_member.phone_number,
        "expected": group.contribution_amount,
        "paid": 0,
        "rotationPosition": len(group.rotation_queue),
        "enrolled": True
    }), 201


if __name__ == '__main__':
    app.run(debug=True, port=5000)