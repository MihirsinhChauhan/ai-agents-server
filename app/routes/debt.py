from datetime import datetime
from typing import List, Optional
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.databases.database import get_db, get_async_db_session, SupabaseDB
from app.dependencies import get_current_active_user, get_blockchain
from app.models.user import UserInDB
from app.models.debt import DebtCreate, DebtCreateRequest, DebtResponse, DebtUpdate, DebtSummaryResponse
from app.repositories.debt_repository import DebtRepository
from app.repositories.user_repository import UserRepository
from app.middleware.auth import CurrentUser
from app.blockchain_interface import BlockchainInterface
from app.services.ai_insights_cache_service import AIInsightsCacheService
from sqlalchemy.ext.asyncio import AsyncSession

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

# Dependency injection for repositories
async def get_debt_repo(db: SupabaseDB = Depends(get_db)) -> DebtRepository:
    """Get debt repository instance"""
    return DebtRepository()

async def get_user_repo(db: SupabaseDB = Depends(get_db)) -> UserRepository:
    """Get user repository instance"""
    return UserRepository(db)

async def get_ai_cache_service(db_session: AsyncSession = Depends(get_async_db_session)) -> AIInsightsCacheService:
    """Get AI insights cache service instance"""
    return AIInsightsCacheService(db_session)


@router.get("/", response_model=List[DebtResponse])
async def get_debts(
    current_user: CurrentUser,
    active_only: bool = Query(True, description="Only return active debts"),
    debt_repo: DebtRepository = Depends(get_debt_repo)
) -> List[DebtResponse]:
    """
    Get all debts for the current user
    """
    try:
        # Get debts using repository
        debts = await debt_repo.get_debts_by_user_id(current_user.id, active_only)

        # Convert to response models
        return [DebtResponse.from_debt_in_db(debt) for debt in debts]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve debts: {str(e)}"
        )


@router.post("/", response_model=DebtResponse)
async def create_debt(
    debt_request: DebtCreateRequest,
    current_user: CurrentUser,
    debt_repo: DebtRepository = Depends(get_debt_repo),
    blockchain: BlockchainInterface = Depends(get_blockchain),
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
) -> DebtResponse:
    """
    Create a new debt
    """
    logger.info(f"[DEBT] Creating debt for user {current_user.id}: {debt_request.name}")

    try:
        # Create DebtCreate model with user_id from authenticated user
        debt_in = DebtCreate(
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

        # Create debt using repository
        logger.debug(f"[DEBT] Calling repository to create debt for user {current_user.id}")
        created_debt = await debt_repo.create_debt(debt_in)
        logger.info(f"[DEBT] Successfully created debt {created_debt.id} for user {current_user.id}")

        # Store on blockchain (optional) - isolated to prevent main operation failure
        try:
            logger.debug(f"[BLOCKCHAIN] Attempting to store debt {created_debt.id} on blockchain")
            blockchain_data = {
                "debt_id": str(created_debt.id),
                "user_id": str(current_user.id),
                "name": created_debt.name,
                "type": created_debt.debt_type,
                "amount": float(created_debt.principal_amount),
                "interest_rate": float(created_debt.interest_rate),
                "timestamp": datetime.utcnow().isoformat()
            }

            blockchain_tx = await blockchain.store_debt(blockchain_data)

            # Update debt with blockchain ID if available
            if blockchain_tx:
                await debt_repo.update_debt(str(created_debt.id), {"blockchain_id": blockchain_tx})
                created_debt.blockchain_id = blockchain_tx
                logger.debug(f"[BLOCKCHAIN] Successfully stored debt {created_debt.id} with tx {blockchain_tx}")
        except Exception as e:
            # Log blockchain error but don't fail the operation
            logger.error(f"[BLOCKCHAIN] Blockchain storage failed for debt {created_debt.id}: {e}")

        # Invalidate AI insights cache since debt portfolio has changed
        # This is isolated and won't affect the main operation
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id}")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id}")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt creation succeeded")

        logger.info(f"[DEBT] Debt creation completed successfully for user {current_user.id}")
        return DebtResponse.from_debt_in_db(created_debt)

    except Exception as e:
        logger.error(f"[DEBT] Failed to create debt for user {current_user.id}: {type(e).__name__}: {str(e)}")
        logger.error(f"[DEBT] Full error traceback:", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create debt: {str(e)}"
        )


