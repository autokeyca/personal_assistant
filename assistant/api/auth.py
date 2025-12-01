"""Authentication middleware for Jarvis API."""

import hashlib
import secrets
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from assistant.db import get_session, APIKey

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new random API key."""
    return secrets.token_urlsafe(32)


async def verify_api_key(api_key: str = Security(api_key_header)) -> APIKey:
    """
    Verify API key and return the associated key object.

    Args:
        api_key: API key from request header

    Returns:
        APIKey object if valid

    Raises:
        HTTPException: If key is invalid or inactive
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing"
        )

    # Hash the provided key
    key_hash = hash_api_key(api_key)

    # Look up in database
    with get_session() as session:
        api_key_obj = session.query(APIKey).filter_by(key=key_hash).first()

        if not api_key_obj:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

        if not api_key_obj.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key has been deactivated"
            )

        # Update usage stats
        api_key_obj.last_used = datetime.utcnow()
        api_key_obj.usage_count += 1
        session.commit()

        # Detach from session
        session.expunge(api_key_obj)

        return api_key_obj


def check_permission(api_key: APIKey, required_permission: str) -> bool:
    """
    Check if API key has required permission.

    Args:
        api_key: APIKey object
        required_permission: Permission string (e.g., "message:send", "task:create")

    Returns:
        True if permission granted
    """
    # "*" means all permissions
    if api_key.permissions == "*":
        return True

    # Check if specific permission is in the list
    permissions = api_key.permissions.split(",")
    return required_permission in permissions or "*" in permissions
