"""Sampling events API endpoints."""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, CurrentUser, DB, TelegramUser
from app.api.schemas import (
    SamplingEventCreate,
    SamplingEventDetailResponse,
    SamplingEventResponse,
    SamplingEventUpdate,
)
from app.db.models import SampleType, UserRole, WellStatus
from app.services.sampling_service import SamplingService
from app.services.site_service import SiteService
from app.services.well_service import WellService

router = APIRouter()


@router.get("", response_model=list[SamplingEventDetailResponse])
async def list_sampling_events(
    db: DB,
    site_id: int | None = Query(default=None),
    well_id: int | None = Query(default=None),
    operator_user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    sample_type: SampleType | None = Query(default=None),
    well_status: WellStatus | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SamplingEventDetailResponse]:
    """Get sampling events with filters."""
    sampling_service = SamplingService(db)
    events = await sampling_service.get_all(
        limit=limit,
        offset=offset,
        site_id=site_id,
        well_id=well_id,
        operator_user_id=operator_user_id,
        date_from=date_from,
        date_to=date_to,
        sample_type=sample_type,
        well_status=well_status,
    )
    return [SamplingEventDetailResponse.model_validate(e) for e in events]


@router.get("/{event_id}", response_model=SamplingEventDetailResponse)
async def get_sampling_event(event_id: int, db: DB) -> SamplingEventDetailResponse:
    """Get sampling event by ID with full details."""
    sampling_service = SamplingService(db)
    event = await sampling_service.get_by_id_with_relations(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sampling event not found",
        )
    return SamplingEventDetailResponse.model_validate(event)


@router.post("", response_model=SamplingEventResponse, status_code=status.HTTP_201_CREATED)
async def create_sampling_event(
    data: SamplingEventCreate,
    db: DB,
    user: CurrentUser,
) -> SamplingEventResponse:
    """Create a new sampling event."""
    site_service = SiteService(db)
    well_service = WellService(db)
    sampling_service = SamplingService(db)

    # Validate site
    site = await site_service.get_by_id(data.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Validate well belongs to site
    well = await well_service.get_by_id(data.well_id)
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Well not found",
        )
    if well.site_id != data.site_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Well does not belong to the specified site",
        )

    event = await sampling_service.create(
        site_id=data.site_id,
        well_id=data.well_id,
        operator_user_id=user.id,
        well_status=data.well_status,
        sampling_start=data.sampling_start,
        sampling_end=data.sampling_end,
        sample_type=data.sample_type,
        sample_note=data.sample_note,
        volume_liters=data.volume_liters,
        gps_status=data.gps_status,
        lat=data.lat,
        lon=data.lon,
    )
    return SamplingEventResponse.model_validate(event)


@router.post("/webapp", response_model=SamplingEventDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_sampling_event_webapp(
    data: SamplingEventCreate,
    db: DB,
    user: TelegramUser,
) -> SamplingEventDetailResponse:
    """Create a new sampling event from Telegram WebApp."""
    site_service = SiteService(db)
    well_service = WellService(db)
    sampling_service = SamplingService(db)

    # Validate site
    site = await site_service.get_by_id(data.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Validate well belongs to site
    well = await well_service.get_by_id(data.well_id)
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Well not found",
        )
    if well.site_id != data.site_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Well does not belong to the specified site",
        )

    event = await sampling_service.create(
        site_id=data.site_id,
        well_id=data.well_id,
        operator_user_id=user.id,
        well_status=data.well_status,
        sampling_start=data.sampling_start,
        sampling_end=data.sampling_end,
        sample_type=data.sample_type,
        sample_note=data.sample_note,
        volume_liters=data.volume_liters,
        gps_status=data.gps_status,
        lat=data.lat,
        lon=data.lon,
    )

    # Reload with relations
    event = await sampling_service.get_by_id_with_relations(event.id)
    return SamplingEventDetailResponse.model_validate(event)


@router.put("/{event_id}", response_model=SamplingEventResponse)
async def update_sampling_event(
    event_id: int,
    data: SamplingEventUpdate,
    db: DB,
    user: CurrentUser,
) -> SamplingEventResponse:
    """Update sampling event. Users can only update their own events."""
    sampling_service = SamplingService(db)

    event = await sampling_service.get_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sampling event not found",
        )

    # Only allow update of own events (unless admin)
    if event.operator_user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other user's sampling events",
        )

    updated = await sampling_service.update(
        event_id=event_id,
        well_status=data.well_status,
        sampling_start=data.sampling_start,
        sampling_end=data.sampling_end,
        sample_type=data.sample_type,
        sample_note=data.sample_note,
        volume_liters=data.volume_liters,
        gps_status=data.gps_status,
        lat=data.lat,
        lon=data.lon,
    )
    return SamplingEventResponse.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sampling_event(
    event_id: int,
    db: DB,
    user: CurrentAdmin,
) -> None:
    """Delete sampling event. Admin only."""
    sampling_service = SamplingService(db)
    deleted = await sampling_service.delete(event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sampling event not found",
        )


@router.get("/site/{site_id}/recent", response_model=list[SamplingEventDetailResponse])
async def get_recent_site_events(
    site_id: int,
    db: DB,
    limit: int = Query(default=20, le=100),
) -> list[SamplingEventDetailResponse]:
    """Get recent sampling events for a site."""
    sampling_service = SamplingService(db)
    events = await sampling_service.get_by_site(site_id, limit=limit)
    return [SamplingEventDetailResponse.model_validate(e) for e in events]
