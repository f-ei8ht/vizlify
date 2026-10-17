import json
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, EmailStr

from app.models.enums import TonePreference

SOURCE = Path(__file__).with_name("demo_agency.json")


class DemoClient(BaseModel):
    name: str
    email: EmailStr
    tone_preference: TonePreference


class DemoMilestone(BaseModel):
    title: str
    amount: Decimal
    due_in_days: int


class DemoTeamMember(BaseModel):
    name: str
    paypal_email: EmailStr
    share_percent: Decimal


class DemoProject(BaseModel):
    name: str
    currency: str
    client_name: str
    milestones: list[DemoMilestone]
    team: list[DemoTeamMember]


class DemoAgency(BaseModel):
    business_name: str
    paypal_email: EmailStr
    clients: list[DemoClient]
    project: DemoProject


def load_demo_agency(path: Path = SOURCE) -> DemoAgency:
    return DemoAgency.model_validate(json.loads(path.read_text(encoding="utf-8")))
