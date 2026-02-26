"""Sampling event service for business logic."""
from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.models import (
    GPSStatus,
    SamplingEvent,
    SampleType,
    WellStatus,
)


class SamplingService:
    """Service for sampling event operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, event_id: int) -> SamplingEvent | None:
        """Get sampling event by ID."""
        result = await self.db.execute(
            select(SamplingEvent).where(SamplingEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_relations(self, event_id: int) -> SamplingEvent | None:
        """Get sampling event by ID with all relations preloaded."""
        result = await self.db.execute(
            select(SamplingEvent)
            .where(SamplingEvent.id == event_id)
            .options(
                selectinload(SamplingEvent.site),
                selectinload(SamplingEvent.well),
                selectinload(SamplingEvent.operator),
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        site_id: int,
        well_id: int,
        operator_user_id: int,
        well_status: WellStatus,
        sample_type: SampleType,
        gps_status: GPSStatus,
        sampling_start: datetime | None = None,
        sampling_end: datetime | None = None,
        sample_note: str | None = None,
        volume_liters: float = 0.7,
        lat: float | None = None,
        lon: float | None = None,
    ) -> SamplingEvent:
        """Create a new sampling event."""
        event = SamplingEvent(
            site_id=site_id,
            well_id=well_id,
            operator_user_id=operator_user_id,
            well_status=well_status,
            sampling_start=sampling_start,
            sampling_end=sampling_end,
            sample_type=sample_type,
            sample_note=sample_note,
            volume_liters=volume_liters,
            gps_status=gps_status,
            lat=lat,
            lon=lon,
        )
        self.db.add(event)
        await self.db.flush()
        logger.info(
            f"Created sampling event: id={event.id}, "
            f"site_id={site_id}, well_id={well_id}, operator={operator_user_id}"
        )
        return event

    async def update(
        self,
        event_id: int,
        well_status: WellStatus | None = None,
        sampling_start: datetime | None = None,
        sampling_end: datetime | None = None,
        sample_type: SampleType | None = None,
        sample_note: str | None = None,
        volume_liters: float | None = None,
        gps_status: GPSStatus | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> SamplingEvent | None:
        """Update sampling event."""
        event = await self.get_by_id(event_id)
        if not event:
            return None

        if well_status is not None:
            event.well_status = well_status
        if sampling_start is not None:
            event.sampling_start = sampling_start
        if sampling_end is not None:
            event.sampling_end = sampling_end
        if sample_type is not None:
            event.sample_type = sample_type
        if sample_note is not None:
            event.sample_note = sample_note
        if volume_liters is not None:
            event.volume_liters = volume_liters
        if gps_status is not None:
            event.gps_status = gps_status
        if lat is not None:
            event.lat = lat
        if lon is not None:
            event.lon = lon

        await self.db.flush()
        logger.info(f"Updated sampling event: id={event_id}")
        return event

    async def delete(self, event_id: int) -> bool:
        """Delete sampling event."""
        event = await self.get_by_id(event_id)
        if not event:
            return False

        await self.db.delete(event)
        await self.db.flush()
        logger.info(f"Deleted sampling event: id={event_id}")
        return True

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        site_id: int | None = None,
        well_id: int | None = None,
        operator_user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sample_type: SampleType | None = None,
        well_status: WellStatus | None = None,
    ) -> list[SamplingEvent]:
        """Get sampling events with filters and pagination."""
        query = (
            select(SamplingEvent)
            .options(
                selectinload(SamplingEvent.site),
                selectinload(SamplingEvent.well),
                selectinload(SamplingEvent.operator),
            )
        )

        conditions = []
        if site_id is not None:
            conditions.append(SamplingEvent.site_id == site_id)
        if well_id is not None:
            conditions.append(SamplingEvent.well_id == well_id)
        if operator_user_id is not None:
            conditions.append(SamplingEvent.operator_user_id == operator_user_id)
        if date_from is not None:
            conditions.append(SamplingEvent.created_at >= date_from)
        if date_to is not None:
            conditions.append(SamplingEvent.created_at <= date_to)
        if sample_type is not None:
            conditions.append(SamplingEvent.sample_type == sample_type)
        if well_status is not None:
            conditions.append(SamplingEvent.well_status == well_status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(SamplingEvent.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_site(self, site_id: int, limit: int = 20) -> list[SamplingEvent]:
        """Get recent sampling events for a site."""
        result = await self.db.execute(
            select(SamplingEvent)
            .where(SamplingEvent.site_id == site_id)
            .options(
                selectinload(SamplingEvent.well),
                selectinload(SamplingEvent.operator),
            )
            .order_by(SamplingEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(
        self,
        site_id: int | None = None,
        well_id: int | None = None,
        operator_user_id: int | None = None,
    ) -> int:
        """Count sampling events with optional filters."""
        from sqlalchemy import func

        query = select(func.count(SamplingEvent.id))

        conditions = []
        if site_id is not None:
            conditions.append(SamplingEvent.site_id == site_id)
        if well_id is not None:
            conditions.append(SamplingEvent.well_id == well_id)
        if operator_user_id is not None:
            conditions.append(SamplingEvent.operator_user_id == operator_user_id)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        return result.scalar() or 0
