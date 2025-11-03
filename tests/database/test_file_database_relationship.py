"""Unit tests for FileDatabase relationship operations."""

import shutil
import tempfile
from datetime import date, datetime

import pytest

from nes.core.models.relationship import Relationship
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
    return Actor(slug="miraj-dhungana", name="Miraj Dhungana")


@pytest.fixture
def sample_version_summary(sample_actor):
    """Create a sample version summary for testing."""
    return VersionSummary(
        entityOrRelationshipId="relationship:person/harka-sampang:organization/shram-sanskriti-party:MEMBER_OF",
        type="RELATIONSHIP",
        versionNumber=1,
        actor=sample_actor,
        changeDescription="Initial relationship creation",
        createdAt=datetime.now(),
    )


@pytest.fixture
def sample_relationship(sample_version_summary):
    """Create a sample relationship for testing."""
    return Relationship(
        sourceEntityId="entity:person/harka-sampang",
        targetEntityId="entity:organization/shram-sanskriti-party",
        type="MEMBER_OF",
        startDate=date(2020, 1, 1),
        versionSummary=sample_version_summary,
        createdAt=datetime.now(),
    )


@pytest.mark.asyncio
async def test_put_relationship(temp_db, sample_relationship):
    """Test putting a relationship."""
    result = await temp_db.put_relationship(sample_relationship)
    assert result == sample_relationship

    file_path = temp_db._id_to_path(sample_relationship.id)
    assert file_path.exists()


@pytest.mark.asyncio
async def test_get_relationship(temp_db, sample_relationship):
    """Test getting a relationship."""
    await temp_db.put_relationship(sample_relationship)
    result = await temp_db.get_relationship(sample_relationship.id)
    assert result.sourceEntityId == sample_relationship.sourceEntityId
    assert result.targetEntityId == sample_relationship.targetEntityId
    assert result.type == sample_relationship.type


@pytest.mark.asyncio
async def test_get_nonexistent_relationship(temp_db):
    """Test getting a non-existent relationship."""
    result = await temp_db.get_relationship("relationship:nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete_relationship(temp_db, sample_relationship):
    """Test deleting a relationship."""
    await temp_db.put_relationship(sample_relationship)
    result = await temp_db.delete_relationship(sample_relationship.id)
    assert result is True

    file_path = temp_db._id_to_path(sample_relationship.id)
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_delete_nonexistent_relationship(temp_db):
    """Test deleting a non-existent relationship."""
    result = await temp_db.delete_relationship("relationship:nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_list_relationships(temp_db, sample_actor):
    """Test listing relationships."""
    version_summary1 = VersionSummary(
        entityOrRelationshipId="relationship:person/harka-sampang:organization/shram-sanskriti-party:MEMBER_OF",
        type="RELATIONSHIP",
        versionNumber=1,
        actor=sample_actor,
        changeDescription="Relationship 1",
        createdAt=datetime.now(),
    )
    version_summary2 = VersionSummary(
        entityOrRelationshipId="relationship:person/rabindra-mishra:organization/rastriya-swatantra-party:AFFILIATED_WITH",
        type="RELATIONSHIP",
        versionNumber=1,
        actor=sample_actor,
        changeDescription="Relationship 2",
        createdAt=datetime.now(),
    )
    relationships = [
        Relationship(
            sourceEntityId="entity:person/harka-sampang",
            targetEntityId="entity:organization/shram-sanskriti-party",
            type="MEMBER_OF",
            versionSummary=version_summary1,
            createdAt=datetime.now(),
        ),
        Relationship(
            sourceEntityId="entity:person/rabindra-mishra",
            targetEntityId="entity:organization/rastriya-swatantra-party",
            type="AFFILIATED_WITH",
            versionSummary=version_summary2,
            createdAt=datetime.now(),
        ),
    ]

    for relationship in relationships:
        await temp_db.put_relationship(relationship)

    result = await temp_db.list_relationships()
    assert len(result) == 2
    assert all(isinstance(rel, Relationship) for rel in result)


@pytest.mark.asyncio
async def test_list_relationships_with_pagination(temp_db, sample_actor):
    """Test listing relationships with pagination."""
    relationships = []
    for i in range(5):
        version_summary = VersionSummary(
            entityOrRelationshipId=f"relationship:person/person-{i}:organization/org-{i}:MEMBER_OF",
            type="RELATIONSHIP",
            versionNumber=1,
            actor=sample_actor,
            changeDescription=f"Relationship {i}",
            createdAt=datetime.now(),
        )
        relationship = Relationship(
            sourceEntityId=f"entity:person/person-{i}",
            targetEntityId=f"entity:organization/org-{i}",
            type="MEMBER_OF",
            versionSummary=version_summary,
            createdAt=datetime.now(),
        )
        relationships.append(relationship)
        await temp_db.put_relationship(relationship)

    result = await temp_db.list_relationships(limit=2, offset=1)
    assert len(result) == 2
