# GaaS Gateway - Comprehensive Testing Guide

This guide provides detailed instructions for testing the entire GaaS Gateway project, including the Security page with bot detection features.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup for Testing](#setup-for-testing)
3. [Backend API Testing](#backend-api-testing)
4. [Frontend Testing](#frontend-testing)
5. [Security Page Testing](#security-page-testing)
6. [Integration Testing](#integration-testing)
7. [Performance Testing](#performance-testing)
8. [Test Checklist](#test-checklist)

---

## Prerequisites

- Python 3.10+ installed
- Node.js 18+ and npm installed
- Backend server running on `http://127.0.0.1:8000`
- Frontend server running on `http://localhost:3000`
- curl or Postman for API testing
- Browser DevTools for frontend debugging

---

## Setup for Testing

### 1. Start the Backend Server

```bash
cd "c:\Users\vinuu\Downloads\5 el\gatekeeper"
venv\Scripts\activate
uvicorn main:app --reload
```

Verify backend is running:
```bash
curl http://127.0.0.1:8000/health
# Expected: {"status": "healthy"}
```

### 2. Start the Frontend Server

```bash
cd "c:\Users\vinuu\Downloads\5 el\gatekeeper\frontend"
npm run dev
```

Verify frontend is running by opening `http://localhost:3000` in your browser.

---

## Backend API Testing

### Test 1: Health Check

**Endpoint:** `GET /health`

```bash
curl http://127.0.0.1:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy"
}
```

✅ **Pass Criteria:** Returns 200 status with "healthy" message

---

### Test 2: Register a New Service

**Endpoint:** `POST /register-api`

```bash
curl -X POST http://127.0.0.1:8000/register-api \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Test Service\", \"target_url\": \"https://httpbin.org/get\"}"
```

**Expected Response:**
```json
{
  "service_id": 1,
  "gateway_url": "/proxy/1",
  "api_key": "YOUR_API_KEY_HERE"
}
```

✅ **Pass Criteria:** 
- Returns 200 status
- Provides service_id, gateway_url, and api_key
- API key is a secure token (32+ characters)

**Save the API key for subsequent tests!**

---

### Test 3: Get API Key (First Time)

**Endpoint:** `GET /me/api-key`

```bash
curl http://127.0.0.1:8000/me/api-key
```

**Expected Response:**
```json
{
  "api_key": "YOUR_API_KEY"
}
```

✅ **Pass Criteria:** Returns the API key on first call

---

### Test 4: Get API Key (Second Time - Should Fail)

```bash
curl http://127.0.0.1:8000/me/api-key
```

**Expected Response:**
```json
{
  "message": "API key cannot be viewed again. It was already revealed once."
}
```

✅ **Pass Criteria:** API key is not revealed again (security feature)

---

### Test 5: Proxy Request (Valid API Key)

**Endpoint:** `GET /proxy/{service_id}`

```bash
curl http://127.0.0.1:8000/proxy/1 \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected Response:**
- Returns data from `https://httpbin.org/get`
- Status code: 200

✅ **Pass Criteria:** 
- Request is successfully proxied
- Response contains data from target URL
- Bot detection log is created

---

### Test 6: Proxy Request (Invalid API Key)

```bash
curl http://127.0.0.1:8000/proxy/1 \
  -H "X-API-Key: invalid_key_12345"
```

**Expected Response:**
```json
{
  "detail": "Invalid API key"
}
```

✅ **Pass Criteria:** Returns 401 Unauthorized

---

### Test 7: Rate Limiting

**Endpoint:** `GET /proxy/{service_id}` (multiple requests)

```bash
# Windows PowerShell
for ($i=1; $i -le 15; $i++) {
  curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_API_KEY"
  Write-Host "Request $i"
}
```

**Expected Behavior:**
- First 10 requests: Success (200)
- Requests 11-15: Rate limit exceeded (429)

✅ **Pass Criteria:** 
- Rate limiting kicks in after 10 requests
- Returns HTTP 429 with "Rate limit exceeded" message

---

### Test 8: Create Additional API Key

**Endpoint:** `POST /services/{service_id}/keys`

```bash
curl -X POST http://127.0.0.1:8000/services/1/keys
```

**Expected Response:**
```json
{
  "api_key": "NEW_API_KEY",
  "service_id": 1,
  "message": "API key created successfully..."
}
```

✅ **Pass Criteria:** 
- New API key is generated
- Old API key still works
- Both keys have independent rate limits

---

### Test 9: List All API Keys

**Endpoint:** `GET /api-keys`

```bash
curl http://127.0.0.1:8000/api-keys
```

**Expected Response:**
```json
{
  "services": [
    {
      "service_id": 1,
      "service_name": "Test Service",
      "api_keys": [
        {
          "id": 1,
          "key": "key_***",
          "is_active": true,
          "rate_limit_requests": 10,
          "rate_limit_window_seconds": 60
        }
      ]
    }
  ]
}
```

✅ **Pass Criteria:** Lists all services with their API keys (masked)

---

### Test 10: Update Rate Limit

**Endpoint:** `PUT /api-keys/{key_id}/rate-limit`

```bash
curl -X PUT http://127.0.0.1:8000/api-keys/1/rate-limit \
  -H "Content-Type: application/json" \
  -d "{\"requests\": 20, \"window_seconds\": 60}"
```

**Expected Response:**
```json
{
  "message": "Rate limit updated successfully",
  "api_key_id": 1,
  "requests": 20,
  "window_seconds": 60
}
```

✅ **Pass Criteria:** Rate limit is updated and applies to future requests

---

### Test 11: Usage Statistics

**Endpoint:** `GET /usage/{service_id}`

```bash
curl http://127.0.0.1:8000/usage/1 \
  -H "X-API-Key: YOUR_API_KEY"
```

**Expected Response:**
```json
{
  "service_id": 1,
  "total_requests": 15,
  "requests_by_api_key": [
    {
      "api_key": "YOUR_API_KEY",
      "count": 15
    }
  ]
}
```

✅ **Pass Criteria:** Accurate request counts are returned

---

### Test 12: Billing Summary

**Endpoint:** `GET /billing/summary`

```bash
curl http://127.0.0.1:8000/billing/summary
```

**Expected Response:**
```json
{
  "total_cost": 0.015,
  "total_requests": 15,
  "services": [
    {
      "service_id": 1,
      "service_name": "Test Service",
      "total_cost": 0.015,
      "total_requests": 15
    }
  ]
}
```

✅ **Pass Criteria:** Billing is calculated correctly (default: $0.001 per request)

---

### Test 13: Bot Detection - Get Bot Activity

**Endpoint:** `GET /security/bot-activity`

```bash
curl http://127.0.0.1:8000/security/bot-activity
```

**Expected Response:**
```json
{
  "total_requests": 15,
  "bot_percentage": 0.0,
  "blocked_count": 0,
  "suspicious_count": 0,
  "recent_activity": [
    {
      "id": 1,
      "timestamp": "2026-01-17T15:30:00",
      "service_id": 1,
      "service_name": "Test Service",
      "api_key": "YOUR_API_KEY",
      "bot_score": 0.1,
      "classification": "human",
      "user_agent": "curl/7.68.0",
      "action_taken": "allowed"
    }
  ]
}
```

✅ **Pass Criteria:** Returns bot detection statistics and recent activity

---

### Test 14: Bot Blocking Configuration

**Endpoint:** `GET /security/bot-blocking-config`

```bash
curl http://127.0.0.1:8000/security/bot-blocking-config
```

**Expected Response:**
```json
{
  "services": [
    {
      "service_id": 1,
      "service_name": "Test Service",
      "block_bots_enabled": false
    }
  ]
}
```

✅ **Pass Criteria:** Returns bot blocking status for all services

---

### Test 15: Enable Bot Blocking

**Endpoint:** `PUT /security/bot-blocking/{service_id}`

```bash
curl -X PUT http://127.0.0.1:8000/security/bot-blocking/1 \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": true}"
```

**Expected Response:**
```json
{
  "message": "Bot blocking updated successfully",
  "service_id": 1,
  "block_bots_enabled": true
}
```

✅ **Pass Criteria:** Bot blocking is enabled for the service

---

### Test 16: Bot Detection with Blocking Enabled

Make a request with a bot-like user agent:

```bash
curl http://127.0.0.1:8000/proxy/1 \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "User-Agent: python-requests/2.28.0"
```

**Expected Behavior:**
- If bot score >= 0.7: Request is blocked (403)
- If bot score < 0.7: Request is allowed but flagged

✅ **Pass Criteria:** Bot detection works and blocking is enforced

---

## Frontend Testing

### Test 1: Dashboard Overview Page

**URL:** `http://localhost:3000/`

**Test Steps:**
1. Open the dashboard
2. Verify all metrics are displayed:
   - Total Services
   - Requests Today
   - Average Rate Limit Usage
   - Gateway Status

**Expected Result:**
- All cards display correct data
- No loading errors
- Metrics update when you refresh

✅ **Pass Criteria:** Dashboard loads without errors and displays metrics

---

### Test 2: APIs Page

**URL:** `http://localhost:3000/apis`

**Test Steps:**
1. Navigate to APIs page
2. Fill in the registration form:
   - API Name: "Frontend Test API"
   - Target URL: "https://httpbin.org/anything"
3. Click "Register API"
4. Copy the API key and gateway URL

**Expected Result:**
- Success toast notification
- Service appears in the list
- API key is displayed once
- Copy buttons work

✅ **Pass Criteria:** Can successfully register a new service via UI

---

### Test 3: API Keys Page

**URL:** `http://localhost:3000/apis` (API Keys tab)

**Test Steps:**
1. View list of API keys
2. Click "Create New Key" for a service
3. Verify new key is created
4. Test "Revoke" button
5. Test "Update Rate Limit" functionality

**Expected Result:**
- All API keys are listed
- Can create new keys
- Can revoke keys
- Can update rate limits
- Changes are reflected immediately

✅ **Pass Criteria:** All API key management features work correctly

---

### Test 4: Usage Analytics Page

**URL:** `http://localhost:3000/usage`

**Test Steps:**
1. Navigate to Usage page
2. Enter a service ID (e.g., 1)
3. Click "Fetch Usage"
4. Verify data is displayed

**Expected Result:**
- Total requests count is accurate
- Breakdown by API key is shown
- Charts/graphs display correctly (if implemented)

✅ **Pass Criteria:** Usage statistics are displayed accurately

---

### Test 5: Billing Page

**URL:** `http://localhost:3000/billing`

**Test Steps:**
1. Navigate to Billing page
2. Verify billing summary is displayed
3. Check per-service breakdown
4. Check per-API-key costs

**Expected Result:**
- Total cost is calculated correctly
- Per-service costs are accurate
- Per-key costs are accurate
- Pricing can be updated

✅ **Pass Criteria:** Billing information is accurate and complete

---

## Security Page Testing

### Test 1: Security Page Load

**URL:** `http://localhost:3000/security`

**Test Steps:**
1. Navigate to Security page
2. Verify all sections load:
   - Requests Analyzed
   - Bot Traffic %
   - Blocked Requests
   - Suspicious Activity
   - Bot Blocking Controls
   - Recent Bot Activity table

**Expected Result:**
- All metrics display correctly
- No loading errors
- Data is fetched from backend

✅ **Pass Criteria:** Security page loads without errors

---

### Test 2: Bot Activity Metrics

**Test Steps:**
1. Make several requests via curl (mix of normal and bot-like user agents)
2. Refresh the Security page
3. Verify metrics update:
   - Total requests analyzed
   - Bot percentage
   - Blocked count
   - Suspicious count

**Expected Result:**
- Metrics reflect actual traffic
- Bot percentage is calculated correctly
- Counts are accurate

✅ **Pass Criteria:** Metrics accurately reflect bot detection results

---

### Test 3: Bot Blocking Toggle

**Test Steps:**
1. Find a service in "Bot Blocking Controls"
2. Toggle the switch to enable bot blocking
3. Verify success toast appears
4. Make a request with bot-like user agent
5. Verify request is blocked (if bot score >= 0.7)

**Expected Result:**
- Toggle updates successfully
- Backend configuration is updated
- Bot blocking is enforced
- Blocked requests appear in metrics

✅ **Pass Criteria:** Bot blocking can be toggled and works correctly

---

### Test 4: Recent Bot Activity Table

**Test Steps:**
1. Make several requests with different user agents:
   ```bash
   # Normal request
   curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_KEY" -H "User-Agent: Mozilla/5.0"
   
   # Bot-like request
   curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_KEY" -H "User-Agent: python-requests/2.28.0"
   
   # Suspicious request
   curl http://127.0.0.1:8000/proxy/1 -H "X-API-Key: YOUR_KEY" -H "User-Agent: curl/7.68.0"
   ```
2. Refresh Security page
3. Verify table shows recent activity

**Expected Result:**
- Table displays last 100 requests
- Columns show:
  - Timestamp
  - Service name
  - API key (masked)
  - Classification (Human/Suspicious/Bot)
  - Bot score
  - User agent
  - Action taken (Allowed/Flagged/Blocked)
- Color coding matches classification

✅ **Pass Criteria:** Activity table displays accurate, real-time data

---

### Test 5: Bot Score Classification

**Test Steps:**
1. Make requests with various user agents to generate different bot scores
2. Verify classifications:
   - Bot score < 0.3 → "Human" (green badge)
   - Bot score 0.3-0.7 → "Suspicious" (yellow badge)
   - Bot score >= 0.7 → "Bot" (red badge)

**Expected Result:**
- Classifications are accurate
- Badges display correct colors
- Scores are calculated correctly

✅ **Pass Criteria:** Bot classification logic works correctly

---

### Test 6: Refresh Functionality

**Test Steps:**
1. Click the "Refresh" button on Security page
2. Verify data is reloaded
3. Check that loading states appear briefly

**Expected Result:**
- Data refreshes without page reload
- Loading skeletons appear during fetch
- Updated data is displayed

✅ **Pass Criteria:** Refresh button works correctly

---

## Integration Testing

### Test 1: End-to-End Flow

**Test Steps:**
1. Register a new service via frontend
2. Create an API key for the service
3. Make proxied requests using the API key
4. Enable bot blocking for the service
5. Make bot-like requests and verify they're blocked
6. Check usage statistics
7. Verify billing is updated
8. Check Security page for bot activity

**Expected Result:**
- All components work together seamlessly
- Data flows correctly between frontend and backend
- Bot detection integrates with proxying
- Billing reflects actual usage

✅ **Pass Criteria:** Complete workflow functions without errors

---

### Test 2: Multi-Service Testing

**Test Steps:**
1. Register 3+ services
2. Create multiple API keys for each
3. Make requests to different services
4. Enable bot blocking for some services only
5. Verify each service has independent:
   - Rate limits
   - Bot blocking settings
   - Usage statistics
   - Billing

**Expected Result:**
- Services are isolated
- Settings don't affect other services
- Statistics are accurate per service

✅ **Pass Criteria:** Multi-service isolation works correctly

---

## Performance Testing

### Test 1: Rate Limit Performance

**Test Steps:**
1. Make 100 requests rapidly
2. Verify rate limiting is enforced
3. Check response times

**Expected Result:**
- Rate limiting is consistent
- No race conditions
- Response times < 100ms for rate limit checks

✅ **Pass Criteria:** Rate limiting performs well under load

---

### Test 2: Bot Detection Performance

**Test Steps:**
1. Make 100 requests with bot detection enabled
2. Measure response time overhead

**Expected Result:**
- Bot detection adds < 50ms overhead
- No significant performance degradation

✅ **Pass Criteria:** Bot detection doesn't significantly impact performance

---

## Test Checklist

### Backend API Tests
- [ ] Health check works
- [ ] Service registration works
- [ ] API key generation works
- [ ] API key reveal (one-time) works
- [ ] Proxy requests work (GET, POST, PUT, DELETE)
- [ ] Rate limiting enforced correctly
- [ ] Invalid API key rejected
- [ ] Usage statistics accurate
- [ ] Billing calculations correct
- [ ] Bot detection logs created
- [ ] Bot blocking can be enabled/disabled
- [ ] Bot blocking enforced when enabled

### Frontend Tests
- [ ] Dashboard loads without errors
- [ ] Can register services via UI
- [ ] Can create API keys via UI
- [ ] Can view usage statistics
- [ ] Can view billing information
- [ ] Security page loads correctly
- [ ] Bot metrics display accurately
- [ ] Bot blocking toggle works
- [ ] Recent activity table displays data
- [ ] Refresh functionality works
- [ ] Toast notifications appear
- [ ] Copy buttons work

### Security Page Tests
- [ ] All metrics display correctly
- [ ] Bot percentage calculated accurately
- [ ] Blocked count accurate
- [ ] Suspicious count accurate
- [ ] Bot blocking controls functional
- [ ] Recent activity table populated
- [ ] Classifications correct (Human/Suspicious/Bot)
- [ ] Action badges correct (Allowed/Flagged/Blocked)
- [ ] Refresh updates data
- [ ] No console errors

### Integration Tests
- [ ] End-to-end flow works
- [ ] Multi-service isolation works
- [ ] Bot detection integrates with proxying
- [ ] Billing integrates with usage
- [ ] Frontend and backend communicate correctly

### Performance Tests
- [ ] Rate limiting performs well
- [ ] Bot detection doesn't degrade performance
- [ ] Frontend loads quickly
- [ ] API responses < 200ms

---

## Common Issues and Solutions

### Issue 1: "Invalid API key" error
**Solution:** Ensure you're using the correct API key from registration or `/me/api-key` endpoint

### Issue 2: Rate limit not resetting
**Solution:** Wait 60 seconds for token bucket to refill, or restart backend to reset in-memory store

### Issue 3: Bot detection not working
**Solution:** Verify `app/bot_detector.py` exists and bot detection logs are being created in database

### Issue 4: Security page shows no data
**Solution:** Make some proxied requests first to generate bot detection logs

### Issue 5: Frontend can't connect to backend
**Solution:** Verify backend is running on port 8000 and CORS is configured correctly

---

## Automated Testing

See `test_api.py` for automated backend API tests.

Run automated tests:
```bash
python test_api.py
```

---

## Conclusion

This comprehensive testing guide covers all aspects of the GaaS Gateway project. Follow the tests in order, and check off items as you complete them. If any test fails, refer to the troubleshooting section or check the console/logs for error messages.

**Happy Testing! 🚀**
