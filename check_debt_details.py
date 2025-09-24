#!/usr/bin/env python3

import asyncio
from app.repositories.user_repository import UserRepository
from app.repositories.debt_repository import DebtRepository

async def check_debt_details():
    try:
        user_repo = UserRepository()
        debt_repo = DebtRepository()

        users = await user_repo.get_all()
        for user in users:
            debts = await debt_repo.get_debts_by_user_id(user.id)
            if debts:
                print(f'User: {user.email}')
                total_minimums = 0
                for i, debt in enumerate(debts):
                    print(f'  Debt {i+1}: {debt.name}')
                    print(f'    Balance: ₹{debt.current_balance}')
                    print(f'    Interest: {debt.interest_rate}%')
                    print(f'    Minimum payment: ₹{debt.minimum_payment}')
                    total_minimums += float(debt.minimum_payment)

                print(f'  Total minimum payments: ₹{total_minimums}')
                break
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_debt_details())