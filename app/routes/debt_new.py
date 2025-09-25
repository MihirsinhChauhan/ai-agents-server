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
    DebtResponse, DebtCreate, DebtCreateRequest, DebtUpdate, DebtType, PaymentFrequency
)
from app.models.payment import (
    PaymentHistoryResponse, PaymentCreate, PaymentStatus
)
from app.models.analytics import DebtSummaryResponse as AnalyticsDebtSummaryResponse
from app.middleware.auth import CurrentUser
from app.utils.auth import AuthUtils
from app.services.ai_service import AIService
from app.services.ai_insights_cache_service import AIInsightsCacheService
from app.databases.database import get_db, get_async_db_session
from sqlalchemy.ext.asyncio import AsyncSession
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def safe_invalidate_user_cache(ai_cache_service: AIInsightsCacheService, user_id: str) -> bool:
    """
    Safely invalidate user cache without affecting main operation.
    Isolates cache errors to prevent session corruption.
    Returns True if successful, False if failed.
    """
    try:
        logger.info(f"[CACHE] Attempting cache invalidation for user {user_id}")
        success = await ai_cache_service.invalidate_cache_for_user(user_id)
        if success:
            logger.info(f"[CACHE] Successfully invalidated cache for user {user_id}")
            return True
        else:
            logger.warning(f"[CACHE] Cache invalidation returned False for user {user_id}")
            return False
    except Exception as e:
        # Log the error with full details but don't propagate it
        logger.error(f"[CACHE] Cache invalidation failed for user {user_id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[CACHE] Full error traceback:", exc_info=True)
        # Cache failures should not affect the main operation - return False but continue
        return False


# Dependency injection - Fixed to use proper SQLAlchemy session
async def get_ai_cache_service() -> AIInsightsCacheService:
    """
    Get AI insights cache service instance with proper SQLAlchemy session.
    This creates a new session specifically for the AI cache service.
    """
    try:
        # Get SQLAlchemy AsyncSession (not AsyncPG connection)
        session_gen = get_async_db_session()
        session = await session_gen.__anext__()
        logger.debug("Created SQLAlchemy session for AI cache service")
        return AIInsightsCacheService(session)
    except Exception as e:
        logger.error(f"Failed to create AI cache service: {e}")
        raise


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
            include_inactive=not active_only
        )

        # Apply additional filters
        if debt_type:
            debts = [d for d in debts if d.debt_type == debt_type]

        if high_priority_only:
            debts = [d for d in debts if d.is_high_priority]

        # Apply sorting
        def get_sort_key(debt):
            if sort_by == "name":
                return debt.name.lower() if debt.name else ""
            elif sort_by == "debt_type":
                return debt.debt_type.value if debt.debt_type else ""
            elif sort_by == "current_balance":
                return debt.current_balance or 0
            elif sort_by == "interest_rate":
                return debt.interest_rate or 0
            elif sort_by == "due_date":
                return debt.due_date or date.max
            else:
                return debt.due_date or date.max

        reverse_order = sort_order.upper() == "DESC"
        debts.sort(key=get_sort_key, reverse=reverse_order)

        # Convert to frontend-compatible response format
        debt_responses = [DebtResponse.from_debt_in_db(debt) for debt in debts]

        return debt_responses

    except Exception as e:
        logger.error(f"[DEBT] Failed to retrieve debts for user {current_user.id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[DEBT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve debts: {str(e)}"
        )


