"""Security utilities: JWT, password hashing, Telegram initData verification."""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, unquote

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """JWT token payload."""
    user_id: int
    telegram_id: int
    role: str
    exp: datetime


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> TokenData | None:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return TokenData(
            user_id=payload.get("user_id"),
            telegram_id=payload.get("telegram_id"),
            role=payload.get("role"),
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
        )
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


class TelegramInitData(BaseModel):
    """Parsed Telegram WebApp initData."""
    query_id: str | None = None
    user: dict[str, Any] | None = None
    auth_date: int
    hash: str

    @property
    def telegram_user_id(self) -> int | None:
        if self.user:
            return self.user.get("id")
        return None

    @property
    def username(self) -> str | None:
        if self.user:
            return self.user.get("username")
        return None

    @property
    def first_name(self) -> str | None:
        if self.user:
            return self.user.get("first_name")
        return None


def verify_telegram_init_data(init_data: str, bot_token: str | None = None) -> TelegramInitData | None:
    """
    Verify Telegram WebApp initData signature.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    from app.core.logging import logger

    if bot_token is None:
        bot_token = settings.bot_token

    if not init_data or not init_data.strip():
        logger.warning("verify_telegram_init_data: empty init_data")
        return None

    try:
        parsed = parse_qs(init_data)

        # Get hash from raw parsed values
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            logger.warning("verify_telegram_init_data: no hash in init_data")
            return None

        # Build data-check-string using raw URL-decoded values (NOT re-serialized)
        # This is critical: Telegram computes hash on the original values
        data_check_pairs = []
        for key in sorted(parsed.keys()):
            if key == "hash":
                continue
            val = parsed[key][0] if parsed[key] else ""
            data_check_pairs.append(f"{key}={val}")
        data_check_string = "\n".join(data_check_pairs)

        # Create secret key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            logger.warning("verify_telegram_init_data: hash mismatch")
            logger.debug(f"  data_check_string: {data_check_string!r}")
            logger.debug(f"  calculated: {calculated_hash}")
            logger.debug(f"  received:   {received_hash}")
            return None

        # Parse user data for the response object
        user_data = None
        user_str = parsed.get("user", [None])[0]
        if user_str:
            user_data = json.loads(user_str)

        auth_date = int(parsed.get("auth_date", ["0"])[0])

        # Check auth_date is not too old (allow 24 hours)
        if time.time() - auth_date > 86400:
            logger.warning(f"verify_telegram_init_data: auth_date too old ({auth_date})")
            return None

        return TelegramInitData(
            query_id=parsed.get("query_id", [None])[0],
            user=user_data,
            auth_date=auth_date,
            hash=received_hash,
        )

    except Exception as e:
        logger.error(f"verify_telegram_init_data error: {e}")
        return None
