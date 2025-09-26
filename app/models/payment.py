from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, computed_field
from uuid import UUID, uuid4


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "completed"  # Changed to match database constraint
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentBase(BaseModel):
    """Base payment model with core fields"""
    debt_id: UUID = Field(..., description="ID of the debt this payment is for")
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_date: Union[str, date] = Field(..., description="Payment date in YYYY-MM-DD format")
    principal_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to principal")
    interest_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to interest")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes about the payment")
    status: PaymentStatus = Field(default=PaymentStatus.CONFIRMED, description="Payment status")

    @field_validator('payment_date')
    @classmethod
    def validate_payment_date(cls, v: Union[str, date]) -> Union[str, date]:
        """Validate payment date format"""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError("Payment date must be in YYYY-MM-DD format")
        raise ValueError("Payment date must be a string in YYYY-MM-DD format or date object")

    @field_validator('principal_portion', 'interest_portion')
    @classmethod
    def validate_portions(cls, v: Optional[float]) -> Optional[float]:
        """Validate payment portions are non-negative"""
        if v is not None and v < 0:
            raise ValueError("Payment portions cannot be negative")
        return v


class PaymentCreate(BaseModel):
    """Model for creating a new payment"""
    debt_id: UUID = Field(..., description="ID of the debt this payment is for")
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Payment date in YYYY-MM-DD format")
    principal_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to principal")
    interest_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to interest")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes about the payment")
    status: PaymentStatus = Field(default=PaymentStatus.CONFIRMED, description="Payment status")
    
    # Internal field
    user_id: UUID

    @field_validator('payment_date')
    @classmethod
    def validate_payment_date(cls, v: Union[str, date]) -> Union[str, date]:
        """Validate payment date format"""
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError("Payment date must be in YYYY-MM-DD format")
        raise ValueError("Payment date must be a string in YYYY-MM-DD format or date object")


class PaymentInDB(PaymentBase):
    """Database representation of payment"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    blockchain_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class PaymentHistoryResponse(BaseModel):
    """Response model matching frontend PaymentHistoryItem interface exactly"""
    id: str = Field(..., description="Unique payment identifier")
    debt_id: str = Field(..., description="ID of the debt this payment is for")
    amount: float = Field(..., description="Payment amount")
    payment_date: str = Field(..., description="Payment date in YYYY-MM-DD format")
    principal_portion: Optional[float] = Field(None, description="Portion that goes to principal")
    interest_portion: Optional[float] = Field(None, description="Portion that goes to interest")
    notes: Optional[str] = Field(None, description="Additional notes about the payment")

    @computed_field
    @property
    def date(self) -> str:
        """Compatibility field mapping to payment_date"""
        return self.payment_date

    @classmethod
    def from_payment_in_db(cls, payment: PaymentInDB) -> "PaymentHistoryResponse":
        """Convert PaymentInDB to PaymentHistoryResponse"""
        # Convert date back to string format for API response
        payment_date = payment.payment_date
        if isinstance(payment_date, date):
            payment_date = payment_date.strftime('%Y-%m-%d')

        return cls(
            id=str(payment.id),
            debt_id=str(payment.debt_id),
            amount=payment.amount,
            payment_date=payment_date,
            principal_portion=payment.principal_portion,
            interest_portion=payment.interest_portion,
            notes=payment.notes
        )


class PaymentUpdate(BaseModel):
    """Model for updating an existing payment"""
    amount: Optional[float] = Field(None, gt=0)
    payment_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    principal_portion: Optional[float] = Field(None, ge=0)
    interest_portion: Optional[float] = Field(None, ge=0)
    status: Optional[PaymentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('payment_date')
    @classmethod
    def validate_payment_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate payment date format"""
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Payment date must be in YYYY-MM-DD format")
        return v

    class Config:
        arbitrary_types_allowed = True


# Legacy compatibility - alias for PaymentHistoryResponse
Payment = PaymentHistoryResponse