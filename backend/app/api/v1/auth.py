from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    UserCreate,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user account."""
    auth_service = AuthService(db)

    # Check if user already exists
    existing = await auth_service.get_user_by_email(user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_in.email} already exists.",
        )

    user = await auth_service.create_user(email=user_in.email, name=user_in.name)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user info."""
    return UserResponse.model_validate(current_user)


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    key_in: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """Create a new API key for the current user."""
    auth_service = AuthService(db)
    api_key, raw_key = await auth_service.create_api_key(
        user_id=current_user.id,
        name=key_in.name,
    )
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    """List all API keys for the current user."""
    auth_service = AuthService(db)
    keys = await auth_service.list_api_keys(current_user.id)
    return ApiKeyListResponse(keys=[ApiKeyResponse.model_validate(k) for k in keys])


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke (deactivate) an API key."""
    auth_service = AuthService(db)
    revoked = await auth_service.revoke_api_key(user_id=current_user.id, key_id=key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    await db.commit()
