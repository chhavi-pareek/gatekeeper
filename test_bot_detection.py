"""
Real Bot Detection Testing Script

This script simulates real bot behavior to test the bot detection system.
It generates various types of traffic patterns that mimic actual bots.

Run with: python test_bot_detection.py
"""

import requests
import time
import random
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://127.0.0.1:8000"

# Real bot user agents (actual bots that would be detected)
REAL_BOT_USER_AGENTS = [
    # Scrapers
    "python-requests/2.28.0",
    "python-urllib3/1.26.5",
    "Scrapy/2.8.0 (+https://scrapy.org)",
    "Apache-HttpClient/4.5.13 (Java/11.0.12)",
    
    # Automation tools
    "Selenium/4.0.0 (Python)",
    "Puppeteer/19.0.0",
    "Playwright/1.30.0",
    "PhantomJS/2.1.1",
    
    # HTTP libraries
    "axios/1.3.0",
    "node-fetch/3.2.0",
    "Go-http-client/1.1",
    "okhttp/4.9.3",
    
    # Crawlers
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
    "Bingbot/2.0 (+http://www.bing.com/bingbot.htm)",
    "facebookexternalhit/1.1",
    
    # Generic bots
    "Bot",
    "Spider",
    "Crawler",
]

# Legitimate browser user agents
LEGITIMATE_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Suspicious user agents (might be bots)
SUSPICIOUS_USER_AGENTS = [
    "curl/7.68.0",
    "Wget/1.20.3",
    "HTTPie/3.2.1",
    "PostmanRuntime/7.32.3",
    "Insomnia/2023.5.8",
]


def print_header(text):
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Style.BRIGHT}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")


def print_success(text):
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_error(text):
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text):
    print(f"{Fore.YELLOW}ℹ {text}{Style.RESET_ALL}")


def print_bot(text):
    print(f"{Fore.RED}🤖 {text}{Style.RESET_ALL}")


def print_human(text):
    print(f"{Fore.GREEN}👤 {text}{Style.RESET_ALL}")


def print_suspicious(text):
    print(f"{Fore.YELLOW}⚠️  {text}{Style.RESET_ALL}")


