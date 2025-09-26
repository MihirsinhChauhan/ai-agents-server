from datetime import datetime, date
from enum import Enum
from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, computed_field
from uuid import UUID, uuid4


class DebtType(str, Enum):
    """Debt types matching frontend TypeScript interface exactly"""
    CREDIT_CARD = "credit_card"
    PERSONAL_LOAN = "personal_loan"
    HOME_LOAN = "home_loan"
    VEHICLE_LOAN = "vehicle_loan"
    EDUCATION_LOAN = "education_loan"
    BUSINESS_LOAN = "business_loan"
    GOLD_LOAN = "gold_loan"
    OVERDRAFT = "overdraft"
    EMI = "emi"
    OTHER = "other"


class PaymentFrequency(str, Enum):
    """Payment frequency matching frontend TypeScript interface exactly"""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class DebtSource(str, Enum):
    """Source of debt data"""
    MANUAL = "manual"
    PLAID = "plaid"


class DebtBase(BaseModel):
    """Base debt model with core fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Debt name")
    debt_type: DebtType = Field(..., description="Type of debt")
    principal_amount: float = Field(..., gt=0, description="Original loan amount")
    current_balance: float = Field(..., ge=0, description="Current outstanding balance")
    interest_rate: float = Field(..., ge=0, le=100, description="Annual interest rate as percentage")
    is_variable_rate: bool = Field(default=False, description="Whether interest rate is variable")
    minimum_payment: float = Field(..., gt=0, description="Minimum monthly payment required")
    due_date: Optional[date] = Field(None, description="Due date")
    lender: str = Field(..., min_length=1, max_length=255, description="Name of the lender")
    remaining_term_months: Optional[int] = Field(None, gt=0, description="Remaining term in months")
    is_tax_deductible: bool = Field(default=False, description="Whether interest is tax deductible")
    payment_frequency: PaymentFrequency = Field(default=PaymentFrequency.MONTHLY, description="Payment frequency")
    is_high_priority: bool = Field(default=False, description="Whether this debt is high priority")
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")
    
    # Legacy fields for backward compatibility
    source: DebtSource = Field(default=DebtSource.MANUAL, description="Source of debt data")

    @field_validator('interest_rate')
    @classmethod
    def validate_interest_rate(cls, v: float) -> float:
        """Validate interest rate is reasonable"""
        if v < 0:
            raise ValueError("Interest rate cannot be negative")
        if v > 100:
            raise ValueError("Interest rate cannot exceed 100%")
        return v

    @field_validator('current_balance')
    @classmethod
    def validate_current_balance(cls, v: float) -> float:
        """Validate current balance"""
        if v < 0:
            raise ValueError("Current balance cannot be negative")
        return v


class DebtCreateRequest(BaseModel):
    """Model for API request to create a new debt (without user_id)"""
    name: str = Field(..., min_length=1, max_length=255)
    debt_type: DebtType
    principal_amount: float = Field(..., gt=0)
    current_balance: float = Field(..., ge=0)
    interest_rate: float = Field(..., ge=0, le=100)
    is_variable_rate: bool = Field(default=False)
    minimum_payment: float = Field(..., gt=0)
    due_date: Optional[date] = Field(None)
    lender: str = Field(..., min_length=1, max_length=255)
    remaining_term_months: Optional[int] = Field(None, gt=0)
    is_tax_deductible: bool = Field(default=False)
    payment_frequency: PaymentFrequency = Field(default=PaymentFrequency.MONTHLY)
    is_high_priority: bool = Field(default=False)
    notes: Optional[str] = Field(None, max_length=1000)

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[Union[str, date]]) -> Optional[date]:
        """Validate due date format and convert to date object"""
        if v is None:
            return None

        # If already a date object, return it
        if isinstance(v, date):
            return v

        # If string, parse and convert to date
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError("Due date must be in YYYY-MM-DD format")

        raise ValueError("Due date must be a string in YYYY-MM-DD format or a date object")


class DebtCreate(BaseModel):
    """Model for creating a new debt (internal use with user_id)"""
    name: str = Field(..., min_length=1, max_length=255)
    debt_type: DebtType
    principal_amount: float = Field(..., gt=0)
    current_balance: float = Field(..., ge=0)
    interest_rate: float = Field(..., ge=0, le=100)
    is_variable_rate: bool = Field(default=False)
    minimum_payment: float = Field(..., gt=0)
    due_date: Optional[date] = Field(None)
    lender: str = Field(..., min_length=1, max_length=255)
    remaining_term_months: Optional[int] = Field(None, gt=0)
    is_tax_deductible: bool = Field(default=False)
    payment_frequency: PaymentFrequency = Field(default=PaymentFrequency.MONTHLY)
    is_high_priority: bool = Field(default=False)
    notes: Optional[str] = Field(None, max_length=1000)
    
    # Internal fields
    user_id: UUID
    source: DebtSource = Field(default=DebtSource.MANUAL)


class DebtInDB(DebtBase):
    """Database representation of debt"""
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    blockchain_id: Optional[str] = None
    is_active: bool = Field(default=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert DebtInDB model to dictionary suitable for caching and serialization.

        Handles proper serialization of:
        - UUIDs to strings
        - Enums to their values
        - Dates and datetimes to ISO format or original format
        - All other fields as-is

        Returns:
            Dict[str, Any]: Dictionary representation of the debt object
        """
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'name': self.name,
            'debt_type': self.debt_type.value,
            'principal_amount': self.principal_amount,
            'current_balance': self.current_balance,
            'interest_rate': self.interest_rate,
            'is_variable_rate': self.is_variable_rate,
            'minimum_payment': self.minimum_payment,
            'due_date': self.due_date.isoformat() if isinstance(self.due_date, date) else self.due_date,
            'lender': self.lender,
            'remaining_term_months': self.remaining_term_months,
            'is_tax_deductible': self.is_tax_deductible,
            'payment_frequency': self.payment_frequency.value,
            'is_high_priority': self.is_high_priority,
            'notes': self.notes,
            'source': self.source.value,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'blockchain_id': self.blockchain_id,
            'is_active': self.is_active
        }

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class DebtResponse(BaseModel):
    """Response model matching frontend TypeScript interface exactly"""
    id: str = Field(..., description="Unique debt identifier")
    name: str = Field(..., description="Debt name")
    debt_type: DebtType = Field(..., description="Type of debt")
    principal_amount: float = Field(..., description="Original loan amount")
    current_balance: float = Field(..., description="Current outstanding balance")
    interest_rate: float = Field(..., description="Annual interest rate as percentage")
    is_variable_rate: bool = Field(..., description="Whether interest rate is variable")
    minimum_payment: float = Field(..., description="Minimum monthly payment required")
    due_date: str = Field(..., description="Due date in YYYY-MM-DD format")
    lender: str = Field(..., description="Name of the lender")
    remaining_term_months: Optional[int] = Field(None, description="Remaining term in months")
    is_tax_deductible: bool = Field(..., description="Whether interest is tax deductible")
    payment_frequency: PaymentFrequency = Field(..., description="Payment frequency")
    is_high_priority: bool = Field(..., description="Whether this debt is high priority")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @computed_field
    @property
    def amount(self) -> float:
        """Compatibility field mapping to principal_amount"""
        return self.principal_amount

    @computed_field
    @property
    def remainingAmount(self) -> float:
        """Compatibility field mapping to current_balance"""
        return self.current_balance

    @computed_field
    @property
    def date(self) -> str:
        """Compatibility field mapping to due_date"""
        return self.due_date

    @computed_field
    @property
    def days_past_due(self) -> int:
        """Calculate days past due based on due_date"""
        if not self.due_date:
            return 0
        
        try:
            due_date_obj = datetime.strptime(self.due_date, '%Y-%m-%d').date()
            today = date.today()
            if today > due_date_obj:
                return (today - due_date_obj).days
        except ValueError:
            pass
        
        return 0

    @classmethod
    def from_debt_in_db(cls, debt: DebtInDB) -> "DebtResponse":
        """Convert DebtInDB to DebtResponse"""
        # Handle due_date conversion properly
        due_date_str = ""
        if debt.due_date:
            if isinstance(debt.due_date, date):
                due_date_str = debt.due_date.isoformat()
            elif isinstance(debt.due_date, str):
                due_date_str = debt.due_date

        return cls(
            id=str(debt.id),
            name=debt.name,
            debt_type=debt.debt_type,
            principal_amount=debt.principal_amount,
            current_balance=debt.current_balance,
            interest_rate=debt.interest_rate,
            is_variable_rate=debt.is_variable_rate,
            minimum_payment=debt.minimum_payment,
            due_date=due_date_str,
            lender=debt.lender,
            remaining_term_months=debt.remaining_term_months,
            is_tax_deductible=debt.is_tax_deductible,
            payment_frequency=debt.payment_frequency,
            is_high_priority=debt.is_high_priority,
            notes=debt.notes,
            created_at=debt.created_at.isoformat() if debt.created_at else None,
            updated_at=debt.updated_at.isoformat() if debt.updated_at else None
        )


