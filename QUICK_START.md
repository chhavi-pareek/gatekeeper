# Quick Start Guide

This guide will help you run and test the GaaS Gateway project.

## Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- Both terminal windows (one for backend, one for frontend)

## Step 1: Set Up the Backend (FastAPI)

1. **Navigate to the project root:**
   ```bash
   cd /Users/chhavipareek/gatekeeper
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the FastAPI server:**
   ```bash
   uvicorn main:app --reload
   ```

   The backend will be available at `http://127.0.0.1:8000`

5. **Verify the backend is running:**
   - Open `http://127.0.0.1:8000/docs` in your browser (Swagger UI)
   - Or check `http://127.0.0.1:8000/health` should return `{"status": "healthy"}`

## Step 2: Set Up the Frontend (Next.js)

1. **Open a new terminal window** (keep the backend running)

2. **Navigate to the frontend directory:**
   ```bash
   cd /Users/chhavipareek/gatekeeper/frontend
   ```

3. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:3000`

5. **Open your browser:**
   Navigate to `http://localhost:3000` to see the dashboard

## Step 3: Test the Application

### Test 1: Register an API Service

1. **Go to the APIs page:**
   - Click "APIs" in the sidebar, or navigate to `http://localhost:3000/apis`

2. **Fill in the registration form:**
   - **API Name**: `Test API`
   - **Target URL**: `https://httpbin.org/get` (a test API service)

3. **Click "Register API"**

4. **Expected result:**
   - Success toast notification
   - Gateway URL displayed (e.g., `/proxy/1`)
   - API key displayed (saved to localStorage automatically)
   - Copy buttons available for both gateway URL and API key

### Test 2: View Dashboard Overview

1. **Go to the Overview page:**
   - Click "Overview" in the sidebar, or navigate to `http://localhost:3000/`

2. **Expected result:**
   - Statistics cards showing metrics
   - Request trends section
   - Top APIs list

### Test 3: Check Usage Analytics

1. **Go to the Usage page:**
   - Click "Usage" in the sidebar, or navigate to `http://localhost:3000/usage`

2. **Enter a Service ID:**
   - Enter `1` (the service ID from Test 1)
   - Click "Fetch Usage"

3. **Expected result:**
   - Total requests count
   - Requests breakdown by API key
   - Table with usage statistics

### Test 4: View Security Settings

1. **Go to the Settings page:**
   - Click "Settings" in the sidebar, or navigate to `http://localhost:3000/settings`

2. **Test API Key Management:**
   - Click the eye icon to reveal your API key
   - Click "Copy" to copy the API key
   - Verify toast notification appears

3. **Expected result:**
   - API key displayed (masked by default)
   - Rate limit policy information
   - Security best practices

### Test 5: Test API Proxying (via curl)

1. **Get your API key:**
   - Copy it from the Settings page or from the registration success message

2. **Test a proxied request:**
   ```bash
   curl http://127.0.0.1:8000/proxy/1 \
     -H "X-API-Key: YOUR_API_KEY_HERE"
   ```

3. **Expected result:**
   - Response from the target URL (`https://httpbin.org/get`)
   - Response includes the proxied data

### Test 6: Test Rate Limiting

1. **Make multiple requests quickly:**
   ```bash
   for i in {1..15}; do
     curl http://127.0.0.1:8000/proxy/1 \
       -H "X-API-Key: YOUR_API_KEY_HERE"
     echo "Request $i"
   done
   ```

2. **Expected result:**
   - First 10 requests succeed
   - Requests 11+ return HTTP 429 (Rate Limit Exceeded)
   - After ~60 seconds, requests should succeed again

## Troubleshooting

### Backend Issues

**Problem:** `ModuleNotFoundError: No module named 'sqlalchemy'`
- **Solution:** Make sure you've activated the virtual environment and installed dependencies:
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Problem:** `Address already in use`
- **Solution:** The port 8000 is already in use. Either:
  - Stop the other process using port 8000
  - Use a different port: `uvicorn main:app --reload --port 8001`

**Problem:** `Could not import module 'main'`
- **Solution:** Make sure you're running from the project root directory:
  ```bash
  cd /Users/chhavipareek/gatekeeper
  uvicorn main:app --reload
  ```

### Frontend Issues

**Problem:** `npm: command not found`
- **Solution:** Install Node.js from https://nodejs.org/ (version 18 or higher)

**Problem:** `Cannot connect to API`
- **Solution:** 
  - Verify the backend is running on `http://127.0.0.1:8000`
  - Check browser console for CORS errors
  - Verify the API URL in `.env.local` if you've customized it

**Problem:** `API key not working`
- **Solution:**
  - Check that the API key is saved in localStorage (check browser DevTools → Application → Local Storage)
  - Verify the API key format matches what was returned from registration
  - Try registering a new service to get a fresh API key

### Database Issues

**Problem:** `sqlite3.OperationalError: no such column: api_key_revealed`
- **Solution:** The database needs to be migrated. Restart the backend server - it will automatically add the missing column on startup.

**Problem:** Database file locked
- **Solution:** Make sure only one instance of the backend is running

## Quick Test Checklist

- [ ] Backend server starts without errors
- [ ] Frontend server starts without errors
- [ ] Can access dashboard at `http://localhost:3000`
- [ ] Can register a new API service
- [ ] API key is saved to localStorage
- [ ] Can view usage statistics
- [ ] Can view/retrieve API key from Settings
- [ ] Can make proxied requests via curl
- [ ] Rate limiting works (10 requests per 60 seconds)

## Environment Variables

### Backend
The backend uses SQLite by default. To use a different database:
```bash
export DATABASE_URL="sqlite:///./gaas_gateway.db"
```

### Frontend
To configure a different backend URL, create `.env.local` in the `frontend/` directory:
```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Next Steps

Once everything is working:
1. Register multiple services
2. Test different backend URLs
3. Monitor usage analytics
4. Test rate limiting with multiple API keys
5. Explore the API documentation at `http://127.0.0.1:8000/docs`

## API Documentation

- **Backend API Docs (Swagger)**: `http://127.0.0.1:8000/docs`
- **Backend API Docs (ReDoc)**: `http://127.0.0.1:8000/redoc`
