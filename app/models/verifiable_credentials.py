from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID


class VerifiableCredentialBase(BaseModel):
    user_id: UUID
    debt_id: Optional[UUID] = None
    type: str
    vc_jwt: Optional[str] = None
    status: str = "issued"


class VerifiableCredentialCreate(VerifiableCredentialBase):
    pass


class VerifiableCredentialInDB(VerifiableCredentialBase):
    id: UUID = Field(default_factory=UUID, alias="id")
    issued_at: datetime = Field(default_factory=datetime.now)
    revoked_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class VerifiableCredential(VerifiableCredentialBase):
    id: UUID = Field(alias="id")
    issued_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class VerifiableCredentialUpdate(BaseModel):
    type: Optional[str] = None
    vc_jwt: Optional[str] = None
    status: Optional[str] = None
    revoked_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True