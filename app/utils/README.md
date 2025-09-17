# Financial Statement Parser and Budget Data Formatter

This directory contains utilities for parsing financial statements from various formats and converting them into structured data for the budget tracking agents.

## Overview

The financial statement parser can process bank statements in multiple formats (CSV, Excel, PDF, JSON) and convert them into standardized Transaction objects that can be used by the budget tracking agents.

## Components

### 1. `financial_statement_parser.py`
Core parser that handles multiple file formats and extracts transaction data.

**Key Classes:**
- `BankStatementParser`: Main parser class
- `FinancialStatementProcessor`: High-level processor with summary statistics
- `ParsedTransaction`: Intermediate data structure for validation

**Supported Formats:**
- **CSV**: Comma-separated values with headers
- **Excel**: .xlsx and .xls files
- **PDF**: Bank statements with table data (requires `pdfplumber`)
- **JSON**: Transaction data in JSON format

### 2. `budget_data_formatter.py`
Formats parsed transaction data for specific budget tracking agents.

**Key Classes:**
- `BudgetDataFormatter`: Formats data for each agent type

**Supported Agents:**
- Expense Tracker Agent
- Budget Planner Agent
- Alert Notification Agent
- Savings Goal Tracker Agent
- Insight Analysis Agent

### 3. `parse_statement.py`
Command-line interface for easy parsing of financial statements.

### 4. `financial_parser_example.py`
Comprehensive examples showing how to use the parsers and integrate with budget tracking agents.

## Installation

### Basic Requirements
```bash
pip install pandas pydantic
```

### Optional Dependencies
For PDF parsing:
```bash
pip install pdfplumber
```

For Excel parsing:
```bash
pip install openpyxl
```

## Usage

### Basic Usage

```python
from app.utils.financial_statement_parser import parse_bank_statement
from app.utils.budget_data_formatter import format_transactions_for_agent

# Parse a bank statement
user_id = "user123"
transactions = parse_bank_statement("bank_statement.csv", user_id)

# Format for expense tracker agent
expense_data = format_transactions_for_agent(transactions, "expense_tracker")
```

### Advanced Usage

```python
from app.utils.financial_statement_parser import FinancialStatementProcessor
from app.utils.budget_data_formatter import BudgetDataFormatter

# Create processor
processor = FinancialStatementProcessor(user_id)

# Process file with custom options
result = processor.process_file(
    "statement.csv",
    delimiter=";",
    encoding="latin-1"
)

# Get comprehensive results
print(f"Parsed {result['metadata']['total_transactions']} transactions")
print(f"Total income: ${result['summary']['total_income']:.2f}")
print(f"Total expenses: ${result['summary']['total_expenses']:.2f}")

# Format for budget planner
formatter = BudgetDataFormatter()
budget_data = formatter.format_for_budget_planner(
    transactions,
    income_frequency="monthly"
)
```

### Command Line Usage

```bash
# Basic parsing
python app/utils/parse_statement.py statement.csv --user-id user123

# Parse and save to file
python app/utils/parse_statement.py bank.xlsx --user-id user123 --output transactions.json

# Format for specific agent
python app/utils/parse_statement.py statement.pdf --user-id user123 --format-for budget_planner

# Get summary only
python app/utils/parse_statement.py data.csv --user-id user123 --summary-only

# Custom options
python app/utils/parse_statement.py statement.csv --user-id user123 --delimiter ";" --encoding latin-1
```

### Integration with Budget Tracking Agents

```python
from app.agents.budget_tracking_agent.orchestrator import BudgetTrackingOrchestrator
from app.utils.financial_statement_parser import FinancialStatementProcessor
from app.utils.budget_data_formatter import BudgetDataFormatter

# Step 1: Parse financial statement
processor = FinancialStatementProcessor(user_id)
parsed_result = processor.process_file("bank_statement.csv")

# Step 2: Format for agents
formatter = BudgetDataFormatter()
budget_data = formatter.format_for_budget_planner(transactions)
alert_data = formatter.format_for_alert_notification(transactions)

# Step 3: Run through orchestrator
orchestrator = BudgetTrackingOrchestrator()

user_input = {
    'income_sources': budget_data['income_sources'],
    'fixed_expenses': budget_data['fixed_expenses'],
    'desired_categories': budget_data['desired_categories'],
    'upcoming_bills': alert_data['upcoming_bills'],
    'historical_spending_patterns': alert_data['historical_spending_patterns']
}

# Convert transactions to dictionaries
transaction_dicts = [tx.model_dump() for tx in transactions]

# Run workflow
result = orchestrator.run_budget_workflow(
    user_id=user_id,
    user_input=user_input,
    transactions=transaction_dicts
)
```

