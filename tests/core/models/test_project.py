"""Tests for Project models in nes."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from nes.core.models.base import Name, NameKind
from nes.core.models.entity import EntitySubType
from nes.core.models.project import (
    CrossCuttingTag,
    DonorExtension,
    FinancingComponent,
    FinancingInstrument,
    FinancingInstrumentType,
    Project,
    ProjectDateEvent,
    ProjectLocation,
    ProjectStage,
    SectorMapping,
)
from nes.core.models.version import Author, VersionSummary, VersionType


def test_project_basic_creation():
    """Test creating a basic Project entity."""

    project = Project(
        slug="test-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Test Project"})],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/test-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.type == "project"
    assert project.sub_type == EntitySubType.DEVELOPMENT_PROJECT
    assert project.slug == "test-project"
    assert project.stage == ProjectStage.UNKNOWN
    assert project.id == "entity:project/development_project/test-project"


def test_project_with_stage():
    """Test Project with different stages."""

    project = Project(
        slug="ongoing-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Ongoing Project"})],
        stage=ProjectStage.ONGOING,
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/ongoing-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.stage == ProjectStage.ONGOING


def test_project_with_financing():
    """Test Project with financing components."""

    project = Project(
        slug="financed-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Financed Project"})],
        financing=[
            FinancingComponent(
                name="Main Component",
                financing=FinancingInstrument(
                    instrument_type=FinancingInstrumentType.LOAN,
                    currency="USD",
                    amount=1000000.0,
                    interest_rate=2.5,
                    repayment_period_years=20,
                    grace_period_years=5,
                ),
            ),
            FinancingComponent(
                name="Technical Assistance",
                financing=FinancingInstrument(
                    instrument_type=FinancingInstrumentType.GRANT,
                    currency="USD",
                    amount=50000.0,
                ),
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/financed-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.financing is not None
    assert len(project.financing) == 2
    assert project.financing[0].name == "Main Component"
    assert project.financing[0].financing.instrument_type == FinancingInstrumentType.LOAN
    assert project.financing[0].financing.amount == 1000000.0
    assert project.financing[1].financing.instrument_type == FinancingInstrumentType.GRANT


def test_project_with_dates():
    """Test Project with date events."""

    project = Project(
        slug="dated-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Dated Project"})],
        dates=[
            ProjectDateEvent(
                date=date(2020, 1, 15),
                type="APPROVAL",
                source="WB",
            ),
            ProjectDateEvent(
                date=date(2020, 6, 1),
                type="START",
                source="WB",
            ),
            ProjectDateEvent(
                date=date(2025, 12, 31),
                type="COMPLETION",
                source="WB",
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/dated-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.dates is not None
    assert len(project.dates) == 3
    assert project.dates[0].type == "APPROVAL"
    assert project.dates[0].date == date(2020, 1, 15)
    assert project.dates[0].source == "WB"


def test_project_with_locations():
    """Test Project with location data."""

    project = Project(
        slug="located-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Located Project"})],
        locations=[
            ProjectLocation(
                latitude=27.7172,
                longitude=85.3240,
                province="Bagmati",
                district="Kathmandu",
                municipality="Kathmandu Metropolitan City",
                source="NPC",
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/located-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.locations is not None
    assert len(project.locations) == 1
    assert project.locations[0].latitude == 27.7172
    assert project.locations[0].district == "Kathmandu"


def test_project_with_sectors():
    """Test Project with sector mappings."""

    project = Project(
        slug="sectored-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Sectored Project"})],
        sectors=[
            SectorMapping(
                normalized_sector="Transport",
                donor_sector="Transportation Infrastructure",
                donor_subsector="Roads",
                donor="WB",
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/sectored-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.sectors is not None
    assert len(project.sectors) == 1
    assert project.sectors[0].normalized_sector == "Transport"
    assert project.sectors[0].donor == "WB"


def test_project_with_tags():
    """Test Project with cross-cutting tags."""

    project = Project(
        slug="tagged-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Tagged Project"})],
        tags=[
            CrossCuttingTag(
                category="CLIMATE",
                normalized_tag="climate_adaptation",
                donor_tag="Climate Change Adaptation",
                donor="ADB",
            ),
            CrossCuttingTag(
                category="GENDER",
                normalized_tag="gender_mainstreaming",
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/tagged-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.tags is not None
    assert len(project.tags) == 2
    assert project.tags[0].category == "CLIMATE"
    assert project.tags[1].category == "GENDER"


def test_project_with_donors():
    """Test Project with donor information."""

    project = Project(
        slug="donor-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Donor Project"})],
        donors=["World Bank", "ADB"],
        donor_extensions=[
            DonorExtension(
                donor="World Bank",
                donor_project_id="P123456",
                raw_payload={"project_id": "P123456", "status": "Active"},
            ),
            DonorExtension(
                donor="ADB",
                donor_project_id="NEP-12345",
            ),
        ],
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/donor-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.donors is not None
    assert len(project.donors) == 2
    assert "World Bank" in project.donors
    assert project.donor_extensions is not None
    assert project.donor_extensions[0].donor_project_id == "P123456"


def test_project_with_agencies():
    """Test Project with implementing and executing agencies."""

    project = Project(
        slug="agency-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "Agency Project"})],
        implementing_agency="Ministry of Physical Infrastructure",
        executing_agency="Department of Roads",
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/agency-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.implementing_agency == "Ministry of Physical Infrastructure"
    assert project.executing_agency == "Department of Roads"


def test_project_with_url():
    """Test Project with project URL."""

    project = Project(
        slug="url-project",
        names=[Name(kind=NameKind.PRIMARY, en={"full": "URL Project"})],
        project_url="https://dfims.mof.gov.np/projects/123",
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/url-project",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="system"),
            change_description="Initial",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.project_url is not None
    assert str(project.project_url) == "https://dfims.mof.gov.np/projects/123"


def test_project_full_example():
    """Test creating a fully populated Project entity."""

    project = Project(
        slug="dfmis-12345",
        names=[
            Name(
                kind=NameKind.PRIMARY,
                en={"full": "Nepal Road Improvement Project"},
                ne={"full": "नेपाल सडक सुधार परियोजना"},
            )
        ],
        stage=ProjectStage.ONGOING,
        implementing_agency="Ministry of Physical Infrastructure and Transport",
        executing_agency="Department of Roads",
        financing=[
            FinancingComponent(
                name="Main Loan",
                financing=FinancingInstrument(
                    instrument_type=FinancingInstrumentType.LOAN,
                    currency="USD",
                    amount=50000000.0,
                    interest_rate=1.5,
                    repayment_period_years=25,
                    grace_period_years=5,
                ),
            ),
        ],
        dates=[
            ProjectDateEvent(date=date(2022, 3, 15), type="APPROVAL", source="MoF DFMIS"),
            ProjectDateEvent(date=date(2022, 7, 1), type="START", source="MoF DFMIS"),
        ],
        locations=[
            ProjectLocation(
                latitude=27.7172,
                longitude=85.3240,
                province="Bagmati",
                district="Kathmandu",
            ),
        ],
        sectors=[
            SectorMapping(
                normalized_sector="Transport",
                donor_sector="Infrastructure - Roads",
            ),
        ],
        donors=["World Bank"],
        donor_extensions=[
            DonorExtension(
                donor="World Bank",
                donor_project_id="P178901",
            ),
        ],
        project_url="https://dfims.mof.gov.np/projects/12345",
        version_summary=VersionSummary(
            entity_or_relationship_id="entity:project/development_project/dfmis-12345",
            type=VersionType.ENTITY,
            version_number=1,
            author=Author(slug="dfmis-import", name="MoF DFMIS Import"),
            change_description="Import from MoF DFMIS",
            created_at=datetime.now(UTC),
        ),
        created_at=datetime.now(UTC),
    )

    assert project.type == "project"
    assert project.sub_type == EntitySubType.DEVELOPMENT_PROJECT
    assert project.stage == ProjectStage.ONGOING
    assert project.id == "entity:project/development_project/dfmis-12345"
    assert len(project.financing) == 1
    assert len(project.dates) == 2
    assert len(project.locations) == 1


def test_financing_instrument_types():
    """Test all financing instrument types."""

    for instrument_type in FinancingInstrumentType:
        instrument = FinancingInstrument(
            instrument_type=instrument_type,
            currency="USD",
            amount=100000.0,
        )
        assert instrument.instrument_type == instrument_type


def test_project_stages():
    """Test all project stages."""

    for stage in ProjectStage:
        project = Project(
            slug=f"stage-{stage.value}",
            names=[Name(kind=NameKind.PRIMARY, en={"full": f"Stage {stage.value} Project"})],
            stage=stage,
            version_summary=VersionSummary(
                entity_or_relationship_id=f"entity:project/development_project/stage-{stage.value}",
                type=VersionType.ENTITY,
                version_number=1,
                author=Author(slug="system"),
                change_description="Initial",
                created_at=datetime.now(UTC),
            ),
            created_at=datetime.now(UTC),
        )
        assert project.stage == stage


def test_project_location_requires_coordinates():
    """Test that ProjectLocation requires latitude and longitude."""

    with pytest.raises(ValidationError):
        ProjectLocation(
            province="Bagmati",
            district="Kathmandu",
        )


def test_financing_component_requires_name():
    """Test that FinancingComponent requires a name."""

    with pytest.raises(ValidationError):
        FinancingComponent(
            financing=FinancingInstrument(
                instrument_type=FinancingInstrumentType.GRANT,
            ),
        )


def test_project_date_event_requires_type():
    """Test that ProjectDateEvent requires a type."""

    with pytest.raises(ValidationError):
        ProjectDateEvent(
            date=date(2020, 1, 1),
        )


def test_cross_cutting_tag_requires_category():
    """Test that CrossCuttingTag requires a category."""

    with pytest.raises(ValidationError):
        CrossCuttingTag(
            normalized_tag="climate_adaptation",
        )


def test_donor_extension_requires_donor():
    """Test that DonorExtension requires a donor."""

    with pytest.raises(ValidationError):
        DonorExtension(
            donor_project_id="P123456",
        )
