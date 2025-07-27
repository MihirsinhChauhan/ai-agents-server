from datetime import datetime
from typing import List, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import SupabaseDB, get_db
from app.dependencies import get_current_active_user, get_blockchain
from app.models.user import User
from app.models.debt import DebtCreate, Debt, DebtUpdate
from app.blockchain_interface import BlockchainInterface

router = APIRouter()


@router.get("/", response_model=List[Debt])
async def get_debts(
    active_only: bool = Query(True, description="Only return active debts"),
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get all debts for the current user
    """
    # Find debts for user
    debts = await db.get_debts(str(current_user.id), active_only)
    
    # Convert to Debt models
    debt_models = []
    for debt in debts:
        debt_model = Debt(
            id=debt["id"],
            user_id=debt["user_id"],
            name=debt["name"],
            type=debt["type"],
            amount=debt["amount"],
            interest_rate=debt["interest_rate"],
            minimum_payment=debt["minimum_payment"],
            payment_frequency=debt["payment_frequency"],
            source=debt["source"],
            due_date=debt.get("due_date"),
            created_at=debt["created_at"],
            updated_at=debt["updated_at"],
            blockchain_id=debt.get("blockchain_id"),
            is_active=debt["is_active"],
            details=debt.get("details", {})
        )
        debt_models.append(debt_model)
    
    return debt_models


@router.post("/", response_model=Debt)
async def create_debt(
    debt_in: DebtCreate,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db),
    blockchain: BlockchainInterface = Depends(get_blockchain)
) -> Any:
    """
    Create a new debt
    """
    # Create debt record
    debt_id = str(uuid.uuid4())
    debt_data = {
        "id": debt_id,
        "user_id": str(current_user.id),
        "name": debt_in.name,
        "type": debt_in.type,
        "amount": debt_in.amount,
        "interest_rate": debt_in.interest_rate,
        "minimum_payment": debt_in.minimum_payment,
        "payment_frequency": debt_in.payment_frequency,
        "source": debt_in.source,
        "due_date": debt_in.due_date,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "details": debt_in.details
    }
    
    # Insert into database
    created_debt = await db.create_debt(debt_data)
    if not created_debt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create debt"
        )
    
    # Store on blockchain
    blockchain_data = {
        "debt_id": debt_id,
        "user_id": str(current_user.id),
        "name": debt_in.name,
        "type": debt_in.type,
        "amount": float(debt_in.amount),
        "interest_rate": float(debt_in.interest_rate),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    blockchain_tx = await blockchain.store_debt(blockchain_data)
    
    # Update debt with blockchain ID if available
    if blockchain_tx:
        await db.update_debt(
            debt_id,
            {"blockchain_id": blockchain_tx}
        )
        created_debt["blockchain_id"] = blockchain_tx
    
    # Convert to model
    debt_model = Debt(
        id=created_debt["id"],
        user_id=created_debt["user_id"],
        name=created_debt["name"],
        type=created_debt["type"],
        amount=created_debt["amount"],
        interest_rate=created_debt["interest_rate"],
        minimum_payment=created_debt["minimum_payment"],
        payment_frequency=created_debt["payment_frequency"],
        source=created_debt["source"],
        due_date=created_debt.get("due_date"),
        created_at=created_debt["created_at"],
        updated_at=created_debt["updated_at"],
        blockchain_id=created_debt.get("blockchain_id"),
        is_active=created_debt["is_active"],
        details=created_debt.get("details", {})
    )
    
    return debt_model


@router.get("/{debt_id}", response_model=Debt)
async def get_debt(
    debt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get a specific debt by ID
    """
    # Find debt
    debt = await db.get_debt(debt_id)
    
    if not debt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )
    
    # Check if debt belongs to user
    if debt["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this debt"
        )
    
    # Convert to model
    debt_model = Debt(
        id=debt["id"],
        user_id=debt["user_id"],
        name=debt["name"],
        type=debt["type"],
        amount=debt["amount"],
        interest_rate=debt["interest_rate"],
        minimum_payment=debt["minimum_payment"],
        payment_frequency=debt["payment_frequency"],
        source=debt["source"],
        due_date=debt.get("due_date"),
        created_at=debt["created_at"],
        updated_at=debt["updated_at"],
        blockchain_id=debt.get("blockchain_id"),
        is_active=debt["is_active"],
        details=debt.get("details", {})
    )
    
    return debt_model


