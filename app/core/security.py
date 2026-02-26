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
    if bot_token is None:
        bot_token = settings.bot_token

    try:
        parsed = parse_qs(init_data)
        data_dict: dict[str, Any] = {}

        for key, value in parsed.items():
            val = value[0] if value else ""
            if key == "user":
                data_dict[key] = json.loads(unquote(val))
            elif key == "auth_date":
                data_dict[key] = int(val)
            else:
                data_dict[key] = val

        received_hash = data_dict.pop("hash", None)
        if not received_hash:
            return None

        # Build data-check-string
        data_check_pairs = []
        for key in sorted(data_dict.keys()):
            value = data_dict[key]
            if key == "user":
                value = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            data_check_pairs.append(f"{key}={value}")
        data_check_string = "\n".join(data_check_pairs)

        # Create secret key
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
            return None

        # Check auth_date is not too old (allow 24 hours)
        auth_date = data_dict.get("auth_date", 0)
        if time.time() - auth_date > 86400:
            return None

        data_dict["hash"] = received_hash
        return TelegramInitData(**data_dict)

    except Exception:
        return None
