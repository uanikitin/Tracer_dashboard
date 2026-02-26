"""Telegram bot initialization."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings

# Initialize bot with default properties
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

# Initialize dispatcher
dp = Dispatcher()

# Import and include routers
from app.telegram_bot.handlers import commands, sampling

dp.include_router(commands.router)
dp.include_router(sampling.router)
