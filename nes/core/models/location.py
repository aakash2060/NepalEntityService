"""Location-specific models."""

from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field, computed_field

if TYPE_CHECKING:
    from .entity import Entity


class LocationType(str, Enum):
    """Types of location entities."""

    PROVINCE = "province"
    DISTRICT = "district"
    METROPOLITAN_CITY = "metropolitan_city"
    SUB_METROPOLITAN_CITY = "sub_metropolitan_city"
    MUNICIPALITY = "municipality"
    RURAL_MUNICIPALITY = "rural_municipality"
    WARD = "ward"
    CONSTITUENCY = "constituency"


# Administrative levels for location entities
ADMINISTRATIVE_LEVELS = {
    LocationType.PROVINCE.value: 1,
    LocationType.DISTRICT.value: 2,
    LocationType.METROPOLITAN_CITY.value: 3,
    LocationType.SUB_METROPOLITAN_CITY.value: 3,
    LocationType.MUNICIPALITY.value: 3,
    LocationType.RURAL_MUNICIPALITY: 3,
    LocationType.WARD.value: 4,
    LocationType.CONSTITUENCY.value: None,  # Electoral boundary, not administrative
}


# Import at the end to avoid circular dependency
from .entity import Entity


class Location(Entity):
    """Location entity."""

    type: Literal["location"] = Field(
        default="location", description="Entity type, always location"
    )
    # TODO: Expose an API endpoint that allows internationalization of static fields like this one
    location_type: LocationType = Field(..., description="Type of location")
    parent: Optional[str] = Field(None, description="Entity ID of parent location")

    @computed_field
    @property
    def administrative_level(self) -> Optional[int]:
        """Administrative level in hierarchy."""
        return ADMINISTRATIVE_LEVELS.get(self.location_type.value)
