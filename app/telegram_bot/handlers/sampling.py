"""Sampling event handlers via conversation."""
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.core.config import settings
from app.core.logging import logger
from app.db.models import GPSStatus, SampleType, WellStatus, WellType
from app.db.session import async_session_maker
from app.services.sampling_service import SamplingService
from app.services.site_service import SiteService
from app.services.user_service import UserService
from app.services.well_service import WellService
from app.telegram_bot.utils import format_sampling_event_message, send_to_group

router = Router()


class SamplingStates(StatesGroup):
    """FSM states for sampling event creation."""
    select_site = State()
    create_site = State()
    select_well = State()
    create_well = State()
    select_well_status = State()
    enter_gps = State()
    enter_start_time = State()
    enter_end_time = State()
    select_sample_type = State()
    enter_volume = State()
    enter_note = State()
    confirm = State()


@router.message(Command("sample"))
async def cmd_sample(message: Message, state: FSMContext) -> None:
    """Start sampling event creation."""
    user = message.from_user
    if not user:
        return

    # Prefer Mini App if available
    if settings.webapp_url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Открыть форму отбора",
                web_app=WebAppInfo(url=f"{settings.webapp_url}/sampling"),
            )],
            [InlineKeyboardButton(
                text="💬 Продолжить в чате",
                callback_data="sampling:chat",
            )],
        ])
        await message.answer(
            "Выберите способ ввода данных:",
            reply_markup=keyboard,
        )
        return

    await start_sampling_chat(message, state)


@router.callback_query(F.data == "sampling:chat")
async def start_sampling_chat_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Start chat-based sampling flow."""
    if callback.message:
        await callback.message.delete()
        await start_sampling_chat(callback.message, state, is_callback=True)
    await callback.answer()


async def start_sampling_chat(
    message: Message,
    state: FSMContext,
    is_callback: bool = False,
) -> None:
    """Start the chat-based sampling flow."""
    async with async_session_maker() as db:
        site_service = SiteService(db)
        sites = await site_service.get_all(limit=50)

    if not sites:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать участок", callback_data="sampling:new_site")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="sampling:cancel")],
        ])
        text = "Участки не найдены. Создайте новый участок:"
    else:
        buttons = []
        for site in sites:
            buttons.append([
                InlineKeyboardButton(
                    text=f"📍 {site.name}",
                    callback_data=f"sampling:site:{site.id}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="➕ Новый участок", callback_data="sampling:new_site")
        ])
        buttons.append([
            InlineKeyboardButton(text="❌ Отмена", callback_data="sampling:cancel")
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = "<b>Шаг 1/8: Выберите участок</b>"

    await state.set_state(SamplingStates.select_site)

    if is_callback:
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "sampling:cancel")
async def cancel_sampling(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel sampling flow."""
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Отбор пробы отменён.")
    await callback.answer()


@router.callback_query(F.data.startswith("sampling:site:"))
async def select_site(callback: CallbackQuery, state: FSMContext) -> None:
    """Site selected, show wells."""
    site_id = int(callback.data.split(":")[-1])
    await state.update_data(site_id=site_id)

    async with async_session_maker() as db:
        site_service = SiteService(db)
        site = await site_service.get_by_id_with_wells(site_id)

    if not site:
        await callback.answer("Участок не найден", show_alert=True)
        return

    await state.update_data(site_name=site.name)

    if not site.wells:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать скважину", callback_data="sampling:new_well")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="sampling:back_to_sites")],
        ])
        text = f"<b>Участок: {site.name}</b>\n\nСкважины не найдены. Создайте новую:"
    else:
        buttons = []
        for well in site.wells:
            well_type_icon = {"injection": "💉", "production": "🛢", "gryphon": "🌋"}.get(
                well.well_type.value, "⚫"
            )
            buttons.append([
                InlineKeyboardButton(
                    text=f"{well_type_icon} {well.name}",
                    callback_data=f"sampling:well:{well.id}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(text="➕ Новая скважина", callback_data="sampling:new_well")
        ])
        buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data="sampling:back_to_sites")
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = f"<b>Шаг 2/8: Участок {site.name}</b>\n\nВыберите скважину:"

    await state.set_state(SamplingStates.select_well)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "sampling:back_to_sites")
