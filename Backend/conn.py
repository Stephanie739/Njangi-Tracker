from flask import Flask, request, jsonify
#Flask create the web app
#request recieve data from the frontend
#jsonify send JSON response to the frontend
from database import add_contribution, get_cycles_by_group
#create the Flask application
app = Flask(__name__)
# The route then sends this information to
# Person 1's add_contribution() function.
@app.route("/payments", methods=["POST"])
def log_payment():
    # Get the JSON data sent by the frontend.
    data = request.get_json()
    # Get the member ID from the request.
    member_id = data.get("member_id")
    # Get the cycle ID from the request.
    cycle_id = data.get("cycle_id")
    # Get the amount paid by the member.
    amount = data.get("amount")
    # add_contribution() saves the payment in the database
    # and handles the payment status automatically.
    contribution_id = add_contribution(
        member_id,
        cycle_id,
        amount
    )
    # Check whether the payment was successfully created.
    if contribution_id is None:
        return jsonify({
            "message": "Payment could not be recorded"
        }), 400

    # Send a successful response to the frontend.
    return jsonify({
        "message": "Payment logged successfully",
        "contribution_id": contribution_id
    }), 201
#This route allows the frontend retrieves the history cycle belonging to a specific Njangi group
@app.route("/cycles/<int:group_id>", methods=["GET"])
def cycle_history(group_id):
    #Get the cycle history for the specified group ID from the database
    cycles = get_cycles_by_group(group_id)
    cycle_history_data = []
    for cycle in cycles:
        cycle_history_data.append({
            "cycle_id": cycle[0],
            "member_id": cycle[1],
            "cycle_number": cycle[2],
            "status": cycle[3]
        })
        #Send the cycle history data as a JSON response to the frontend
        return jsonify({
            "cycles": cycle_history_data,
            "group_id" : group_id
        }),200
if __name__ == "__main__":
    app.run(debug=True)
    