"""Organization-specific models."""

from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field

if TYPE_CHECKING:
    from .entity import Entity, EntitySubType


class GovernmentType(str, Enum):
    """Types of government entities."""

    FEDERAL = "federal"
    PROVINCIAL = "provincial"
    LOCAL = "local"
    OTHER = "other"
    UNKNOWN = "unknown"


# Import at the end to avoid circular dependency
from .entity import Entity, EntitySubType


class Organization(Entity):
    """Organization entity."""

    type: Literal["organization"] = Field(
        default="organization", description="Entity type, always organization"
    )


class PoliticalParty(Organization):
    """Political party organization."""

    sub_type: Literal[EntitySubType.POLITICAL_PARTY] = Field(
        default=EntitySubType.POLITICAL_PARTY,
        description="Organization subtype, always political_party",
    )


class GovernmentBody(Organization):
    """Government body organization."""

    sub_type: Literal[EntitySubType.GOVERNMENT_BODY] = Field(
        default=EntitySubType.GOVERNMENT_BODY,
        description="Organization subtype, always government_body",
    )
    government_type: Optional[GovernmentType] = Field(
        None, description="Type of government (federal, provincial, local)"
    )
