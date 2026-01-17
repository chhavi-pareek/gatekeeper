"""
Script to GUARANTEE a "Bot Detected" (Red) alert.

The system requires multiple requests to upgrade a detection 
from "Suspicious" (Yellow) to "Bot" (Red) to avoid false positives.

This script sends 10 quick requests as 'Googlebot' to trigger the Red alert.
"""

import requests
import time
from colorama import init, Fore, Style

init(autoreset=True)

BASE_URL = "http://127.0.0.1:8000"
BOT_NAME = "Googlebot/2.1 (+http://www.google.com/bot.html)"

def trigger_bot_alert():
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"🚨 TRIGGERING BOT ALERT 🚨")
    print(f"{'=' * 80}\n")
    
    # Get/Create Service
    print("1. Getting API Key...")
    reg_payload = {"name": "Bot Trigger Test", "target_url": "https://httpbin.org/get"}
    try:
        r = requests.post(f"{BASE_URL}/register-api", json=reg_payload)
        data = r.json()
        service_id = data['service_id']
        api_key = data.get('api_key')
        
        # Handle existing user case
        if not api_key:
            k = requests.post(f"{BASE_URL}/services/{service_id}/keys")
            api_key = k.json()['api_key']
            
        print(f"   Using Service ID: {service_id}")
        # print(f"   Using API Key: {api_key[:10]}...")
    except Exception as e:
        print(f"{Fore.RED}Error setting up: {e}")
        return

    # Send requests
    print(f"\n2. Sending 10 requests as '{Fore.YELLOW}{BOT_NAME}{Style.RESET_ALL}'...")
    
    headers = {
        "X-API-Key": api_key,
        "User-Agent": BOT_NAME
    }
    
    for i in range(1, 11):
        try:
            r = requests.get(f"{BASE_URL}/proxy/{service_id}", headers=headers)
            
            # Check if blocked
            if r.status_code == 403:
                print(f"   Request {i}: {Fore.RED}BLOCKED (HTTP 403){Style.RESET_ALL} -> BOT DETECTED! 🤖")
            elif r.status_code == 429:
                print(f"   Request {i}: {Fore.MAGENTA}Rate Limited (HTTP 429){Style.RESET_ALL}")
            else:
                print(f"   Request {i}: {Fore.YELLOW}Allowed (Suspicious){Style.RESET_ALL}")
            
            time.sleep(0.1) 
        except Exception as e:
            print(f"   Error: {e}")

    print(f"\n{Fore.GREEN}Done! Check the Security Page now.{Style.RESET_ALL}")
    print(f"http://localhost:3000/security")

if __name__ == "__main__":
    trigger_bot_alert()
