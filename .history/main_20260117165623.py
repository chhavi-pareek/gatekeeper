"""
Main entry point for the gaas-gateway FastAPI application.
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, List
from app.database import init_db, get_db
from app.models import User, Service, UsageLog, ApiKey
import httpx
import secrets
import time
from collections import defaultdict
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import base64
import json
import re
import uuid

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Watermarking Utilities
# ============================================================================

def generate_watermark(service_id: int, api_key_id: int, request_id: str, timestamp: str) -> str:
    """
    Generate a base64-encoded watermark containing tracing information.
    Format: service_id|api_key_id|request_id|timestamp
    """
    watermark_data = f"{service_id}|{api_key_id}|{request_id}|{timestamp}"
    encoded = base64.b64encode(watermark_data.encode()).decode()
    return encoded


def decode_watermark(encoded_watermark: str) -> Optional[Dict]:
    """
    Decode a base64-encoded watermark and extract metadata.
    Returns dict with service_id, api_key_id, request_id, timestamp or None if invalid.
    """
    try:
        decoded = base64.b64decode(encoded_watermark.encode()).decode()
        parts = decoded.split("|")
        if len(parts) != 4:
            return None
        return {
            "service_id": int(parts[0]),
            "api_key_id": int(parts[1]),
            "request_id": parts[2],
            "timestamp": parts[3]
        }
    except Exception:
        return None


def extract_watermark_from_json(data: dict) -> Optional[str]:
    """
    Extract _gaas_watermark field from JSON data (recursively).
    """
    if isinstance(data, dict):
        if "_gaas_watermark" in data:
            return data["_gaas_watermark"]
        for value in data.values():
            result = extract_watermark_from_json(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = extract_watermark_from_json(item)
            if result:
                return result
    return None


def extract_watermark_from_text(text: str) -> Optional[str]:
    """
    Extract watermark from text content (hidden in HTML comment or suffix).
    Looks for pattern: <!-- GAAS_WM:base64_data --> or [GAAS_WM:base64_data]
    """
    # HTML comment pattern
    html_pattern = r'<!--\s*GAAS_WM:([A-Za-z0-9+/=]+)\s*-->'
    match = re.search(html_pattern, text)
    if match:
        return match.group(1)
    
    # Bracket pattern for plain text
    bracket_pattern = r'\[GAAS_WM:([A-Za-z0-9+/=]+)\]'
    match = re.search(bracket_pattern, text)
    if match:
        return match.group(1)
    
    return None


def inject_watermark_json(data: dict, watermark: str) -> dict:
    """
    Inject watermark into JSON data by adding _gaas_watermark field.
    """
    if isinstance(data, dict):
        data["_gaas_watermark"] = watermark
    return data


def inject_watermark_text(text: str, watermark: str, content_type: str) -> str:
    """
    Inject watermark into text content.
    For HTML: adds as HTML comment at the end
    For plain text: adds as bracket-enclosed suffix
    """
    if "html" in content_type.lower():
        return f"{text}\n<!-- GAAS_WM:{watermark} -->"
    else:
        return f"{text}\n[GAAS_WM:{watermark}]"

app = FastAPI(
    title="GaaS Gateway",
    description="Gateway API for GaaS (Gateway as a Service)",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to GaaS Gateway API"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/overview")
async def get_overview(db: Session = Depends(get_db)):
    """
    Get overview statistics for the gateway.
    
    Returns:
    - total_services: Total number of registered services
    - requests_today: Total requests made today
    - top_services: List of top services with request counts
    - average_rate_limit_usage: Average rate limit usage percentage
    - gateway_status: Current gateway operational status
    """
    # Get total services
    total_services = db.query(func.count(Service.id)).scalar() or 0
    
    # Get requests today (start of today to now)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    requests_today = db.query(func.count(UsageLog.id)).filter(
        UsageLog.timestamp >= today_start
    ).scalar() or 0
    
    # Get top services (service name + request count)
    # Join Service with UsageLog, group by service, count requests, order by count DESC, limit to top 5
    top_services_query = db.query(
        Service.name,
        func.count(UsageLog.id).label('request_count')
    ).join(
        UsageLog, Service.id == UsageLog.service_id
    ).group_by(
        Service.id, Service.name
    ).order_by(
        func.count(UsageLog.id).desc()
    ).limit(5).all()
    
    top_services = [
        {"name": name, "request_count": count}
        for name, count in top_services_query
    ]
    
    # Calculate average rate limit usage
    # Rate limit: 10 requests per 60 seconds per API key
    # For each unique API key, calculate requests in last 60 seconds, then average the percentages
    sixty_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    
    # Get unique API keys
    unique_api_keys = db.query(UsageLog.api_key).distinct().all()
    unique_api_keys = [key[0] for key in unique_api_keys]
    
    if unique_api_keys:
        usage_percentages = []
        for api_key in unique_api_keys:
            # Count requests in last 60 seconds for this API key
            recent_requests = db.query(func.count(UsageLog.id)).filter(
                UsageLog.api_key == api_key,
                UsageLog.timestamp >= sixty_seconds_ago
            ).scalar() or 0
            
            # Calculate percentage (requests / limit * 100)
            usage_percentage = min((recent_requests / RATE_LIMIT_CAPACITY) * 100, 100.0)
            usage_percentages.append(usage_percentage)
        
        # Average the percentages
        average_rate_limit_usage = sum(usage_percentages) / len(usage_percentages) if usage_percentages else 0.0
    else:
        average_rate_limit_usage = 0.0
    
    # Gateway status
    gateway_status = "Operational"
    
    return {
        "total_services": total_services,
        "requests_today": requests_today,
        "top_services": top_services,
        "average_rate_limit_usage": round(average_rate_limit_usage, 2),
        "gateway_status": gateway_status
    }


class RegisterApiRequest(BaseModel):
    """Request model for registering a new API service."""
    name: str
    target_url: HttpUrl


class RegisterApiResponse(BaseModel):
    """Response model for API registration."""
    service_id: int
    gateway_url: str
    api_key: Optional[str] = None  # Only returned once during user creation


class CreateApiKeyResponse(BaseModel):
    """Response model for API key creation."""
    api_key: str
    service_id: int
    message: str = "API key created successfully. Save this key securely - it will only be shown once."


class UpdateRateLimitRequest(BaseModel):
    """Request model for updating API key rate limits."""
    requests: int
    window_seconds: int


def get_current_user(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to validate API key from X-API-Key header.
    First checks ApiKey table for active keys, then falls back to User.api_key for backward compatibility.
    Returns the authenticated user or raises HTTP 401.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header"
        )
    
    # First, check ApiKey table for active keys (new system)
    api_key_obj = db.query(ApiKey).filter(
        ApiKey.key == x_api_key,
        ApiKey.is_active == True
    ).first()
    
    if api_key_obj:
        # API key found in ApiKey table, get the user from the service owner
        service = db.query(Service).filter(Service.id == api_key_obj.service_id).first()
        if service:
            user = db.query(User).filter(User.id == service.owner_id).first()
            if user:
                return user
    
    # Fallback to User.api_key for backward compatibility (old system)
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return user


# Rate limiting using Token Bucket algorithm
# In-memory store for rate limit data (per API key)
# In production, this would be replaced with Redis for distributed rate limiting
_rate_limit_store = defaultdict(lambda: {'tokens': 10, 'last_refill': time.time()})
_rate_limit_lock = asyncio.Lock()

# Rate limit configuration: 10 requests per 60 seconds
RATE_LIMIT_CAPACITY = 10
RATE_LIMIT_REFILL_RATE = 10.0 / 60.0  # tokens per second (10 tokens per 60 seconds)
RATE_LIMIT_WINDOW = 60.0  # seconds


async def check_rate_limit(api_key: str, db: Session) -> bool:
    """
    Check if the API key has available tokens using Token Bucket algorithm.
    
    Checks for per-API-key rate limit overrides (rate_limit_requests, rate_limit_window_seconds).
    If present, uses those values. Otherwise, falls back to service-level defaults.
    
    Returns True if request is allowed, False if rate limit exceeded.
    """
    # Determine rate limit configuration (check for API key overrides)
    capacity = RATE_LIMIT_CAPACITY
    refill_rate = RATE_LIMIT_REFILL_RATE
    window = RATE_LIMIT_WINDOW
    
    # Check if this API key has custom rate limits
    api_key_obj = db.query(ApiKey).filter(
        ApiKey.key == api_key,
        ApiKey.is_active == True
    ).first()
    
    if api_key_obj and api_key_obj.rate_limit_requests is not None and api_key_obj.rate_limit_window_seconds is not None:
        # Use API key-specific rate limits
        capacity = api_key_obj.rate_limit_requests
        window = float(api_key_obj.rate_limit_window_seconds)
        refill_rate = float(capacity) / window  # tokens per second
    # Otherwise, use defaults (RATE_LIMIT_CAPACITY, RATE_LIMIT_WINDOW, RATE_LIMIT_REFILL_RATE)
    
    async with _rate_limit_lock:
        now = time.time()
        # Use a unique key that includes rate limit config to separate buckets with different limits
        bucket_key = f"{api_key}:{capacity}:{window}"
        bucket = _rate_limit_store[bucket_key]
        
        # Initialize bucket if it doesn't exist or capacity changed
        if 'capacity' not in bucket or bucket['capacity'] != capacity:
            bucket['tokens'] = float(capacity)
            bucket['last_refill'] = now
            bucket['capacity'] = capacity
            bucket['refill_rate'] = refill_rate
        
        # Calculate elapsed time since last refill
        elapsed = now - bucket['last_refill']
        
        # Refill tokens based on elapsed time (but don't exceed capacity)
        tokens_to_add = elapsed * bucket['refill_rate']
        bucket['tokens'] = min(float(capacity), bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = now
        
        # Check if we have tokens available
        if bucket['tokens'] >= 1.0:
            # Consume one token
            bucket['tokens'] -= 1.0
            return True
        else:
            # Rate limit exceeded
            return False


@app.post("/register-api", response_model=RegisterApiResponse)
async def register_api(
    request: RegisterApiRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new API service.
    
    Creates a new Service entry linked to an existing user.
    If no user exists, auto-creates a default user.
    Returns service_id, gateway_url, and api_key (only on first user creation).
    """
    # Get or create a default user
    user = db.query(User).first()
    api_key_to_return = None
    
    if not user:
        # Create a default user with a generated API key
        api_key = secrets.token_urlsafe(32)
        user = User(
            name="Default User",
            api_key=api_key
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        # Return API key only once during creation
        api_key_to_return = api_key
    
    # Create a new service
    service = Service(
        name=request.name,
        target_url=str(request.target_url),
        owner_id=user.id
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    
    # Return the response
    return RegisterApiResponse(
        service_id=service.id,
        gateway_url=f"/proxy/{service.id}",
        api_key=api_key_to_return
    )


async def proxy_request(
    service: Service,
    request: Request,
    method: str,
    api_key: str,
    db: Session,
    path_suffix: str = ""
) -> Response:
    """
    Proxy an HTTP request to the service's target_url.
    
    Forwards query parameters, request body, HTTP method, and safe headers.
    Returns status code, response body, and response headers.
    Handles timeouts gracefully.
    Injects watermarks if enabled for the service.
    
    Args:
        path_suffix: Optional path to append to the target URL
    """
    # Validate and normalize the target URL
    target_url = service.target_url.strip()
    if not target_url:
        raise HTTPException(
            status_code=500,
            detail="Service target_url is not configured"
        )
    
    # Ensure URL has a scheme
    if not target_url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=500,
            detail=f"Invalid target_url format: {target_url}. URL must start with http:// or https://"
        )
    
    # Append path suffix if provided
    if path_suffix:
        # Remove trailing slash from target_url and leading slash from path_suffix
        target_url = target_url.rstrip('/')
        path_suffix = path_suffix.lstrip('/')
        target_url = f"{target_url}/{path_suffix}"
    
    # Get safe headers (exclude host, content-length, and X-API-Key)
    excluded_headers = {'host', 'content-length', 'x-api-key', 'connection', 'transfer-encoding'}
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in excluded_headers
    }
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Get request body if present (for methods that may have body)
    body = None
    if method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        try:
            body = await request.body()
            # Only use body if it's not empty
            if not body:
                body = None
        except Exception:
            body = None
    
    # Make the proxied request with timeout
    timeout = httpx.Timeout(30.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=target_url,
                params=query_params,
                content=body,
                headers=headers,
                follow_redirects=True
            )
            
            # Build response headers (exclude some that shouldn't be forwarded)
            response_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in {'content-length', 'connection', 'transfer-encoding'}
            }
            
            # Get API key object for watermarking
            api_key_obj = db.query(ApiKey).filter(
                ApiKey.key == api_key,
                ApiKey.is_active == True
            ).first()
            
            # Log successful requests (HTTP 2xx) to UsageLog and update billing
            if 200 <= response.status_code < 300:
                try:
                    # Log usage
                    usage_log = UsageLog(
                        service_id=service.id,
                        api_key=api_key
                        # timestamp will be set automatically via server_default
                    )
                    db.add(usage_log)
                    
                    # Update billing: increment ApiKey.total_cost by ApiKey.price_per_request
                    if api_key_obj:
                        api_key_obj.total_cost += api_key_obj.price_per_request
                    
                    db.commit()
                except Exception:
                    # Don't fail the request if logging/billing update fails
                    db.rollback()
                    pass
            
            # Prepare response content (potentially with watermark)
            response_content = response.content
            content_type = response.headers.get('content-type', '')
            
            # Inject watermark if enabled for service
            if getattr(service, 'watermarking_enabled', False) and api_key_obj:
                try:
                    # Generate unique request ID and timestamp
                    request_id = str(uuid.uuid4())[:8]
                    timestamp = datetime.now(timezone.utc).isoformat()
                    
                    # Generate watermark
                    watermark = generate_watermark(
                        service_id=service.id,
                        api_key_id=api_key_obj.id,
                        request_id=request_id,
                        timestamp=timestamp
                    )
                    
                    # Inject based on content type
                    if 'application/json' in content_type:
                        try:
                            json_data = json.loads(response_content.decode('utf-8'))
                            watermarked_data = inject_watermark_json(json_data, watermark)
                            response_content = json.dumps(watermarked_data).encode('utf-8')
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            # If JSON parsing fails, treat as text
                            text_content = response_content.decode('utf-8', errors='replace')
                            watermarked_text = inject_watermark_text(text_content, watermark, content_type)
                            response_content = watermarked_text.encode('utf-8')
                    elif 'text/' in content_type or 'html' in content_type:
                        text_content = response_content.decode('utf-8', errors='replace')
                        watermarked_text = inject_watermark_text(text_content, watermark, content_type)
                        response_content = watermarked_text.encode('utf-8')
                    # For binary content types (images, etc.), don't add watermark
                except Exception as e:
                    # Don't fail the request if watermarking fails
                    logger.warning(f"Watermarking failed: {e}")
                    pass
            
            # Return response with status code, body, and headers
            return Response(
                content=response_content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get('content-type')
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Gateway timeout: The target service did not respond in time"
        )
    except httpx.ConnectError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bad gateway: Cannot connect to target service. The hostname may be invalid or unreachable. Error: {str(e)}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Bad gateway: Failed to connect to target service - {str(e)}"
        )


