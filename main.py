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
from app.models import User, Service, UsageLog, ApiKey, RequestHash, MerkleRoot
import httpx
import secrets
import time
from collections import defaultdict
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import hashlib
import os

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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


# Merkle tree configuration
MERKLE_BATCH_SIZE = int(os.getenv("MERKLE_BATCH_SIZE", "10"))


def compute_request_hash(
    service_id: int,
    api_key_id: int,
    timestamp: datetime,
    request_path: str,
    response_status: int
) -> str:
    """
    Compute SHA-256 hash of API request for cryptographic transparency.
    
    Hash input format: service_id|api_key_id|timestamp_iso|request_path|response_status
    
    Args:
        service_id: ID of the service
        api_key_id: ID of the API key used
        timestamp: Request timestamp
        request_path: Request path (e.g., "/api/users")
        response_status: HTTP response status code
    
    Returns:
        64-character hexadecimal SHA-256 hash
    """
    # Format: service_id|api_key_id|timestamp_iso|request_path|response_status
    data = f"{service_id}|{api_key_id}|{timestamp.isoformat()}|{request_path}|{response_status}"
    return hashlib.sha256(data.encode()).hexdigest()


def build_merkle_tree(hashes: List[str]) -> str:
    """
    Build Merkle tree from list of hashes and return root hash.
    
    Uses binary Merkle tree construction:
    - Leaf nodes: Individual hashes
    - Parent nodes: SHA-256(left_hash + right_hash)
    - Odd number handling: Duplicate last hash
    
    Args:
        hashes: List of SHA-256 hashes (hex strings)
    
    Returns:
        Root hash of the Merkle tree (64-character hex string)
        Empty string if input is empty
    """
    if len(hashes) == 0:
        return ""
    if len(hashes) == 1:
        return hashes[0]
    
    # Build tree level by level
    current_level = hashes[:]
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            # If odd number, duplicate last hash
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            # Combine and hash
            parent = hashlib.sha256((left + right).encode()).hexdigest()
            next_level.append(parent)
        current_level = next_level
    
    return current_level[0]


