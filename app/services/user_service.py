"""User service for business logic."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import User, UserRole


class UserService:
    """Service for user-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> tuple[User, bool]:
        """
        Get existing user or create new one.
        Returns tuple of (user, created).
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            # Update user info if changed
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                await self.db.flush()
            return user, False

        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.USER,
        )
        self.db.add(user)
        await self.db.flush()
        logger.info(f"Created new user: telegram_id={telegram_id}, username={username}")
        return user, True

    async def update_role(self, user_id: int, role: UserRole) -> User | None:
        """Update user role."""
        user = await self.get_by_id(user_id)
        if user:
            user.role = role
            await self.db.flush()
            logger.info(f"Updated user role: user_id={user_id}, role={role}")
        return user

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users with pagination."""
        result = await self.db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def is_admin(self, telegram_id: int) -> bool:
        """Check if user is admin."""
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.role == UserRole.ADMIN