async def back_to_sites(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to site selection."""
    await state.set_state(SamplingStates.select_site)

    async with async_session_maker() as db:
        site_service = SiteService(db)
        sites = await site_service.get_all(limit=50)

    buttons = []
    for site in sites:
        buttons.append([
            InlineKeyboardButton(
                text=f"📍 {site.name}",
                callback_data=f"sampling:site:{site.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ Новый участок", callback_data="sampling:new_site")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="sampling:cancel")
    ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 1/8: Выберите участок</b>",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sampling:well:"))
async def select_well(callback: CallbackQuery, state: FSMContext) -> None:
    """Well selected, ask for well status."""
    well_id = int(callback.data.split(":")[-1])
    await state.update_data(well_id=well_id)

    async with async_session_maker() as db:
        well_service = WellService(db)
        well = await well_service.get_by_id(well_id)

    if well:
        await state.update_data(well_name=well.name)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Работает", callback_data="sampling:status:working")],
        [InlineKeyboardButton(text="🔧 Ремонт", callback_data="sampling:status:repair")],
        [InlineKeyboardButton(text="❌ Не работает", callback_data="sampling:status:not_working")],
        [InlineKeyboardButton(text="🏗 КРС", callback_data="sampling:status:krs")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sampling:site:{(await state.get_data()).get('site_id')}")],
    ])

    await state.set_state(SamplingStates.select_well_status)
    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 3/8: Состояние скважины</b>",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sampling:status:"))
async def select_well_status(callback: CallbackQuery, state: FSMContext) -> None:
    """Well status selected, ask for GPS."""
    status_value = callback.data.split(":")[-1]
    await state.update_data(well_status=status_value)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Ввести координаты", callback_data="sampling:gps:enter")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="sampling:gps:skip")],
    ])

    await state.set_state(SamplingStates.enter_gps)
    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 4/8: GPS координаты</b>\n\n"
            "Отправьте координаты или пропустите этот шаг.",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data == "sampling:gps:skip")
async def skip_gps(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip GPS entry."""
    await state.update_data(gps_status="skipped_by_user", lat=None, lon=None)
    await ask_sample_type(callback, state)


@router.callback_query(F.data == "sampling:gps:enter")
async def enter_gps_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for GPS coordinates."""
    if callback.message:
        await callback.message.edit_text(
            "<b>Введите координаты</b>\n\n"
            "Формат: <code>широта, долгота</code>\n"
            "Пример: <code>55.7558, 37.6173</code>\n\n"
            "Или отправьте геолокацию.",
        )
    await callback.answer()


@router.message(SamplingStates.enter_gps, F.location)
async def receive_location(message: Message, state: FSMContext) -> None:
    """Receive location from user."""
    location = message.location
    if location:
        await state.update_data(
            gps_status="received",
            lat=location.latitude,
            lon=location.longitude,
        )
        await message.answer(
            f"✅ Координаты получены: {location.latitude:.6f}, {location.longitude:.6f}"
        )
        # Continue to sample type
        await ask_sample_type_message(message, state)


@router.message(SamplingStates.enter_gps, F.text)
async def receive_gps_text(message: Message, state: FSMContext) -> None:
    """Receive GPS coordinates as text."""
    text = message.text or ""
    try:
        parts = text.replace(" ", "").split(",")
        lat = float(parts[0])
        lon = float(parts[1])
        await state.update_data(gps_status="received", lat=lat, lon=lon)
        await message.answer(f"✅ Координаты получены: {lat:.6f}, {lon:.6f}")
        await ask_sample_type_message(message, state)
    except (ValueError, IndexError):
        await message.answer(
            "❌ Неверный формат. Введите координаты в формате:\n"
            "<code>55.7558, 37.6173</code>"
        )


async def ask_sample_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask for sample type via callback."""
    data = await state.get_data()
    well_status = data.get("well_status")

    # If well is not working, we can skip sampling times
    if well_status != "working":
        await state.update_data(sampling_start=None, sampling_end=None)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💧 Вода", callback_data="sampling:type:water")],
        [InlineKeyboardButton(text="🛢 Нефть", callback_data="sampling:type:oil")],
        [InlineKeyboardButton(text="💨 Газ", callback_data="sampling:type:gas")],
        [InlineKeyboardButton(
            text="⚠️ Не отобрана (газ)",
            callback_data="sampling:type:not_sampled_gas"
        )],
        [InlineKeyboardButton(text="📝 Другое", callback_data="sampling:type:other")],
    ])

    await state.set_state(SamplingStates.select_sample_type)
    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 5/8: Тип пробы</b>",
            reply_markup=keyboard,
        )
    await callback.answer()


