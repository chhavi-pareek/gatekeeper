"""
Automated API Testing Script for GaaS Gateway

This script tests all backend API endpoints including:
- Service registration
- API key management
- Proxy requests
- Rate limiting
- Bot detection
- Billing
- Usage statistics

Run with: python test_api.py
"""

import requests
import time
import json
from typing import Optional, Dict, Any
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_KEY: Optional[str] = None
SERVICE_ID: Optional[int] = None
API_KEY_ID: Optional[int] = None

# Test results tracking
tests_passed = 0
tests_failed = 0
test_results = []


def print_test_header(test_name: str):
    """Print a formatted test header."""
    print(f"\n{'=' * 80}")
    print(f"{Fore.CYAN}{Style.BRIGHT}TEST: {test_name}{Style.RESET_ALL}")
    print(f"{'=' * 80}")


def print_success(message: str):
    """Print success message."""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print error message."""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message."""
    print(f"{Fore.YELLOW}ℹ {message}{Style.RESET_ALL}")


def record_test(test_name: str, passed: bool, details: str = ""):
    """Record test result."""
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        print_success(f"PASSED: {test_name}")
    else:
        tests_failed += 1
        print_error(f"FAILED: {test_name}")
    
    test_results.append({
        "test": test_name,
        "passed": passed,
        "details": details
    })


