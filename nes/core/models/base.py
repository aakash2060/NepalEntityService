"""Base models using Pydantic."""

from enum import Enum
from typing import Annotated, Dict, Optional

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    constr,
    field_validator,
    model_validator,
)

from nes.core.identifiers.builders import break_entity_id
from nes.core.identifiers.validators import is_valid_entity_id


# E.164 phone number, e.g., "+977123456789"
E164PhoneStr = constr(pattern=r"^\+[1-9]\d{1,14}$")


class Language(str, Enum):
    """Supported languages."""

    EN = "en"
    NE = "ne"


LangField = Annotated[Language, Field(..., description="Language code")]


class NameKind(str, Enum):
    """Kinds of names."""

    PRIMARY = "PRIMARY"
    ALIAS = "ALIAS"
    ALTERNATE = "ALTERNATE"
    BIRTH = "BIRTH_NAME"
    OFFICIAL = "BIRTH_NAME"


class NamePart(str, Enum):
    """Parts of a name."""

    FULL = "full"
    FIRST = "first"
    MIDDLE = "middle"
    LAST = "last"
    PREFIX = "prefix"
    SUFFIX = "suffix"


class ProvenanceMethod(str, Enum):
    """Source of the data."""

    HUMAN = "human"
    LLM = "llm"
    TRANSLATION_SERVICE = "translation_service"
    # Imported from a data source
    IMPORTED = "imported"


class LangTextValue(BaseModel):
    """Text with provenance tracking."""

    model_config = ConfigDict(extra="forbid")

    value: str
    provenance: Optional[ProvenanceMethod] = None


class LangText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: Optional[LangTextValue] = Field(
        None,
        description="English or romanized Nepali",
    )
    ne: Optional[LangTextValue] = Field(
        None,
        description="Nepali (Devanagari)",
    )


class CursorPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_more: bool
    offset: int = 0
    count: int


class NameParts(BaseModel):
    """Name parts dictionary."""

    model_config = ConfigDict(extra="forbid")

    full: str
    first: Optional[str] = None
    middle: Optional[str] = None
    last: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class Name(BaseModel):
    """Represents a name with language and kind classification."""

    model_config = ConfigDict(extra="forbid")

    kind: NameKind = Field(..., description="Type of name")
    en: Optional[NameParts] = Field(None, description="English/romanized name parts")
    ne: Optional[NameParts] = Field(None, description="Nepali (Devanagari) name parts")

    @model_validator(mode="after")
    def validate_at_least_one_language(self) -> "Name":
        if not self.en and not self.ne:
            raise ValueError("Name must have at least one of en or ne")
        return self


class ContactType(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    TWITTER = "TWITTER"
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    TELEGRAM = "TELEGRAM"
    WECHAT = "WECHAT"
    OTHER = "OTHER"


class Contact(BaseModel):
    type: ContactType
    value: str

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_value_by_type(self) -> "Contact":
        t = self.type
        v = self.value
        if t == ContactType.EMAIL:
            # Re-parse as EmailStr for validation, but store original string
            EmailStr.validate(v)
        elif t in {
            ContactType.URL,
            ContactType.TWITTER,
            ContactType.FACEBOOK,
            ContactType.INSTAGRAM,
            ContactType.LINKEDIN,
        }:
            # Accept any URL (http/https)
            AnyUrl.validate(v)
        elif t == ContactType.PHONE or t == ContactType.WHATSAPP:
            # E.164 phone format
            if not E164PhoneStr.regex.match(v):
                raise ValueError("PHONE/WHATSAPP must be E.164 (e.g., +977123456789)")
        # TELEGRAM/WECHAT/OTHER are free-form (usernames/IDs/handles)
        return self


class Address(BaseModel):
    """Address information."""

    model_config = ConfigDict(extra="forbid")

    location_id: Optional[str] = Field(None, description="Location identifier")
    description: Optional[str] = Field(None, description="Address description")

    @field_validator("location_id")
    @classmethod
    def validate_location_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not is_valid_entity_id(v):
            raise ValueError("location_id must be a valid entity ID")
        components = break_entity_id(v)
        if components.type != "location":
            raise ValueError("location_id must reference a location entity")
        return v


class EntityPictureType(str, Enum):
    """Types of entity pictures."""

    THUMB = "thumb"
    FULL = "full"
    WIDE = "wide"


class EntityPicture(BaseModel):
    """Picture information for an entity."""

    model_config = ConfigDict(extra="forbid")

    type: EntityPictureType = Field(..., description="Picture type")
    url: str = Field(..., description="Picture URL")
    width: Optional[int] = Field(None, description="Picture width in pixels")
    height: Optional[int] = Field(None, description="Picture height in pixels")
    description: Optional[str] = Field(None, description="Picture description")
