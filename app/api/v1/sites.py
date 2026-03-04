"""Sites API endpoints."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentAdmin, CurrentUser, DB, TelegramUser
from app.api.schemas import (
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    SiteWithWellsResponse,
)
from app.core.config import settings
from app.db.models import Deposit
from app.services.site_service import SiteService

router = APIRouter()


@router.get("", response_model=list[SiteResponse])
async def list_sites(
    db: DB,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SiteResponse]:
    """Get all sites."""
    site_service = SiteService(db)
    sites = await site_service.get_all(limit=limit, offset=offset)
    return [SiteResponse.model_validate(s) for s in sites]


@router.get("/{site_id}", response_model=SiteWithWellsResponse)
async def get_site(site_id: int, db: DB) -> SiteWithWellsResponse:
    """Get site by ID with wells."""
    site_service = SiteService(db)
    site = await site_service.get_by_id_with_wells(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    return SiteWithWellsResponse.model_validate(site)


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(data: SiteCreate, db: DB, user: CurrentAdmin) -> SiteResponse:
    """Create a new site. Admin only."""
    # Find deposit by current bot token
    result = await db.execute(
        select(Deposit).where(Deposit.bot_token == settings.bot_token)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit not found for this bot",
        )

    site_service = SiteService(db)

    # Check for duplicate name
    existing = await site_service.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Site with this name already exists",
        )

    site = await site_service.create(
        name=data.name,
        inj_well_name=data.inj_well_name,
        deposit_id=deposit.id,
        description=data.description,
    )
    return SiteResponse.model_validate(site)


@router.post("/webapp", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site_webapp(data: SiteCreate, db: DB, user: TelegramUser) -> SiteResponse:
    """Create a new site from Telegram WebApp."""
    # Find deposit by current bot token
    result = await db.execute(
        select(Deposit).where(Deposit.bot_token == settings.bot_token)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deposit not found for this bot",
        )

    site_service = SiteService(db)

    existing = await site_service.get_by_name(data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Site with this name already exists",
        )

    site = await site_service.create(
        name=data.name,
        inj_well_name=data.inj_well_name,
        deposit_id=deposit.id,
        description=data.description,
    )
    return SiteResponse.model_validate(site)


@router.put("/{site_id}", response_model=SiteResponse)
async def update_site(
    site_id: int,
    data: SiteUpdate,
    db: DB,
    user: CurrentAdmin,
) -> SiteResponse:
    """Update site. Admin only."""
    site_service = SiteService(db)

    # Check duplicate name if updating
    if data.name:
        existing = await site_service.get_by_name(data.name)
        if existing and existing.id != site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site with this name already exists",
            )

    site = await site_service.update(
        site_id=site_id,
        name=data.name,
        inj_well_name=data.inj_well_name,
        description=data.description,
    )
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    return SiteResponse.model_validate(site)


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(site_id: int, db: DB, user: CurrentAdmin) -> None:
    """Delete site. Admin only."""
    site_service = SiteService(db)
    deleted = await site_service.delete(site_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
