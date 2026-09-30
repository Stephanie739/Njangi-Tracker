from flask import Flask, render_template, request, jsonify 
from models import NjangiGroup, Contribution 
from persistance import load_group, save_group, list_group_names 
 
# Create the Flask application
app = Flask(__name__) 

# Default name used when no group name is provided
DEFAULT_GROUP_NAME = "Njangi Group" 
 
 
def get_or_create_group(name: str = DEFAULT_GROUP_NAME) -> NjangiGroup: 
    """Helper to ensure group exists in SQLite.""" 
    
    # Try to load the group from the database
    group = load_group(name) 
    
    # If the group does not exist, create a new group
    if group is None: 
        
        # Create a new Njangi group with the default contribution amount
        # and a 30-day contribution cycle
        group = NjangiGroup(group_name=name, contribution_amount=10000.0, frequency_days=30) 
        
        # Save the newly created group to the database
        save_group(group) 
    
    # Return the existing or newly created group
    return group 
 
# Page Route 
# Displays the members page
@app.route('/members') 
def members_page(): 
    return render_template('members.html') 
 
 
# Get Members API 
# Handles requests for retrieving all members in a group
@app.route('/api/members', methods=['GET']) 
def api_get_members(): 
    
    # Get the group name from the request.
    # If no group is provided, use the default group name.
    group_name = request.args.get('group', DEFAULT_GROUP_NAME) 
    
    # Load the group or create it if it does not exist
    group = get_or_create_group(group_name) 
    
    # Get the current contribution cycle
    cycle = group.current_cycle() 
 
    # Map rotation queue positions (1-indexed)
    # Each member ID is mapped to its position in the rotation queue
    queue_map = {m.member_id: idx + 1 for idx, m in enumerate(group.rotation_queue)} 
 
    # Create an empty list to store the member information
    result = [] 
    
    # Go through every member in the group
    for m in group.members: 
        
        # Default values for members who have not made a payment
        paid = 0.0 
        expected = group.contribution_amount 
        status_str = "Pending" 
 
        # Check if there is a current cycle and the member has a contribution
        if cycle and m.member_id in cycle.contributions: 
            contrib = cycle.contributions[m.member_id] 
            
            # Get the amount paid by the member
            paid = contrib.amount_paid 
            
            # Get the expected contribution amount
            expected = contrib.amount_expected 
            
            # Get the member's payment status
            status_str = contrib.status.value 
 
        # Add the member's information to the result list
        result.append({ 
            "id": str(m.member_id), 
            "name": m.name, 
            "phone": m.phone_number, 
            "expected": expected, 
            "paid": paid, 
            
            # Get the member's position in the rotation queue
            "rotationPosition": queue_map.get(m.member_id, len(result) + 1), 
            
            # Check whether the member is enrolled in the rotation queue
            "enrolled": m.member_id in queue_map, 
            
            # Store the member's current payment status
            "status": status_str 
        }) 
 
    # Return the member information as JSON with HTTP status 200
    return jsonify(result), 200 
 
 
# 
# Add Member Route
# Handles requests for adding a new member to the group
@app.route('/api/members', methods=['POST']) 
def api_add_member(): 
    
    # Get the JSON data sent by the client
    # If no data is received, use an empty dictionary
    data = request.get_json() or {} 
 
    # Get and clean the member's name
    name = data.get('name', '').strip() 
    
    # Get and clean the member's phone number
    phone = data.get('phone', '').strip() 
    
    # Get the group name or use the default group name
    group_name = data.get('group', DEFAULT_GROUP_NAME) 
 
    # Acceptance Criteria validation
    # Check that the member's name was provided
    if not name: 
        return jsonify({'error': 'Member name is required.'}), 400 
    
    # Check that the member's phone number was provided
    if not phone: 
        return jsonify({'error': 'Phone number is required.'}), 400 
 
    # Load the selected group or create it if it does not exist
    group = get_or_create_group(group_name) 
 
    # handles member list and rotation queue
    # Add the new member to the group
    new_member = group.add_member(name=name, phone_number=phone) 
 
    # If a cycle is currently open, enroll the new member into it
    current_cyc = group.current_cycle() 
    
    # Check that a cycle exists and is not closed
    if current_cyc and not current_cyc.closed: 
        
        # Create a contribution record for the new member
        current_cyc.contributions[new_member.member_id] = Contribution( 
            new_member, group.contribution_amount 
        ) 
 
    #database persistence
    # Save all changes made to the group in the database
    save_group(group) 
 
    # Return the newly created member's information as JSON
    # HTTP status 201 means the resource was successfully created
    return jsonify({ 
        "id": str(new_member.member_id), 
        "name": new_member.name, 
        "phone": new_member.phone_number, 
        "expected": group.contribution_amount, 
        "paid": 0, 
        
        # Position of the new member in the rotation queue
        "rotationPosition": len(group.rotation_queue), 
        
        # The new member is enrolled by default
        "enrolled": True 
    }), 201 
 
 
# Run the Flask development server when this file is executed directly
if __name__ == '__main__': 
    app.run(debug=True, port=5000)