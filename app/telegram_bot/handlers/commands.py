"""Basic command handlers."""
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session_maker
from app.services.user_service import UserService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    user = message.from_user
    if not user:
        return

    # Register user in database
    async with async_session_maker() as db:
        user_service = UserService(db)
        db_user, created = await user_service.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        await db.commit()

        action = "зарегистрирован" if created else "обновлён"
        logger.info(f"User {action}: {user.id} (@{user.username})")

    # Build keyboard with Mini App button
    keyboard = []

    if settings.webapp_url:
        keyboard.append([
            InlineKeyboardButton(
                text="📝 Отбор пробы",
                web_app=WebAppInfo(url=f"{settings.webapp_url}/sampling"),
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="📊 Дашборд", url=f"{settings.app_url}/"),
    ])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await message.answer(
        f"👋 Привет, {user.first_name or 'оператор'}!\n\n"
        "Я бот для учёта отбора проб.\n\n"
        "Доступные действия:\n"
        "• /sample - Начать отбор пробы\n"
        "• /sites - Список участков\n"
        "• /help - Справка\n\n"
        "Или используйте кнопки ниже:",
        reply_markup=reply_markup,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "<b>Справка по боту</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начало работы\n"
        "/sample - Создать событие отбора пробы\n"
        "/sites - Список всех участков\n"
        "/wells - Список скважин\n"
        "/help - Эта справка\n\n"
        "<b>Для администраторов:</b>\n"
        "/addsite - Добавить участок\n"
        "/addwell - Добавить скважину\n\n"
        "Для удобного ввода данных рекомендуем "
        "использовать мини-приложение (кнопка 'Отбор пробы').",
    )


@router.message(Command("sites"))
async def cmd_sites(message: Message) -> None:
    """Handle /sites command - list all sites."""
    from app.services.site_service import SiteService

    async with async_session_maker() as db:
        site_service = SiteService(db)
        sites = await site_service.get_all(limit=50)

        if not sites:
            await message.answer("Участки пока не созданы.")
            return

        text = "<b>Участки:</b>\n\n"
        for site in sites:
            wells_count = len(site.wells) if site.wells else 0
            text += f"• <b>{site.name}</b> (скв. нагн.: {site.inj_well_name})\n"
            text += f"  Скважин: {wells_count}\n"

        await message.answer(text)


@router.message(Command("wells"))
async def cmd_wells(message: Message) -> None:
    """Handle /wells command - list wells."""
    from app.services.well_service import WellService

    async with async_session_maker() as db:
        well_service = WellService(db)
        wells = await well_service.get_all(limit=50)

        if not wells:
            await message.answer("Скважины пока не созданы.")
            return

        text = "<b>Скважины:</b>\n\n"
        current_site = None
        for well in wells:
            if well.site and well.site.name != current_site:
                current_site = well.site.name
                text += f"\n<b>Участок: {current_site}</b>\n"
            well_type_ru = {
                "injection": "нагн.",
                "production": "доб.",
                "gryphon": "грифон",
            }.get(well.well_type.value, well.well_type.value)
            text += f"  • {well.name} ({well_type_ru})\n"

        await message.answer(text)