@app.get("/proxy/{service_id}")
@app.get("/proxy/{service_id}/{path:path}")
async def proxy_get(
    service_id: int,
    request: Request,
    path: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for GET requests.
    Protected by API key authentication and rate limiting.
    Supports optional path suffix: /proxy/{service_id}/{path}
    """
    # Extract API key from request header for rate limiting
    api_key_from_header = request.headers.get("X-API-Key", "")
    
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check rate limit using the API key from header
    if not await check_rate_limit(api_key_from_header, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    return await proxy_request(service, request, "GET", api_key_from_header, db, path)


@app.post("/proxy/{service_id}")
@app.post("/proxy/{service_id}/{path:path}")
async def proxy_post(
    service_id: int,
    request: Request,
    path: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for POST requests.
    Protected by API key authentication and rate limiting.
    Supports optional path suffix: /proxy/{service_id}/{path}
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Extract API key from request header for rate limiting
    api_key_from_header = request.headers.get("X-API-Key", "")
    
    # Check rate limit using the API key from header
    if not await check_rate_limit(api_key_from_header, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    return await proxy_request(service, request, "POST", api_key_from_header, db, path)


@app.put("/proxy/{service_id}")
@app.put("/proxy/{service_id}/{path:path}")
async def proxy_put(
    service_id: int,
    request: Request,
    path: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for PUT requests.
    Protected by API key authentication and rate limiting.
    Supports optional path suffix: /proxy/{service_id}/{path}
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Extract API key from request header for rate limiting
    api_key_from_header = request.headers.get("X-API-Key", "")
    
    # Check rate limit using the API key from header
    if not await check_rate_limit(api_key_from_header, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    return await proxy_request(service, request, "PUT", api_key_from_header, db, path)


@app.delete("/proxy/{service_id}")
@app.delete("/proxy/{service_id}/{path:path}")
async def proxy_delete(
    service_id: int,
    request: Request,
    path: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for DELETE requests.
    Protected by API key authentication and rate limiting.
    Supports optional path suffix: /proxy/{service_id}/{path}
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Extract API key from request header for rate limiting
    api_key_from_header = request.headers.get("X-API-Key", "")
    
    # Check rate limit using the API key from header
    if not await check_rate_limit(api_key_from_header, db):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )
    
    return await proxy_request(service, request, "DELETE", api_key_from_header, db, path)


@app.get("/me/api-key")
async def get_my_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Get the user's API key.
    
    This endpoint is for demo purposes only.
    Returns the API key only once. After first retrieval,
    marks it as revealed and subsequent calls return a message
    saying the key cannot be viewed again.
    
    For demo: If no API key is provided, returns the first user's
    API key if it hasn't been revealed yet.
    """
    # If API key is provided, authenticate and get that user
    if x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        # For demo: get the first user if no auth provided
        user = db.query(User).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="No user found. Please register an API first using POST /register-api"
            )
    
    # Refresh user to ensure we have the latest data
    db.refresh(user)
    
    # Check if API key has already been revealed (handle None as False)
    if user.api_key_revealed is True:
        return {
            "message": "API key cannot be viewed again. It was already revealed once."
        }
    
    # Mark as revealed and return the API key
    user.api_key_revealed = True
    db.commit()
    db.refresh(user)
    
    return {
        "api_key": user.api_key
    }


