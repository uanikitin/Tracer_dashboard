"""Web dashboard routes."""
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SampleType, WellStatus
from app.db.session import get_db
from app.services.sampling_service import SamplingService
from app.services.site_service import SiteService
from app.services.well_service import WellService

router = APIRouter()

# Setup templates
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# Custom filters for Jinja2
def format_datetime(value: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    if value is None:
        return "—"
    return value.strftime(fmt)


def format_coords(lat: float | None, lon: float | None) -> str:
    if lat is None or lon is None:
        return "—"
    return f"{lat:.6f}, {lon:.6f}"


templates.env.filters["datetime"] = format_datetime
templates.env.filters["coords"] = format_coords


DB = Annotated[AsyncSession, Depends(get_db)]


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, db: DB) -> HTMLResponse:
    """Dashboard home page."""
    site_service = SiteService(db)
    sampling_service = SamplingService(db)

    sites = await site_service.get_all(limit=10)
    recent_events = await sampling_service.get_all(limit=10)

    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "sites": sites,
            "recent_events": recent_events,
        },
    )


@router.get("/map", response_class=HTMLResponse)
async def map_page(request: Request, db: DB) -> HTMLResponse:
    """Map page with all wells."""
    well_service = WellService(db)
    wells = await well_service.get_all_with_coordinates()

    # Also get wells without coordinates for the list
    all_wells = await well_service.get_all(limit=500)

    return templates.TemplateResponse(
        "pages/map.html",
        {
            "request": request,
            "wells": wells,
            "all_wells": all_wells,
        },
    )


@router.get("/sites", response_class=HTMLResponse)
async def sites_page(request: Request, db: DB) -> HTMLResponse:
    """Sites list page."""
    site_service = SiteService(db)
    sites = await site_service.get_all(limit=100)

    return templates.TemplateResponse(
        "pages/sites.html",
        {
            "request": request,
            "sites": sites,
        },
    )


@router.get("/sites/{site_id}", response_class=HTMLResponse)
async def site_detail(request: Request, site_id: int, db: DB) -> HTMLResponse:
    """Site detail page."""
    site_service = SiteService(db)
    sampling_service = SamplingService(db)

    site = await site_service.get_by_id_with_wells(site_id)
    if not site:
        return templates.TemplateResponse(
            "pages/404.html",
            {"request": request, "message": "Участок не найден"},
            status_code=404,
        )

    recent_events = await sampling_service.get_by_site(site_id, limit=20)

    return templates.TemplateResponse(
        "pages/site_detail.html",
        {
            "request": request,
            "site": site,
            "recent_events": recent_events,
        },
    )


@router.get("/samples", response_class=HTMLResponse)
async def samples_page(
    request: Request,
    db: DB,
    site_id: int | None = Query(default=None),
    well_id: int | None = Query(default=None),
    sample_type: SampleType | None = Query(default=None),
    well_status: WellStatus | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
) -> HTMLResponse:
    """Samples table page with filters."""
    site_service = SiteService(db)
    well_service = WellService(db)
    sampling_service = SamplingService(db)

    # Parse dates
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to)
        except ValueError:
            pass

    # Pagination
    limit = 50
    offset = (page - 1) * limit

    events = await sampling_service.get_all(
        limit=limit,
        offset=offset,
        site_id=site_id,
        well_id=well_id,
        sample_type=sample_type,
        well_status=well_status,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )

    # Get filter options
    sites = await site_service.get_all(limit=100)
    wells = []
    if site_id:
        wells = await well_service.get_by_site(site_id)

    return templates.TemplateResponse(
        "pages/samples.html",
        {
            "request": request,
            "events": events,
            "sites": sites,
            "wells": wells,
            "filters": {
                "site_id": site_id,
                "well_id": well_id,
                "sample_type": sample_type.value if sample_type else None,
                "well_status": well_status.value if well_status else None,
                "date_from": date_from,
                "date_to": date_to,
            },
            "page": page,
            "sample_types": SampleType,
            "well_statuses": WellStatus,
        },
    )


# Mini App routes
@router.get("/webapp/sampling", response_class=HTMLResponse)
async def webapp_sampling(request: Request, db: DB) -> HTMLResponse:
    """Telegram Mini App - Sampling form."""
    site_service = SiteService(db)
    sites = await site_service.get_all(limit=100)

    return templates.TemplateResponse(
        "pages/webapp_sampling.html",
        {
            "request": request,
            "sites": sites,
        },
    )
