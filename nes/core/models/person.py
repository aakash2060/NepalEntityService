"""Person-specific models."""

from datetime import date
from typing import TYPE_CHECKING, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .base import LangText
from .entity import Entity


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


class Person(Entity):
    """Person entity."""

    type: Literal["person"] = Field(
        default="person", description="Entity type, always person"
    )
    education: Optional[List[Education]] = Field(
        None, description="Educational background"
    )
    positions: Optional[List[Position]] = Field(
        None, description="Professional positions held"
    )