@router.get("/summary", response_model=DebtSummaryResponse)
async def get_debt_summary(
    current_user: CurrentUser,
    debt_repo: DebtRepository = Depends(get_debt_repo)
) -> DebtSummaryResponse:
    """
    Get debt summary statistics for the current user
    """
    try:
        # Get all active debts for user
        debts = await debt_repo.get_debts_by_user_id(current_user.id, active_only=True)

        if not debts:
            return DebtSummaryResponse(
                total_debt=0,
                total_interest_paid=0,
                total_minimum_payments=0,
                average_interest_rate=0,
                debt_count=0,
                high_priority_count=0,
                upcoming_payments_count=0
            )

        # Calculate summary statistics
        total_debt = sum(debt.current_balance for debt in debts)
        total_minimum_payments = sum(debt.minimum_payment for debt in debts)
        high_priority_count = sum(1 for debt in debts if debt.is_high_priority)

        # Calculate weighted average interest rate
        total_principal = sum(debt.principal_amount for debt in debts)
        if total_principal > 0:
            average_interest_rate = sum(
                (debt.principal_amount / total_principal) * debt.interest_rate
                for debt in debts
            )
        else:
            average_interest_rate = 0

        # Count upcoming payments (due within 7 days)
        from datetime import date, timedelta
        today = date.today()
        upcoming_count = 0

        for debt in debts:
            if debt.due_date:
                try:
                    due_date_obj = datetime.strptime(debt.due_date, '%Y-%m-%d').date()
                    if today <= due_date_obj <= today + timedelta(days=7):
                        upcoming_count += 1
                except ValueError:
                    pass

        return DebtSummaryResponse(
            total_debt=total_debt,
            total_interest_paid=0,  # Would need payment history to calculate this
            total_minimum_payments=total_minimum_payments,
            average_interest_rate=round(average_interest_rate, 2),
            debt_count=len(debts),
            high_priority_count=high_priority_count,
            upcoming_payments_count=upcoming_count
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get debt summary: {str(e)}"
        )


@router.get("/{debt_id}", response_model=DebtResponse)
async def get_debt(
    debt_id: str,
    current_user: CurrentUser,
    debt_repo: DebtRepository = Depends(get_debt_repo)
) -> DebtResponse:
    """
    Get a specific debt by ID
    """
    try:
        # Get debt using repository
        debt = await debt_repo.get_debt_by_id(debt_id)

        if not debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        # Check if debt belongs to user
        if debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this debt"
            )

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
    debt_id: str,
    debt_in: DebtUpdate,
    current_user: CurrentUser,
    debt_repo: DebtRepository = Depends(get_debt_repo),
    blockchain: BlockchainInterface = Depends(get_blockchain),
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
) -> DebtResponse:
    """
    Update a debt
    """
    try:
        # Get debt to check ownership
        debt = await debt_repo.get_debt_by_id(debt_id)

        if not debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        # Check if debt belongs to user
        if debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this debt"
            )

        # Update debt using repository
        updated_debt = await debt_repo.update_debt(debt_id, debt_in.model_dump(exclude_unset=True))

        if not updated_debt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update debt"
            )

        # Update on blockchain if significant changes
        if any(field in debt_in.model_fields_set for field in ['principal_amount', 'interest_rate']):
            try:
                blockchain_data = {
                    "debt_id": debt_id,
                    "user_id": str(current_user.id),
                    "name": updated_debt.name,
                    "type": updated_debt.debt_type,
                    "amount": float(updated_debt.principal_amount),
                    "interest_rate": float(updated_debt.interest_rate),
                    "timestamp": datetime.utcnow().isoformat(),
                    "action": "update"
                }

                await blockchain.store_debt(blockchain_data)
            except Exception as e:
                logger.error(f"[BLOCKCHAIN] Blockchain update failed for debt {debt_id}: {e}")

        # Invalidate AI insights cache since debt portfolio has changed
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id} after update")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id} after update")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt update succeeded")

        return DebtResponse.from_debt_in_db(updated_debt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update debt: {str(e)}"
        )


@router.delete("/{debt_id}", response_model=DebtResponse)
async def delete_debt(
    debt_id: str,
    current_user: CurrentUser,
    debt_repo: DebtRepository = Depends(get_debt_repo),
    blockchain: BlockchainInterface = Depends(get_blockchain),
    ai_cache_service: AIInsightsCacheService = Depends(get_ai_cache_service)
) -> DebtResponse:
    """
    Mark a debt as inactive (soft delete)
    """
    try:
        # Get debt to check ownership
        debt = await debt_repo.get_debt_by_id(debt_id)

        if not debt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debt not found"
            )

        # Check if debt belongs to user
        if debt.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this debt"
            )

        # Soft delete debt using repository
        updated_debt = await debt_repo.update_debt(debt_id, {"is_active": False})

        if not updated_debt:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete debt"
            )

        # Record on blockchain (optional)
        try:
            blockchain_data = {
                "debt_id": debt_id,
                "user_id": str(current_user.id),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "delete"
            }

            await blockchain.store_debt(blockchain_data)
        except Exception as e:
            logger.error(f"[BLOCKCHAIN] Blockchain delete recording failed for debt {debt_id}: {e}")

        # Invalidate AI insights cache since debt portfolio has changed
        logger.debug(f"[DEBT] Attempting cache invalidation for user {current_user.id} after delete")
        cache_success = await safe_invalidate_user_cache(ai_cache_service, current_user.id)
        if cache_success:
            logger.debug(f"[DEBT] Cache invalidation successful for user {current_user.id} after delete")
        else:
            logger.warning(f"[DEBT] Cache invalidation failed for user {current_user.id}, but debt deletion succeeded")

        return DebtResponse.from_debt_in_db(updated_debt)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete debt: {str(e)}"
        )