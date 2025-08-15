#!/usr/bin/env python3
"""
Test script to verify import paths are working correctly.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all utility modules can be imported correctly."""
    
    print("🧪 Testing import paths...")
    print("=" * 50)
    
    # Test 1: Basic imports
    try:
        from app.utils.financial_statement_parser import FinancialStatementProcessor
        print("✅ financial_statement_parser imported successfully")
    except ImportError as e:
        print(f"❌ financial_statement_parser import failed: {e}")
        return False
    
    try:
        from app.utils.budget_data_formatter import BudgetDataFormatter
        print("✅ budget_data_formatter imported successfully")
    except ImportError as e:
        print(f"❌ budget_data_formatter import failed: {e}")
        return False
    
    try:
        from app.models.transaction import Transaction
        print("✅ Transaction model imported successfully")
    except ImportError as e:
        print(f"❌ Transaction model import failed: {e}")
        return False
    
    try:
        from app.agents.budget_tracking_agent.orchestrator import BudgetTrackingOrchestrator
        print("✅ BudgetTrackingOrchestrator imported successfully")
    except ImportError as e:
        print(f"❌ BudgetTrackingOrchestrator import failed: {e}")
        return False
    
    # Test 2: Test utility functionality
    print("\n🔧 Testing utility functionality...")
    
    try:
        processor = FinancialStatementProcessor("test-user")
        print("✅ FinancialStatementProcessor instantiated successfully")
    except Exception as e:
        print(f"❌ FinancialStatementProcessor instantiation failed: {e}")
        return False
    
    try:
        formatter = BudgetDataFormatter()
        print("✅ BudgetDataFormatter instantiated successfully")
    except Exception as e:
        print(f"❌ BudgetDataFormatter instantiation failed: {e}")
        return False
    
    # Test 3: Test model instantiation
    print("\n📊 Testing model instantiation...")
    
    try:
        from datetime import datetime
        transaction = Transaction(
            id="test-123",
            user_id="test-user",
            amount=100.0,
            description="Test transaction",
            date=datetime.now(),
            type="expense"
        )
        print("✅ Transaction model instantiated successfully")
    except Exception as e:
        print(f"❌ Transaction model instantiation failed: {e}")
        return False
    
    print("\n🎉 All import tests passed!")
    return True

def test_cli_imports():
    """Test that CLI scripts can be imported correctly."""
    
    print("\n🖥️ Testing CLI script imports...")
    print("=" * 50)
    
    try:
        # Test parse_statement CLI
        from app.utils.parse_statement import main as parse_main
        print("✅ parse_statement CLI imported successfully")
    except ImportError as e:
        print(f"❌ parse_statement CLI import failed: {e}")
        return False
    
    try:
        # Test example script
        from app.utils.financial_parser_example import main as example_main
        print("✅ financial_parser_example imported successfully")
    except ImportError as e:
        print(f"❌ financial_parser_example import failed: {e}")
        return False
    
    print("✅ All CLI script imports passed!")
    return True

if __name__ == "__main__":
    print("🚀 DebtEase AI Agents Server - Import Test")
    print("=" * 60)
    
    # Run import tests
    imports_ok = test_imports()
    cli_ok = test_cli_imports()
    
    if imports_ok and cli_ok:
        print("\n🎉 SUCCESS: All imports are working correctly!")
        print("\nYou can now run:")
        print("  python app/utils/parse_statement.py your_file.pdf --user-id your_id")
        print("  python app/utils/financial_parser_example.py")
        print("  python test_imports.py")
    else:
        print("\n❌ FAILURE: Some imports are not working correctly.")
        print("Please check the error messages above.")
        sys.exit(1) 