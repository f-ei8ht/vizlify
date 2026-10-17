from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import TonePreference


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    tone_preference: TonePreference = TonePreference.FRIENDLY


class ClientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    tone_preference: TonePreference | None = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    tone_preference: TonePreference