@router.put("/{debt_id}", response_model=Debt)
async def update_debt(
    debt_id: str,
    debt_in: DebtUpdate,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db),
    blockchain: BlockchainInterface = Depends(get_blockchain)
) -> Any:
    """
    Update a debt
    """
    # Find debt
    debt = await db.get_debt(debt_id)
    
    if not debt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )
    
    # Check if debt belongs to user
    if debt["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this debt"
        )
    
    # Update fields
    update_data = debt_in.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    # Update in database
    updated_debt = await db.update_debt(debt_id, update_data)
    if not updated_debt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update debt"
        )
    
    # Update on blockchain if needed
    if "amount" in update_data or "interest_rate" in update_data:
        blockchain_data = {
            "debt_id": debt_id,
            "user_id": str(current_user.id),
            "name": updated_debt["name"],
            "type": updated_debt["type"],
            "amount": float(updated_debt["amount"]),
            "interest_rate": float(updated_debt["interest_rate"]),
            "timestamp": datetime.utcnow().isoformat(),
            "action": "update"
        }
        
        await blockchain.store_debt(blockchain_data)
    
    # Convert to model
    debt_model = Debt(
        id=updated_debt["id"],
        user_id=updated_debt["user_id"],
        name=updated_debt["name"],
        type=updated_debt["type"],
        amount=updated_debt["amount"],
        interest_rate=updated_debt["interest_rate"],
        minimum_payment=updated_debt["minimum_payment"],
        payment_frequency=updated_debt["payment_frequency"],
        source=updated_debt["source"],
        due_date=updated_debt.get("due_date"),
        created_at=updated_debt["created_at"],
        updated_at=updated_debt["updated_at"],
        blockchain_id=updated_debt.get("blockchain_id"),
        is_active=updated_debt["is_active"],
        details=updated_debt.get("details", {})
    )
    
    return debt_model


@router.delete("/{debt_id}", response_model=Debt)
async def delete_debt(
    debt_id: str,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db),
    blockchain: BlockchainInterface = Depends(get_blockchain)
) -> Any:
    """
    Mark a debt as inactive (soft delete)
    """
    # Find debt
    debt = await db.get_debt(debt_id)
    
    if not debt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )
    
    # Check if debt belongs to user
    if debt["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this debt"
        )
    
    # Update in database (soft delete)
    updated_debt = await db.update_debt(
        debt_id,
        {
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        }
    )
    
    if not updated_debt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete debt"
        )
    
    # Record on blockchain
    blockchain_data = {
        "debt_id": debt_id,
        "user_id": str(current_user.id),
        "timestamp": datetime.utcnow().isoformat(),
        "action": "delete"
    }
    
    await blockchain.store_debt(blockchain_data)
    
    # Convert to model
    debt_model = Debt(
        id=updated_debt["id"],
        user_id=updated_debt["user_id"],
        name=updated_debt["name"],
        type=updated_debt["type"],
        amount=updated_debt["amount"],
        interest_rate=updated_debt["interest_rate"],
        minimum_payment=updated_debt["minimum_payment"],
        payment_frequency=updated_debt["payment_frequency"],
        source=updated_debt["source"],
        due_date=updated_debt.get("due_date"),
        created_at=updated_debt["created_at"],
        updated_at=updated_debt["updated_at"],
        blockchain_id=updated_debt.get("blockchain_id"),
        is_active=updated_debt["is_active"],
        details=updated_debt.get("details", {})
    )
    
    return debt_model


@router.post("/{debt_id}/payment", response_model=dict)
async def record_payment(
    debt_id: str,
    amount: float,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db),
    blockchain: BlockchainInterface = Depends(get_blockchain)
) -> Any:
    """
    Record a payment for a debt
    """
    # Find debt
    debt = await db.get_debt(debt_id)
    
    if not debt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debt not found"
        )
    
    # Check if debt belongs to user
    if debt["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to make payments on this debt"
        )
    
    # Check if debt is active
    if not debt["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot make payments on inactive debt"
        )
    
    # Validate payment amount
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be positive"
        )
    
    # Create payment record
    payment_id = str(uuid.uuid4())
    payment_data = {
        "id": payment_id,
        "debt_id": debt_id,
        "user_id": str(current_user.id),
        "amount": amount,
        "date": datetime.utcnow().isoformat(),
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Insert payment into database
    created_payment = await db.create_payment(payment_data)
    if not created_payment:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record payment"
        )
    
    # Record payment on blockchain
    blockchain_data = {
        "payment_id": payment_id,
        "debt_id": debt_id,
        "user_id": str(current_user.id),
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    blockchain_tx = await blockchain.record_payment(blockchain_data)
    
    # Update payment with blockchain ID if available
    if blockchain_tx:
        await db.update_payment(
            payment_id,
            {"blockchain_id": blockchain_tx}
        )
        created_payment["blockchain_id"] = blockchain_tx
    
    return {
        "payment_id": created_payment["id"],
        "debt_id": created_payment["debt_id"],
        "amount": created_payment["amount"],
        "date": created_payment["date"],
        "status": created_payment["status"],
        "blockchain_id": created_payment.get("blockchain_id")
    }