#!/usr/bin/env python3
"""
Example script demonstrating how to use the financial statement parser
and integrate it with the budget tracking agents.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.utils.financial_statement_parser import FinancialStatementProcessor, parse_bank_statement
    from app.utils.budget_data_formatter import BudgetDataFormatter, format_transactions_for_agent
    from app.agents.budget_tracking_agent.orchestrator import BudgetTrackingOrchestrator
    from app.models.transaction import Transaction
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(project_root / "app"))
    from utils.financial_statement_parser import FinancialStatementProcessor, parse_bank_statement
    from utils.budget_data_formatter import BudgetDataFormatter, format_transactions_for_agent
    from agents.budget_tracking_agent.orchestrator import BudgetTrackingOrchestrator
    from models.transaction import Transaction

def example_parse_and_process_statement(file_path: str, user_id: str) -> Dict[str, Any]:
    """
    Example function showing how to parse a financial statement and process it
    through the budget tracking agents.
    
    Args:
        file_path: Path to the financial statement file
        user_id: User ID for the transactions
        
    Returns:
        Dictionary with parsed data and agent results
    """
    print(f"Processing financial statement: {file_path}")
    
    # Step 1: Parse the financial statement
    processor = FinancialStatementProcessor(user_id)
    
    try:
        # Process the file and get comprehensive results
        parsed_result = processor.process_file(file_path)
        
        print(f"Successfully parsed {parsed_result['metadata']['total_transactions']} transactions")
        print(f"Total income: ${parsed_result['summary']['total_income']:.2f}")
        print(f"Total expenses: ${parsed_result['summary']['total_expenses']:.2f}")
        print(f"Net amount: ${parsed_result['summary']['net_amount']:.2f}")
        
        # Convert back to Transaction objects for agent processing
        transactions = []
        for tx_data in parsed_result['transactions']:
            transaction = Transaction.model_validate(tx_data)
            transactions.append(transaction)
        
        # Step 2: Format data for budget tracking agents
        formatter = BudgetDataFormatter()
        
        # Format for expense tracker
        expense_tracker_data = formatter.format_for_expense_tracker(transactions)
        
        # Format for budget planner
        budget_planner_data = formatter.format_for_budget_planner(
            transactions, 
            income_frequency='monthly'
        )
        
        # Format for alert notification
        alert_data = formatter.format_for_alert_notification(transactions)
        
        # Step 3: Run through budget tracking orchestrator
        orchestrator = BudgetTrackingOrchestrator()
        
        # Prepare input for orchestrator
        user_input = {
            'action': 'analyze_transactions',
            'income_sources': budget_planner_data['income_sources'],
            'fixed_expenses': budget_planner_data['fixed_expenses'],
            'desired_categories': budget_planner_data['desired_categories'],
            'upcoming_bills': alert_data['upcoming_bills'],
            'historical_spending_patterns': alert_data['historical_spending_patterns']
        }
        
        # Convert transactions to dictionaries for orchestrator
        transaction_dicts = [tx.model_dump() for tx in transactions]
        
        # Run the budget workflow
        workflow_result = orchestrator.run_budget_workflow(
            user_id=user_id,
            user_input=user_input,
            transactions=transaction_dicts
        )
        
        return {
            'parsed_data': parsed_result,
            'formatted_data': {
                'expense_tracker': expense_tracker_data,
                'budget_planner': budget_planner_data,
                'alert_notification': alert_data
            },
            'workflow_result': workflow_result
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return {'error': str(e)}

def example_csv_parsing():
    """Example of parsing a CSV bank statement."""
    print("\n" + "="*50)
    print("CSV PARSING EXAMPLE")
    print("="*50)
    
    # Create a sample CSV file for demonstration
    sample_csv_content = """Date,Description,Amount,Type
