"""Pydantic schemas for API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import GPSStatus, SampleType, UserRole, WellStatus, WellType


# ==================== User Schemas ====================

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    created_at: datetime


# ==================== Site Schemas ====================

class SiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    inj_well_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    inj_well_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class SiteResponse(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class SiteWithWellsResponse(SiteResponse):
    wells: list["WellResponse"] = []


# ==================== Well Schemas ====================

class WellBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    well_type: WellType
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: Optional[str] = None


class WellCreate(WellBase):
    site_id: int


class WellUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    well_type: Optional[WellType] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    description: Optional[str] = None


class WellResponse(WellBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    created_at: datetime
    updated_at: datetime


class WellWithSiteResponse(WellResponse):
    site: SiteResponse


# ==================== Sampling Event Schemas ====================

class SamplingEventBase(BaseModel):
    well_status: WellStatus
    sampling_start: Optional[datetime] = None
    sampling_end: Optional[datetime] = None
    sample_type: SampleType
    sample_note: Optional[str] = None
    volume_liters: float = Field(default=0.7, ge=0)
    gps_status: GPSStatus
    lat: Optional[float] = None
    lon: Optional[float] = None


class SamplingEventCreate(SamplingEventBase):
    site_id: int
    well_id: int


class SamplingEventUpdate(BaseModel):
    well_status: Optional[WellStatus] = None
    sampling_start: Optional[datetime] = None
    sampling_end: Optional[datetime] = None
    sample_type: Optional[SampleType] = None
    sample_note: Optional[str] = None
    volume_liters: Optional[float] = Field(None, ge=0)
    gps_status: Optional[GPSStatus] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class SamplingEventResponse(SamplingEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    well_id: int
    operator_user_id: int
    created_at: datetime
    updated_at: datetime


class SamplingEventDetailResponse(SamplingEventResponse):
    site: SiteResponse
    well: WellResponse
    operator: UserResponse


# ==================== Auth Schemas ====================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TelegramAuthRequest(BaseModel):
    init_data: str


# ==================== Filter Schemas ====================

class SamplingEventFilter(BaseModel):
    site_id: Optional[int] = None
    well_id: Optional[int] = None
    operator_user_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    sample_type: Optional[SampleType] = None
    well_status: Optional[WellStatus] = None


# Rebuild models to resolve forward references
SiteWithWellsResponse.model_rebuild()
