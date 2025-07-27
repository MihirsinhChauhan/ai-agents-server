from typing import List, Any, Optional
from datetime import datetime
import uuid
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import SupabaseDB, get_db
from app.dependencies import get_current_active_user, get_blockchain
from app.models.user import User
from app.models.repayment_plan import RepaymentPlan, RepaymentStrategy
from app.ai_module.orchestrator import DebtOptimizerOrchestrator
from app.blockchain_interface import BlockchainInterface

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_repayment_plans(
    active_only: bool = Query(True, description="Only return active plans"),
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get all repayment plans for the current user
    """
    # Find repayment plans
    plans = await db.get_repayment_plans(str(current_user.id), active_only)
    
    # Convert to response format
    plan_responses = []
    for plan in plans:
        # Parse JSON fields
        details = plan.get("details", {})
        if isinstance(details, str):
            details = json.loads(details)
            
        payment_schedule = plan.get("payment_schedule", [])
        if isinstance(payment_schedule, str):
            payment_schedule = json.loads(payment_schedule)
            
        debt_order = plan.get("debt_order", [])
        if isinstance(debt_order, str):
            debt_order = json.loads(debt_order)
        
        plan_response = {
            "id": plan["id"],
            "user_id": plan["user_id"],
            "strategy": plan["strategy"],
            "monthly_payment_amount": plan["monthly_payment_amount"],
            "debt_order": debt_order,
            "expected_completion_date": plan.get("expected_completion_date"),
            "total_interest_saved": plan.get("total_interest_saved"),
            "created_at": plan["created_at"],
            "updated_at": plan["updated_at"],
            "is_active": plan["is_active"],
            "blockchain_id": plan.get("blockchain_id"),
            "details": details,
            "payment_schedule": payment_schedule
        }
        plan_responses.append(plan_response)
    
    return plan_responses


@router.post("/generate", response_model=dict)
async def generate_repayment_plan(
    monthly_payment: float = Query(..., description="Monthly payment amount"),
    strategy: Optional[str] = Query(None, description="Repayment strategy (avalanche, snowball, custom, ai_optimized)"),
    debt_ids: Optional[List[str]] = Query(None, description="List of debt IDs to include (all active debts if none)"),
    custom_order: Optional[List[str]] = Query(None, description="Custom order of debt IDs (for custom strategy)"),
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db),
    blockchain: BlockchainInterface = Depends(get_blockchain)
) -> Any:
    """
    Generate a repayment plan using AI optimization
    """
    # Get debts
    if debt_ids:
        # Get specific debts
        debts = []
        for debt_id in debt_ids:
            debt = await db.get_debt(debt_id)
            if debt and debt["user_id"] == str(current_user.id) and debt["is_active"]:
                debts.append(debt)
    else:
        # Get all active debts
        debts = await db.get_debts(str(current_user.id), active_only=True)
    
    if not debts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No debts found"
        )
    
    # Calculate minimum payment sum
    min_payment_sum = sum(debt["minimum_payment"] for debt in debts)
    
    # Check if monthly payment is sufficient
    if monthly_payment < min_payment_sum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Monthly payment ({monthly_payment}) must be at least the sum of minimum payments ({min_payment_sum})"
        )
    
    # Create orchestrator
    orchestrator = DebtOptimizerOrchestrator()
    
    try:
        # Generate optimization using AI agents
        optimization_result = await orchestrator.optimize_debt_repayment(
            debts=debts,
            monthly_payment=monthly_payment,
            preferred_strategy=strategy
        )
        
        # Create plan ID
        plan_id = str(uuid.uuid4())
        
        # Get repayment plan
        repayment_plan = optimization_result["repayment_plan"]
        debt_analysis = optimization_result["debt_analysis"]
        payment_schedule = optimization_result["payment_schedule"]
        
        # Prepare plan data
        plan_data = {
            "id": plan_id,
            "user_id": str(current_user.id),
            "strategy": repayment_plan["recommended_strategy"],
            "monthly_payment_amount": monthly_payment,
            "debt_order": json.dumps(repayment_plan["debt_order"]),
            "expected_completion_date": repayment_plan["expected_completion_date"],
            "total_interest_saved": repayment_plan["total_interest_saved"],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "details": json.dumps({
                "debt_analysis": debt_analysis,
                "total_debt": debt_analysis["total_debt"],
                "minimum_payment_sum": min_payment_sum,
                "total_months": repayment_plan["time_to_debt_free"],
                "alternative_strategies": repayment_plan["alternative_strategies"]
            }),
            "payment_schedule": json.dumps(payment_schedule)
        }
        
        # Save to database
        created_plan = await db.create_repayment_plan(plan_data)
        if not created_plan:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save repayment plan"
            )
        
        # Store on blockchain
        blockchain_data = {
            "plan_id": plan_id,
            "user_id": str(current_user.id),
            "strategy": repayment_plan["recommended_strategy"],
            "monthly_payment": monthly_payment,
            "debt_count": len(debts),
            "total_debt": debt_analysis["total_debt"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        blockchain_tx = await blockchain.store_debt(blockchain_data)
        
        # Update plan with blockchain ID if available
        if blockchain_tx:
            await db.update_repayment_plan(
                plan_id,
                {"blockchain_id": blockchain_tx}
            )
            created_plan["blockchain_id"] = blockchain_tx
        
        # Parse JSON fields for response
        details = created_plan.get("details", {})
        if isinstance(details, str):
            details = json.loads(details)
            
        payment_schedule = created_plan.get("payment_schedule", [])
        if isinstance(payment_schedule, str):
            payment_schedule = json.loads(payment_schedule)
            
        debt_order = created_plan.get("debt_order", [])
        if isinstance(debt_order, str):
            debt_order = json.loads(debt_order)
        
        # Create response
        response = {
            "id": created_plan["id"],
            "user_id": created_plan["user_id"],
            "strategy": created_plan["strategy"],
            "monthly_payment_amount": created_plan["monthly_payment_amount"],
            "debt_order": debt_order,
            "expected_completion_date": created_plan.get("expected_completion_date"),
            "total_interest_saved": created_plan.get("total_interest_saved"),
            "created_at": created_plan["created_at"],
            "updated_at": created_plan["updated_at"],
            "is_active": created_plan["is_active"],
            "blockchain_id": created_plan.get("blockchain_id"),
            "details": details,
            "payment_schedule": payment_schedule,
            "debt_analysis": debt_analysis
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating repayment plan: {str(e)}"
        )


@router.get("/{plan_id}", response_model=dict)
async def get_repayment_plan(
    plan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get a specific repayment plan by ID
    """
    # Find plan
    plan = await db.get_repayment_plan(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repayment plan not found"
        )
    
    # Check if plan belongs to user
    if plan["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this repayment plan"
        )
    
    # Parse JSON fields
    details = plan.get("details", {})
    if isinstance(details, str):
        details = json.loads(details)
        
    payment_schedule = plan.get("payment_schedule", [])
    if isinstance(payment_schedule, str):
        payment_schedule = json.loads(payment_schedule)
        
    debt_order = plan.get("debt_order", [])
    if isinstance(debt_order, str):
        debt_order = json.loads(debt_order)
    
    # Create response
    response = {
        "id": plan["id"],
        "user_id": plan["user_id"],
        "strategy": plan["strategy"],
        "monthly_payment_amount": plan["monthly_payment_amount"],
        "debt_order": debt_order,
        "expected_completion_date": plan.get("expected_completion_date"),
        "total_interest_saved": plan.get("total_interest_saved"),
        "created_at": plan["created_at"],
        "updated_at": plan["updated_at"],
        "is_active": plan["is_active"],
        "blockchain_id": plan.get("blockchain_id"),
        "details": details,
        "payment_schedule": payment_schedule
    }
    
    return response


@router.delete("/{plan_id}", response_model=dict)
async def delete_repayment_plan(
    plan_id: str,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Mark a repayment plan as inactive (soft delete)
    """
    # Find plan
    plan = await db.get_repayment_plan(plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repayment plan not found"
        )
    
    # Check if plan belongs to user
    if plan["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this repayment plan"
        )
    
    # Update in database (soft delete)
    updated_plan = await db.update_repayment_plan(
        plan_id,
        {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }
    )
    
    if not updated_plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete repayment plan"
        )
    
    # Parse JSON fields
    details = updated_plan.get("details", {})
    if isinstance(details, str):
        details = json.loads(details)
        
    payment_schedule = updated_plan.get("payment_schedule", [])
    if isinstance(payment_schedule, str):
        payment_schedule = json.loads(payment_schedule)
        
    debt_order = updated_plan.get("debt_order", [])
    if isinstance(debt_order, str):
        debt_order = json.loads(debt_order)
    
    # Create response
    response = {
        "id": updated_plan["id"],
        "user_id": updated_plan["user_id"],
        "strategy": updated_plan["strategy"],
        "monthly_payment_amount": updated_plan["monthly_payment_amount"],
        "debt_order": debt_order,
        "expected_completion_date": updated_plan.get("expected_completion_date"),
        "total_interest_saved": updated_plan.get("total_interest_saved"),
        "created_at": updated_plan["created_at"],
        "updated_at": updated_plan["updated_at"],
        "is_active": updated_plan["is_active"],
        "blockchain_id": updated_plan.get("blockchain_id"),
        "details": details,
        "payment_schedule": payment_schedule
    }
    
    return response