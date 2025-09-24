#!/usr/bin/env python3
"""
Test AI insights with real user who has debts
"""

import asyncio
from app.repositories.user_repository import UserRepository
from app.services.ai_service import AIService
from app.repositories.debt_repository import DebtRepository
from app.repositories.analytics_repository import AnalyticsRepository

async def test_with_real_user():
    try:
        user_repo = UserRepository()
        debt_repo = DebtRepository()
        analytics_repo = AnalyticsRepository()

        # Get the user with debts
        users = await user_repo.get_all()
        user_with_debts = None

        for user in users:
            user_debts = await debt_repo.get_debts_by_user_id(user.id)
            if user_debts and len(user_debts) > 0:
                user_with_debts = user
                print(f'Found user with debts: {user.email}')
                print(f'User ID: {user.id}')
                print(f'Number of debts: {len(user_debts)}')

                # Show debt details
                for i, debt in enumerate(user_debts):
                    print(f'  Debt {i+1}: {debt.name} - ₹{debt.current_balance} at {debt.interest_rate}%')
                break

        if not user_with_debts:
            print('No user with debts found')
            return

        # Test AI insights with this user
        ai_service = AIService(debt_repo, user_repo, analytics_repo)

        print('\nTesting enhanced AI insights...')
        result = await ai_service.get_enhanced_ai_insights(
            user_id=user_with_debts.id,
            monthly_payment_budget=12000,  # Higher than $10k minimum
            preferred_strategy='avalanche'
        )

        print('✅ Enhanced AI insights successful!')
        print(f'Current strategy: {result["current_strategy"]["name"]}')
        print(f'Time to debt free: {result["current_strategy"]["time_to_debt_free"]} months')
        print(f'Payment timeline entries: {len(result["payment_timeline"])}')
        print(f'Alternative strategies: {len(result["alternative_strategies"])}')

        return user_with_debts.id, result

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_real_user())