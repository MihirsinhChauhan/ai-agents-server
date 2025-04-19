from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class DidStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class DidBase(BaseModel):
    user_id: UUID
    did: str
    status: DidStatus = DidStatus.ACTIVE


class DidCreate(DidBase):
    pass


class DidInDB(DidBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class Did(DidBase):
    id: UUID = Field(alias="id")
    created_at: datetime

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class DidUpdate(BaseModel):
    status: Optional[DidStatus] = None

    class Config:
        arbitrary_types_allowed = True