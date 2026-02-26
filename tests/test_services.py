"""Tests for business logic services."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import GPSStatus, SampleType, UserRole, WellStatus, WellType
from app.services.sampling_service import SamplingService
from app.services.site_service import SiteService
from app.services.user_service import UserService
from app.services.well_service import WellService


class TestUserService:
    """Tests for UserService."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation."""
        service = UserService(db_session)

        user, created = await service.get_or_create(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
        )

        assert created is True
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.role == UserRole.USER

    @pytest.mark.asyncio
    async def test_get_existing_user(self, db_session: AsyncSession):
        """Test getting existing user."""
        service = UserService(db_session)

        user1, created1 = await service.get_or_create(telegram_id=123456789)
        user2, created2 = await service.get_or_create(telegram_id=123456789)

        assert created1 is True
        assert created2 is False
        assert user1.id == user2.id

    @pytest.mark.asyncio
    async def test_update_role(self, db_session: AsyncSession):
        """Test updating user role."""
        service = UserService(db_session)

        user, _ = await service.get_or_create(telegram_id=123456789)
        assert user.role == UserRole.USER

        updated = await service.update_role(user.id, UserRole.ADMIN)
        assert updated.role == UserRole.ADMIN


class TestSiteService:
    """Tests for SiteService."""

    @pytest.mark.asyncio
    async def test_create_site(self, db_session: AsyncSession):
        """Test site creation."""
        service = SiteService(db_session)

        site = await service.create(
            name="inj_2335",
            inj_well_name="2335",
        )

        assert site.name == "inj_2335"
        assert site.inj_well_name == "2335"

    @pytest.mark.asyncio
    async def test_get_or_create_site(self, db_session: AsyncSession):
        """Test get_or_create for sites."""
        service = SiteService(db_session)

        site1, created1 = await service.get_or_create(name="inj_2335", inj_well_name="2335")
        site2, created2 = await service.get_or_create(name="inj_2335")

        assert created1 is True
        assert created2 is False
        assert site1.id == site2.id


class TestWellService:
    """Tests for WellService."""

    @pytest.mark.asyncio
    async def test_create_well(self, db_session: AsyncSession):
        """Test well creation."""
        site_service = SiteService(db_session)
        well_service = WellService(db_session)

        site = await site_service.create(name="inj_2335", inj_well_name="2335")
        well = await well_service.create(
            site_id=site.id,
            name="well_001",
            well_type=WellType.PRODUCTION,
        )

        assert well.name == "well_001"
        assert well.site_id == site.id
        assert well.well_type == WellType.PRODUCTION

    @pytest.mark.asyncio
    async def test_well_unique_within_site(self, db_session: AsyncSession):
        """Test well name uniqueness within site."""
        site_service = SiteService(db_session)
        well_service = WellService(db_session)

        site = await site_service.create(name="inj_2335", inj_well_name="2335")

        well1, created1 = await well_service.get_or_create(
            site_id=site.id,
            name="well_001",
            well_type=WellType.PRODUCTION,
        )
        well2, created2 = await well_service.get_or_create(
            site_id=site.id,
            name="well_001",
            well_type=WellType.PRODUCTION,
        )

        assert created1 is True
        assert created2 is False
        assert well1.id == well2.id


class TestSamplingService:
    """Tests for SamplingService."""

    @pytest.mark.asyncio
    async def test_create_sampling_event(self, db_session: AsyncSession):
        """Test sampling event creation."""
        user_service = UserService(db_session)
        site_service = SiteService(db_session)
        well_service = WellService(db_session)
        sampling_service = SamplingService(db_session)

        user, _ = await user_service.get_or_create(telegram_id=123456789)
        site = await site_service.create(name="inj_2335", inj_well_name="2335")
        well = await well_service.create(
            site_id=site.id,
            name="well_001",
            well_type=WellType.PRODUCTION,
        )

        event = await sampling_service.create(
            site_id=site.id,
            well_id=well.id,
            operator_user_id=user.id,
            well_status=WellStatus.WORKING,
            sample_type=SampleType.WATER,
            gps_status=GPSStatus.SKIPPED,
            volume_liters=0.7,
        )

        assert event.site_id == site.id
        assert event.well_id == well.id
        assert event.operator_user_id == user.id
        assert event.well_status == WellStatus.WORKING
        assert event.sample_type == SampleType.WATER
        assert event.volume_liters == 0.7

    @pytest.mark.asyncio
    async def test_get_events_by_site(self, db_session: AsyncSession):
        """Test getting events by site."""
        user_service = UserService(db_session)
        site_service = SiteService(db_session)
        well_service = WellService(db_session)
        sampling_service = SamplingService(db_session)

        user, _ = await user_service.get_or_create(telegram_id=123456789)
        site = await site_service.create(name="inj_2335", inj_well_name="2335")
        well = await well_service.create(
            site_id=site.id,
            name="well_001",
            well_type=WellType.PRODUCTION,
        )

        # Create multiple events
        for _ in range(3):
            await sampling_service.create(
                site_id=site.id,
                well_id=well.id,
                operator_user_id=user.id,
                well_status=WellStatus.WORKING,
                sample_type=SampleType.WATER,
                gps_status=GPSStatus.SKIPPED,
            )

        events = await sampling_service.get_by_site(site.id)
        assert len(events) == 3
