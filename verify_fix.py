import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(method, path, data=None):
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        
        print(f"{method} {path}: Status {response.status_code}")
        if response.status_code == 200:
            return True, response.json()
        else:
            print(f"Error: {response.text}")
            return False, response.text
    except Exception as e:
        print(f"Failed to connect to {path}: {e}")
        return False, str(e)

print("Verifying API fixes...")

# 1. Check /security/bot-activity (was 404)
success, data = check_endpoint("GET", "/security/bot-activity")
if success:
    print("[OK] /security/bot-activity is working")
else:
    print("[FAIL] /security/bot-activity failed")

# 2. Check /services/bot-blocking (was 404)
success, data = check_endpoint("GET", "/services/bot-blocking")
if success:
    print("[OK] /services/bot-blocking is working")
else:
    print("[FAIL] /services/bot-blocking failed")

# 3. Check /billing/api-keys (was 500 due to DB schema)
# This one triggered the SQL error "no such column: services.watermarking_enabled"
success, data = check_endpoint("GET", "/billing/api-keys")
if success:
    print("[OK] /billing/api-keys is working (DB schema fixed)")
else:
    print("[FAIL] /billing/api-keys failed (DB schema issue might persist)")

