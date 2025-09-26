"""
Debt repository for debt management operations.
Handles debt CRUD operations, debt-specific queries, and debt analytics.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID

from app.models.debt import DebtInDB, DebtCreate, DebtUpdate, DebtType, PaymentFrequency
from app.repositories.base_repository import BaseRepository, RecordNotFoundError
from app.models.analytics import DebtSummaryResponse

logger = logging.getLogger(__name__)


class DebtRepository(BaseRepository[DebtInDB]):
    """Repository for debt operations"""

    def __init__(self):
        super().__init__("debts")

    def _record_to_model(self, record: asyncpg.Record) -> DebtInDB:
        """Convert database record to DebtInDB model"""
        return DebtInDB(
            id=record['id'],
            user_id=record['user_id'],
            name=record['name'],
            debt_type=DebtType(record['debt_type']),
            principal_amount=float(record['principal_amount']),
            current_balance=float(record['current_balance']),
            interest_rate=float(record['interest_rate']),
            is_variable_rate=record['is_variable_rate'],
            minimum_payment=float(record['minimum_payment']),
            due_date=record['due_date'],
            lender=record['lender'],
            remaining_term_months=record['remaining_term_months'],
            is_tax_deductible=record['is_tax_deductible'],
            payment_frequency=PaymentFrequency(record['payment_frequency']),
            is_high_priority=record['is_high_priority'],
            notes=record['notes'],
            source=record.get('source', 'manual'),
            created_at=record['created_at'],
            updated_at=record['updated_at'],
            blockchain_id=record['blockchain_id'],
            is_active=record['is_active']
        )

    def _model_to_dict(self, model: DebtInDB) -> Dict[str, Any]:
        """Convert DebtInDB model to dictionary for database operations"""
        return {
            'id': str(model.id),
            'user_id': str(model.user_id),
            'name': model.name,
            'debt_type': model.debt_type.value,
            'principal_amount': model.principal_amount,
            'current_balance': model.current_balance,
            'interest_rate': model.interest_rate,
            'is_variable_rate': model.is_variable_rate,
            'minimum_payment': model.minimum_payment,
            'due_date': model.due_date,
            'lender': model.lender,
            'remaining_term_months': model.remaining_term_months,
            'is_tax_deductible': model.is_tax_deductible,
            'payment_frequency': model.payment_frequency.value,
            'is_high_priority': model.is_high_priority,
            'notes': model.notes,
            'source': model.source.value,
            'created_at': model.created_at,
            'updated_at': model.updated_at,
            'blockchain_id': model.blockchain_id,
            'is_active': model.is_active
        }

    async def create_debt(self, debt_create: DebtCreate) -> DebtInDB:
        """
        Create a new debt record.
        
        Args:
            debt_create: Debt creation data
            
        Returns:
            Created debt
        """
        debt_in_db = DebtInDB(
            user_id=debt_create.user_id,
            name=debt_create.name,
            debt_type=debt_create.debt_type,
            principal_amount=debt_create.principal_amount,
            current_balance=debt_create.current_balance,
            interest_rate=debt_create.interest_rate,
            is_variable_rate=debt_create.is_variable_rate,
            minimum_payment=debt_create.minimum_payment,
            due_date=debt_create.due_date,  # Now a date object
            lender=debt_create.lender,
            remaining_term_months=debt_create.remaining_term_months,
            is_tax_deductible=debt_create.is_tax_deductible,
            payment_frequency=debt_create.payment_frequency,
            is_high_priority=debt_create.is_high_priority,
            notes=debt_create.notes,
            source=debt_create.source,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_active=True
        )
        
        return await self.create(debt_in_db)

    async def get_user_debts(self, user_id: UUID, include_inactive: bool = False) -> List[DebtInDB]:
        """
        Get all debts for a specific user.
        
        Args:
            user_id: User's ID
            include_inactive: Whether to include inactive debts
            
        Returns:
            List of user's debts
        """
        query = "SELECT * FROM debts WHERE user_id = $1"
        args = [str(user_id)]
        
        if not include_inactive:
            query += " AND is_active = true"
        
        query += " ORDER BY created_at DESC"
        
        records = await self._fetch_all_with_error_handling(query, *args)
        return [self._record_to_model(record) for record in records]

    async def get_debts_by_user_id(self, user_id: UUID, active_only: bool = True) -> List[DebtInDB]:
        """
        Get all debts for a specific user (alternative method signature for compatibility).
        
        Args:
            user_id: User's ID
            active_only: Whether to include only active debts
            
        Returns:
            List of user's debts
        """
        return await self.get_user_debts(user_id, include_inactive=not active_only)

    async def get_debts_by_type(self, user_id: UUID, debt_type: DebtType) -> List[DebtInDB]:
        """
        Get debts by type for a specific user.
        
        Args:
            user_id: User's ID
            debt_type: Type of debt to filter by
            
        Returns:
            List of debts of the specified type
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND debt_type = $2 AND is_active = true
            ORDER BY current_balance DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id), debt_type.value)
        return [self._record_to_model(record) for record in records]

    async def get_high_priority_debts(self, user_id: UUID) -> List[DebtInDB]:
        """
        Get high priority debts for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            List of high priority debts
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND is_high_priority = true AND is_active = true
            ORDER BY interest_rate DESC, current_balance DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        return [self._record_to_model(record) for record in records]

    async def get_debts_by_interest_rate(self, user_id: UUID, min_rate: float = 0) -> List[DebtInDB]:
        """
        Get debts ordered by interest rate (highest first).
        
        Args:
            user_id: User's ID
            min_rate: Minimum interest rate to filter by
            
        Returns:
            List of debts ordered by interest rate
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND interest_rate >= $2 AND is_active = true
            ORDER BY interest_rate DESC, current_balance DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id), min_rate)
        return [self._record_to_model(record) for record in records]

    async def get_debts_by_balance(self, user_id: UUID, min_balance: float = 0) -> List[DebtInDB]:
        """
        Get debts ordered by balance (smallest first for snowball method).
        
        Args:
            user_id: User's ID
            min_balance: Minimum balance to filter by
            
        Returns:
            List of debts ordered by balance
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND current_balance >= $2 AND is_active = true
            ORDER BY current_balance ASC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id), min_balance)
        return [self._record_to_model(record) for record in records]

    async def get_overdue_debts(self, user_id: Optional[UUID] = None) -> List[DebtInDB]:
        """
        Get debts that are past their due date.
        
        Args:
            user_id: Optional user ID to filter by specific user
            
        Returns:
            List of overdue debts
        """
        query = """
            SELECT * FROM debts 
            WHERE due_date < $1 AND is_active = true
        """
        args = [date.today().isoformat()]
        
        if user_id:
            query += " AND user_id = $2"
            args.append(str(user_id))
        
        query += " ORDER BY due_date ASC"
        
        records = await self._fetch_all_with_error_handling(query, *args)
        return [self._record_to_model(record) for record in records]

    async def get_upcoming_payments(self, user_id: UUID, days_ahead: int = 7) -> List[DebtInDB]:
        """
        Get debts with payments due in the next N days.
        
        Args:
            user_id: User's ID
            days_ahead: Number of days to look ahead
            
        Returns:
            List of debts with upcoming payments
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 
            AND due_date BETWEEN $2 AND $3
            AND is_active = true
            ORDER BY due_date ASC
        """
        
        today = date.today()
        future_date = date.fromordinal(today.toordinal() + days_ahead)
        
        records = await self._fetch_all_with_error_handling(
            query, 
            str(user_id), 
            today.isoformat(), 
            future_date.isoformat()
        )
        return [self._record_to_model(record) for record in records]

    async def update_debt_balance(self, debt_id: UUID, new_balance: float) -> Optional[DebtInDB]:
        """
        Update debt balance after a payment.
        
        Args:
            debt_id: Debt's ID
            new_balance: New current balance
            
        Returns:
            Updated debt if found, None otherwise
        """
        return await self.update(debt_id, {'current_balance': new_balance})

    async def get_debt_summary(self, user_id: UUID) -> DebtSummaryResponse:
        """
        Get comprehensive debt summary for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Debt summary with statistics
        """
        query = """
            SELECT 
                COUNT(*) as debt_count,
                COUNT(*) FILTER (WHERE is_high_priority = true) as high_priority_count,
                COUNT(*) FILTER (WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days') as upcoming_payments_count,
                COALESCE(SUM(current_balance), 0) as total_debt,
                COALESCE(SUM(minimum_payment), 0) as total_minimum_payments,
                COALESCE(AVG(interest_rate), 0) as average_interest_rate
            FROM debts 
            WHERE user_id = $1 AND is_active = true
        """
        
        record = await self._fetch_one_with_error_handling(query, str(user_id))
        
        if record:
            # Calculate total interest paid (this would need payment history data)
            # For now, we'll set it to 0 and calculate it when payment history is available
            total_interest_paid = 0.0
            
            return DebtSummaryResponse(
                total_debt=float(record['total_debt']),
                total_interest_paid=total_interest_paid,
                total_minimum_payments=float(record['total_minimum_payments']),
                average_interest_rate=float(record['average_interest_rate']),
                debt_count=record['debt_count'],
                high_priority_count=record['high_priority_count'],
                upcomingPaymentsCount=record['upcoming_payments_count']
            )
        
        return DebtSummaryResponse(
            total_debt=0.0,
            total_interest_paid=0.0,
            total_minimum_payments=0.0,
            average_interest_rate=0.0,
            debt_count=0,
            high_priority_count=0,
            upcomingPaymentsCount=0
        )

    async def get_debt_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get detailed debt analytics for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with debt analytics
        """
        analytics_query = """
            SELECT 
                debt_type,
                COUNT(*) as count,
                SUM(current_balance) as total_balance,
                AVG(interest_rate) as avg_interest_rate,
                SUM(minimum_payment) as total_minimum_payment
            FROM debts 
            WHERE user_id = $1 AND is_active = true
            GROUP BY debt_type
            ORDER BY total_balance DESC
        """
        
        records = await self._fetch_all_with_error_handling(analytics_query, str(user_id))
        
        debt_breakdown = []
        for record in records:
            debt_breakdown.append({
                'debt_type': record['debt_type'],
                'count': record['count'],
                'total_balance': float(record['total_balance']),
                'avg_interest_rate': float(record['avg_interest_rate']),
                'total_minimum_payment': float(record['total_minimum_payment'])
            })
        
        # Get overall statistics
        summary = await self.get_debt_summary(user_id)
        
        return {
            'summary': summary.model_dump(),
            'debt_breakdown': debt_breakdown,
            'analysis_date': datetime.now().isoformat()
        }

    async def search_debts(self, user_id: UUID, search_term: str) -> List[DebtInDB]:
        """
        Search user's debts by name or lender.
        
        Args:
            user_id: User's ID
            search_term: Term to search for
            
        Returns:
            List of matching debts
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 
            AND (name ILIKE $2 OR lender ILIKE $2)
            AND is_active = true
            ORDER BY current_balance DESC
        """
        
        search_pattern = f"%{search_term}%"
        records = await self._fetch_all_with_error_handling(query, str(user_id), search_pattern)
        return [self._record_to_model(record) for record in records]

    async def get_debts_by_lender(self, user_id: UUID, lender: str) -> List[DebtInDB]:
        """
        Get all debts from a specific lender.
        
        Args:
            user_id: User's ID
            lender: Lender name
            
        Returns:
            List of debts from the lender
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND lender ILIKE $2 AND is_active = true
            ORDER BY current_balance DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id), f"%{lender}%")
        return [self._record_to_model(record) for record in records]

    async def update_debt(self, debt_id: UUID, debt_update) -> Optional[DebtInDB]:
        """
        Update debt information.

        Args:
            debt_id: Debt's ID
            debt_update: Update data (DebtUpdate model or dict)

        Returns:
            Updated debt if found, None otherwise
        """
        # Handle both Pydantic model and dict
        if hasattr(debt_update, 'model_dump'):
            update_data = debt_update.model_dump(exclude_unset=True)
        elif isinstance(debt_update, dict):
            update_data = debt_update
        else:
            update_data = dict(debt_update)

        # Convert enum values to strings if present
        if 'debt_type' in update_data and hasattr(update_data['debt_type'], 'value'):
            update_data['debt_type'] = update_data['debt_type'].value
        if 'payment_frequency' in update_data and hasattr(update_data['payment_frequency'], 'value'):
            update_data['payment_frequency'] = update_data['payment_frequency'].value

        return await self.update(debt_id, update_data)

    async def get_tax_deductible_debts(self, user_id: UUID) -> List[DebtInDB]:
        """
        Get tax-deductible debts for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            List of tax-deductible debts
        """
        query = """
            SELECT * FROM debts 
            WHERE user_id = $1 AND is_tax_deductible = true AND is_active = true
            ORDER BY interest_rate DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        return [self._record_to_model(record) for record in records]

    async def get_debt_payment_schedule(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get payment schedule for all user debts.
        
        Args:
            user_id: User's ID
            
        Returns:
            List of payment schedule items
        """
        query = """
            SELECT 
                id,
                name,
                lender,
                minimum_payment,
                due_date,
                payment_frequency,
                is_high_priority
            FROM debts 
            WHERE user_id = $1 AND is_active = true
            ORDER BY due_date ASC, is_high_priority DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        
        schedule = []
        for record in records:
            schedule.append({
                'debt_id': str(record['id']),
                'debt_name': record['name'],
                'lender': record['lender'],
                'amount': float(record['minimum_payment']),
                'due_date': record['due_date'],
                'frequency': record['payment_frequency'],
                'is_priority': record['is_high_priority']
            })
        
        return schedule

    async def bulk_update_debt_balances(self, balance_updates: List[Dict[str, Any]]) -> List[DebtInDB]:
        """
        Update multiple debt balances in a single transaction.
        
        Args:
            balance_updates: List of {debt_id, new_balance} dictionaries
            
        Returns:
            List of updated debts
        """
        operations = []
        for update in balance_updates:
            query = """
                UPDATE debts 
                SET current_balance = $2, updated_at = $3 
                WHERE id = $1
            """
            operations.append((query, update['debt_id'], update['new_balance'], datetime.now()))
        
        await self.execute_transaction(operations)
        
        # Return updated debts
        updated_debts = []
        for update in balance_updates:
            debt = await self.get_by_id(update['debt_id'])
            if debt:
                updated_debts.append(debt)
        
        return updated_debts