async def ask_sample_type_message(message: Message, state: FSMContext) -> None:
    """Ask for sample type via message."""
    data = await state.get_data()
    well_status = data.get("well_status")

    if well_status == "working":
        # Set current time as start time
        await state.update_data(sampling_start=datetime.now(timezone.utc).isoformat())

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💧 Вода", callback_data="sampling:type:water")],
        [InlineKeyboardButton(text="🛢 Нефть", callback_data="sampling:type:oil")],
        [InlineKeyboardButton(text="💨 Газ", callback_data="sampling:type:gas")],
        [InlineKeyboardButton(
            text="⚠️ Не отобрана (газ)",
            callback_data="sampling:type:not_sampled_gas"
        )],
        [InlineKeyboardButton(text="📝 Другое", callback_data="sampling:type:other")],
    ])

    await state.set_state(SamplingStates.select_sample_type)
    await message.answer("<b>Шаг 5/8: Тип пробы</b>", reply_markup=keyboard)


@router.callback_query(F.data.startswith("sampling:type:"))
async def select_sample_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Sample type selected, ask for volume."""
    sample_type = callback.data.split(":")[-1]
    await state.update_data(sample_type=sample_type)

    # Set end time for working wells
    data = await state.get_data()
    if data.get("well_status") == "working":
        await state.update_data(sampling_end=datetime.now(timezone.utc).isoformat())

    # If not sampled, volume is 0
    if sample_type == "not_sampled_gas":
        await state.update_data(volume_liters=0.0)
        await ask_note(callback, state)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="0.7 л (стандарт)", callback_data="sampling:vol:0.7")],
        [InlineKeyboardButton(text="0.5 л", callback_data="sampling:vol:0.5")],
        [InlineKeyboardButton(text="1.0 л", callback_data="sampling:vol:1.0")],
        [InlineKeyboardButton(text="✏️ Другое", callback_data="sampling:vol:custom")],
    ])

    await state.set_state(SamplingStates.enter_volume)
    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 6/8: Объём пробы (литры)</b>",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sampling:vol:"))
async def select_volume(callback: CallbackQuery, state: FSMContext) -> None:
    """Volume selected."""
    vol_value = callback.data.split(":")[-1]

    if vol_value == "custom":
        if callback.message:
            await callback.message.edit_text(
                "<b>Введите объём пробы в литрах</b>\n\n"
                "Пример: <code>0.5</code>"
            )
        await callback.answer()
        return

    await state.update_data(volume_liters=float(vol_value))
    await ask_note(callback, state)


@router.message(SamplingStates.enter_volume, F.text)
async def receive_volume_text(message: Message, state: FSMContext) -> None:
    """Receive volume as text."""
    try:
        volume = float(message.text.replace(",", "."))
        if volume < 0:
            raise ValueError("Negative volume")
        await state.update_data(volume_liters=volume)
        await ask_note_message(message, state)
    except ValueError:
        await message.answer("❌ Введите число (например: 0.5)")


async def ask_note(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask for note via callback."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="sampling:note:skip")],
    ])

    await state.set_state(SamplingStates.enter_note)
    if callback.message:
        await callback.message.edit_text(
            "<b>Шаг 7/8: Примечание</b>\n\n"
            "Введите примечание или пропустите:",
            reply_markup=keyboard,
        )
    await callback.answer()


async def ask_note_message(message: Message, state: FSMContext) -> None:
    """Ask for note via message."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="sampling:note:skip")],
    ])

    await state.set_state(SamplingStates.enter_note)
    await message.answer(
        "<b>Шаг 7/8: Примечание</b>\n\n"
        "Введите примечание или пропустите:",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "sampling:note:skip")
