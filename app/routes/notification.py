from datetime import datetime, timedelta
from typing import List, Any, Optional
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.database import SupabaseDB, get_db
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=List[dict])
async def get_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get notifications for the current user
    """
    # Build query
    query = f"user_id = '{str(current_user.id)}'"
    if unread_only:
        query += " AND read = false"
    
    # Query notifications
    response = await db.supabase.table("notifications").select("*").eq("user_id", str(current_user.id))
    if unread_only:
        response = response.eq("read", False)
    
    response = await response.order("created_at", desc=True).execute()
    notifications = response.data
    
    # Format response
    notification_responses = []
    for notif in notifications:
        # Parse metadata if it's a string
        metadata = notif.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
            
        notification_response = {
            "id": notif["id"],
            "user_id": notif["user_id"],
            "title": notif["title"],
            "message": notif["message"],
            "type": notif["type"],
            "read": notif["read"],
            "read_at": notif.get("read_at"),
            "created_at": notif["created_at"],
            "metadata": metadata
        }
        notification_responses.append(notification_response)
    
    return notification_responses


@router.post("/mark-read/{notification_id}")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Mark a notification as read
    """
    # Check if notification exists
    response = await db.supabase.table("notifications").select("*").eq("id", notification_id).execute()
    notification = response.data[0] if response.data else None
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to user
    if notification["user_id"] != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notification"
        )
    
    # Mark as read
    update_data = {
        "read": True,
        "read_at": datetime.utcnow().isoformat()
    }
    
    response = await db.supabase.table("notifications").update(update_data).eq("id", notification_id).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )
    
    return {"success": True}


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Mark all notifications as read
    """
    # Mark all as read
    update_data = {
        "read": True,
        "read_at": datetime.utcnow().isoformat()
    }
    
    # Count unread notifications
    count_response = await db.supabase.table("notifications").select("id").eq("user_id", str(current_user.id)).eq("read", False).execute()
    unread_count = len(count_response.data)
    
    # Update all unread notifications
    response = await db.supabase.table("notifications").update(update_data).eq("user_id", str(current_user.id)).eq("read", False).execute()
    
    if not response.data and unread_count > 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications as read"
        )
    
    return {"success": True, "marked_read_count": len(response.data)}


@router.post("/create")
async def create_notification(
    title: str,
    message: str,
    notification_type: str = Query(..., alias="type"),
    metadata: Optional[dict] = None,
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Create a new notification (admin or system use)
    """
    # Create notification
    notification_id = str(uuid.uuid4())
    notification_data = {
        "id": notification_id,
        "user_id": str(current_user.id),
        "title": title,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": json.dumps(metadata) if metadata else "{}"
    }
    
    # Save to database
    response = await db.supabase.table("notifications").insert(notification_data).execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification"
        )
    
    created_notification = response.data[0]
    
    return {
        "id": created_notification["id"],
        "title": created_notification["title"],
        "message": created_notification["message"],
        "type": created_notification["type"],
        "created_at": created_notification["created_at"]
    }


@router.get("/upcoming-payments")
async def get_upcoming_payments(
    days: int = Query(7, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_active_user),
    db: SupabaseDB = Depends(get_db)
) -> Any:
    """
    Get upcoming payments based on the user's active repayment plan
    """
    # Find active repayment plan
    response = await db.supabase.table("repayment_plans").select("*").eq("user_id", str(current_user.id)).eq("is_active", True).order("created_at", desc=True).limit(1).execute()
    plan = response.data[0] if response.data else None
    
    if not plan:
        return {"upcoming_payments": []}
    
    # Parse payment schedule
    payment_schedule = plan.get("payment_schedule", [])
    if isinstance(payment_schedule, str):
        payment_schedule = json.loads(payment_schedule)
    
    # Get current date and end date
    now = datetime.utcnow()
    end_date = now + timedelta(days=days)
    
    # Extract upcoming payments
    upcoming_payments = []
    
    for month_data in payment_schedule:
        # Parse date
        payment_date = datetime.fromisoformat(month_data["date"].replace("Z", "+00:00") if month_data["date"].endswith("Z") else month_data["date"])
        
        # Check if this payment is in our date range
        if now <= payment_date <= end_date:
            # Add month's payments to the list
            for payment in month_data["payments"]:
                # Get debt details
                debt_response = await db.supabase.table("debts").select("*").eq("id", payment["debt_id"]).execute()
                debt = debt_response.data[0] if debt_response.data else None
                
                if debt:
                    upcoming_payments.append({
                        "debt_id": payment["debt_id"],
                        "debt_name": debt["name"],
                        "amount": payment["amount"],
                        "type": payment["type"],
                        "date": payment_date.isoformat(),
                        "remaining_balance": payment["remaining_balance"]
                    })
    
    # Sort by date
    upcoming_payments.sort(key=lambda x: x["date"])
    
    return {"upcoming_payments": upcoming_payments}