@app.get("/usage/{service_id}")
async def get_usage_stats(
    service_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics for a service.
    
    Returns total request count and request count grouped by API key.
    Protected by API key authentication.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get total request count for this service
    total_count = db.query(func.count(UsageLog.id)).filter(
        UsageLog.service_id == service_id
    ).scalar()
    
    # Get request count grouped by API key
    usage_by_api_key = db.query(
        UsageLog.api_key,
        func.count(UsageLog.id).label('count')
    ).filter(
        UsageLog.service_id == service_id
    ).group_by(UsageLog.api_key).all()
    
    # Format the grouped results
    api_key_counts = [
        {"api_key": api_key, "count": count}
        for api_key, count in usage_by_api_key
    ]
    
    return {
        "service_id": service_id,
        "total_requests": total_count or 0,
        "requests_by_api_key": api_key_counts
    }


@app.post("/services/{service_id}/keys", response_model=CreateApiKeyResponse)
async def create_service_api_key(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Create a new API key for a service.
    
    Generates a new API key, stores it as active in the ApiKey table,
    and returns it once. Existing keys remain valid and are not revoked.
    
    Control-plane endpoint - no authentication required.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Generate a unique API key
    # Keep generating until we get a unique one (should be rare collision)
    max_attempts = 10
    for attempt in range(max_attempts):
        new_api_key = secrets.token_urlsafe(32)
        
        # Check if key already exists (both in ApiKey table and User table for uniqueness)
        existing_api_key = db.query(ApiKey).filter(ApiKey.key == new_api_key).first()
        existing_user_key = db.query(User).filter(User.api_key == new_api_key).first()
        
        if not existing_api_key and not existing_user_key:
            break
        
        if attempt == max_attempts - 1:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate unique API key. Please try again."
            )
    
    # Create new ApiKey entry
    api_key_obj = ApiKey(
        key=new_api_key,
        service_id=service_id,
        is_active=True
    )
    
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)
    
    return CreateApiKeyResponse(
        api_key=new_api_key,
        service_id=service_id
    )


