from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertBase(BaseModel):
    channel: str = "telegram"
    message: str
    telegram_message_id: str | None = None
    status: str = "sent"


class AlertCreate(AlertBase):
    incident_id: int


class AlertUpdate(BaseModel):
    status: str | None = None
    telegram_message_id: str | None = None


class AlertRead(AlertBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    created_at: datetime
    updated_at: datetime
