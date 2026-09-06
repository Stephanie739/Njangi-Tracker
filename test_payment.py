import requests
url = "http://127.0.0.1:5000/payments"
payment_data = {
    "member_id": 1,
    "cycle_id": 1,
    "amount": 10000.0
}
response = requests.post(url, json=payment_data)
print("Status code:", response.status_code)
print("Response:", response.json())