@app.get("/api-keys")
async def list_all_api_keys(
    db: Session = Depends(get_db)
):
    """
    List all services and their API keys.
    
    Control-plane endpoint - no authentication required.
    Returns all services with their API keys.
    """
    # Get all services (control-plane endpoint - public access)
    services = db.query(Service).all()
    
    result = []
    for service in services:
        # Get all API keys for this service
        api_keys = db.query(ApiKey).filter(ApiKey.service_id == service.id).order_by(ApiKey.created_at.desc()).all()
        
        result.append({
            "service_id": service.id,
            "service_name": service.name,
            "api_keys": [
                {
                    "id": key.id,
                    "key_masked": f"{key.key[:8]}••••{key.key[-4:]}" if len(key.key) > 12 else "••••••••",
                    "created_at": key.created_at.isoformat() if key.created_at else None,
                    "is_active": key.is_active,
                    "rate_limit_requests": key.rate_limit_requests,
                    "rate_limit_window_seconds": key.rate_limit_window_seconds
                }
                for key in api_keys
            ]
        })
    
    return {"services": result}


@app.get("/services/{service_id}/keys")
async def list_service_api_keys(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    List all API keys for a service.
    
    Returns API keys with masked values, timestamps, and status.
    Control-plane endpoint - no authentication required.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get all API keys for this service
    api_keys = db.query(ApiKey).filter(ApiKey.service_id == service_id).order_by(ApiKey.created_at.desc()).all()
    
    return {
        "service_id": service_id,
        "service_name": service.name,
        "api_keys": [
            {
                "id": key.id,
                "key_masked": f"{key.key[:8]}••••{key.key[-4:]}" if len(key.key) > 12 else "••••••••",
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "is_active": key.is_active,
                "rate_limit_requests": key.rate_limit_requests,
                "rate_limit_window_seconds": key.rate_limit_window_seconds
            }
            for key in api_keys
        ]
    }


@app.patch("/services/{service_id}/keys/{key_id}/revoke")
async def revoke_service_api_key(
    service_id: int,
    key_id: int,
    db: Session = Depends(get_db)
):
    """
    Revoke an API key for a service.
    
    Sets the API key's is_active to False, making it invalid for authentication.
    Control-plane endpoint - no authentication required.
    """
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get the API key
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.service_id == service_id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Revoke the key
    api_key.is_active = False
    db.commit()
    db.refresh(api_key)
    
    return {
        "message": "API key revoked successfully",
        "key_id": key_id,
        "service_id": service_id
    }


@app.put("/api-keys/{key_id}/rate-limit")
async def update_api_key_rate_limit(
    key_id: int,
    request: UpdateRateLimitRequest,
    db: Session = Depends(get_db)
):
    """
    Update rate limits for a specific API key.
    
    Sets rate_limit_requests and rate_limit_window_seconds on the ApiKey model.
    Changes take effect immediately for subsequent requests.
    Control-plane endpoint - no authentication required.
    """
    # Validate input
    if request.requests <= 0:
        raise HTTPException(status_code=400, detail="requests must be greater than 0")
    if request.window_seconds <= 0:
        raise HTTPException(status_code=400, detail="window_seconds must be greater than 0")
    
    # Get the API key
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Update rate limit settings
    api_key.rate_limit_requests = request.requests
    api_key.rate_limit_window_seconds = request.window_seconds
    
    db.commit()
    db.refresh(api_key)
    
    return {
        "message": "Rate limit updated successfully",
        "key_id": key_id,
        "rate_limit_requests": api_key.rate_limit_requests,
        "rate_limit_window_seconds": api_key.rate_limit_window_seconds
    }


class UpdatePricingRequest(BaseModel):
    """Request model for updating API key pricing."""
    price_per_request: float


@app.put("/api-keys/{key_id}/pricing")
async def update_api_key_pricing(
    key_id: int,
    request: UpdatePricingRequest,
    db: Session = Depends(get_db)
):
    """
    Update price_per_request for a specific API key.
    
    Updates the price per request for billing calculations.
    Control-plane endpoint - no authentication required.
    """
    print(f"PUT /api-keys/{key_id}/pricing endpoint hit with price_per_request={request.price_per_request}")
    logger.info(f"PUT /api-keys/{key_id}/pricing called with price_per_request={request.price_per_request}")
    
    # Validate price_per_request > 0
    if request.price_per_request <= 0:
        error_msg = f"Invalid price_per_request: {request.price_per_request} (must be > 0)"
        print(f"ERROR: {error_msg}")
        logger.warning(error_msg)
        raise HTTPException(
            status_code=400,
            detail="price_per_request must be greater than 0"
        )
    
    # Get the API key
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    
    if not api_key:
        error_msg = f"API key not found: key_id={key_id}"
        print(f"ERROR: {error_msg}")
        logger.warning(error_msg)
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Update price_per_request
    old_price = api_key.price_per_request
    api_key.price_per_request = request.price_per_request
    
    db.commit()
    db.refresh(api_key)
    
    success_msg = f"Updated price_per_request for key_id={key_id}: {old_price} -> {api_key.price_per_request}"
    print(f"SUCCESS: {success_msg}")
    logger.info(success_msg)
    
    # Return updated ApiKey
    return {
        "id": api_key.id,
        "key": f"{api_key.key[:8]}••••{api_key.key[-4:]}" if len(api_key.key) > 12 else "••••••••",
        "service_id": api_key.service_id,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "rate_limit_requests": api_key.rate_limit_requests,
        "rate_limit_window_seconds": api_key.rate_limit_window_seconds,
        "price_per_request": float(api_key.price_per_request),
        "total_cost": float(api_key.total_cost)
    }


@app.get("/billing/summary")
async def get_billing_summary(db: Session = Depends(get_db)):
    """
    Get billing summary overview.
    
    Returns aggregated billing metrics:
    - total_requests: Total number of requests across all API keys
    - total_cost: Total accumulated cost across all API keys
    - cost_this_month: Current billing cycle cost (same as total_cost for now)
    
    Control-plane endpoint - no authentication required.
    """
    # Get all API keys
    api_keys = db.query(ApiKey).all()
    
    total_requests = 0
    total_cost = 0.0
    
    for api_key in api_keys:
        # Count usage log entries for this API key
        requests_used = db.query(func.count(UsageLog.id)).filter(
            UsageLog.api_key == api_key.key
        ).scalar() or 0
        
        total_requests += requests_used
        total_cost += float(api_key.total_cost)
    
    # Cost this month is the same as total_cost for now (manual reset cycles)
    cost_this_month = total_cost
    
    return {
        "total_requests": total_requests,
        "total_cost": total_cost,
        "cost_this_month": cost_this_month
    }


@app.get("/billing/api-keys")
async def get_billing_api_keys(db: Session = Depends(get_db)):
    """
    Get billing information for all API keys.
    
    Returns billing data including requests used, price per request, and total cost.
    Control-plane endpoint - no authentication required.
    """
    # Query all API keys
    api_keys = db.query(ApiKey).all()
    
    result = []
    for api_key in api_keys:
        # Get service name
        service = db.query(Service).filter(Service.id == api_key.service_id).first()
        service_name = service.name if service else "Unknown"
        
        # Count usage log entries for this API key
        requests_used = db.query(func.count(UsageLog.id)).filter(
            UsageLog.api_key == api_key.key
        ).scalar() or 0
        
        result.append({
            "api_key_id": api_key.id,
            "service_name": service_name,
            "requests_used": requests_used,
            "price_per_request": float(api_key.price_per_request),
            "total_cost": float(api_key.total_cost)
        })
    
    return {"api_keys": result}


@app.put("/billing/api-keys/{key_id}/price")
async def update_api_key_price(
    key_id: int,
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Update price_per_request for a specific API key.
    
    Control-plane endpoint - no authentication required.
    """
    price_per_request = request.get("price_per_request")
    
    if price_per_request is None:
        raise HTTPException(status_code=400, detail="price_per_request is required")
    
    # Validate price > 0
    try:
        price = float(price_per_request)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="price_per_request must be a valid number")
    
    if price <= 0:
        raise HTTPException(status_code=400, detail="price_per_request must be greater than 0")
    
    # Validate max 3 decimal places
    decimal_places = len(str(price).split('.')[-1]) if '.' in str(price) else 0
    if decimal_places > 3:
        raise HTTPException(status_code=400, detail="price_per_request must have at most 3 decimal places")
    
    # Get the API key
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Update price_per_request
    api_key.price_per_request = price
    
    db.commit()
    db.refresh(api_key)
    
    return {
        "message": "Price per request updated successfully",
        "key_id": key_id,
        "price_per_request": float(api_key.price_per_request)
    }


@app.post("/billing/reset")
async def reset_billing(db: Session = Depends(get_db)):
    """
    Reset total_cost to 0 for all API keys.
    
    This starts a new billing cycle by clearing accumulated costs.
    Control-plane endpoint - no authentication required.
    """
    # Get all API keys
    api_keys = db.query(ApiKey).all()
    
    # Reset total_cost for all API keys
    for api_key in api_keys:
        api_key.total_cost = 0.0
    
    db.commit()
    
    return {
        "message": "Billing cycle reset successfully. All API key costs have been cleared.",
        "reset_count": len(api_keys)
    }


# ============================================================================
# Watermarking Endpoints
# ============================================================================

class WatermarkingToggleRequest(BaseModel):
    """Request model for toggling watermarking."""
    enabled: bool


class WatermarkVerifyRequest(BaseModel):
    """Request model for verifying watermarked data."""
    data: str  # The leaked data (JSON string or text)


@app.post("/services/{service_id}/watermarking")
async def toggle_watermarking(
    service_id: int,
    request: WatermarkingToggleRequest,
    db: Session = Depends(get_db)
):
    """
    Enable or disable watermarking for a service.
    
    When enabled, all API responses will be watermarked with:
    - service_id
    - api_key_id
    - request_id
    - timestamp
    
    Control-plane endpoint - no authentication required.
    """
    # Get the service
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Update watermarking status
    service.watermarking_enabled = request.enabled
    db.commit()
    db.refresh(service)
    
    status = "enabled" if request.enabled else "disabled"
    return {
        "message": f"Watermarking {status} for service {service.name}",
        "service_id": service_id,
        "service_name": service.name,
        "watermarking_enabled": service.watermarking_enabled
    }


@app.get("/services/{service_id}/watermarking")
async def get_watermarking_status(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current watermarking status for a service.
    
    Control-plane endpoint - no authentication required.
    """
    # Get the service
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {
        "service_id": service_id,
        "service_name": service.name,
        "watermarking_enabled": getattr(service, 'watermarking_enabled', False)
    }


@app.post("/watermark/verify")
async def verify_watermark(
    request: WatermarkVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify and extract watermark from leaked data.
    
    Accepts JSON string or text content and attempts to extract the watermark.
    Returns the decoded watermark metadata including:
    - service_id and service_name
    - api_key_id and masked key
    - request_id
    - timestamp
    
    Control-plane endpoint - no authentication required.
    """
    data = request.data.strip()
    watermark = None
    
    # Try to extract watermark from JSON
    try:
        json_data = json.loads(data)
        watermark = extract_watermark_from_json(json_data)
    except json.JSONDecodeError:
        pass
    
    # If not found in JSON, try text extraction
    if not watermark:
        watermark = extract_watermark_from_text(data)
    
    if not watermark:
        raise HTTPException(
            status_code=404,
            detail="No watermark found in the provided data. The data may not be watermarked or the watermark may have been removed."
        )
    
    # Decode the watermark
    decoded = decode_watermark(watermark)
    
    if not decoded:
        raise HTTPException(
            status_code=400,
            detail="Invalid watermark format. The watermark appears to be corrupted or tampered with."
        )
    
    # Enrich with additional context from database
    service = db.query(Service).filter(Service.id == decoded["service_id"]).first()
    api_key_obj = db.query(ApiKey).filter(ApiKey.id == decoded["api_key_id"]).first()
    
    service_name = service.name if service else "Unknown (deleted)"
    
    # Mask the API key for security
    key_masked = "Unknown (deleted)"
    if api_key_obj:
        key_masked = api_key_obj.key[:8] + "..." + api_key_obj.key[-4:] if len(api_key_obj.key) > 12 else "***"
    
    return {
        "watermark_found": True,
        "raw_watermark": watermark,
        "decoded": {
            "service_id": decoded["service_id"],
            "service_name": service_name,
            "api_key_id": decoded["api_key_id"],
            "api_key_masked": key_masked,
            "request_id": decoded["request_id"],
            "timestamp": decoded["timestamp"]
        },
        "attribution": f"This data was accessed via API key ID {decoded['api_key_id']} on service '{service_name}' at {decoded['timestamp']}"
    }


@app.get("/services/list")
async def list_services(db: Session = Depends(get_db)):
    """
    List all registered services with their watermarking status.
    
    Control-plane endpoint - no authentication required.
    """
    services = db.query(Service).all()
    
    result = []
    for service in services:
        result.append({
            "id": service.id,
            "name": service.name,
            "target_url": service.target_url,
            "watermarking_enabled": getattr(service, 'watermarking_enabled', False)
        })
    
    return {"services": result}
