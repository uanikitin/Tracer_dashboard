"""Site service for business logic."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.models import Site


class SiteService:
    """Service for site-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, site_id: int) -> Site | None:
        """Get site by ID."""
        result = await self.db.execute(select(Site).where(Site.id == site_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Site | None:
        """Get site by name."""
        result = await self.db.execute(select(Site).where(Site.name == name))
        return result.scalar_one_or_none()

    async def get_by_id_with_wells(self, site_id: int) -> Site | None:
        """Get site by ID with wells preloaded."""
        result = await self.db.execute(
            select(Site)
            .where(Site.id == site_id)
            .options(selectinload(Site.wells))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        inj_well_name: str,
        deposit_id: int | None = None,
        description: str | None = None,
    ) -> Site:
        """Create a new site."""
        site = Site(
            name=name,
            inj_well_name=inj_well_name,
            deposit_id=deposit_id,
            description=description,
        )
        self.db.add(site)
        await self.db.flush()
        logger.info(f"Created site: id={site.id}, name={name}")
        return site

    async def update(
        self,
        site_id: int,
        name: str | None = None,
        inj_well_name: str | None = None,
        description: str | None = None,
    ) -> Site | None:
        """Update site."""
        site = await self.get_by_id(site_id)
        if not site:
            return None

        if name is not None:
            site.name = name
        if inj_well_name is not None:
            site.inj_well_name = inj_well_name
        if description is not None:
            site.description = description

        await self.db.flush()
        logger.info(f"Updated site: id={site_id}")
        return site

    async def delete(self, site_id: int) -> bool:
        """Delete site."""
        site = await self.get_by_id(site_id)
        if not site:
            return False

        await self.db.delete(site)
        await self.db.flush()
        logger.info(f"Deleted site: id={site_id}")
        return True

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[Site]:
        """Get all sites with pagination."""
        result = await self.db.execute(
            select(Site)
            .options(selectinload(Site.wells))
            .order_by(Site.name)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_or_create(self, name: str, inj_well_name: str | None = None, deposit_id: int | None = None) -> tuple[Site, bool]:
        """
        Get existing site or create new one.
        Returns tuple of (site, created).
        """
        site = await self.get_by_name(name)
        if site:
            return site, False

        site = await self.create(
            name=name,
            inj_well_name=inj_well_name or name,
            deposit_id=deposit_id,
        )
        return site, True
