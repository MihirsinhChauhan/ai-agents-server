#!/usr/bin/env python3
"""
Command-line interface for parsing financial statements.

Usage:
    python parse_statement.py input.csv --user-id user123 --output-format json
    python parse_statement.py bank_statement.pdf --user-id user123 --output output.json
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Optional

# Add project root to Python path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.utils.financial_statement_parser import FinancialStatementProcessor
    from app.utils.budget_data_formatter import BudgetDataFormatter
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(project_root / "app"))
    from utils.financial_statement_parser import FinancialStatementProcessor
    from utils.budget_data_formatter import BudgetDataFormatter

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Parse financial statements and convert to structured data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s statement.csv --user-id user123
  %(prog)s bank.xlsx --user-id user123 --output transactions.json
  %(prog)s statement.pdf --user-id user123 --format-for budget_planner
  %(prog)s data.json --user-id user123 --summary-only
  
Supported formats: CSV, Excel (.xlsx, .xls), PDF, JSON
        """
    )
    
    # Required arguments
    parser.add_argument(
        'input_file',
        help='Path to the financial statement file to parse'
    )
    parser.add_argument(
        '--user-id',
        required=True,
        help='User ID for the transactions'
    )
    
    # Optional arguments
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: print to stdout)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--format-for',
        choices=['expense_tracker', 'budget_planner', 'alert_notification', 'savings_goal_tracker', 'insight_analysis'],
        help='Format data for a specific budget tracking agent'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Output only the summary statistics'
    )
    parser.add_argument(
        '--file-type',
        choices=['csv', 'xlsx', 'xls', 'pdf', 'json'],
        help='Override file type detection'
    )
    parser.add_argument(
        '--delimiter',
        help='CSV delimiter (default: auto-detect)'
    )
    parser.add_argument(
        '--encoding',
        default='utf-8',
        help='File encoding (default: utf-8)'
    )
    parser.add_argument(
        '--sheet-name',
        help='Excel sheet name (default: first sheet)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # Parse the file
    try:
        if args.verbose:
            print(f"Parsing file: {input_path}", file=sys.stderr)
        
        processor = FinancialStatementProcessor(args.user_id)
        
        # Prepare parsing options
        parse_options = {}
        if args.file_type:
            parse_options['file_type'] = args.file_type
        if args.delimiter:
            parse_options['delimiter'] = args.delimiter
        if args.encoding:
            parse_options['encoding'] = args.encoding
        if args.sheet_name:
            parse_options['sheet_name'] = args.sheet_name
        
        # Process the file
        result = processor.process_file(input_path, **parse_options)
        
        if args.verbose:
            print(f"Successfully parsed {result['metadata']['total_transactions']} transactions", file=sys.stderr)
        
        # Format data for specific agent if requested
        if args.format_for:
            if args.verbose:
                print(f"Formatting data for {args.format_for} agent", file=sys.stderr)
            
            # Convert transaction data back to Transaction objects
            try:
                from app.models.transaction import Transaction
            except ImportError:
                from models.transaction import Transaction
            
            transactions = [Transaction.model_validate(tx) for tx in result['transactions']]
            
            formatter = BudgetDataFormatter()
            
            if args.format_for == 'expense_tracker':
                formatted_data = formatter.format_for_expense_tracker(transactions)
            elif args.format_for == 'budget_planner':
                formatted_data = formatter.format_for_budget_planner(transactions)
            elif args.format_for == 'alert_notification':
                formatted_data = formatter.format_for_alert_notification(transactions)
            elif args.format_for == 'savings_goal_tracker':
                # This requires financial goals, so we'll provide empty list
                formatted_data = formatter.format_for_savings_goal_tracker(transactions, [])
            elif args.format_for == 'insight_analysis':
                # This requires historical data, so we'll provide empty lists
                formatted_data = formatter.format_for_insight_analysis(transactions, [], [])
            
            output_data = {
                'agent_data': formatted_data,
                'metadata': result['metadata']
            }
        elif args.summary_only:
            output_data = {
                'summary': result['summary'],
                'metadata': result['metadata']
            }
        else:
            output_data = result
        
        # Output the result
        if args.output_format == 'json':
            output_json = json.dumps(output_data, indent=2, default=str)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output_json)
                if args.verbose:
                    print(f"Output written to: {args.output}", file=sys.stderr)
            else:
                print(output_json)
        
        elif args.output_format == 'csv':
            # Convert transactions to CSV format
            import csv
            import io
            
            if args.format_for:
                print("Error: CSV output not supported with --format-for option", file=sys.stderr)
                sys.exit(1)
            
            output_buffer = io.StringIO()
            if result['transactions']:
                # Use the first transaction to get field names
                fieldnames = list(result['transactions'][0].keys())
                writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(result['transactions'])
            
            csv_output = output_buffer.getvalue()
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(csv_output)
                if args.verbose:
                    print(f"Output written to: {args.output}", file=sys.stderr)
            else:
                print(csv_output)
        
    except Exception as e:
        print(f"Error parsing file: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 