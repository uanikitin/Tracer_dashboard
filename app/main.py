"""Tracer Dashboard - FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import logger
from app.telegram_bot import bot, dp
from app.web import web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Tracer Dashboard...")

    # Start bot (skip if token is placeholder)
    bot_enabled = not settings.bot_token.startswith("123456")
    if bot_enabled:
        if settings.use_webhook and settings.telegram_webhook_url:
            # Set webhook
            await bot.set_webhook(
                url=settings.telegram_webhook_url,
                drop_pending_updates=True,
            )
            logger.info(f"Webhook set: {settings.telegram_webhook_url}")
        else:
            # Start polling in background
            asyncio.create_task(dp.start_polling(bot, skip_updates=True))
            logger.info("Bot polling started")
    else:
        logger.warning("Bot token is placeholder — Telegram bot disabled")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if bot_enabled:
        if settings.use_webhook:
            await bot.delete_webhook()
        else:
            await dp.stop_polling()
        await bot.session.close()


# Create FastAPI app
app = FastAPI(
    title="Tracer Dashboard",
    description="Система учёта отбора проб с Telegram-ботом и веб-дашбордом",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(web_router)


# Telegram webhook handler
@app.post("/api/v1/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    """Handle Telegram webhook updates."""
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
