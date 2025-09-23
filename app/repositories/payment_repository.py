"""
Payment repository for payment history and transaction operations.
Handles payment CRUD operations, payment analytics, and payment-related queries.
"""

import asyncpg
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from uuid import UUID

from app.models.payment import PaymentInDB, PaymentCreate, PaymentUpdate, PaymentStatus
from app.repositories.base_repository import BaseRepository
from app.repositories.debt_repository import DebtRepository

logger = logging.getLogger(__name__)


class PaymentRepository(BaseRepository[PaymentInDB]):
    """Repository for payment operations"""

    def __init__(self):
        super().__init__("payment_history")
        self.debt_repo = DebtRepository()

    def _record_to_model(self, record: asyncpg.Record) -> PaymentInDB:
        """Convert database record to PaymentInDB model"""
        return PaymentInDB(
            id=record['id'],
            debt_id=record['debt_id'],
            user_id=record['user_id'],
            amount=float(record['amount']),
            payment_date=record['payment_date'],
            principal_portion=float(record['principal_portion']) if record['principal_portion'] else None,
            interest_portion=float(record['interest_portion']) if record['interest_portion'] else None,
            notes=record['notes'],
            status=PaymentStatus(record.get('status', 'confirmed')),
            extra_details=record.get('extra_details', {}),
            created_at=record['created_at'],
            updated_at=record['updated_at'],
            blockchain_id=record['blockchain_id']
        )

    def _model_to_dict(self, model: PaymentInDB) -> Dict[str, Any]:
        """Convert PaymentInDB model to dictionary for database operations"""
        return {
            'id': str(model.id),
            'debt_id': str(model.debt_id),
            'user_id': str(model.user_id),
            'amount': model.amount,
            'payment_date': model.payment_date,
            'principal_portion': model.principal_portion,
            'interest_portion': model.interest_portion,
            'notes': model.notes,
            'status': model.status.value,
            'extra_details': model.extra_details,
            'created_at': model.created_at,
            'updated_at': model.updated_at,
            'blockchain_id': model.blockchain_id
        }

    async def create_payment(self, payment_create: PaymentCreate) -> PaymentInDB:
        """
        Create a new payment record and update debt balance.
        
        Args:
            payment_create: Payment creation data
            
        Returns:
            Created payment
        """
        # Create payment record
        payment_in_db = PaymentInDB(
            debt_id=payment_create.debt_id,
            user_id=payment_create.user_id,
            amount=payment_create.amount,
            payment_date=payment_create.payment_date,
            principal_portion=payment_create.principal_portion,
            interest_portion=payment_create.interest_portion,
            notes=payment_create.notes,
            status=payment_create.status,
            extra_details=payment_create.extra_details,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Use transaction to create payment and update debt balance
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    # Create payment
                    payment_dict = self._model_to_dict(payment_in_db)
                    insert_data = {k: v for k, v in payment_dict.items() if v is not None}
                    
                    columns = list(insert_data.keys())
                    placeholders = [f"${i+1}" for i in range(len(columns))]
                    values = list(insert_data.values())
                    
                    payment_query = f"""
                        INSERT INTO payment_history ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING *
                    """
                    
                    payment_record = await conn.fetchrow(payment_query, *values)
                    
                    # Update debt balance if principal portion is specified
                    if payment_create.principal_portion and payment_create.principal_portion > 0:
                        balance_query = """
                            UPDATE debts 
                            SET current_balance = current_balance - $1, updated_at = $2
                            WHERE id = $3
                        """
                        await conn.execute(
                            balance_query, 
                            payment_create.principal_portion, 
                            datetime.now(),
                            str(payment_create.debt_id)
                        )
                    
                    return self._record_to_model(payment_record)
                    
        except Exception as e:
            logger.error(f"Failed to create payment: {e}")
            raise

    async def get_user_payments(self, user_id: UUID, limit: Optional[int] = None, offset: int = 0) -> List[PaymentInDB]:
        """
        Get all payments for a specific user.
        
        Args:
            user_id: User's ID
            limit: Maximum number of payments to return
            offset: Number of payments to skip
            
        Returns:
            List of user's payments
        """
        query = """
            SELECT * FROM payment_history 
            WHERE user_id = $1 
            ORDER BY payment_date DESC, created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        return [self._record_to_model(record) for record in records]

    async def get_debt_payments(self, debt_id: UUID, limit: Optional[int] = None) -> List[PaymentInDB]:
        """
        Get all payments for a specific debt.
        
        Args:
            debt_id: Debt's ID
            limit: Maximum number of payments to return
            
        Returns:
            List of debt's payments
        """
        query = """
            SELECT * FROM payment_history 
            WHERE debt_id = $1 
            ORDER BY payment_date DESC, created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        records = await self._fetch_all_with_error_handling(query, str(debt_id))
        return [self._record_to_model(record) for record in records]

    async def get_payments_by_date_range(
        self, 
        user_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> List[PaymentInDB]:
        """
        Get payments within a date range for a user.
        
        Args:
            user_id: User's ID
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            List of payments in the date range
        """
        query = """
            SELECT * FROM payment_history 
            WHERE user_id = $1 
            AND payment_date BETWEEN $2 AND $3
            ORDER BY payment_date DESC
        """
        
        records = await self._fetch_all_with_error_handling(
            query, 
            str(user_id), 
            start_date.isoformat(), 
            end_date.isoformat()
        )
        return [self._record_to_model(record) for record in records]

    async def get_recent_payments(self, user_id: UUID, days: int = 30) -> List[PaymentInDB]:
        """
        Get recent payments for a user.
        
        Args:
            user_id: User's ID
            days: Number of days to look back
            
        Returns:
            List of recent payments
        """
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()
        
        return await self.get_payments_by_date_range(user_id, start_date, end_date)

    async def get_payment_summary(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get payment summary statistics for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with payment statistics
        """
        summary_query = """
            SELECT 
                COUNT(*) as total_payments,
                COALESCE(SUM(amount), 0) as total_amount_paid,
                COALESCE(SUM(principal_portion), 0) as total_principal_paid,
                COALESCE(SUM(interest_portion), 0) as total_interest_paid,
                COALESCE(AVG(amount), 0) as average_payment,
                MIN(payment_date) as first_payment_date,
                MAX(payment_date) as last_payment_date,
                COUNT(*) FILTER (WHERE payment_date >= CURRENT_DATE - INTERVAL '30 days') as payments_last_30_days,
                COUNT(*) FILTER (WHERE payment_date >= CURRENT_DATE - INTERVAL '7 days') as payments_last_7_days
            FROM payment_history 
            WHERE user_id = $1
        """
        
        record = await self._fetch_one_with_error_handling(summary_query, str(user_id))
        
        if record:
            return {
                'total_payments': record['total_payments'],
                'total_amount_paid': float(record['total_amount_paid']),
                'total_principal_paid': float(record['total_principal_paid']) if record['total_principal_paid'] else 0.0,
                'total_interest_paid': float(record['total_interest_paid']) if record['total_interest_paid'] else 0.0,
                'average_payment': float(record['average_payment']),
                'first_payment_date': record['first_payment_date'],
                'last_payment_date': record['last_payment_date'],
                'payments_last_30_days': record['payments_last_30_days'],
                'payments_last_7_days': record['payments_last_7_days']
            }
        
        return {
            'total_payments': 0,
            'total_amount_paid': 0.0,
            'total_principal_paid': 0.0,
            'total_interest_paid': 0.0,
            'average_payment': 0.0,
            'first_payment_date': None,
            'last_payment_date': None,
            'payments_last_30_days': 0,
            'payments_last_7_days': 0
        }

    async def get_monthly_payment_trends(self, user_id: UUID, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get monthly payment trends for a user.
        
        Args:
            user_id: User's ID
            months: Number of months to include
            
        Returns:
            List of monthly payment data
        """
        query = """
            SELECT 
                DATE_TRUNC('month', payment_date) as month,
                COUNT(*) as payment_count,
                SUM(amount) as total_amount,
                SUM(principal_portion) as total_principal,
                SUM(interest_portion) as total_interest,
                AVG(amount) as average_payment
            FROM payment_history 
            WHERE user_id = $1 
            AND payment_date >= CURRENT_DATE - INTERVAL '%s months'
            GROUP BY DATE_TRUNC('month', payment_date)
            ORDER BY month DESC
        """ % months
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        
        trends = []
        for record in records:
            trends.append({
                'month': record['month'].strftime('%Y-%m'),
                'payment_count': record['payment_count'],
                'total_amount': float(record['total_amount']),
                'total_principal': float(record['total_principal']) if record['total_principal'] else 0.0,
                'total_interest': float(record['total_interest']) if record['total_interest'] else 0.0,
                'average_payment': float(record['average_payment'])
            })
        
        return trends

    async def get_debt_payment_history_with_details(self, debt_id: UUID) -> Dict[str, Any]:
        """
        Get detailed payment history for a specific debt including impact on balance.
        
        Args:
            debt_id: Debt's ID
            
        Returns:
            Dictionary with payment history and analysis
        """
        # Get debt details
        debt = await self.debt_repo.get_by_id(debt_id)
        if not debt:
            return {'error': 'Debt not found'}
        
        # Get payment history
        payments = await self.get_debt_payments(debt_id)
        
        # Calculate running balance
        payment_history = []
        current_balance = debt.current_balance
        
        for payment in reversed(payments):  # Start from oldest
            # Add back this payment to see balance before payment
            if payment.principal_portion:
                current_balance += payment.principal_portion
            
            payment_history.append({
                'payment_id': str(payment.id),
                'payment_date': payment.payment_date,
                'amount': payment.amount,
                'principal_portion': payment.principal_portion,
                'interest_portion': payment.interest_portion,
                'balance_before': current_balance,
                'balance_after': current_balance - (payment.principal_portion or 0),
                'notes': payment.notes
            })
            
            # Update balance for next iteration
            if payment.principal_portion:
                current_balance -= payment.principal_portion
        
        # Reverse to get newest first
        payment_history.reverse()
        
        # Calculate summary
        total_paid = sum(p.amount for p in payments)
        total_principal = sum(p.principal_portion or 0 for p in payments)
        total_interest = sum(p.interest_portion or 0 for p in payments)
        
        return {
            'debt': {
                'id': str(debt.id),
                'name': debt.name,
                'original_balance': debt.principal_amount,
                'current_balance': debt.current_balance,
                'lender': debt.lender
            },
            'payment_summary': {
                'total_payments': len(payments),
                'total_paid': total_paid,
                'total_principal': total_principal,
                'total_interest': total_interest,
                'principal_reduction': debt.principal_amount - debt.current_balance
            },
            'payment_history': payment_history
        }

    async def update_payment(self, payment_id: UUID, payment_update: PaymentUpdate) -> Optional[PaymentInDB]:
        """
        Update payment information.
        
        Args:
            payment_id: Payment's ID
            payment_update: Update data
            
        Returns:
            Updated payment if found, None otherwise
        """
        update_data = payment_update.model_dump(exclude_unset=True)
        
        # Convert enum values to strings if present
        if 'status' in update_data:
            update_data['status'] = update_data['status'].value
            
        return await self.update(payment_id, update_data)

    async def get_payment_streaks(self, user_id: UUID) -> Dict[str, Any]:
        """
        Calculate payment streaks for gamification.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with streak information
        """
        # Get all payment dates in descending order
        query = """
            SELECT DISTINCT payment_date 
            FROM payment_history 
            WHERE user_id = $1 
            ORDER BY payment_date DESC
        """
        
        records = await self._fetch_all_with_error_handling(query, str(user_id))
        
        if not records:
            return {
                'current_streak': 0,
                'longest_streak': 0,
                'total_payment_days': 0,
                'last_payment_date': None
            }
        
        payment_dates = [record['payment_date'] for record in records]
        
        # Calculate current streak (consecutive days with payments)
        current_streak = 0
        today = date.today()
        
        for i, payment_date in enumerate(payment_dates):
            expected_date = today - timedelta(days=i)
            if payment_date == expected_date:
                current_streak += 1
            else:
                break
        
        # Calculate longest streak
        longest_streak = 0
        current_temp_streak = 1
        
        for i in range(1, len(payment_dates)):
            prev_date = payment_dates[i-1]
            curr_date = payment_dates[i]
            
            # Check if dates are consecutive
            if (prev_date - curr_date).days == 1:
                current_temp_streak += 1
                longest_streak = max(longest_streak, current_temp_streak)
            else:
                current_temp_streak = 1
        
        longest_streak = max(longest_streak, current_temp_streak)
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_payment_days': len(payment_dates),
            'last_payment_date': payment_dates[0] if payment_dates else None
        }

    async def get_payment_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive payment analytics for a user.
        
        Args:
            user_id: User's ID
            
        Returns:
            Dictionary with payment analytics
        """
        summary = await self.get_payment_summary(user_id)
        trends = await self.get_monthly_payment_trends(user_id, 6)  # 6 months
        streaks = await self.get_payment_streaks(user_id)
        
        # Get payment frequency analysis
        frequency_query = """
            SELECT 
                EXTRACT(DOW FROM payment_date) as day_of_week,
                COUNT(*) as payment_count
            FROM payment_history 
            WHERE user_id = $1 
            GROUP BY EXTRACT(DOW FROM payment_date)
            ORDER BY payment_count DESC
        """
        
        frequency_records = await self._fetch_all_with_error_handling(frequency_query, str(user_id))
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        payment_frequency = []
        
        for record in frequency_records:
            payment_frequency.append({
                'day_of_week': day_names[int(record['day_of_week'])],
                'payment_count': record['payment_count']
            })
        
        return {
            'summary': summary,
            'monthly_trends': trends,
            'streaks': streaks,
            'payment_frequency': payment_frequency,
            'analysis_date': datetime.now().isoformat()
        }

    async def get_upcoming_payment_reminders(self, days_ahead: int = 3) -> List[Dict[str, Any]]:
        """
        Get upcoming payment reminders for all users.
        
        Args:
            days_ahead: Number of days to look ahead for due payments
            
        Returns:
            List of payment reminders
        """
        query = """
            SELECT 
                d.id as debt_id,
                d.user_id,
                d.name as debt_name,
                d.lender,
                d.minimum_payment,
                d.due_date,
                u.email,
                u.full_name,
                u.notification_preferences
            FROM debts d
            JOIN users u ON d.user_id = u.id
            WHERE d.due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '%s days'
            AND d.is_active = true
            AND u.is_active = true
            ORDER BY d.due_date ASC
        """ % days_ahead
        
        records = await self._fetch_all_with_error_handling(query)
        
        reminders = []
        for record in records:
            reminders.append({
                'debt_id': str(record['debt_id']),
                'user_id': str(record['user_id']),
                'user_email': record['email'],
                'user_name': record['full_name'],
                'debt_name': record['debt_name'],
                'lender': record['lender'],
                'amount_due': float(record['minimum_payment']),
                'due_date': record['due_date'],
                'notification_preferences': record['notification_preferences']
            })
        
        return reminders

    async def bulk_create_payments(self, payments: List[PaymentCreate]) -> List[PaymentInDB]:
        """
        Create multiple payments in a single transaction.
        
        Args:
            payments: List of payment creation data
            
        Returns:
            List of created payments
        """
        created_payments = []
        
        try:
            async with self.db_manager.get_connection() as conn:
                async with conn.transaction():
                    for payment_create in payments:
                        payment_in_db = PaymentInDB(
                            debt_id=payment_create.debt_id,
                            user_id=payment_create.user_id,
                            amount=payment_create.amount,
                            payment_date=payment_create.payment_date,
                            principal_portion=payment_create.principal_portion,
                            interest_portion=payment_create.interest_portion,
                            notes=payment_create.notes,
                            status=payment_create.status,
                            extra_details=payment_create.extra_details,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        
                        # Insert payment
                        payment_dict = self._model_to_dict(payment_in_db)
                        insert_data = {k: v for k, v in payment_dict.items() if v is not None}
                        
                        columns = list(insert_data.keys())
                        placeholders = [f"${i+1}" for i in range(len(columns))]
                        values = list(insert_data.values())
                        
                        payment_query = f"""
                            INSERT INTO payment_history ({', '.join(columns)})
                            VALUES ({', '.join(placeholders)})
                            RETURNING *
                        """
                        
                        payment_record = await conn.fetchrow(payment_query, *values)
                        created_payment = self._record_to_model(payment_record)
                        created_payments.append(created_payment)
                        
                        # Update debt balance if principal portion is specified
                        if payment_create.principal_portion and payment_create.principal_portion > 0:
                            balance_query = """
                                UPDATE debts 
                                SET current_balance = current_balance - $1, updated_at = $2
                                WHERE id = $3
                            """
                            await conn.execute(
                                balance_query, 
                                payment_create.principal_portion, 
                                datetime.now(),
                                str(payment_create.debt_id)
                            )
            
            return created_payments
            
        except Exception as e:
            logger.error(f"Failed to bulk create payments: {e}")
            raise



