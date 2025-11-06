"""Person-specific models."""

from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from nes.core.identifiers.validators import is_valid_entity_id
from .base import Address, LangText
from .entity import Entity


class Gender(str, Enum):
    """Gender enumeration."""
    
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class PersonDetails(BaseModel):
    """Personal details for a person."""
    
    model_config = ConfigDict(extra="forbid")
    
    birth_date: Optional[str] = Field(None, description="Birth date (may be partial, e.g., year only)")
    gender: Optional[Gender] = Field(None, description="Gender")
    birth_place: Optional[Address] = Field(None, description="Place of birth")
    address: Optional[Address] = Field(None, description="Current address")
    father_name: Optional[LangText] = Field(None, description="Father's name")
    mother_name: Optional[LangText] = Field(None, description="Mother's name")
    spouse_name: Optional[LangText] = Field(None, description="Spouse's name")


class Education(BaseModel):
    """Education record for a person."""

    model_config = ConfigDict(extra="forbid")

    institution: LangText = Field(..., description="Name of the educational institution")
    degree: Optional[LangText] = Field(None, description="Degree or qualification obtained")
    field: Optional[LangText] = Field(None, description="Field of study")
    start_year: Optional[int] = Field(None, description="Year education started")
    end_year: Optional[int] = Field(None, description="Year education completed")


class Position(BaseModel):
    """Position or role held by a person."""

    model_config = ConfigDict(extra="forbid")

    title: LangText = Field(..., description="Job title or position name")
    organization: Optional[LangText] = Field(
        None, description="Organization or company name"
    )
    start_date: Optional[date] = Field(
        None, description="Start date of the position"
    )
    end_date: Optional[date] = Field(None, description="End date of the position")
    description: Optional[str] = Field(
        None, max_length=200, description="Description of the position"
    )


class Symbol(BaseModel):
    """Election symbol."""

    model_config = ConfigDict(extra="forbid")

    name: LangText = Field(..., description="Symbol name")
    id: str = Field(..., description="Symbol identifier")


class Candidacy(BaseModel):
    """Electoral candidacy record."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., description="Candidate entity ID")
    election_year: int = Field(..., description="Election year")
    symbol: Symbol = Field(..., description="Election symbol")
    serial_no: str = Field(..., description="Serial number")
    party_id: Optional[str] = Field(None, description="Party entity ID")
    remarks: Optional[LangText] = Field(None, description="Additional remarks")
    votes_received: Optional[int] = Field(None, description="Number of votes received")
    elected: Optional[bool] = Field(None, description="Whether candidate was elected")

    @field_validator("candidate_id", "party_id")
    @classmethod
    def validate_entity_ids(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not is_valid_entity_id(v):
            raise ValueError("Must be a valid entity ID")
        return v


class ElectoralDetails(BaseModel):
    """Electoral details for a person."""

    model_config = ConfigDict(extra="forbid")

    candidacies: Optional[List[Candidacy]] = Field(
        None, description="List of electoral candidacies"
    )


class Person(Entity):
    """Person entity."""

    type: Literal["person"] = Field(
        default="person", description="Entity type, always person"
    )
    personal_details: Optional[PersonDetails] = Field(
        None, description="Personal details"
    )
    education: Optional[List[Education]] = Field(
        None, description="Educational background"
    )
    positions: Optional[List[Position]] = Field(
        None, description="Professional positions held"
    )
    electoral_details: Optional[ElectoralDetails] = Field(
        None, description="Electoral details"
    )
