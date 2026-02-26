"""API dependencies."""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TelegramInitData, decode_access_token, verify_telegram_init_data
from app.db.models import User, UserRole
from app.db.session import get_db
from app.services.user_service import UserService

security = HTTPBearer(auto_error=False)


async def get_current_user_from_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get current user from JWT token (optional)."""
    if not credentials:
        return None

    token_data = decode_access_token(credentials.credentials)
    if not token_data:
        return None

    user_service = UserService(db)
    return await user_service.get_by_id(token_data.user_id)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current user from JWT token (required)."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_access_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current user and verify admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def verify_telegram_webapp(
    x_telegram_init_data: Annotated[str | None, Header()] = None,
) -> TelegramInitData:
    """Verify Telegram WebApp initData from header."""
    if not x_telegram_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram initData required",
        )

    init_data = verify_telegram_init_data(x_telegram_init_data)
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        )

    return init_data


async def get_user_from_telegram_webapp(
    init_data: Annotated[TelegramInitData, Depends(verify_telegram_webapp)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get or create user from Telegram WebApp initData."""
    if not init_data.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data not found in initData",
        )

    user_service = UserService(db)
    user, _ = await user_service.get_or_create(
        telegram_id=init_data.telegram_user_id,
        username=init_data.username,
        first_name=init_data.first_name,
    )
    return user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
OptionalUser = Annotated[User | None, Depends(get_current_user_from_token)]
TelegramUser = Annotated[User, Depends(get_user_from_telegram_webapp)]
TelegramData = Annotated[TelegramInitData, Depends(verify_telegram_webapp)]
DB = Annotated[AsyncSession, Depends(get_db)]
