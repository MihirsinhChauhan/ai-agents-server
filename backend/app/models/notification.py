from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class NotificationBase(BaseModel):
    user_id: UUID
    type: str
    title: str
    message: str
    read: bool = False


class NotificationCreate(NotificationBase):
    pass


class NotificationInDB(NotificationBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    read_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Notification(NotificationBase):
    id: UUID = Field(alias="id")
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class NotificationUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    read: Optional[bool] = None
    read_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True