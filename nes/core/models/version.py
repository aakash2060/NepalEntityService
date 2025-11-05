"""Version models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from nes.core.identifiers import build_version_id

from ..constraints import MAX_SLUG_LENGTH, MIN_SLUG_LENGTH, SLUG_PATTERN


class Actor(BaseModel):
    slug: str = Field(
        ...,
        min_length=MIN_SLUG_LENGTH,
        max_length=MAX_SLUG_LENGTH,
        pattern=SLUG_PATTERN,
        description="URL-friendly identifier for the actor",
    )
    name: Optional[str] = None

    @computed_field
    @property
    def id(self) -> str:
        return f"actor:{self.slug}"


class VersionType(str, Enum):
    ENTITY = "ENTITY"
    RELATIONSHIP = "RELATIONSHIP"


class VersionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_or_relationship_id: str = Field(
        ..., description="ID of the entity or relationship this version belongs to"
    )
    type: VersionType
    version_number: int
    actor: Actor
    change_description: str
    created_at: datetime

    @computed_field
    @property
    def id(self) -> str:
        return build_version_id(self.entity_or_relationship_id, self.version_number)


class Version(VersionSummary):
    changes: Optional[Dict[str, Any]] = None
    snapshot: Optional[Dict[str, Any]] = None