def setup_test_environment():
    """Setup test service and API key."""
    print_header("SETUP: Creating Test Environment")
    
    # Register a test service
    payload = {
        "name": "Bot Detection Test Service",
        "target_url": "https://httpbin.org/get"
    }
    
    response = requests.post(f"{BASE_URL}/register-api", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        service_id = data.get("service_id")
        api_key = data.get("api_key")
        
        # If API key is None (user already exists), create a new key for this service
        if not api_key:
            print_info("User already exists. Creating a new API key for this service...")
            key_response = requests.post(f"{BASE_URL}/services/{service_id}/keys")
            if key_response.status_code == 200:
                key_data = key_response.json()
                api_key = key_data.get("api_key")
                print_success("New API key generated successfully")
            else:
                print_error(f"Failed to generate API key: {key_response.text}")
                return service_id, None
        
        print_success(f"Service created - ID: {service_id}")
        if api_key:
            print_info(f"API Key: {api_key[:20]}...")
        
        return service_id, api_key
    else:
        print_error(f"Failed to create service: {response.text}")
        return None, None


def simulate_bot_pattern_1_rapid_requests(service_id, api_key):
    """
    Bot Pattern 1: Rapid Sequential Requests
    Real bots often make many requests very quickly without delays.
    """
    print_header("BOT PATTERN 1: Rapid Sequential Requests")
    print_info("Simulating a scraper bot making rapid requests...")
    
    user_agent = random.choice(REAL_BOT_USER_AGENTS[:4])  # Scraper bots
    print_bot(f"Using bot user agent: {user_agent}")
    
    headers = {
        "X-API-Key": api_key,
        "User-Agent": user_agent
    }
    
    results = {"success": 0, "blocked": 0, "rate_limited": 0}
    
    for i in range(20):
        try:
            response = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            if response.status_code == 200:
                results["success"] += 1
                print(f"  Request {i+1}: ✓ Allowed", end="\r")
            elif response.status_code == 403:
                results["blocked"] += 1
                print_bot(f"  Request {i+1}: ✗ BLOCKED (Bot detected!)")
            elif response.status_code == 429:
                results["rate_limited"] += 1
                print_info(f"  Request {i+1}: ⏱ Rate limited")
            
            time.sleep(0.05)  # Very short delay (bots are fast)
        
        except Exception as e:
            print_error(f"Request {i+1} failed: {str(e)}")
    
    print(f"\n")
    print_info(f"Results: {results['success']} allowed, {results['blocked']} blocked, {results['rate_limited']} rate limited")
    return results


def simulate_bot_pattern_2_automation_tools(service_id, api_key):
    """
    Bot Pattern 2: Automation Tool Signatures
    Testing with user agents from Selenium, Puppeteer, etc.
    """
    print_header("BOT PATTERN 2: Automation Tool Signatures")
    print_info("Simulating browser automation tools...")
    
    automation_agents = REAL_BOT_USER_AGENTS[4:8]
    results = {"success": 0, "blocked": 0}
    
    for user_agent in automation_agents:
        print_bot(f"Testing: {user_agent}")
        
        headers = {
            "X-API-Key": api_key,
            "User-Agent": user_agent
        }
        
        try:
            response = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            if response.status_code == 200:
                results["success"] += 1
                print(f"  → Allowed")
            elif response.status_code == 403:
                results["blocked"] += 1
                print_bot(f"  → BLOCKED!")
            
            time.sleep(0.5)
        
        except Exception as e:
            print_error(f"  → Error: {str(e)}")
    
    print_info(f"Results: {results['success']} allowed, {results['blocked']} blocked")
    return results


def simulate_bot_pattern_3_http_libraries(service_id, api_key):
    """
    Bot Pattern 3: HTTP Library User Agents
    Testing with axios, node-fetch, Go client, etc.
    """
    print_header("BOT PATTERN 3: HTTP Library User Agents")
    print_info("Simulating HTTP library requests...")
    
    http_lib_agents = REAL_BOT_USER_AGENTS[8:12]
    results = {"success": 0, "blocked": 0}
    
    for user_agent in http_lib_agents:
        print_bot(f"Testing: {user_agent}")
        
        headers = {
            "X-API-Key": api_key,
            "User-Agent": user_agent
        }
        
        try:
            response = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            if response.status_code == 200:
                results["success"] += 1
                print(f"  → Allowed")
            elif response.status_code == 403:
                results["blocked"] += 1
                print_bot(f"  → BLOCKED!")
            
            time.sleep(0.5)
        
        except Exception as e:
            print_error(f"  → Error: {str(e)}")
    
    print_info(f"Results: {results['success']} allowed, {results['blocked']} blocked")
    return results


def simulate_legitimate_traffic(service_id, api_key):
    """
    Simulate legitimate browser traffic for comparison.
    """
    print_header("LEGITIMATE TRAFFIC: Real Browser Requests")
    print_info("Simulating legitimate user traffic...")
    
    results = {"success": 0, "blocked": 0}
    
    for i in range(10):
        user_agent = random.choice(LEGITIMATE_USER_AGENTS)
        
        headers = {
            "X-API-Key": api_key,
            "User-Agent": user_agent
        }
        
        try:
            response = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            if response.status_code == 200:
                results["success"] += 1
                print_human(f"Request {i+1}: ✓ Allowed (Human traffic)")
            elif response.status_code == 403:
                results["blocked"] += 1
                print_error(f"Request {i+1}: ✗ BLOCKED (False positive!)")
            
            time.sleep(random.uniform(1, 3))  # Human-like delays
        
        except Exception as e:
            print_error(f"Request {i+1} failed: {str(e)}")
    
    print_info(f"Results: {results['success']} allowed, {results['blocked']} blocked")
    return results


def simulate_suspicious_traffic(service_id, api_key):
    """
    Simulate suspicious traffic (curl, wget, etc.)
    """
    print_header("SUSPICIOUS TRAFFIC: Command-line Tools")
    print_info("Simulating suspicious but possibly legitimate traffic...")
    
    results = {"success": 0, "blocked": 0}
    
    for user_agent in SUSPICIOUS_USER_AGENTS:
        print_suspicious(f"Testing: {user_agent}")
        
        headers = {
            "X-API-Key": api_key,
            "User-Agent": user_agent
        }
        
        try:
            response = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            if response.status_code == 200:
                results["success"] += 1
                print(f"  → Allowed (Flagged as suspicious)")
            elif response.status_code == 403:
                results["blocked"] += 1
                print_suspicious(f"  → BLOCKED!")
            
            time.sleep(0.5)
        
        except Exception as e:
            print_error(f"  → Error: {str(e)}")
    
    print_info(f"Results: {results['success']} allowed, {results['blocked']} blocked")
    return results


def check_bot_activity_metrics():
    """
    Check the bot activity metrics from the API.
    """
    print_header("CHECKING BOT ACTIVITY METRICS")
    
    try:
        response = requests.get(f"{BASE_URL}/security/bot-activity")
        
        if response.status_code == 200:
            data = response.json()
            
            print_success("Bot activity data retrieved successfully!")
            print(f"\n{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")
            print(f"{Style.BRIGHT}METRICS SUMMARY:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")
            
            total = data.get('total_requests', 0)
            bot_pct = data.get('bot_percentage', 0)
            blocked = data.get('blocked_count', 0)
            suspicious = data.get('suspicious_count', 0)
            recent = data.get('recent_activity', [])
            
            print(f"\n📊 Total Requests Analyzed: {Fore.YELLOW}{total}{Style.RESET_ALL}")
            print(f"🤖 Bot Traffic Percentage: {Fore.RED}{bot_pct:.2f}%{Style.RESET_ALL}")
            print(f"🚫 Blocked Requests: {Fore.RED}{blocked}{Style.RESET_ALL}")
            print(f"⚠️  Suspicious Requests: {Fore.YELLOW}{suspicious}{Style.RESET_ALL}")
            print(f"📝 Recent Activity Entries: {Fore.CYAN}{len(recent)}{Style.RESET_ALL}")
            
            # Show classification breakdown
            if recent:
                classifications = {"human": 0, "suspicious": 0, "bot": 0}
                actions = {"allowed": 0, "flagged": 0, "blocked": 0}
                
                for activity in recent:
                    classifications[activity['classification']] = classifications.get(activity['classification'], 0) + 1
                    actions[activity['action_taken']] = actions.get(activity['action_taken'], 0) + 1
                
                print(f"\n{Style.BRIGHT}CLASSIFICATION BREAKDOWN:{Style.RESET_ALL}")
                print(f"  👤 Human: {Fore.GREEN}{classifications.get('human', 0)}{Style.RESET_ALL}")
                print(f"  ⚠️  Suspicious: {Fore.YELLOW}{classifications.get('suspicious', 0)}{Style.RESET_ALL}")
                print(f"  🤖 Bot: {Fore.RED}{classifications.get('bot', 0)}{Style.RESET_ALL}")
                
                print(f"\n{Style.BRIGHT}ACTION BREAKDOWN:{Style.RESET_ALL}")
                print(f"  ✓ Allowed: {Fore.GREEN}{actions.get('allowed', 0)}{Style.RESET_ALL}")
                print(f"  ⚠️  Flagged: {Fore.YELLOW}{actions.get('flagged', 0)}{Style.RESET_ALL}")
                print(f"  ✗ Blocked: {Fore.RED}{actions.get('blocked', 0)}{Style.RESET_ALL}")
                
                # Show sample of recent bot detections
                print(f"\n{Style.BRIGHT}SAMPLE RECENT DETECTIONS:{Style.RESET_ALL}")
                for activity in recent[:10]:
                    score = activity['bot_score']
                    classification = activity['classification']
                    action = activity['action_taken']
                    ua = activity['user_agent'][:50]
                    
                    color = Fore.GREEN if classification == 'human' else (Fore.YELLOW if classification == 'suspicious' else Fore.RED)
                    
                    print(f"  {color}[{classification.upper()}]{Style.RESET_ALL} Score: {score:.2f} | Action: {action} | UA: {ua}")
            
            print(f"\n{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}\n")
            
            return data
        else:
            print_error(f"Failed to retrieve bot activity: Status {response.status_code}")
            return None
    
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None


def test_bot_blocking_toggle(service_id):
    """
    Test enabling and disabling bot blocking.
    """
    print_header("TESTING BOT BLOCKING TOGGLE")
    
    # Enable bot blocking
    print_info("Enabling bot blocking...")
    try:
        response = requests.put(
            f"{BASE_URL}/security/bot-blocking/{service_id}",
            json={"enabled": True}
        )
        
        if response.status_code == 200:
            print_success("Bot blocking ENABLED")
        else:
            print_error(f"Failed to enable: {response.text}")
    except Exception as e:
        print_error(f"Error: {str(e)}")
    
    time.sleep(1)
    
    # Disable bot blocking
    print_info("Disabling bot blocking...")
    try:
        response = requests.put(
            f"{BASE_URL}/security/bot-blocking/{service_id}",
            json={"enabled": False}
        )
        
        if response.status_code == 200:
            print_success("Bot blocking DISABLED")
        else:
            print_error(f"Failed to disable: {response.text}")
    except Exception as e:
        print_error(f"Error: {str(e)}")


def main():
    """
    Main test execution.
    """
    print(f"{Fore.CYAN}{Style.BRIGHT}")
    print("=" * 80)
    print("🤖 REAL BOT DETECTION TESTING SUITE 🤖")
    print("=" * 80)
    print(f"{Style.RESET_ALL}")
    
    print_info(f"Testing backend at: {BASE_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info("\nThis script will simulate real bot traffic patterns to test detection.\n")
    
    # Setup
    service_id, api_key = setup_test_environment()
    
    if not service_id or not api_key:
        print_error("Setup failed. Make sure the backend is running!")
        return
    
    time.sleep(1)
    
    # Test bot blocking toggle
    test_bot_blocking_toggle(service_id)
    time.sleep(1)
    
    # Simulate different traffic patterns
    print_info("\nStarting traffic simulation...\n")
    
    # 1. Legitimate traffic (baseline)
    simulate_legitimate_traffic(service_id, api_key)
    time.sleep(2)
    
    # 2. Suspicious traffic
    simulate_suspicious_traffic(service_id, api_key)
    time.sleep(2)
    
    # 3. Bot Pattern 1: Rapid requests
    simulate_bot_pattern_1_rapid_requests(service_id, api_key)
    time.sleep(2)
    
    # 4. Bot Pattern 2: Automation tools
    simulate_bot_pattern_2_automation_tools(service_id, api_key)
    time.sleep(2)
    
    # 5. Bot Pattern 3: HTTP libraries
    simulate_bot_pattern_3_http_libraries(service_id, api_key)
    time.sleep(2)
    
    # Check metrics
    check_bot_activity_metrics()
    
    # Final instructions
    print_header("TESTING COMPLETE - NEXT STEPS")
    print_success("All bot detection tests completed!")
    
    print(f"\n{Style.BRIGHT}Now open the Security page to verify:{Style.RESET_ALL}")
    print(f"\n  {Fore.CYAN}http://localhost:3000/security{Style.RESET_ALL}\n")
    
    print(f"{Style.BRIGHT}What to check:{Style.RESET_ALL}")
    print(f"  ✓ Total requests analyzed should be 50+")
    print(f"  ✓ Bot percentage should be 30-60%")
    print(f"  ✓ Blocked count depends on bot blocking setting")
    print(f"  ✓ Suspicious count should be 5-10")
    print(f"  ✓ Recent activity table shows all traffic")
    print(f"  ✓ Classifications are color-coded correctly")
    print(f"  ✓ Bot blocking toggle works")
    
    print(f"\n{Style.BRIGHT}To test bot blocking enforcement:{Style.RESET_ALL}")
    print(f"  1. Enable bot blocking for service {service_id} on Security page")
    print(f"  2. Run this script again")
    print(f"  3. Verify that bot requests (score >= 0.7) are blocked\n")
    
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