2024-01-01,Salary Deposit,3500.00,credit
2024-01-02,Grocery Store,-85.50,debit
2024-01-03,Gas Station,-45.00,debit
2024-01-05,Electric Bill,-120.00,debit
2024-01-10,Restaurant,-35.50,debit
2024-01-15,Salary Deposit,3500.00,credit
2024-01-16,Rent Payment,-1200.00,debit
2024-01-20,Online Shopping,-89.99,debit"""
    
    # Write sample file
    sample_file = Path("sample_transactions.csv")
    with open(sample_file, 'w') as f:
        f.write(sample_csv_content)
    
    try:
        # Parse the sample file
        user_id = "example-user-123"
        result = example_parse_and_process_statement(str(sample_file), user_id)
        
        if 'error' not in result:
            print("\nParsing successful!")
            print("\nSample workflow results:")
            
            if result['workflow_result']['budget_plan']:
                print("- Budget plan created successfully")
                print(f"- Total income: ${result['workflow_result']['budget_plan']['total_income']:.2f}")
                print(f"- Discretionary income: ${result['workflow_result']['budget_plan']['discretionary_income']:.2f}")
            
            if result['workflow_result']['expense_summary']:
                print("- Expense tracking completed")
                print(f"- Total expenses: ${result['workflow_result']['expense_summary']['total_expenses']:.2f}")
            
            if result['workflow_result']['alerts']:
                alerts = result['workflow_result']['alerts']['alerts']
                print(f"- {len(alerts)} alerts generated")
                for alert in alerts[:3]:  # Show first 3 alerts
                    print(f"  * {alert['type']}: {alert['message']}")
        else:
            print(f"Error: {result['error']}")
            
    finally:
        # Clean up sample file
        if sample_file.exists():
            sample_file.unlink()

def example_supported_formats():
    """Show examples of supported file formats."""
    print("\n" + "="*50)
    print("SUPPORTED FILE FORMATS")
    print("="*50)
    
    formats = {
        'CSV': {
            'extensions': ['.csv'],
            'description': 'Comma-separated values with headers',
            'example_columns': ['Date', 'Description', 'Amount', 'Type']
        },
        'Excel': {
            'extensions': ['.xlsx', '.xls'],
            'description': 'Microsoft Excel spreadsheets',
            'example_columns': ['Date', 'Memo', 'Debit', 'Credit', 'Balance']
        },
        'PDF': {
            'extensions': ['.pdf'],
            'description': 'PDF bank statements with tables',
            'note': 'Requires pdfplumber: pip install pdfplumber'
        },
        'JSON': {
            'extensions': ['.json'],
            'description': 'JSON format with transaction arrays',
            'example_structure': {'transactions': [{'date': '...', 'amount': '...'}]}
        }
    }
    
    for format_name, info in formats.items():
        print(f"\n{format_name}:")
        print(f"  Extensions: {', '.join(info['extensions'])}")
        print(f"  Description: {info['description']}")
        if 'example_columns' in info:
            print(f"  Example columns: {', '.join(info['example_columns'])}")
        if 'note' in info:
            print(f"  Note: {info['note']}")
        if 'example_structure' in info:
            print(f"  Example structure: {info['example_structure']}")

def example_custom_parsing():
    """Example of custom parsing with specific options."""
    print("\n" + "="*50)
    print("CUSTOM PARSING OPTIONS")
    print("="*50)
    
    print("Examples of custom parsing options:")
    print("\n1. CSV with custom delimiter:")
    print("   parse_bank_statement('file.csv', user_id, delimiter=';')")
    
    print("\n2. Excel with specific sheet:")
    print("   parse_bank_statement('file.xlsx', user_id, sheet_name='Transactions')")
    
    print("\n3. Custom encoding:")
    print("   parse_bank_statement('file.csv', user_id, encoding='latin-1')")
    
    print("\n4. File type override:")
    print("   parse_bank_statement('file.txt', user_id, file_type='csv')")
    
    print("\nThe parser automatically handles:")
    print("- Multiple date formats")
    print("- Different currency formats")
    print("- Various column naming conventions")
    print("- Credit/debit notation variations")
    print("- Encoding detection")

def main():
    """Main function demonstrating the financial statement parser."""
    print("FINANCIAL STATEMENT PARSER EXAMPLES")
    print("="*50)
    
    # Show supported formats
    example_supported_formats()
    
    # Show custom parsing options
    example_custom_parsing()
    
    # Run CSV parsing example
    example_csv_parsing()
    
    print("\n" + "="*50)
    print("USAGE EXAMPLES COMPLETE")
    print("="*50)
    
    print("\nTo use in your application:")
    print("1. Import the parser: from app.utils.financial_statement_parser import parse_bank_statement")
    print("2. Parse your file: transactions = parse_bank_statement('path/to/file.csv', user_id)")
    print("3. Format for agents: from app.utils.budget_data_formatter import format_transactions_for_agent")
    print("4. Run through orchestrator: orchestrator.run_budget_workflow(...)")

if __name__ == "__main__":
    main() 