class DebtUpdate(BaseModel):
    """Model for updating an existing debt"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    debt_type: Optional[DebtType] = None
    principal_amount: Optional[float] = Field(None, gt=0)
    current_balance: Optional[float] = Field(None, ge=0)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    is_variable_rate: Optional[bool] = None
    minimum_payment: Optional[float] = Field(None, gt=0)
    due_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    lender: Optional[str] = Field(None, min_length=1, max_length=255)
    remaining_term_months: Optional[int] = Field(None, gt=0)
    is_tax_deductible: Optional[bool] = None
    payment_frequency: Optional[PaymentFrequency] = None
    is_high_priority: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    details: Optional[Dict[str, Any]] = None

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate due date format"""
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Due date must be in YYYY-MM-DD format")
        return v

    class Config:
        arbitrary_types_allowed = True


class DebtSummaryResponse(BaseModel):
    """Response model for debt summary statistics"""
    total_debt: float = Field(..., description="Total current debt balance")
    total_interest_paid: float = Field(default=0.0, description="Total interest paid to date")
    total_minimum_payments: float = Field(..., description="Sum of all minimum payments")
    average_interest_rate: float = Field(..., description="Weighted average interest rate")
    debt_count: int = Field(..., description="Total number of active debts")
    high_priority_count: int = Field(..., description="Number of high priority debts")
    upcoming_payments_count: int = Field(default=0, description="Number of payments due soon")


# Legacy compatibility - alias for DebtResponse
Debt = DebtResponse