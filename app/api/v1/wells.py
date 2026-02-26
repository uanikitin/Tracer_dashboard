"""Wells API endpoints."""
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentAdmin, DB, TelegramUser
from app.api.schemas import WellCreate, WellResponse, WellUpdate, WellWithSiteResponse
from app.services.site_service import SiteService
from app.services.well_service import WellService

router = APIRouter()


@router.get("", response_model=list[WellWithSiteResponse])
async def list_wells(
    db: DB,
    site_id: int | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[WellWithSiteResponse]:
    """Get wells, optionally filtered by site."""
    well_service = WellService(db)

    if site_id is not None:
        wells = await well_service.get_by_site(site_id)
    else:
        wells = await well_service.get_all(limit=limit, offset=offset)

    return [WellWithSiteResponse.model_validate(w) for w in wells]


@router.get("/with-coordinates", response_model=list[WellWithSiteResponse])
async def list_wells_with_coordinates(db: DB) -> list[WellWithSiteResponse]:
    """Get all wells that have GPS coordinates (for map display)."""
    well_service = WellService(db)
    wells = await well_service.get_all_with_coordinates()
    return [WellWithSiteResponse.model_validate(w) for w in wells]


@router.get("/{well_id}", response_model=WellWithSiteResponse)
async def get_well(well_id: int, db: DB) -> WellWithSiteResponse:
    """Get well by ID with site info."""
    well_service = WellService(db)
    well = await well_service.get_by_id_with_site(well_id)
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Well not found",
        )
    return WellWithSiteResponse.model_validate(well)


@router.post("", response_model=WellResponse, status_code=status.HTTP_201_CREATED)
async def create_well(data: WellCreate, db: DB, user: CurrentAdmin) -> WellResponse:
    """Create a new well. Admin only."""
    site_service = SiteService(db)
    well_service = WellService(db)

    # Check site exists
    site = await site_service.get_by_id(data.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    # Check duplicate name within site
    existing = await well_service.get_by_site_and_name(data.site_id, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Well with this name already exists in this site",
        )

    well = await well_service.create(
        site_id=data.site_id,
        name=data.name,
        well_type=data.well_type,
        lat=data.lat,
        lon=data.lon,
        description=data.description,
    )
    return WellResponse.model_validate(well)


@router.post("/webapp", response_model=WellResponse, status_code=status.HTTP_201_CREATED)
async def create_well_webapp(data: WellCreate, db: DB, user: TelegramUser) -> WellResponse:
    """Create a new well from Telegram WebApp."""
    site_service = SiteService(db)
    well_service = WellService(db)

    site = await site_service.get_by_id(data.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )

    existing = await well_service.get_by_site_and_name(data.site_id, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Well with this name already exists in this site",
        )

    well = await well_service.create(
        site_id=data.site_id,
        name=data.name,
        well_type=data.well_type,
        lat=data.lat,
        lon=data.lon,
        description=data.description,
    )
    return WellResponse.model_validate(well)


@router.put("/{well_id}", response_model=WellResponse)
async def update_well(
    well_id: int,
    data: WellUpdate,
    db: DB,
    user: CurrentAdmin,
) -> WellResponse:
    """Update well. Admin only."""
    well_service = WellService(db)

    well = await well_service.get_by_id(well_id)
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Well not found",
        )

    # Check duplicate name if updating
    if data.name and data.name != well.name:
        existing = await well_service.get_by_site_and_name(well.site_id, data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Well with this name already exists in this site",
            )

    updated = await well_service.update(
        well_id=well_id,
        name=data.name,
        well_type=data.well_type,
        lat=data.lat,
        lon=data.lon,
        description=data.description,
    )
    return WellResponse.model_validate(updated)


@router.delete("/{well_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_well(well_id: int, db: DB, user: CurrentAdmin) -> None:
    """Delete well. Admin only."""
    well_service = WellService(db)
    deleted = await well_service.delete(well_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Well not found",
        )
