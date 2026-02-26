"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import DB, TelegramData
from app.api.schemas import TelegramAuthRequest, Token, UserResponse
from app.core.security import create_access_token, verify_telegram_init_data
from app.services.user_service import UserService

router = APIRouter()


@router.post("/telegram", response_model=Token)
async def auth_telegram(request: TelegramAuthRequest, db: DB) -> Token:
    """
    Authenticate user via Telegram initData.
    Returns JWT token for subsequent API calls.
    """
    init_data = verify_telegram_init_data(request.init_data)
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram initData",
        )

    if not init_data.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data not found in initData",
        )

    user_service = UserService(db)
    user, created = await user_service.get_or_create(
        telegram_id=init_data.telegram_user_id,
        username=init_data.username,
        first_name=init_data.first_name,
    )

    token = create_access_token(
        data={
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "role": user.role.value,
        }
    )

    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(init_data: TelegramData, db: DB) -> UserResponse:
    """Get current user info from Telegram initData."""
    if not init_data.telegram_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data not found",
        )

    user_service = UserService(db)
    user, _ = await user_service.get_or_create(
        telegram_id=init_data.telegram_user_id,
        username=init_data.username,
        first_name=init_data.first_name,
    )

    return UserResponse.model_validate(user)
