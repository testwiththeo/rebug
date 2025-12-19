from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.models.user import User
from app.services.auth import AuthService
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from API key in Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include 'Authorization: Bearer rbg_...' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raw_key = credentials.credentials
    if not raw_key.startswith("rbg_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Key must start with 'rbg_'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    user = await auth_service.validate_api_key(raw_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Store user in request state for later access
    request.state.user = user
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract user from API key if present, but don't require it."""
    if not credentials:
        return None

    raw_key = credentials.credentials
    if not raw_key.startswith("rbg_"):
        return None

    auth_service = AuthService(db)
    user = await auth_service.validate_api_key(raw_key)

    if user:
        request.state.user = user

    return user
