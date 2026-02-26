"""Well service for business logic."""
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.models import Well, WellType


class WellService:
    """Service for well-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, well_id: int) -> Well | None:
        """Get well by ID."""
        result = await self.db.execute(select(Well).where(Well.id == well_id))
        return result.scalar_one_or_none()

    async def get_by_id_with_site(self, well_id: int) -> Well | None:
        """Get well by ID with site preloaded."""
        result = await self.db.execute(
            select(Well)
            .where(Well.id == well_id)
            .options(selectinload(Well.site))
        )
        return result.scalar_one_or_none()

    async def get_by_site_and_name(self, site_id: int, name: str) -> Well | None:
        """Get well by site_id and name."""
        result = await self.db.execute(
            select(Well).where(
                and_(Well.site_id == site_id, Well.name == name)
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        site_id: int,
        name: str,
        well_type: WellType,
        lat: float | None = None,
        lon: float | None = None,
        description: str | None = None,
    ) -> Well:
        """Create a new well."""
        well = Well(
            site_id=site_id,
            name=name,
            well_type=well_type,
            lat=lat,
            lon=lon,
            description=description,
        )
        self.db.add(well)
        await self.db.flush()
        logger.info(f"Created well: id={well.id}, name={name}, site_id={site_id}")
        return well

    async def update(
        self,
        well_id: int,
        name: str | None = None,
        well_type: WellType | None = None,
        lat: float | None = None,
        lon: float | None = None,
        description: str | None = None,
    ) -> Well | None:
        """Update well."""
        well = await self.get_by_id(well_id)
        if not well:
            return None

        if name is not None:
            well.name = name
        if well_type is not None:
            well.well_type = well_type
        if lat is not None:
            well.lat = lat
        if lon is not None:
            well.lon = lon
        if description is not None:
            well.description = description

        await self.db.flush()
        logger.info(f"Updated well: id={well_id}")
        return well

    async def delete(self, well_id: int) -> bool:
        """Delete well."""
        well = await self.get_by_id(well_id)
        if not well:
            return False

        await self.db.delete(well)
        await self.db.flush()
        logger.info(f"Deleted well: id={well_id}")
        return True

    async def get_by_site(self, site_id: int) -> list[Well]:
        """Get all wells for a site."""
        result = await self.db.execute(
            select(Well)
            .where(Well.site_id == site_id)
            .order_by(Well.name)
        )
        return list(result.scalars().all())

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Well]:
        """Get all wells with pagination."""
        result = await self.db.execute(
            select(Well)
            .options(selectinload(Well.site))
            .order_by(Well.site_id, Well.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_all_with_coordinates(self) -> list[Well]:
        """Get all wells that have coordinates."""
        result = await self.db.execute(
            select(Well)
            .where(
                and_(Well.lat.isnot(None), Well.lon.isnot(None))
            )
            .options(selectinload(Well.site))
            .order_by(Well.site_id, Well.name)
        )
        return list(result.scalars().all())

    async def get_or_create(
        self,
        site_id: int,
        name: str,
        well_type: WellType,
    ) -> tuple[Well, bool]:
        """
        Get existing well or create new one.
        Returns tuple of (well, created).
        """
        well = await self.get_by_site_and_name(site_id, name)
        if well:
            return well, False

        well = await self.create(
            site_id=site_id,
            name=name,
            well_type=well_type,
        )
        return well, True
