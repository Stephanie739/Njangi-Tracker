from flask import Flask, request, jsonify
#Flask create the web app
#request recieve data from the frontend
#jsonify send JSON response to the frontend
from database import add_contribution
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
# This runs the Flask server when we execute:
if __name__ == "__main__":
    app.run(debug=True)