async def skip_note(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip note entry."""
    await state.update_data(sample_note=None)
    await show_confirmation(callback, state)


@router.message(SamplingStates.enter_note, F.text)
async def receive_note(message: Message, state: FSMContext) -> None:
    """Receive note text."""
    await state.update_data(sample_note=message.text)
    await show_confirmation_message(message, state)


async def show_confirmation(callback: CallbackQuery, state: FSMContext) -> None:
    """Show confirmation dialog via callback."""
    data = await state.get_data()

    text = format_preview(data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="sampling:confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="sampling:cancel")],
    ])

    await state.set_state(SamplingStates.confirm)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


async def show_confirmation_message(message: Message, state: FSMContext) -> None:
    """Show confirmation dialog via message."""
    data = await state.get_data()

    text = format_preview(data)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="sampling:confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="sampling:cancel")],
    ])

    await state.set_state(SamplingStates.confirm)
    await message.answer(text, reply_markup=keyboard)


def format_preview(data: dict) -> str:
    """Format preview text."""
    status_labels = {
        "working": "Работает",
        "repair": "Ремонт",
        "not_working": "Не работает",
        "krs": "КРС",
    }
    type_labels = {
        "water": "Вода",
        "oil": "Нефть",
        "gas": "Газ",
        "not_sampled_gas": "Не отобрана (высокий газовый фактор)",
        "other": "Другое",
    }

    well_status = status_labels.get(data.get("well_status", ""), data.get("well_status", ""))
    sample_type = type_labels.get(data.get("sample_type", ""), data.get("sample_type", ""))

    coords = "—"
    if data.get("lat") and data.get("lon"):
        coords = f"{data['lat']:.6f}, {data['lon']:.6f}"

    volume = data.get("volume_liters", 0.7)
    note = data.get("sample_note") or "—"

    return (
        "<b>Шаг 8/8: Подтверждение</b>\n\n"
        f"<b>Участок:</b> {data.get('site_name', '?')}\n"
        f"<b>Скважина:</b> {data.get('well_name', '?')}\n"
        f"<b>Состояние:</b> {well_status}\n"
        f"<b>Тип пробы:</b> {sample_type}\n"
        f"<b>Объём:</b> {volume} л\n"
        f"<b>Координаты:</b> {coords}\n"
        f"<b>Примечание:</b> {note}\n\n"
        "Сохранить событие?"
    )


@router.callback_query(F.data == "sampling:confirm")
async def confirm_sampling(callback: CallbackQuery, state: FSMContext) -> None:
    """Save sampling event."""
    data = await state.get_data()
    user = callback.from_user

    if not user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    try:
        async with async_session_maker() as db:
            # Get or create user
            user_service = UserService(db)
            db_user, _ = await user_service.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
            )

            # Create sampling event
            sampling_service = SamplingService(db)

            # Parse datetime if present
            sampling_start = None
            sampling_end = None
            if data.get("sampling_start"):
                sampling_start = datetime.fromisoformat(data["sampling_start"])
            if data.get("sampling_end"):
                sampling_end = datetime.fromisoformat(data["sampling_end"])

            event = await sampling_service.create(
                site_id=data["site_id"],
                well_id=data["well_id"],
                operator_user_id=db_user.id,
                well_status=WellStatus(data["well_status"]),
                sampling_start=sampling_start,
                sampling_end=sampling_end,
                sample_type=SampleType(data["sample_type"]),
                sample_note=data.get("sample_note"),
                volume_liters=data.get("volume_liters", 0.7),
                gps_status=GPSStatus(data.get("gps_status", "skipped_by_user")),
                lat=data.get("lat"),
                lon=data.get("lon"),
            )

            # Reload with relations for message
            event = await sampling_service.get_by_id_with_relations(event.id)
            await db.commit()

            logger.info(f"Created sampling event {event.id} by user {user.id}")

            # Send to group
            if event:
                await send_to_group(event)

        await state.clear()

        if callback.message:
            await callback.message.edit_text(
                "✅ <b>Событие сохранено!</b>\n\n"
                f"ID: {event.id}\n"
                "Сообщение отправлено в группу."
            )
        await callback.answer("Сохранено!")

    except Exception as e:
        logger.error(f"Error saving sampling event: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# New site creation handlers
@router.callback_query(F.data == "sampling:new_site")
async def new_site_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for new site creation."""
    await state.set_state(SamplingStates.create_site)
    if callback.message:
        await callback.message.edit_text(
            "<b>Создание участка</b>\n\n"
            "Введите номер нагнетательной скважины (например: 2335):"
        )
    await callback.answer()


@router.message(SamplingStates.create_site, F.text)
async def create_site(message: Message, state: FSMContext) -> None:
    """Create new site."""
    inj_well = message.text.strip()
    name = f"inj_{inj_well}"

    async with async_session_maker() as db:
        site_service = SiteService(db)
        site, created = await site_service.get_or_create(name=name, inj_well_name=inj_well)
        await db.commit()

        await state.update_data(site_id=site.id, site_name=site.name)

        if created:
            await message.answer(f"✅ Участок <b>{name}</b> создан!")
        else:
            await message.answer(f"Участок <b>{name}</b> уже существует, выбран.")

        # Continue to well selection
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать скважину", callback_data="sampling:new_well")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="sampling:back_to_sites")],
        ])
        await message.answer(
            f"<b>Участок: {site.name}</b>\n\nСоздайте скважину:",
            reply_markup=keyboard,
        )
        await state.set_state(SamplingStates.select_well)