def test_health_check():
    """Test 1: Health Check Endpoint"""
    print_test_header("Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200 and response.json().get("status") == "healthy":
            record_test("Health Check", True, f"Response: {response.json()}")
        else:
            record_test("Health Check", False, f"Unexpected response: {response.text}")
    except Exception as e:
        record_test("Health Check", False, f"Error: {str(e)}")


def test_register_service():
    """Test 2: Register a New Service"""
    global SERVICE_ID, API_KEY
    print_test_header("Register Service")
    
    try:
        payload = {
            "name": "Test API Service",
            "target_url": "https://httpbin.org/get"
        }
        
        response = requests.post(f"{BASE_URL}/register-api", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            SERVICE_ID = data.get("service_id")
            API_KEY = data.get("api_key")
            
            # If API key is None (user already exists), create a new key
            if SERVICE_ID and not API_KEY:
                print_info("User already exists. Creating a new API key...")
                key_response = requests.post(f"{BASE_URL}/services/{SERVICE_ID}/keys")
                if key_response.status_code == 200:
                    key_data = key_response.json()
                    API_KEY = key_data.get("api_key")
                    print_success("New API key generated")
            
            if SERVICE_ID and API_KEY:
                print_info(f"Service ID: {SERVICE_ID}")
                print_info(f"API Key: {API_KEY[:20]}...")
                record_test("Register Service", True, f"Service ID: {SERVICE_ID}")
            else:
                record_test("Register Service", False, "Missing service_id or api_key in response")
        else:
            record_test("Register Service", False, f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        record_test("Register Service", False, f"Error: {str(e)}")


def test_get_api_key_first_time():
    """Test 3: Get API Key (First Time)"""
    print_test_header("Get API Key (First Time)")
    
    try:
        response = requests.get(f"{BASE_URL}/me/api-key")
        
        if response.status_code == 200:
            data = response.json()
            if "api_key" in data:
                record_test("Get API Key (First Time)", True, "API key retrieved successfully")
            else:
                record_test("Get API Key (First Time)", False, "API key not in response")
        else:
            record_test("Get API Key (First Time)", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Get API Key (First Time)", False, f"Error: {str(e)}")


def test_get_api_key_second_time():
    """Test 4: Get API Key (Second Time - Should Be Blocked)"""
    print_test_header("Get API Key (Second Time)")
    
    try:
        response = requests.get(f"{BASE_URL}/me/api-key")
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "cannot be viewed again" in data["message"]:
                record_test("Get API Key (Second Time)", True, "API key correctly blocked from re-reveal")
            else:
                record_test("Get API Key (Second Time)", False, "API key should not be revealed again")
        else:
            record_test("Get API Key (Second Time)", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Get API Key (Second Time)", False, f"Error: {str(e)}")


def test_proxy_request_valid_key():
    """Test 5: Proxy Request with Valid API Key"""
    print_test_header("Proxy Request (Valid Key)")
    
    if not API_KEY or not SERVICE_ID:
        record_test("Proxy Request (Valid Key)", False, "No API key or service ID available")
        return
    
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{BASE_URL}/proxy/{SERVICE_ID}", headers=headers)
        
        if response.status_code == 200:
            record_test("Proxy Request (Valid Key)", True, "Request proxied successfully")
        else:
            record_test("Proxy Request (Valid Key)", False, f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        record_test("Proxy Request (Valid Key)", False, f"Error: {str(e)}")


def test_proxy_request_invalid_key():
    """Test 6: Proxy Request with Invalid API Key"""
    print_test_header("Proxy Request (Invalid Key)")
    
    if not SERVICE_ID:
        record_test("Proxy Request (Invalid Key)", False, "No service ID available")
        return
    
    try:
        headers = {"X-API-Key": "invalid_key_12345"}
        response = requests.get(f"{BASE_URL}/proxy/{SERVICE_ID}", headers=headers)
        
        if response.status_code == 401:
            record_test("Proxy Request (Invalid Key)", True, "Invalid key correctly rejected")
        else:
            record_test("Proxy Request (Invalid Key)", False, f"Expected 401, got {response.status_code}")
    except Exception as e:
        record_test("Proxy Request (Invalid Key)", False, f"Error: {str(e)}")


def test_rate_limiting():
    """Test 7: Rate Limiting"""
    print_test_header("Rate Limiting")
    
    if not API_KEY or not SERVICE_ID:
        record_test("Rate Limiting", False, "No API key or service ID available")
        return
    
    try:
        headers = {"X-API-Key": API_KEY}
        success_count = 0
        rate_limited_count = 0
        
        print_info("Making 15 rapid requests...")
        
        for i in range(15):
            response = requests.get(f"{BASE_URL}/proxy/{SERVICE_ID}", headers=headers)
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited_count += 1
            
            time.sleep(0.1)  # Small delay to avoid overwhelming the server
        
        print_info(f"Successful requests: {success_count}")
        print_info(f"Rate limited requests: {rate_limited_count}")
        
        # We expect around 10 successful requests and 5 rate limited
        if success_count >= 8 and rate_limited_count >= 3:
            record_test("Rate Limiting", True, f"Success: {success_count}, Limited: {rate_limited_count}")
        else:
            record_test("Rate Limiting", False, f"Unexpected counts - Success: {success_count}, Limited: {rate_limited_count}")
    except Exception as e:
        record_test("Rate Limiting", False, f"Error: {str(e)}")


def test_create_additional_api_key():
    """Test 8: Create Additional API Key"""
    global API_KEY_ID
    print_test_header("Create Additional API Key")
    
    if not SERVICE_ID:
        record_test("Create Additional API Key", False, "No service ID available")
        return
    
    try:
        response = requests.post(f"{BASE_URL}/services/{SERVICE_ID}/keys")
        
        if response.status_code == 200:
            data = response.json()
            new_key = data.get("api_key")
            
            if new_key:
                print_info(f"New API Key: {new_key[:20]}...")
                record_test("Create Additional API Key", True, "New key created successfully")
            else:
                record_test("Create Additional API Key", False, "No API key in response")
        else:
            record_test("Create Additional API Key", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Create Additional API Key", False, f"Error: {str(e)}")


def test_list_api_keys():
    """Test 9: List All API Keys"""
    global API_KEY_ID
    print_test_header("List All API Keys")
    
    try:
        response = requests.get(f"{BASE_URL}/api-keys")
        
        if response.status_code == 200:
            data = response.json()
            services = data.get("services", [])
            
            if services:
                print_info(f"Found {len(services)} service(s)")
                
                # Get the first API key ID for later tests
                if services[0].get("api_keys"):
                    API_KEY_ID = services[0]["api_keys"][0].get("id")
                    print_info(f"API Key ID: {API_KEY_ID}")
                
                record_test("List All API Keys", True, f"Found {len(services)} services")
            else:
                record_test("List All API Keys", False, "No services found")
        else:
            record_test("List All API Keys", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("List All API Keys", False, f"Error: {str(e)}")


def test_update_rate_limit():
    """Test 10: Update Rate Limit"""
    print_test_header("Update Rate Limit")
    
    if not API_KEY_ID:
        record_test("Update Rate Limit", False, "No API key ID available")
        return
    
    try:
        payload = {
            "requests": 20,
            "window_seconds": 60
        }
        
        response = requests.put(f"{BASE_URL}/api-keys/{API_KEY_ID}/rate-limit", json=payload)
        
        if response.status_code == 200:
            record_test("Update Rate Limit", True, "Rate limit updated successfully")
        else:
            record_test("Update Rate Limit", False, f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        record_test("Update Rate Limit", False, f"Error: {str(e)}")


def test_usage_statistics():
    """Test 11: Usage Statistics"""
    print_test_header("Usage Statistics")
    
    if not API_KEY or not SERVICE_ID:
        record_test("Usage Statistics", False, "No API key or service ID available")
        return
    
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{BASE_URL}/usage/{SERVICE_ID}", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            total_requests = data.get("total_requests", 0)
            
            print_info(f"Total requests: {total_requests}")
            record_test("Usage Statistics", True, f"Total requests: {total_requests}")
        else:
            record_test("Usage Statistics", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Usage Statistics", False, f"Error: {str(e)}")


def test_billing_summary():
    """Test 12: Billing Summary"""
    print_test_header("Billing Summary")
    
    try:
        response = requests.get(f"{BASE_URL}/billing/summary")
        
        if response.status_code == 200:
            data = response.json()
            total_cost = data.get("total_cost", 0)
            
            print_info(f"Total cost: ${total_cost:.4f}")
            record_test("Billing Summary", True, f"Total cost: ${total_cost:.4f}")
        else:
            record_test("Billing Summary", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Billing Summary", False, f"Error: {str(e)}")


def test_bot_activity():
    """Test 13: Bot Activity"""
    print_test_header("Bot Activity")
    
    try:
        response = requests.get(f"{BASE_URL}/security/bot-activity")
        
        if response.status_code == 200:
            data = response.json()
            total_requests = data.get("total_requests", 0)
            bot_percentage = data.get("bot_percentage", 0)
            
            print_info(f"Total requests analyzed: {total_requests}")
            print_info(f"Bot percentage: {bot_percentage:.2f}%")
            record_test("Bot Activity", True, f"Requests: {total_requests}, Bot %: {bot_percentage:.2f}")
        else:
            record_test("Bot Activity", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Bot Activity", False, f"Error: {str(e)}")


def test_bot_blocking_config():
    """Test 14: Bot Blocking Configuration"""
    print_test_header("Bot Blocking Configuration")
    
    try:
        response = requests.get(f"{BASE_URL}/security/bot-blocking-config")
        
        if response.status_code == 200:
            data = response.json()
            services = data.get("services", [])
            
            print_info(f"Found {len(services)} service(s) with bot blocking config")
            record_test("Bot Blocking Configuration", True, f"Found {len(services)} services")
        else:
            record_test("Bot Blocking Configuration", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Bot Blocking Configuration", False, f"Error: {str(e)}")


def test_enable_bot_blocking():
    """Test 15: Enable Bot Blocking"""
    print_test_header("Enable Bot Blocking")
    
    if not SERVICE_ID:
        record_test("Enable Bot Blocking", False, "No service ID available")
        return
    
    try:
        payload = {"enabled": True}
        response = requests.put(f"{BASE_URL}/security/bot-blocking/{SERVICE_ID}", json=payload)
        
        if response.status_code == 200:
            record_test("Enable Bot Blocking", True, "Bot blocking enabled successfully")
        else:
            record_test("Enable Bot Blocking", False, f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        record_test("Enable Bot Blocking", False, f"Error: {str(e)}")


def test_bot_detection_with_blocking():
    """Test 16: Bot Detection with Blocking Enabled"""
    print_test_header("Bot Detection with Blocking")
    
    if not API_KEY or not SERVICE_ID:
        record_test("Bot Detection with Blocking", False, "No API key or service ID available")
        return
    
    try:
        # Make a request with a bot-like user agent
        headers = {
            "X-API-Key": API_KEY,
            "User-Agent": "python-requests/2.28.0"
        }
        
        response = requests.get(f"{BASE_URL}/proxy/{SERVICE_ID}", headers=headers)
        
        # Depending on bot score, it might be blocked (403) or allowed (200)
        if response.status_code in [200, 403]:
            if response.status_code == 403:
                print_info("Bot request was blocked (as expected for high bot score)")
            else:
                print_info("Bot request was allowed (bot score likely < 0.7)")
            
            record_test("Bot Detection with Blocking", True, f"Status: {response.status_code}")
        else:
            record_test("Bot Detection with Blocking", False, f"Unexpected status: {response.status_code}")
    except Exception as e:
        record_test("Bot Detection with Blocking", False, f"Error: {str(e)}")


def test_overview_endpoint():
    """Test 17: Overview Endpoint"""
    print_test_header("Overview Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/overview")
        
        if response.status_code == 200:
            data = response.json()
            total_services = data.get("total_services", 0)
            requests_today = data.get("requests_today", 0)
            
            print_info(f"Total services: {total_services}")
            print_info(f"Requests today: {requests_today}")
            record_test("Overview Endpoint", True, f"Services: {total_services}, Requests: {requests_today}")
        else:
            record_test("Overview Endpoint", False, f"Status: {response.status_code}")
    except Exception as e:
        record_test("Overview Endpoint", False, f"Error: {str(e)}")


def print_summary():
    """Print test summary."""
    print(f"\n{'=' * 80}")
    print(f"{Fore.CYAN}{Style.BRIGHT}TEST SUMMARY{Style.RESET_ALL}")
    print(f"{'=' * 80}")
    
    total_tests = tests_passed + tests_failed
    pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"{Fore.GREEN}Passed: {tests_passed}{Style.RESET_ALL}")
    print(f"{Fore.RED}Failed: {tests_failed}{Style.RESET_ALL}")
    print(f"Pass Rate: {pass_rate:.2f}%")
    
    if tests_failed > 0:
        print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
        for result in test_results:
            if not result["passed"]:
                print(f"  - {result['test']}: {result['details']}")
    
    print(f"\n{'=' * 80}\n")


def main():
    """Run all tests."""
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("=" * 80)
    print("GaaS Gateway - Automated API Testing")
    print("=" * 80)
    print(f"{Style.RESET_ALL}")
    
    print_info(f"Testing backend at: {BASE_URL}")
    print_info("Make sure the backend server is running!\n")
    
    # Run all tests in order
    test_health_check()
    test_register_service()
    test_get_api_key_first_time()
    test_get_api_key_second_time()
    test_proxy_request_valid_key()
    test_proxy_request_invalid_key()
    test_rate_limiting()
    test_create_additional_api_key()
    test_list_api_keys()
    test_update_rate_limit()
    test_usage_statistics()
    test_billing_summary()
    test_bot_activity()
    test_bot_blocking_config()
    test_enable_bot_blocking()
    test_bot_detection_with_blocking()
    test_overview_endpoint()
    
    # Print summary
    print_summary()
    
    # Exit with appropriate code
    exit(0 if tests_failed == 0 else 1)


if __name__ == "__main__":
    main()
