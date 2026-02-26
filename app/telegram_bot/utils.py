"""Telegram bot utilities."""
from app.core.config import settings
from app.core.logging import logger
from app.db.models import SamplingEvent


def format_sampling_event_message(event: SamplingEvent) -> str:
    """Format sampling event for Telegram group message."""
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
    gps_labels = {
        "received": "получены",
        "timeout": "таймаут",
        "skipped_by_user": "пропущено",
    }

    operator_name = event.operator.display_name if event.operator else "Неизвестно"
    site_name = event.site.name if event.site else "?"
    well_name = event.well.name if event.well else "?"

    well_status = status_labels.get(event.well_status.value, event.well_status.value)
    sample_type = type_labels.get(event.sample_type.value, event.sample_type.value)
    gps_status = gps_labels.get(event.gps_status.value, event.gps_status.value)

    # Format times
    start_time = "—"
    end_time = "—"
    if event.sampling_start:
        start_time = event.sampling_start.strftime("%d.%m.%Y %H:%M")
    if event.sampling_end:
        end_time = event.sampling_end.strftime("%d.%m.%Y %H:%M")

    # Format volume
    volume_text = f"{event.volume_liters} л"
    if event.volume_liters == 0:
        volume_text = "не отобрано"

    # Format coordinates
    coords_text = "нет"
    if event.lat is not None and event.lon is not None:
        coords_text = f"{event.lat:.6f}, {event.lon:.6f}"

    # Format note
    note_text = event.sample_note or "—"

    message = (
        "🧪 <b>Новое событие: Отбор пробы</b>\n\n"
        f"<b>Оператор:</b> {operator_name}\n"
        f"<b>Участок:</b> {site_name}\n"
        f"<b>Скважина:</b> {well_name}\n"
        f"<b>Состояние скважины:</b> {well_status}\n"
        f"<b>Время отбора начало:</b> {start_time}\n"
        f"<b>Время отбора конец:</b> {end_time}\n"
        f"<b>Отобрано:</b> {volume_text}\n"
        f"<b>Состояние пробы:</b> {sample_type}\n"
        f"<b>Примечания:</b> {note_text}\n"
        f"<b>Координаты:</b> {coords_text} (GPS: {gps_status})"
    )

    return message


async def send_to_group(event: SamplingEvent) -> bool:
    """Send sampling event message to Telegram group."""
    from app.telegram_bot.bot import bot

    if not settings.telegram_group_chat_id:
        logger.warning("TELEGRAM_GROUP_CHAT_ID not configured, skipping group notification")
        return False

    try:
        message = format_sampling_event_message(event)
        await bot.send_message(
            chat_id=settings.telegram_group_chat_id,
            text=message,
        )
        logger.info(f"Sent sampling event {event.id} to group {settings.telegram_group_chat_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send to group: {e}")
        return False
