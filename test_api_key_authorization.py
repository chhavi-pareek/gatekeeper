"""
Test script to reproduce and verify the API key authorization vulnerability.

This script tests whether an API key for Service A can be used to access Service B.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_cross_service_api_key_usage():
    """
    Test if an API key from one service can be used to access another service.
    
    Steps:
    1. Register two services (Service A and Service B)
    2. Create an API key for Service A
    3. Try to use Service A's API key to access Service B
    4. Expected: Should be rejected (403 Forbidden)
    5. Actual (before fix): Request succeeds (vulnerability)
    """
    
    print("=" * 80)
    print("API Key Authorization Vulnerability Test")
    print("=" * 80)
    
    # Step 1: Register Service A
    print("\n[1] Registering Service A...")
    service_a_response = requests.post(
        f"{BASE_URL}/register-api",
        json={
            "name": "Test Service A",
            "target_url": "https://jsonplaceholder.typicode.com"
        }
    )
    
    if service_a_response.status_code != 200:
        print(f"❌ Failed to register Service A: {service_a_response.text}")
        return
    
    service_a_data = service_a_response.json()
    service_a_id = service_a_data["service_id"]
    user_api_key = service_a_data.get("api_key")  # Only returned on first user creation
    
    print(f"✅ Service A registered: ID={service_a_id}")
    if user_api_key:
        print(f"   User API Key: {user_api_key}")
    
    # Step 2: Register Service B
    print("\n[2] Registering Service B...")
    service_b_response = requests.post(
        f"{BASE_URL}/register-api",
        json={
            "name": "Test Service B",
            "target_url": "https://httpbin.org"
        },
        headers={"X-API-Key": user_api_key} if user_api_key else {}
    )
    
    if service_b_response.status_code != 200:
        print(f"❌ Failed to register Service B: {service_b_response.text}")
        return
    
    service_b_data = service_b_response.json()
    service_b_id = service_b_data["service_id"]
    
    print(f"✅ Service B registered: ID={service_b_id}")
    
    # Step 3: Create an API key for Service A
    print("\n[3] Creating API key for Service A...")
    api_key_response = requests.post(
        f"{BASE_URL}/services/{service_a_id}/keys",
        headers={"X-API-Key": user_api_key} if user_api_key else {}
    )
    
    if api_key_response.status_code != 200:
        print(f"❌ Failed to create API key for Service A: {api_key_response.text}")
        return
    
    api_key_data = api_key_response.json()
    service_a_api_key = api_key_data["api_key"]
    
    print(f"✅ API key created for Service A: {service_a_api_key[:20]}...")
    
    # Step 4: Try to use Service A's API key to access Service B (VULNERABILITY TEST)
    print("\n[4] Testing: Using Service A's API key to access Service B...")
    print(f"   Request: GET {BASE_URL}/proxy/{service_b_id}/get")
    print(f"   API Key: {service_a_api_key[:20]}... (belongs to Service A)")
    print(f"   Target: Service B (ID={service_b_id})")
    
    unauthorized_request = requests.get(
        f"{BASE_URL}/proxy/{service_b_id}/get",
        headers={
            "X-API-Key": service_a_api_key
        }
    )
    
    print(f"\n   Response Status: {unauthorized_request.status_code}")
    
    # Step 5: Verify that the API key DOES work for its own service
    print("\n[5] Verification: Using Service A's API key to access Service A...")
    authorized_request = requests.get(
        f"{BASE_URL}/proxy/{service_a_id}/posts/1",
        headers={"X-API-Key": service_a_api_key}
    )
    
    print(f"   Response Status: {authorized_request.status_code}")
    
    # Step 6: Analyze results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    # Check cross-service access (should be blocked)
    cross_service_blocked = False
    if unauthorized_request.status_code == 200:
        print("❌ VULNERABILITY CONFIRMED!")
        print("   Service A's API key was able to access Service B")
        print("   This is a critical security flaw - API keys should be service-specific")
        print(f"\n   Response preview: {unauthorized_request.text[:200]}...")
    elif unauthorized_request.status_code == 403:
        print("✅ Cross-Service Access Blocked")
        print("   Service A's API key was correctly rejected when accessing Service B")
        print(f"   Response: {unauthorized_request.text}")
        cross_service_blocked = True
    elif unauthorized_request.status_code == 401:
        print("✅ Cross-Service Access Blocked")
        print("   Service A's API key was correctly rejected (401 Unauthorized)")
        print(f"   Response: {unauthorized_request.text}")
        cross_service_blocked = True
    else:
        print(f"⚠️  UNEXPECTED RESPONSE: {unauthorized_request.status_code}")
        print(f"   Response: {unauthorized_request.text}")
    
    # Check legitimate access (should work)
    print()
    if authorized_request.status_code == 200:
        print("✅ Legitimate Access Works")
        print("   API key works correctly for its own service")
    else:
        print(f"❌ Legitimate Access Failed")
        print(f"   API key failed for its own service: {authorized_request.text}")
    
    # Final verdict
    print("\n" + "=" * 80)
    if cross_service_blocked and authorized_request.status_code == 200:
        print("🎉 ALL TESTS PASSED - VULNERABILITY FIXED!")
        print("=" * 80)
        return True
    else:
        print("❌ TESTS FAILED")
        print("=" * 80)
        return False


if __name__ == "__main__":
    try:
        test_cross_service_api_key_usage()
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Cannot connect to the server.")
        print("   Make sure the FastAPI server is running on http://localhost:8000")
        print("   Run: python main.py")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
