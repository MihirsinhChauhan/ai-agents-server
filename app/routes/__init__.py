# Route module exports
# Temporarily commenting out old routes with import issues
# from .auth import router as auth
# from .debt import router as debts
# from .repayment_plan import router as repayment_plans
# from .notification import router as notifications

# Session-based routes (using repository pattern and enhanced models)
from .auth import router as auth
from .debt_new import router as debt_new
from .payment_new import router as payment_new
from .ai import router as ai

__all__ = [
    'auth',
    'debt_new',
    'payment_new',
    'ai'
]