@router.post("/", response_model=DebtResponse, status_code=status.HTTP_201_CREATED)
async def create_debt(
    debt_request: DebtCreateRequest,
    current_user: CurrentUser,
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
) -> DebtResponse:
    """
    Create a new debt for the current user.
    Validates all input data and ensures proper relationships.
    """
    logger.info(f"[DEBT] Creating debt for user {current_user.id}: {debt_request.name}")
    debt_repo = DebtRepository()

    try:
        # Create DebtCreate model with user_id from authenticated user
        debt_data = DebtCreate(
            user_id=current_user.id,
            name=debt_request.name,
            debt_type=debt_request.debt_type,
            principal_amount=debt_request.principal_amount,
            current_balance=debt_request.current_balance,
            interest_rate=debt_request.interest_rate,
            is_variable_rate=debt_request.is_variable_rate,
            minimum_payment=debt_request.minimum_payment,
            due_date=debt_request.due_date,
            lender=debt_request.lender,
            remaining_term_months=debt_request.remaining_term_months,
            is_tax_deductible=debt_request.is_tax_deductible,
            payment_frequency=debt_request.payment_frequency,
            is_high_priority=debt_request.is_high_priority,
            notes=debt_request.notes
        )

        # Create the debt
        logger.debug(f"[DEBT] Calling repository to create debt for user {current_user.id}")
        new_debt = await debt_repo.create_debt(debt_data)

        if not new_debt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create debt"
            )

        logger.info(f"[DEBT] Successfully created debt {new_debt.id} for user {current_user.id}")

        # Invalidate AI insights cache since debt portfolio has changed
        # This is isolated and won't affect the main operation
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id}")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id}")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt creation succeeded")

        logger.info(f"[DEBT] Debt creation completed successfully for user {current_user.id}")
        # Return frontend-compatible response
        return DebtResponse.from_debt_in_db(new_debt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEBT] Failed to create debt for user {current_user.id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[DEBT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create debt: {str(e)}"
        )


@router.get("/summary", response_model=AnalyticsDebtSummaryResponse)
async def get_debt_summary(
    current_user: CurrentUser
) -> AnalyticsDebtSummaryResponse:
    """
    Get comprehensive debt summary for dashboard.
    Includes totals, averages, and upcoming payments.
    """
    debt_repo = DebtRepository()

    try:
        # Get debt summary data - this returns a DebtSummaryResponse object, not a dict
        summary_data = await debt_repo.get_debt_summary(current_user.id)

        # Get all active debts to calculate upcoming payments
        debts = await debt_repo.get_user_debts(
            user_id=current_user.id,
            include_inactive=False
        )

        # Calculate upcoming payments (due in next 7 days)
        today = date.today()
        next_week = today + timedelta(days=7)
        upcoming_payments_count = sum(
            1 for debt in debts
            if debt.due_date and today <= debt.due_date <= next_week
        )

        # Use attribute access instead of dict access since summary_data is a DebtSummaryResponse object
        return AnalyticsDebtSummaryResponse(
            total_debt=summary_data.total_debt,
            total_interest_paid=0.0,  # TODO: Calculate actual interest paid from payment history
            total_minimum_payments=summary_data.total_minimum_payments,
            average_interest_rate=summary_data.average_interest_rate,
            debt_count=summary_data.debt_count,
            high_priority_count=summary_data.high_priority_count,
            upcomingPaymentsCount=upcoming_payments_count  # Use camelCase to match frontend
        )

    except Exception as e:
        logger.error(f"[DEBT] Failed to get debt summary for user {current_user.id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[DEBT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get debt summary: {str(e)}"
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
    current_user: CurrentUser,
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
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

        # Invalidate AI insights cache since debt portfolio has changed
        # This is isolated and won't affect the main operation
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id} after update")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id} after update")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt update succeeded")

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
    current_user: CurrentUser,
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
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

        # Invalidate AI insights cache since debt portfolio has changed
        # This is isolated and won't affect the main operation
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id} after delete")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id} after delete")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt deletion succeeded")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DEBT] Failed to delete debt for user {current_user.id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[DEBT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete debt: {str(e)}"
        )


@router.post("/{debt_id}/payment", response_model=PaymentRecordResponse)
async def record_payment(
    debt_id: UUID,
    payment_data: PaymentRecordRequest,
    current_user: CurrentUser,
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
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

        # Invalidate AI insights cache since debt balance has changed
        # This is isolated and won't affect the main operation
        logger.debug(f"[PAYMENT] Attempting cache invalidation for user {current_user.id} after payment")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[PAYMENT] Cache invalidation successful for user {current_user.id} after payment")
        else:
            logger.warning(f"[PAYMENT] Cache invalidation failed for user {current_user.id}, but payment recording succeeded")

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
        logger.error(f"[PAYMENT] Failed to record payment for user {current_user.id}, debt {debt_id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[PAYMENT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record payment: {str(e)}"
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
        debts = await debt_repo.get_user_debts(current_user.id, include_inactive=False)

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