## File Format Examples

### CSV Format
```csv
Date,Description,Amount,Type
2024-01-01,Salary Deposit,3500.00,credit
2024-01-02,Grocery Store,-85.50,debit
2024-01-03,Gas Station,-45.00,debit
```

### Excel Format
Excel files should have columns like:
- Date, Transaction Date, Posting Date
- Description, Memo, Payee
- Amount, Credit, Debit
- Balance (optional)

### JSON Format
```json
{
  "transactions": [
    {
      "date": "2024-01-01",
      "description": "Salary Deposit",
      "amount": 3500.00,
      "type": "credit"
    },
    {
      "date": "2024-01-02", 
      "description": "Grocery Store",
      "amount": -85.50,
      "type": "debit"
    }
  ]
}
```

## Parser Features

### Automatic Detection
- **Date Formats**: Supports 13+ common date formats
- **Currency Formats**: Handles various currency notations ($, €, comma separators)
- **Column Names**: Maps different bank column naming conventions
- **File Encoding**: Auto-detects encoding for text files
- **Delimiters**: Auto-detects CSV delimiters

### Data Cleaning
- Removes currency symbols and formatting
- Handles parentheses notation for negative amounts
- Normalizes transaction types (credit/debit → income/expense)
- Categorizes transactions based on description patterns

### Error Handling
- Graceful handling of malformed data
- Detailed error messages for debugging
- Skips invalid rows while processing valid ones
- Multiple encoding attempts for text files

## Agent Data Formatting

### Expense Tracker Agent
```python
{
    'transactions': [
        {
            'id': 'uuid',
            'amount': 85.50,
            'description': 'Grocery Store',
            'date': '2024-01-02T00:00:00',
            'type': 'expense'
        }
    ],
    'total_count': 1
}
```

### Budget Planner Agent
```python
{
    'income_sources': [
        {
            'name': 'Salary',
            'amount': 3500.00,
            'frequency': 'monthly'
        }
    ],
    'fixed_expenses': [
        {
            'name': 'rent payment',
            'amount': 1200.00,
            'frequency': 'monthly'
        }
    ],
    'desired_categories': ['Housing', 'Food', 'Transportation', ...]
}
```

### Alert Notification Agent
```python
{
    'recent_transactions': [...],
    'current_budget': {...},
    'upcoming_bills': [
        {
            'name': 'Electric Bill',
            'amount': 120.00,
            'due_date': '2024-02-05T00:00:00'
        }
    ],
    'historical_spending_patterns': {
        'Food': {
            'average': 450.00,
            'min': 200.00,
            'max': 800.00
        }
    }
}
```

## Error Handling and Troubleshooting

### Common Issues

1. **Encoding Errors**
   - Try different encodings: `encoding='latin-1'` or `encoding='cp1252'`
   - Use the verbose flag to see detailed error messages

2. **Date Parsing Errors**
   - Check date format in your file
   - The parser supports most common formats automatically

3. **Amount Parsing Errors**
   - Ensure amounts are numeric
   - Currency symbols are automatically removed

4. **PDF Parsing Issues**
   - Install `pdfplumber`: `pip install pdfplumber`
   - PDF tables must be well-structured

### Debugging

Use the verbose flag for detailed information:
```bash
python app/utils/parse_statement.py statement.csv --user-id user123 --verbose
```

Enable logging in your code:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Testing

Run the example script to test the functionality:
```bash
python app/utils/financial_parser_example.py
```

This will:
1. Create a sample CSV file
2. Parse it using the financial statement parser
3. Format the data for budget tracking agents
4. Run it through the orchestrator
5. Display the results

## Best Practices

1. **Data Validation**: Always validate parsed data before using it in production
2. **Error Handling**: Implement proper error handling for file parsing failures
3. **Backup Data**: Keep original files as backup before processing
4. **Privacy**: Ensure financial data is handled securely and in compliance with regulations
5. **Testing**: Test with various file formats and edge cases

## Contributing

When adding new parser features:

1. Add tests for new file formats
2. Update column mapping dictionaries for new bank formats
3. Add examples to the example script
4. Update this README with new features

## License

This code is part of the DebtEase project and follows the project's licensing terms. 