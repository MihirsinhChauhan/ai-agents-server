"""
Payment history API endpoints using repository pattern and enhanced models.
Provides RESTful API for payment management that matches frontend expectations.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, date
from uuid import UUID

from app.repositories.payment_repository import PaymentRepository
from app.repositories.debt_repository import DebtRepository
from app.models.payment import PaymentHistoryResponse, PaymentCreate, PaymentStatus
from app.models.debt import DebtResponse
from app.middleware.auth import CurrentUser
from app.models.analytics import UserStreakResponse

router = APIRouter()


@router.get("/", response_model=List[PaymentHistoryResponse])
async def get_user_payments(
    current_user: CurrentUser,
    debt_id: Optional[UUID] = Query(None, description="Filter by specific debt"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    status_filter: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of payments to return"),
    offset: int = Query(0, ge=0, description="Number of payments to skip")
) -> List[PaymentHistoryResponse]:
    """
    Get payment history for the current user with filtering options.
    Returns payments in the exact format expected by the frontend.
    """
    payment_repo = PaymentRepository()

    try:
        if debt_id:
            # Get payments for a specific debt
            payments = await payment_repo.get_debt_payments(
                debt_id=debt_id,
                user_id=current_user.id,
                limit=limit,
                offset=offset
            )
        else:
            # Get all user payments
            payments = await payment_repo.get_user_payments(
                user_id=current_user.id,
                start_date=start_date,
                end_date=end_date,
                status=status_filter,
                limit=limit,
                offset=offset
            )

        # Convert to frontend-compatible response format
        payment_responses = [PaymentHistoryResponse.from_payment_in_db(payment) for payment in payments]

        return payment_responses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(e)}"
        )


@router.get("/{payment_id}", response_model=PaymentHistoryResponse)
async def get_payment(
    payment_id: UUID,
    current_user: CurrentUser
) -> PaymentHistoryResponse:
    """
    Get a specific payment by ID.
    Ensures user can only access their own payments.
    """
    payment_repo = PaymentRepository()

    try:
        # Get the payment
        payment = await payment_repo.get_by_id(payment_id)

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        # Verify ownership
        if payment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this payment"
            )

        # Return frontend-compatible response
        return PaymentHistoryResponse.from_payment_in_db(payment)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment: {str(e)}"
        )


@router.put("/{payment_id}", response_model=PaymentHistoryResponse)
async def update_payment(
    payment_id: UUID,
    current_user: CurrentUser,
    notes: Optional[str] = None,
    status_update: Optional[PaymentStatus] = None
) -> PaymentHistoryResponse:
    """
    Update payment details (limited to notes and status for security).
    """
    payment_repo = PaymentRepository()

    try:
        # Verify payment exists and user owns it
        existing_payment = await payment_repo.get_by_id(payment_id)

        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if existing_payment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this payment"
            )

        # Prepare update data
        update_data = {}
        if notes is not None:
            update_data["notes"] = notes
        if status_update is not None:
            update_data["status"] = status_update

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields provided for update"
            )

        # Update the payment
        updated_payment = await payment_repo.update_payment(payment_id, update_data)

        if not updated_payment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update payment"
            )

        # Return frontend-compatible response
        return PaymentHistoryResponse.from_payment_in_db(updated_payment)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update payment: {str(e)}"
        )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: UUID,
    current_user: CurrentUser
) -> None:
    """
    Delete a payment record.
    Note: This may affect debt balance calculations.
    """
    payment_repo = PaymentRepository()

    try:
        # Verify payment exists and user owns it
        existing_payment = await payment_repo.get_by_id(payment_id)

        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )

        if existing_payment.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this payment"
            )

        # Delete the payment
        success = await payment_repo.delete(payment_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete payment"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete payment: {str(e)}"
        )


@router.get("/summary/overview", response_model=Dict[str, Any])
async def get_payment_summary(
    current_user: CurrentUser,
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze")
) -> Dict[str, Any]:
    """
    Get payment summary and analytics for the user.
    """
    payment_repo = PaymentRepository()

    try:
        # Get payment summary data
        summary_data = await payment_repo.get_payment_summary(current_user.id, months)

        # Get monthly payment trends
        trends = await payment_repo.get_monthly_payment_trends(current_user.id, months)

        return {
            "summary": summary_data,
            "trends": trends,
            "period_months": months
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment summary: {str(e)}"
        )


@router.get("/streaks", response_model=UserStreakResponse)
async def get_payment_streaks(
    current_user: CurrentUser
) -> UserStreakResponse:
    """
    Get user's payment streak information.
    """
    payment_repo = PaymentRepository()

    try:
        # Get streak data
        streak_data = await payment_repo.get_payment_streaks(current_user.id)

        return UserStreakResponse(
            user_id=current_user.id,
            current_streak=streak_data.get("current_streak", 0),
            longest_streak=streak_data.get("longest_streak", 0),
            last_check_in=streak_data.get("last_check_in"),
            total_payments_logged=streak_data.get("total_payments_logged", 0),
            milestones_achieved=streak_data.get("milestones_achieved", [])
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get payment streaks: {str(e)}"
        )


@router.post("/bulk-import")
async def bulk_import_payments(
    payments: List[PaymentCreate],
    current_user: CurrentUser
) -> Dict[str, Any]:
    """
    Bulk import multiple payments.
    Useful for importing historical payment data.
    """
    payment_repo = PaymentRepository()

    try:
        # Validate all payments belong to the user
        for payment in payments:
            if payment.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot import payments for another user"
                )

        # Import payments in bulk
        imported_payments = await payment_repo.bulk_create_payments(payments)

        return {
            "imported_count": len(imported_payments),
            "payments": [PaymentHistoryResponse.from_payment_in_db(p) for p in imported_payments],
            "message": f"Successfully imported {len(imported_payments)} payments"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import payments: {str(e)}"
        )


@router.get("/debt/{debt_id}/history", response_model=List[PaymentHistoryResponse])
async def get_debt_payment_history(
    debt_id: UUID,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of payments to return")
) -> List[PaymentHistoryResponse]:
    """
    Get complete payment history for a specific debt.
    """
    payment_repo = PaymentRepository()
    debt_repo = DebtRepository()

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
                detail="Not authorized to access this debt's payment history"
            )

        # Get payment history
        payments = await payment_repo.get_debt_payments(
            debt_id=debt_id,
            user_id=current_user.id,
            limit=limit
        )

        # Convert to frontend-compatible response format
        payment_responses = [PaymentHistoryResponse.from_payment_in_db(payment) for payment in payments]

        return payment_responses

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get debt payment history: {str(e)}"
        )


@router.get("/analytics/monthly", response_model=Dict[str, Any])
async def get_monthly_payment_analytics(
    current_user: CurrentUser,
    year: Optional[int] = Query(None, description="Year to analyze (defaults to current year)")
) -> Dict[str, Any]:
    """
    Get monthly payment analytics for the specified year.
    """
    payment_repo = PaymentRepository()

    if not year:
        year = datetime.now().year

    try:
        # Get monthly trends
        monthly_data = await payment_repo.get_monthly_payment_trends(current_user.id, months=12)

        # Group by month
        monthly_totals = {}
        for month in range(1, 13):
            monthly_totals[f"{year}-{month:02d}"] = 0

        for item in monthly_data:
            month_key = item["month"][:7]  # Extract YYYY-MM
            monthly_totals[month_key] = item["total_amount"]

        return {
            "year": year,
            "monthly_totals": monthly_totals,
            "total_yearly": sum(monthly_totals.values()),
            "best_month": max(monthly_totals.items(), key=lambda x: x[1]) if monthly_totals else None,
            "worst_month": min(monthly_totals.items(), key=lambda x: x[1]) if monthly_totals else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monthly analytics: {str(e)}"
        )
