"""
Bot detection module for identifying automated traffic.

Uses request signals to classify traffic as human, suspicious, or bot:
- User-Agent analysis
- Request rate tracking
- Header entropy analysis
"""
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Tuple
import re

# Common bot User-Agent patterns
BOT_USER_AGENT_PATTERNS = [
    r'bot',
    r'crawler',
    r'spider',
    r'scraper',
    r'curl',
    r'wget',
    r'python-requests',
    r'python-urllib',
    r'scrapy',
    r'headless',
    r'phantomjs',
    r'selenium',
    r'puppeteer',
    r'playwright',
    r'axios',
    r'go-http-client',
    r'java',
    r'okhttp',
    r'apache-httpclient',
]

# Expected browser headers
EXPECTED_BROWSER_HEADERS = [
    'accept',
    'accept-language',
    'accept-encoding',
    'user-agent',
    'referer',
]


def analyze_user_agent(user_agent: str) -> float:
    """
    Analyze User-Agent string for bot patterns.
    
    Returns a score from 0.0 (human) to 1.0 (bot).
    """
    if not user_agent:
        return 0.8  # Missing User-Agent is suspicious
    
    user_agent_lower = user_agent.lower()
    
    # Check for bot patterns
    for pattern in BOT_USER_AGENT_PATTERNS:
        if re.search(pattern, user_agent_lower):
            return 0.9  # Strong bot indicator
    
    # Check for very short User-Agent (likely custom/bot)
    if len(user_agent) < 20:
        return 0.7
    
    # Check for common browsers
    browser_patterns = [
        r'mozilla',
        r'chrome',
        r'safari',
        r'firefox',
        r'edge',
        r'opera',
    ]
    
    has_browser_pattern = any(re.search(p, user_agent_lower) for p in browser_patterns)
    if has_browser_pattern:
        return 0.1  # Likely human
    
    return 0.5  # Unknown/neutral


def analyze_request_rate(api_key: str, db: Session) -> float:
    """
    Analyze request rate for the API key.
    
    Returns a score from 0.0 (normal) to 1.0 (suspicious).
    """
    from app.models import UsageLog
    
    # Check requests in last 60 seconds
    sixty_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    
    recent_requests = db.query(func.count(UsageLog.id)).filter(
        UsageLog.api_key == api_key,
        UsageLog.timestamp >= sixty_seconds_ago
    ).scalar() or 0
    
    # Score based on request frequency
    # 0-5 requests: normal (0.0)
    # 6-10 requests: moderate (0.3)
    # 11-20 requests: suspicious (0.6)
    # 20+ requests: very suspicious (0.9)
    
    if recent_requests <= 5:
        return 0.0
    elif recent_requests <= 10:
        return 0.3
    elif recent_requests <= 20:
        return 0.6
    else:
        return 0.9


def analyze_header_entropy(request: Request) -> float:
    """
    Analyze HTTP headers for completeness and patterns.
    
    Returns a score from 0.0 (complete headers) to 1.0 (minimal headers).
    """
    headers = dict(request.headers)
    header_keys = [key.lower() for key in headers.keys()]
    
    # Count how many expected browser headers are present
    present_headers = sum(1 for h in EXPECTED_BROWSER_HEADERS if h in header_keys)
    
    # Calculate completeness score
    completeness = present_headers / len(EXPECTED_BROWSER_HEADERS)
    
    # Invert: high completeness = low bot score
    entropy_score = 1.0 - completeness
    
    # Bonus penalty if very few headers
    if len(header_keys) < 5:
        entropy_score = min(1.0, entropy_score + 0.3)
    
    return entropy_score


def calculate_bot_score(request: Request, api_key: str, db: Session) -> float:
    """
    Calculate overall bot score based on multiple signals.
    
    Returns a score from 0.0 (definitely human) to 1.0 (definitely bot).
    """
    user_agent = request.headers.get('user-agent', '')
    
    # Get individual scores
    ua_score = analyze_user_agent(user_agent)
    rate_score = analyze_request_rate(api_key, db)
    header_score = analyze_header_entropy(request)
    
    # Weighted average (User-Agent is most important)
    bot_score = (
        ua_score * 0.5 +      # 50% weight on User-Agent
        rate_score * 0.3 +    # 30% weight on request rate
        header_score * 0.2    # 20% weight on header entropy
    )
    
    return min(1.0, max(0.0, bot_score))


def classify_traffic(bot_score: float) -> str:
    """
    Classify traffic based on bot score.
    
    Returns: 'human', 'suspicious', or 'bot'
    """
    if bot_score < 0.3:
        return 'human'
    elif bot_score < 0.7:
        return 'suspicious'
    else:
        return 'bot'


def should_block(bot_score: float, block_enabled: bool, threshold: float = 0.7) -> Tuple[bool, str]:
    """
    Determine if request should be blocked based on bot score and configuration.
    
    Args:
        bot_score: The calculated bot score (0.0-1.0)
        block_enabled: Whether bot blocking is enabled for this service
        threshold: Bot score threshold for blocking (default 0.7)
    
    Returns:
        Tuple of (should_block: bool, action_taken: str)
    """
    classification = classify_traffic(bot_score)
    
    if not block_enabled:
        # Blocking disabled, just flag
        if classification == 'bot':
            return False, 'flagged'
        else:
            return False, 'allowed'
    
    # Blocking enabled
    if bot_score >= threshold:
        return True, 'blocked'
    elif classification == 'suspicious':
        return False, 'flagged'
    else:
        return False, 'allowed'
