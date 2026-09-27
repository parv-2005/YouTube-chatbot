"""
Authentication API
==================
Endpoints for user registration, login, and profile.

Security measures:
- Passwords are hashed with bcrypt before storage
- JWT tokens expire after a configurable duration
- Rate limiting prevents brute-force login attempts
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.database.models import User
from app.schemas.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services.cache_service import check_rate_limit
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Validates email format and password length (Pydantic)
    - Checks for duplicate emails
    - Hashes the password with bcrypt
    - Returns the created user (without password)
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create user with hashed password
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("user_registered", email=data.email)

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    data: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Login and receive a JWT access token.

    - Rate-limited to prevent brute-force attacks
    - Verifies email exists and password matches
    - Returns a signed JWT token
    """
    # Rate limit login attempts by IP address
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"login:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Find user by email
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        # Intentionally vague error to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create JWT token with user ID as the subject
    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info("user_logged_in", email=data.email)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's profile.
    Requires a valid JWT token in the Authorization header.
    """
    return current_user
