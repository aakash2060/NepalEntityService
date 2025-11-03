"""Unit tests for FileDatabase entity operations."""

import shutil
import tempfile
from datetime import datetime

import pytest

from nes.core.models.base import Name
from nes.core.models.entity import Entity, Organization, Person
from nes.core.models.version import Actor, VersionSummary
from nes.database.file_database import FileDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    temp_dir = tempfile.mkdtemp()
    db = FileDatabase(temp_dir)
    yield db
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_actor():
    """Create a sample actor for testing."""
    return Actor(slug="harka-sampang", name="Harka Sampang")


@pytest.fixture
def sample_version_summary(sample_actor):
    """Create a sample version summary for testing."""
    return VersionSummary(
        entityOrRelationshipId="entity:person/harka-sampang",
        type="ENTITY",
        versionNumber=1,
        actor=sample_actor,
        changeDescription="Initial creation",
        createdAt=datetime.now(),
    )


@pytest.fixture
def sample_person(sample_version_summary):
    """Create a sample person entity for testing."""
    return Person(
        slug="harka-sampang",
        names=[Name(kind="DEFAULT", value="Harka Sampang", lang="ne")],
        versionSummary=sample_version_summary,
        createdAt=datetime.now(),
    )


@pytest.fixture
def sample_organization(sample_version_summary):
    """Create a sample organization entity for testing."""
    return Organization(
        slug="shram-sanskriti-party",
        type="organization",
        names=[Name(kind="DEFAULT", value="Shram Sanskriti Party", lang="ne")],
        versionSummary=sample_version_summary,
        createdAt=datetime.now(),
    )


@pytest.mark.asyncio
async def test_put_entity(temp_db, sample_person):
    """Test putting an entity."""
    result = await temp_db.put_entity(sample_person)
    assert result == sample_person

    file_path = temp_db._id_to_path(sample_person.id)
    assert file_path.exists()


@pytest.mark.asyncio
async def test_get_entity(temp_db, sample_person):
    """Test getting an entity."""
    await temp_db.put_entity(sample_person)
    result = await temp_db.get_entity(sample_person.id)
    assert result.slug == sample_person.slug
    assert result.type == sample_person.type


@pytest.mark.asyncio
async def test_get_nonexistent_entity(temp_db):
    """Test getting a non-existent entity."""
    result = await temp_db.get_entity("person:nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete_entity(temp_db, sample_person):
    """Test deleting an entity."""
    await temp_db.put_entity(sample_person)
    result = await temp_db.delete_entity(sample_person.id)
    assert result is True

    file_path = temp_db._id_to_path(sample_person.id)
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_entity(temp_db):
    """Test deleting a non-existent entity."""
    result = await temp_db.delete_entity("person:nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_list_entities(temp_db, sample_person, sample_organization):
    """Test listing entities."""
    await temp_db.put_entity(sample_person)
    await temp_db.put_entity(sample_organization)

    result = await temp_db.list_entities()
    assert len(result) == 2
    assert all(isinstance(entity, Entity) for entity in result)


@pytest.mark.asyncio
async def test_list_entities_with_pagination(temp_db, sample_actor):
    """Test listing entities with pagination."""
    entities = []
    for i in range(5):
        version_summary = VersionSummary(
            entityOrRelationshipId=f"entity:person/person-{i}",
            type="ENTITY",
            versionNumber=1,
            actor=sample_actor,
            changeDescription=f"Person {i} creation",
            createdAt=datetime.now(),
        )
        entity = Person(
            slug=f"person-{i}",
            names=[Name(kind="DEFAULT", value=f"Person {i}", lang="ne")],
            versionSummary=version_summary,
            createdAt=datetime.now(),
        )
        entities.append(entity)
        await temp_db.put_entity(entity)

    result = await temp_db.list_entities(limit=2, offset=1)
    assert len(result) == 2
