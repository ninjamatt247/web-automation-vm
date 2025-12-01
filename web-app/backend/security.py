#!/usr/bin/env python3
"""
Security utilities for voice assistant endpoints
"""

import os
import time
import hashlib
import logging
from typing import Dict, Optional
from datetime import datetime
from collections import defaultdict
from fastapi import HTTPException, Header, Request
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_assistant_audit.log'),
        logging.StreamHandler()
    ]
)

audit_logger = logging.getLogger('voice_assistant_audit')

# Rate limiting storage (in-memory, for production use Redis)
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: Dict[str, list] = defaultdict(list)
        self.hour_buckets: Dict[str, list] = defaultdict(list)

    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limits"""
        now = time.time()

        # Clean old entries
        minute_ago = now - 60
        hour_ago = now - 3600

        self.minute_buckets[client_id] = [
            t for t in self.minute_buckets[client_id] if t > minute_ago
        ]
        self.hour_buckets[client_id] = [
            t for t in self.hour_buckets[client_id] if t > hour_ago
        ]

        # Check limits
        if len(self.minute_buckets[client_id]) >= self.requests_per_minute:
            return False

        if len(self.hour_buckets[client_id]) >= self.requests_per_hour:
            return False

        # Record this request
        self.minute_buckets[client_id].append(now)
        self.hour_buckets[client_id].append(now)

        return True

    def get_remaining_requests(self, client_id: str) -> Dict[str, int]:
        """Get remaining requests for client"""
        minute_remaining = self.requests_per_minute - len(self.minute_buckets[client_id])
        hour_remaining = self.requests_per_hour - len(self.hour_buckets[client_id])

        return {
            "minute": max(0, minute_remaining),
            "hour": max(0, hour_remaining)
        }

# Global rate limiter instance
rate_limiter = RateLimiter()

def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key for voice assistant endpoints"""
    # In development, allow requests without API key
    if os.getenv('ENVIRONMENT', 'development') == 'development':
        return 'development-client'

    # In production, require API key
    expected_key = os.getenv('VOICE_ASSISTANT_API_KEY')
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="Voice assistant API key not configured"
        )

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header"
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    # Hash the API key for client identification (don't log the actual key)
    return hashlib.sha256(x_api_key.encode()).hexdigest()[:16]

def check_rate_limit(client_id: str):
    """Check rate limit for client"""
    if not rate_limiter.check_rate_limit(client_id):
        remaining = rate_limiter.get_remaining_requests(client_id)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again later. Remaining: {remaining['minute']}/min, {remaining['hour']}/hour"
        )

def audit_log(
    action: str,
    client_id: str,
    patient_name: Optional[str] = None,
    details: Optional[Dict] = None,
    success: bool = True
):
    """Log voice assistant actions for audit trail"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "client_id": client_id,
        "patient_name": patient_name,
        "success": success,
        "details": details or {}
    }

    if success:
        audit_logger.info(f"AUDIT: {log_entry}")
    else:
        audit_logger.warning(f"AUDIT_FAILED: {log_entry}")

async def voice_security_middleware(
    request: Request,
    x_api_key: Optional[str] = Header(None)
) -> str:
    """
    Combined security middleware for voice endpoints
    - Verifies API key
    - Checks rate limits
    - Returns client ID for audit logging
    """
    # Verify API key and get client ID
    client_id = verify_api_key(x_api_key)

    # Check rate limits
    check_rate_limit(client_id)

    return client_id

def sanitize_for_voice(text: str, max_length: int = 500) -> str:
    """
    Sanitize text for voice response
    - Remove PHI (Protected Health Information)
    - Limit length for voice
    - Remove special characters
    """
    # Truncate long text
    if len(text) > max_length:
        text = text[:max_length] + "..."

    # Remove potentially sensitive patterns (very basic)
    # In production, use more sophisticated PHI detection
    import re

    # Remove patterns that look like SSN
    text = re.sub(r'\d{3}-\d{2}-\d{4}', '[REDACTED]', text)

    # Remove patterns that look like credit cards
    text = re.sub(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}', '[REDACTED]', text)

    # Remove email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

    # Remove phone numbers
    text = re.sub(r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', '[PHONE]', text)

    return text
