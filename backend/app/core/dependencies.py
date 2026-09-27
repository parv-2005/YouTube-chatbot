"""
FastAPI Dependencies
====================
Dependencies are reusable functions that FastAPI injects
into route handlers. They handle cross-cutting concerns:

1. get_db()         → Provides a database session, auto-closes after request
2. get_current_user → Extracts and validates JWT, returns the User object

Using Depends() keeps route handlers clean and focused
on business logic instead of boilerplate.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import verify_access_token
from app.database.session import SessionLocal
from app.database import models


# OAuth2PasswordBearer tells FastAPI where to find the token.
# It looks for "Authorization: Bearer <token>" header.
# The tokenUrl is used by Swagger UI to know the login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_db():
    """
    Database session dependency.

    Creates a new SQLAlchemy session for each request.
    The 'yield' keyword means:
    - Before yield: session is created and given to the route handler
    - After yield: session is closed (even if an error occurred)

    This pattern is called a "context manager dependency".
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Authentication dependency.

    Flow:
    1. Extract JWT from Authorization header (via oauth2_scheme)
    2. Verify and decode the token
    3. Look up the user in the database
    4. Return the User object

    If any step fails, raise 401 Unauthorized.

    Usage in routes:
        @router.get("/protected")
        def protected_route(user: models.User = Depends(get_current_user)):
            return {"email": user.email}
    """
    # Step 1: Verify the token signature and expiration
    user_id = verify_access_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 2: Look up the user in the database
    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
