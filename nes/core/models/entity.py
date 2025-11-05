"""Entity model using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)

from nes.core.identifiers import build_entity_id

from ..constraints import (
    MAX_SLUG_LENGTH,
    MIN_SLUG_LENGTH,
    SLUG_PATTERN,
)
from .base import LangText, Contact, Name, NameKind
from .version import VersionSummary


class IdentifierScheme(str, Enum):
    """External identifier schemes."""

    WIKIPEDIA = "wikipedia"
    WIKIDATA = "wikidata"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    GITHUB = "github"
    DOI = "doi"
    ORCID = "orcid"
    OFFICIAL_WEBSITE = "official_website"
    OTHER = "other"


class ExternalIdentifier(BaseModel):
    """A normalized external identifier reference."""

    scheme: IdentifierScheme = Field(..., description="Type of external identifier")
    value: str = Field(..., min_length=1, description="Identifier value")
    url: Optional[AnyUrl] = Field(None, description="URL to the external resource")


class EntityType(str, Enum):
    """Types of entities."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"


class EntitySubType(str, Enum):
    """Subtypes for entities."""

    # Organization subtypes
    POLITICAL_PARTY = "political_party"
    GOVERNMENT_BODY = "government_body"

    # Location subtypes (using LocationType values)
    PROVINCE = "province"
    DISTRICT = "district"
    METROPOLITAN_CITY = "metropolitan_city"
    SUB_METROPOLITAN_CITY = "sub_metropolitan_city"
    MUNICIPALITY = "municipality"
    RURAL_MUNICIPALITY = "rural_municipality"
    WARD = "ward"
    CONSTITUENCY = "constituency"


class Entity(BaseModel):
    """Base entity model. At least one name with kind='DEFAULT' should be provided for all entities."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        ...,
        min_length=MIN_SLUG_LENGTH,
        max_length=MAX_SLUG_LENGTH,
        pattern=SLUG_PATTERN,
        description="URL-friendly identifier for the entity",
    )
    type: EntityType = Field(
        ...,
        description="Type of entity",
    )
    sub_type: Optional[EntitySubType] = Field(
        None,
        description="Subtype classification for the entity",
    )
    names: List[Name] = Field(
        ..., description="List of names associated with the entity"
    )
    misspelled_names: Optional[List[Name]] = Field(
        None, description="List of misspelled or alternative name variations"
    )
    version_summary: VersionSummary = Field(
        ..., description="Summary of the latest version information"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the entity was created"
    )
    identifiers: Optional[List[ExternalIdentifier]] = Field(
        None, description="External identifiers for the entity"
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorizing the entity"
    )
    attributes: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional attributes for the entity.",
    )
    contacts: Optional[List[Contact]] = Field(
        None, description="Contact information for the entity"
    )
    short_description: Optional[LangText] = Field(
        None,
        description="Brief description of the entity",
    )
    description: Optional[LangText] = Field(
        None,
        description="Detailed description of the entity",
    )
    attributions: Optional[LangText] = Field(
        None, description="Sources and attributions for the entity data"
    )

    @computed_field
    @property
    def id(self) -> str:
        return build_entity_id(self.type, self.sub_type, self.slug)

    @field_validator("names")
    @classmethod
    def validate_names(cls, v: List[Name]):
        if not any(name.kind == NameKind.PRIMARY for name in v):
            raise ValueError(f'At least one name with kind="{NameKind.PRIMARY}" is required')

        return v