def compute_and_store_merkle_root(db: Session) -> Optional[int]:
    """
    Compute Merkle root for unbatched request hashes and store it.
    
    Fetches the last MERKLE_BATCH_SIZE unbatched hashes, computes the Merkle root,
    stores it in merkle_roots table, and updates the hashes with the batch ID.
    
    Args:
        db: Database session
    
    Returns:
        ID of the created MerkleRoot record, or None if no unbatched hashes
    """
    # Fetch unbatched hashes (oldest first)
    unbatched_hashes = db.query(RequestHash).filter(
        RequestHash.merkle_batch_id == None
    ).order_by(RequestHash.timestamp.asc()).limit(MERKLE_BATCH_SIZE).all()
    
    if len(unbatched_hashes) < MERKLE_BATCH_SIZE:
        # Not enough hashes to create a batch yet
        return None
    
    # Extract hash values
    hash_values = [h.hash for h in unbatched_hashes]
    
    # Compute Merkle root
    merkle_root = build_merkle_tree(hash_values)
    
    # Get time range
    start_time = unbatched_hashes[0].timestamp
    end_time = unbatched_hashes[-1].timestamp
    
    # Create MerkleRoot record
    merkle_root_record = MerkleRoot(
        merkle_root=merkle_root,
        start_time=start_time,
        end_time=end_time,
        request_count=len(unbatched_hashes)
    )
    db.add(merkle_root_record)
    db.flush()  # Get the ID without committing
    
    # Update hashes with batch ID
    for hash_record in unbatched_hashes:
        hash_record.merkle_batch_id = merkle_root_record.id
    
    db.commit()
    db.refresh(merkle_root_record)
    
    logger.info(f"Computed Merkle root: batch_id={merkle_root_record.id}, root={merkle_root[:16]}..., count={len(unbatched_hashes)}")
    
    return merkle_root_record.id


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
    db: Session
) -> Response:
    """
    Proxy an HTTP request to the service's target_url.
    
    Forwards query parameters, request body, HTTP method, and safe headers.
    Returns status code, response body, and response headers.
    Handles timeouts gracefully.
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
            
            # Store request hash for cryptographic transparency
            try:
                # Get API key ID
                api_key_obj = db.query(ApiKey).filter(
                    ApiKey.key == api_key,
                    ApiKey.is_active == True
                ).first()
                
                if api_key_obj:
                    # Extract request path from the original request
                    request_path = str(request.url.path)
                    
                    # Compute hash
                    request_timestamp = datetime.now(timezone.utc)
                    request_hash = compute_request_hash(
                        service_id=service.id,
                        api_key_id=api_key_obj.id,
                        timestamp=request_timestamp,
                        request_path=request_path,
                        response_status=response.status_code
                    )
                    
                    # Store hash
                    hash_record = RequestHash(
                        service_id=service.id,
                        api_key_id=api_key_obj.id,
                        timestamp=request_timestamp,
                        request_path=request_path,
                        response_status=response.status_code,
                        hash=request_hash,
                        merkle_batch_id=None  # Will be set when batched
                    )
                    db.add(hash_record)
                    db.commit()
                    
                    logger.debug(f"Stored request hash: service_id={service.id}, hash={request_hash[:16]}...")
                    
                    # Try to compute Merkle root if we have enough unbatched hashes
                    try:
                        compute_and_store_merkle_root(db)
                    except Exception as e:
                        logger.warning(f"Failed to compute Merkle root: {e}")
                        # Don't fail the request if Merkle computation fails
                        pass
            except Exception as e:
                logger.warning(f"Failed to store request hash: {e}")
                # Don't fail the request if hash storage fails
                db.rollback()
                pass
            
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
                    api_key_obj = db.query(ApiKey).filter(
                        ApiKey.key == api_key,
                        ApiKey.is_active == True
                    ).first()
                    
                    if api_key_obj:
                        api_key_obj.total_cost += api_key_obj.price_per_request
                    
                    db.commit()
                except Exception:
                    # Don't fail the request if logging/billing update fails
                    db.rollback()
                    pass
            
            # Return response with status code, body, and headers
            return Response(
                content=response.content,
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
async def proxy_get(
    service_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for GET requests.
    Protected by API key authentication and rate limiting.
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
    
    return await proxy_request(service, request, "GET", api_key_from_header, db)


@app.post("/proxy/{service_id}")
async def proxy_post(
    service_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for POST requests.
    Protected by API key authentication and rate limiting.
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
    
    return await proxy_request(service, request, "POST", api_key_from_header, db)


@app.put("/proxy/{service_id}")
async def proxy_put(
    service_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for PUT requests.
    Protected by API key authentication and rate limiting.
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
    
    return await proxy_request(service, request, "PUT", api_key_from_header, db)


@app.delete("/proxy/{service_id}")
async def proxy_delete(
    service_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxy endpoint for DELETE requests.
    Protected by API key authentication and rate limiting.
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
    
    return await proxy_request(service, request, "DELETE", api_key_from_header, db)


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
# Transparency / Merkle Root Endpoints
# ============================================================================

@app.get("/transparency/merkle-latest")
async def get_latest_merkle_root(db: Session = Depends(get_db)):
    """
    Get the latest computed Merkle root.
    
    Returns the most recent Merkle root with metadata including time range
    and request count.
    
    Returns:
        Latest Merkle root data or 404 if no roots computed yet
    """
    # Get the latest Merkle root (highest ID)
    latest_root = db.query(MerkleRoot).order_by(MerkleRoot.id.desc()).first()
    
    if not latest_root:
        raise HTTPException(
            status_code=404,
            detail="No Merkle roots computed yet. Make requests through the gateway to generate roots."
        )
    
    return {
        "batch_id": latest_root.id,
        "merkle_root": latest_root.merkle_root,
        "start_time": latest_root.start_time.isoformat(),
        "end_time": latest_root.end_time.isoformat(),
        "request_count": latest_root.request_count,
        "created_at": latest_root.created_at.isoformat()
    }


@app.get("/transparency/merkle-history")
async def get_merkle_history(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get historical Merkle roots with pagination.
    
    Args:
        limit: Maximum number of roots to return (default: 50, max: 100)
        offset: Number of roots to skip (default: 0)
    
    Returns:
        List of Merkle roots with pagination metadata
    """
    # Validate and cap limit
    if limit < 1:
        limit = 50
    if limit > 100:
        limit = 100
    
    if offset < 0:
        offset = 0
    
    # Get total count
    total = db.query(func.count(MerkleRoot.id)).scalar() or 0
    
    # Get paginated roots (newest first)
    roots = db.query(MerkleRoot).order_by(
        MerkleRoot.id.desc()
    ).limit(limit).offset(offset).all()
    
    return {
        "merkle_roots": [
            {
                "batch_id": root.id,
                "merkle_root": root.merkle_root,
                "start_time": root.start_time.isoformat(),
                "end_time": root.end_time.isoformat(),
                "request_count": root.request_count,
                "created_at": root.created_at.isoformat()
            }
            for root in roots
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.get("/transparency/verify/{batch_id}")
async def verify_merkle_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all hashes in a Merkle batch for client-side verification.
    
    Returns the list of hashes that were used to compute the Merkle root,
    allowing clients to independently verify the computation.
    
    Args:
        batch_id: ID of the Merkle batch to verify
    
    Returns:
        Batch hashes and expected root for verification
    """
    # Get the Merkle root record
    merkle_root = db.query(MerkleRoot).filter(MerkleRoot.id == batch_id).first()
    
    if not merkle_root:
        raise HTTPException(
            status_code=404,
            detail=f"Merkle batch {batch_id} not found"
        )
    
    # Get all hashes in this batch (ordered by timestamp)
    hashes = db.query(RequestHash).filter(
        RequestHash.merkle_batch_id == batch_id
    ).order_by(RequestHash.timestamp.asc()).all()
    
    return {
        "batch_id": batch_id,
        "hashes": [h.hash for h in hashes],
        "expected_root": merkle_root.merkle_root,
        "request_count": len(hashes),
        "start_time": merkle_root.start_time.isoformat(),
        "end_time": merkle_root.end_time.isoformat()
    }

