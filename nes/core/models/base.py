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


class Name(BaseModel):
    """Represents a name with language and kind classification."""

    model_config = ConfigDict(extra="forbid")

    parts: Dict[NamePart, str] = Field(..., description="Name parts dictionary")
    lang: LangField
    kind: NameKind = Field(
        ...,
        description="Type of name",
    )

    @field_validator("parts")
    @classmethod
    def validate_full_name_required(cls, v):
        if NamePart.FULL not in v:
            raise ValueError("A Name must always have the FULL name part.")
        return v


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
