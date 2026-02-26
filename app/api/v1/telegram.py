"""Telegram webhook endpoint."""
from fastapi import APIRouter, Request, Response

from app.core.logging import logger

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """
    Telegram webhook endpoint.
    This is handled by the bot's feed_webhook method in main.py.
    """
    # The actual processing is done in main.py via bot.feed_webhook
    # This endpoint just needs to exist for routing
    logger.debug("Webhook endpoint called directly (should be handled by bot)")
    return Response(status_code=200)
