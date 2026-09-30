import requests
url = "http://127.0.0.1:5000/cycles/2"
response = requests.get(url)
print("Status code:", response.status_code)
print("Response:")
print(response.json())