# New well creation handlers
@router.callback_query(F.data == "sampling:new_well")
async def new_well_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for new well creation."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛢 Добывающая", callback_data="sampling:welltype:production")],
        [InlineKeyboardButton(text="🌋 Грифон", callback_data="sampling:welltype:gryphon")],
    ])
    await state.set_state(SamplingStates.create_well)
    if callback.message:
        await callback.message.edit_text(
            "<b>Создание скважины</b>\n\nВыберите тип:",
            reply_markup=keyboard,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sampling:welltype:"))
async def select_well_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Well type selected, ask for name."""
    well_type = callback.data.split(":")[-1]
    await state.update_data(new_well_type=well_type)

    if callback.message:
        await callback.message.edit_text(
            "<b>Введите название/номер скважины:</b>"
        )
    await callback.answer()


@router.message(SamplingStates.create_well, F.text)
async def create_well(message: Message, state: FSMContext) -> None:
    """Create new well."""
    data = await state.get_data()
    well_name = message.text.strip()
    site_id = data["site_id"]
    well_type = WellType(data.get("new_well_type", "production"))

    async with async_session_maker() as db:
        well_service = WellService(db)
        well, created = await well_service.get_or_create(
            site_id=site_id,
            name=well_name,
            well_type=well_type,
        )
        await db.commit()

        await state.update_data(well_id=well.id, well_name=well.name)

        if created:
            await message.answer(f"✅ Скважина <b>{well_name}</b> создана!")
        else:
            await message.answer(f"Скважина <b>{well_name}</b> уже существует, выбрана.")

    # Continue to well status
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Работает", callback_data="sampling:status:working")],
        [InlineKeyboardButton(text="🔧 Ремонт", callback_data="sampling:status:repair")],
        [InlineKeyboardButton(text="❌ Не работает", callback_data="sampling:status:not_working")],
        [InlineKeyboardButton(text="🏗 КРС", callback_data="sampling:status:krs")],
    ])

    await state.set_state(SamplingStates.select_well_status)
    await message.answer(
        "<b>Шаг 3/8: Состояние скважины</b>",
        reply_markup=keyboard,
    )
