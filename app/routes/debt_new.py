"""
New debt management API endpoints using repository pattern and enhanced models.
Provides RESTful API for debt management that exactly matches frontend expectations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
from uuid import UUID

from app.repositories.debt_repository import DebtRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.models.debt import (
    DebtResponse, DebtCreate, DebtUpdate, DebtType, PaymentFrequency
)
from app.models.payment import (
    PaymentHistoryResponse, PaymentCreate, PaymentStatus
)
from app.models.analytics import DebtSummaryResponse
from app.middleware.auth import CurrentUser, require_authentication
from app.utils.auth import AuthUtils

router = APIRouter()


# Request/Response models
class PaymentRecordRequest(BaseModel):
    """Request model for recording a payment"""
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$', description="Payment date in YYYY-MM-DD format")
    principal_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to principal")
    interest_portion: Optional[float] = Field(None, ge=0, description="Portion that goes to interest")
    notes: Optional[str] = Field(None, max_length=1000, description="Payment notes")


class PaymentRecordResponse(BaseModel):
    """Response model for payment recording with celebration data"""
    payment: PaymentHistoryResponse = Field(..., description="Payment details")
    debt: DebtResponse = Field(..., description="Updated debt details")
    celebration: Dict[str, Any] = Field(..., description="Celebration data for frontend")
    message: str = Field(..., description="Success message")


class DebtSummaryResponse(BaseModel):
    """Enhanced debt summary for dashboard"""
    total_debt: float = Field(..., description="Total debt across all accounts")
    total_monthly_payments: float = Field(..., description="Total monthly minimum payments")
    average_interest_rate: float = Field(..., description="Average interest rate across debts")
    debt_count: int = Field(..., description="Total number of active debts")
    high_priority_count: int = Field(..., description="Number of high priority debts")
    upcoming_payments_count: int = Field(..., description="Number of payments due in next 7 days")
    debts: List[DebtResponse] = Field(..., description="All active debts")


@router.get("/", response_model=List[DebtResponse])
async def get_user_debts(
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Only return active debts"),
    debt_type: Optional[DebtType] = Query(None, description="Filter by debt type"),
    high_priority_only: bool = Query(False, description="Only return high priority debts"),
    sort_by: str = Query("due_date", description="Sort field (name, debt_type, current_balance, interest_rate, due_date)"),
    sort_order: str = Query("ASC", description="Sort order (ASC, DESC)")
) -> List[DebtResponse]:
    """
    Get all debts for the current user with filtering and sorting options.
    Returns debts in the exact format expected by the frontend.
    """
    debt_repo = DebtRepository()

    try:
        # Get user debts with filtering
        debts = await debt_repo.get_user_debts(
            user_id=current_user.id,
            is_active=active_only,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Apply additional filters
        if debt_type:
            debts = [d for d in debts if d.debt_type == debt_type]

        if high_priority_only:
            debts = [d for d in debts if d.is_high_priority]

        # Convert to frontend-compatible response format
        debt_responses = [DebtResponse.from_debt_in_db(debt) for debt in debts]

        return debt_responses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve debts: {str(e)}"
        )


@router.post("/", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
    debt_data: DebtCreate,
    current_user: CurrentUser
) -> DebtResponse:
    """
    Create a new debt for the current user.
    Validates all input data and ensures proper relationships.
    """
    debt_repo = DebtRepository()

    try:
        # Validate user authorization (debt_data should include user_id)
        if debt_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create debt for another user"
            )

        # Create the debt
        new_debt = await debt_repo.create_debt(debt_data)

        if not new_debt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create debt"
            )

        # Return frontend-compatible response
        return DebtResponse.from_debt_in_db(new_debt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create debt: {str(e)}"
        )


@router.get("/{debt_id}", response_model=DebtResponse)
async def get_debt(
    debt_id: UUID,
    current_user: CurrentUser
) -> DebtResponse:
    """
    Get a specific debt by ID.
    Ensures user can only access their own debts.
    """
    debt_repo = DebtRepository()

    try:
        # Get the debt
        debt = await debt_repo.get_by_id(debt_id)

        if not debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        # Verify ownership
        if debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this debt"
            )

        # Verify debt is active
        if not debt.is_active:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Debt is no longer active"
            )

        # Return frontend-compatible response
        return DebtResponse.from_debt_in_db(debt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve debt: {str(e)}"
        )


@router.put("/{debt_id}", response_model=DebtResponse)
async def update_debt(
    debt_id: UUID,
    debt_update: DebtUpdate,
    current_user: CurrentUser
) -> DebtResponse:
    """
    Update an existing debt.
    Validates ownership and ensures data consistency.
    """
    debt_repo = DebtRepository()

    try:
        # Verify debt exists and user owns it
        existing_debt = await debt_repo.get_by_id(debt_id)

        if not existing_debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        if existing_debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this debt"
            )

        # Update the debt
        updated_debt = await debt_repo.update_debt(debt_id, debt_update.model_dump(exclude_unset=True))

        if not updated_debt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update debt"
            )

        # Return frontend-compatible response
        return DebtResponse.from_debt_in_db(updated_debt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update debt: {str(e)}"
        )


@router.delete("/{debt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_debt(
    debt_id: UUID,
    current_user: CurrentUser
) -> None:
    """
    Soft delete a debt (mark as inactive).
    Ensures user can only delete their own debts.
    """
    debt_repo = DebtRepository()

    try:
        # Verify debt exists and user owns it
        existing_debt = await debt_repo.get_by_id(debt_id)

        if not existing_debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        if existing_debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this debt"
            )

        # Soft delete the debt
        success = await debt_repo.delete(debt_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete debt"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete debt: {str(e)}"
        )


@router.post("/{debt_id}/payment", response_model=PaymentRecordResponse)
async def record_payment(
    debt_id: UUID,
    payment_data: PaymentRecordRequest,
    current_user: CurrentUser
) -> PaymentRecordResponse:
    """
    Record a payment for a specific debt.
    Updates debt balance and triggers celebration system.
    """
    debt_repo = DebtRepository()
    payment_repo = PaymentRepository()

    try:
        # Verify debt exists and user owns it
        debt = await debt_repo.get_by_id(debt_id)

        if not debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        if debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to make payments on this debt"
            )

        if not debt.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot make payments on inactive debt"
            )

        # Validate payment amount doesn't exceed balance
        if payment_data.amount > debt.current_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount cannot exceed current balance"
            )

        # Create payment record
        payment_create = PaymentCreate(
            debt_id=debt_id,
            user_id=current_user.id,
            amount=payment_data.amount,
            payment_date=payment_data.payment_date,
            principal_portion=payment_data.principal_portion,
            interest_portion=payment_data.interest_portion,
            notes=payment_data.notes,
            status=PaymentStatus.CONFIRMED
        )

        # Record payment (this also updates debt balance in transaction)
        payment = await payment_repo.create_payment(payment_create)

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record payment"
            )

        # Get updated debt
        updated_debt = await debt_repo.get_by_id(debt_id)

        # Generate celebration data
        celebration = await _generate_celebration_data(
            payment, updated_debt, debt.current_balance
        )

        # Convert to frontend-compatible responses
        payment_response = PaymentHistoryResponse.from_payment_in_db(payment)
        debt_response = DebtResponse.from_debt_in_db(updated_debt)

        return PaymentRecordResponse(
            payment=payment_response,
            debt=debt_response,
            celebration=celebration,
            message="Payment recorded successfully!"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record payment: {str(e)}"
        )


@router.get("/summary", response_model=DebtSummaryResponse)
async def get_debt_summary(
    current_user: CurrentUser
) -> DebtSummaryResponse:
    """
    Get comprehensive debt summary for dashboard.
    Includes totals, averages, and upcoming payments.
    """
    debt_repo = DebtRepository()

    try:
        # Get debt summary data
        summary_data = await debt_repo.get_debt_summary(current_user.id)

        # Get all active debts for the response
        debts = await debt_repo.get_user_debts(
            user_id=current_user.id,
            is_active=True,
            sort_by="due_date"
        )

        # Calculate upcoming payments (due in next 7 days)
        today = date.today()
        next_week = today + timedelta(days=7)
        upcoming_payments_count = sum(
            1 for debt in debts
            if debt.due_date and today <= debt.due_date <= next_week
        )

        # Convert debts to frontend-compatible format
        debt_responses = [DebtResponse.from_debt_in_db(debt) for debt in debts]

        return DebtSummaryResponse(
            total_debt=summary_data["total_debt"],
            total_monthly_payments=summary_data["total_monthly_payments"],
            average_interest_rate=summary_data["average_interest_rate"],
            debt_count=summary_data["debt_count"],
            high_priority_count=summary_data["high_priority_count"],
            upcoming_payments_count=upcoming_payments_count,
            debts=debt_responses
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get debt summary: {str(e)}"
        )


@router.get("/reminders", response_model=List[Dict[str, Any]])
async def get_payment_reminders(
    current_user: CurrentUser,
    days_ahead: int = Query(7, description="Number of days to look ahead for reminders")
) -> List[Dict[str, Any]]:
    """
    Get payment reminders for upcoming due dates.
    """
    debt_repo = DebtRepository()

    try:
        # Get active debts
        debts = await debt_repo.get_user_debts(current_user.id, is_active=True)

        # Find debts with due dates within the specified period
        today = date.today()
        cutoff_date = today + timedelta(days=days_ahead)

        reminders = []
        for debt in debts:
            if debt.due_date:
                due_date = debt.due_date
                if today <= due_date <= cutoff_date:
                    days_until_due = (due_date - today).days

                    reminder = {
                        "debt_id": str(debt.id),
                        "debt_name": debt.name,
                        "lender": debt.lender,
                        "due_date": debt.due_date,
                        "minimum_payment": debt.minimum_payment,
                        "days_until_due": days_until_due,
                        "urgency": "overdue" if days_until_due < 0 else "due_soon" if days_until_due <= 3 else "upcoming"
                    }
                    reminders.append(reminder)

        # Sort by due date (soonest first)
        reminders.sort(key=lambda x: x["due_date"])

        return reminders

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment reminders: {str(e)}"
        )


@router.get("/high-priority", response_model=List[DebtResponse])
async def get_high_priority_debts(
    current_user: CurrentUser
) -> List[DebtResponse]:
    """
    Get all high priority debts for the user.
    """
    debt_repo = DebtRepository()

    try:
        debts = await debt_repo.get_high_priority_debts(current_user.id)
        debt_responses = [DebtResponse.from_debt_in_db(debt) for debt in debts]

        return debt_responses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get high priority debts: {str(e)}"
        )


async def _generate_celebration_data(
    payment, updated_debt, previous_balance: float
) -> Dict[str, Any]:
    """
    Generate celebration data based on payment impact.
    """
    celebration = {
        "should_celebrate": False,
        "celebration_type": "payment",
        "message": "",
        "confetti": False,
        "fireworks": False,
        "trophy": False
    }

    # Calculate payment impact
    payment_percentage = (payment.amount / previous_balance) * 100
    remaining_percentage = (updated_debt.current_balance / updated_debt.principal_amount) * 100

    # Determine celebration level
    if payment_percentage >= 50:  # Major payment
        celebration.update({
            "should_celebrate": True,
            "message": f"🎉 Amazing! You paid off {payment_percentage:.1f}% of your {updated_debt.name}!",
            "confetti": True,
            "fireworks": True
        })
    elif payment_percentage >= 25:  # Significant payment
        celebration.update({
            "should_celebrate": True,
            "message": f"🎊 Great job! You paid off {payment_percentage:.1f}% of your {updated_debt.name}!",
            "confetti": True
        })
    elif payment_percentage >= 10:  # Good payment
        celebration.update({
            "should_celebrate": True,
            "message": f"👍 Well done! You made a solid payment on your {updated_debt.name}!",
            "confetti": False
        })

    # Check for milestone achievements
    if remaining_percentage <= 25:  # Quarter paid off
        celebration["message"] += " 🌟 You're over 75% done!"
        celebration["trophy"] = True
    elif remaining_percentage <= 50:  # Half paid off
        celebration["message"] += " 🎯 Halfway there!"
        celebration["trophy"] = True

    # Check if debt is paid off
    if updated_debt.current_balance <= 0:
        celebration.update({
            "should_celebrate": True,
            "celebration_type": "debt_paid_off",
            "message": f"🎉🎊 CONGRATULATIONS! You paid off your {updated_debt.name} completely!",
            "confetti": True,
            "fireworks": True,
            "trophy": True
        })

    return celebration
