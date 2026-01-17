# How to Test Bot Detection with Real Bots

## Quick Start - Manual Testing with curl

### Step 1: Get Your API Key

First, register a service and get your API key:

```bash
curl -X POST http://127.0.0.1:8000/register-api \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Bot Test Service\", \"target_url\": \"https://httpbin.org/get\"}"
```

**Save the `api_key` and `service_id` from the response!**

---

### Step 2: Test with Different User Agents

Replace `YOUR_API_KEY` and `SERVICE_ID` with your actual values.

#### 🤖 Test 1: Python Bot (High Bot Score)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: python-requests/2.28.0"
```

**Expected:** Bot score ~0.8-0.9, classified as "bot"

---

#### 🤖 Test 2: Scrapy Bot (High Bot Score)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Scrapy/2.8.0 (+https://scrapy.org)"
```

**Expected:** Bot score ~0.9, classified as "bot"

---

#### 🤖 Test 3: Selenium Bot (High Bot Score)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Selenium/4.0.0 (Python)"
```

**Expected:** Bot score ~0.8, classified as "bot"

---

#### ⚠️ Test 4: curl (Suspicious)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: curl/7.68.0"
```

**Expected:** Bot score ~0.3-0.5, classified as "suspicious"

---

#### ⚠️ Test 5: Wget (Suspicious)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Wget/1.20.3"
```

**Expected:** Bot score ~0.4-0.6, classified as "suspicious"

---

#### 👤 Test 6: Chrome Browser (Human)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

**Expected:** Bot score ~0.1-0.2, classified as "human"

---

#### 👤 Test 7: Firefox Browser (Human)

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
```

**Expected:** Bot score ~0.1, classified as "human"

---

### Step 3: Check Bot Activity

After making several requests, check the bot activity:

```bash
curl http://127.0.0.1:8000/security/bot-activity
```

**You should see:**
- `total_requests`: Number of requests made
- `bot_percentage`: Percentage classified as bots
- `blocked_count`: Number of blocked requests (if blocking enabled)
- `suspicious_count`: Number of suspicious requests
- `recent_activity`: Array of recent requests with classifications

---

### Step 4: Enable Bot Blocking

```bash
curl -X PUT http://127.0.0.1:8000/security/bot-blocking/SERVICE_ID \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": true}"
```

---

### Step 5: Test Bot Blocking

Now make a bot request again:

```bash
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: python-requests/2.28.0"
```

**Expected:** If bot score >= 0.7, you'll get:
```json
{
  "detail": "Bot traffic detected (score: 0.85). This service has bot blocking enabled."
}
```

Status code: **403 Forbidden**

---

### Step 6: View Security Page

Open your browser and go to:

```
http://localhost:3000/security
```

**You should see:**
- ✅ Metrics cards with request counts
- ✅ Bot percentage calculation
- ✅ Blocked/Suspicious counts
- ✅ Bot blocking toggle switches
- ✅ Recent activity table with all your test requests
- ✅ Color-coded classifications (green=human, yellow=suspicious, red=bot)
- ✅ Action badges (Allowed/Flagged/Blocked)

---

## Automated Testing (Recommended)

### Option 1: Run the Bot Detection Test Script

```bash
# Install dependencies
pip install colorama requests

# Run the test
python test_bot_detection.py
```

This script will:
- Create a test service
- Simulate 50+ requests with different user agents
- Test all bot patterns (rapid requests, automation tools, HTTP libraries)
- Show detailed metrics and classifications
- Provide instructions for viewing the Security page

---

### Option 2: Run Quick Security Test

```bash
python test_security.py
```

This generates mixed traffic and verifies the Security page has data.

---

## Understanding Bot Scores

The bot detection system calculates a score from 0.0 to 1.0:

| Score Range | Classification | Color | Action (if blocking enabled) |
|-------------|----------------|-------|------------------------------|
| 0.0 - 0.3   | Human          | 🟢 Green | ✅ Allowed |
| 0.3 - 0.7   | Suspicious     | 🟡 Yellow | ⚠️ Flagged (allowed but logged) |
| 0.7 - 1.0   | Bot            | 🔴 Red | ❌ Blocked (if enabled) |

---

## Bot Detection Factors

The system checks:

1. **User Agent String**
   - Known bot patterns (python, scrapy, selenium, etc.)
   - Browser signatures
   - HTTP library identifiers

2. **Request Patterns** (future enhancement)
   - Request frequency
   - Time between requests
   - Request volume

3. **Behavior Analysis** (future enhancement)
   - Navigation patterns
   - JavaScript execution
   - Cookie handling

---

## 💡 Important: How to Trigger "Bot Detected" (Red)

