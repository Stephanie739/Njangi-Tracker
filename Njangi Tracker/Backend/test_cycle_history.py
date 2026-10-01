
# Import the requests library
import requests


# API endpoint for cycle 2
url = "http://127.0.0.1:5000/cycles/2"


# Send a GET request to the server
response = requests.get(url)


# Display the status code and returned data
print("Status code:", response.status_code)
print("Response:")
print(response.json())
```
