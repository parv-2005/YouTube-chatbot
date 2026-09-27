"""
Security Module
===============
Handles two critical security concerns:

1. Password Hashing
   - Uses bcrypt directly to hash passwords before storage
   - bcrypt is deliberately slow, making brute-force attacks impractical
   - Never stores or compares plaintext passwords

2. JWT Token Management
   - Creates signed tokens after successful login
   - Verifies tokens on protected routes
   - Tokens expire after a configurable duration
   - The secret key MUST be changed in production
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt

from app.core.config import settings


# ── Password Hashing ────────────────────────────────────────
# Using bcrypt directly (passlib is unmaintained and incompatible
# with bcrypt>=4.1). bcrypt handles:
# - Automatic salt generation
# - Configurable work factor (rounds=12 by default)
# - Transparent hash verification


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    The result includes the salt, so each hash is unique
    even for the same password.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Returns True if they match, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT Tokens ───────────────────────────────────────────────

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    The token contains:
    - 'sub': the user identifier (typically user ID)
    - 'exp': expiration timestamp
    - Any additional claims passed in 'data'

    The token is signed with our secret key using HS256.
    Anyone can DECODE the payload, but only our server
    can VERIFY the signature.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_EXPIRATION_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_access_token(token: str) -> Optional[str]:
    """
    Verify a JWT token and extract the user ID.

    Returns the user ID (from 'sub' claim) if valid.
    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        return user_id

    except JWTError:
        return None