The detection system is conservative to avoid false positives. 
**A single request from a bot will often be classified as "Suspicious" (Yellow), not "Bot" (Red).**

To get a **"Bot Detected" (Red, Score ≥ 0.7)** alert, you must satisfy TWO conditions:
1. Use a Bot User-Agent (e.g., `Googlebot`, `python-requests`)
2. Make **MULTIPLE requests** (6+) in a short time

The system increases the bot score based on request rate.

### 🔴 Command to Trigger RED Alert

Run this loop to send 10 requests quickly:

**Windows PowerShell:**
```powershell
1..10 | % { curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_KEY" -H "User-Agent: Googlebot/2.1" }
```

**Linux/Mac:**
```bash
for i in {1..10}; do curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_KEY" -H "User-Agent: Googlebot/2.1"; done
```

---

## Testing Different Scenarios

### Scenario 1: Legitimate Developer Using curl

```bash
# This will be flagged as suspicious but allowed
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: curl/7.68.0"
```

**Result:** Suspicious (0.3-0.5), Allowed, Flagged in logs

---

### Scenario 2: Malicious Scraper

```bash
# This will be blocked if bot blocking is enabled
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: python-requests/2.28.0"
```

**Result:** Bot (0.8-0.9), Blocked (if enabled)

---

### Scenario 3: Legitimate Browser

```bash
# This will always be allowed
curl http://127.0.0.1:8000/proxy/SERVICE_ID \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
```

**Result:** Human (0.1-0.2), Allowed

---

### Scenario 4: Rapid Bot Requests (Rate Limiting)

```powershell
# PowerShell - Make 20 rapid requests
for ($i=1; $i -le 20; $i++) {
  curl http://127.0.0.1:8000/proxy/SERVICE_ID `
    -H "X-API-Key: YOUR_API_KEY" `
    -H "User-Agent: python-requests/2.28.0"
  Write-Host "Request $i"
}
```

**Result:** 
- First 10: May be allowed (depending on bot blocking)
- After 10: Rate limited (429)
- All logged as bot traffic

---

## Verifying Results

### Check Bot Activity Metrics

```bash
curl http://127.0.0.1:8000/security/bot-activity | python -m json.tool
```

### Check Bot Blocking Config

```bash
curl http://127.0.0.1:8000/security/bot-blocking-config | python -m json.tool
```

### Check Recent Activity

The `/security/bot-activity` endpoint returns recent activity with:
- `timestamp`: When the request was made
- `service_id` and `service_name`: Which service
- `api_key`: Which key was used (masked in UI)
- `bot_score`: Calculated score (0.0-1.0)
- `classification`: "human", "suspicious", or "bot"
- `user_agent`: The User-Agent header
- `action_taken`: "allowed", "flagged", or "blocked"

---

## Troubleshooting

### "No bot activity data"
- **Solution:** Make some requests first using the curl commands above

### "Bot blocking not working"
- **Solution:** Check that bot score >= 0.7 (lower scores are flagged but not blocked)

### "All requests blocked"
- **Solution:** Disable bot blocking or use a browser user agent

### "No requests blocked"
- **Solution:** Enable bot blocking via the Security page or API

---

## Best Practices for Testing

1. **Start with bot blocking disabled** to see classifications
2. **Make requests with different user agents** to see score variations
3. **Enable bot blocking** and test enforcement
4. **Check the Security page** after each test batch
5. **Use the Refresh button** on Security page to update data
6. **Test with multiple services** to verify independent configs

---

## Real-World Bot Examples

### Good Bots (Should Allow)
- Googlebot: `Googlebot/2.1 (+http://www.google.com/bot.html)`
- Bingbot: `Bingbot/2.0 (+http://www.bing.com/bingbot.htm)`

### Bad Bots (Should Block)
- Scrapers: `Scrapy/2.8.0`, `python-requests/2.28.0`
- Automation: `Selenium/4.0.0`, `Puppeteer/19.0.0`
- Generic: `Bot`, `Spider`, `Crawler`

### Suspicious (Flag but Allow)
- Developer tools: `curl/7.68.0`, `Wget/1.20.3`, `Postman`
- HTTP clients: `axios/1.3.0`, `node-fetch/3.2.0`

---

## Next Steps

After testing:

1. ✅ Verify Security page displays all metrics correctly
2. ✅ Test bot blocking toggle on/off
3. ✅ Check that classifications are accurate
4. ✅ Verify action badges match actual behavior
5. ✅ Test with multiple services
6. ✅ Review recent activity table

---

## Summary

You now have multiple ways to test bot detection:

1. **Manual curl commands** - Quick, specific tests
2. **Automated Python script** - Comprehensive, realistic simulation
3. **Security page UI** - Visual verification and management

**Happy Bot Testing! 🤖🔍**
