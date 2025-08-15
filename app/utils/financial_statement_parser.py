import csv
import json
import re
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging
from uuid import uuid4
from dataclasses import dataclass
import sys

# Add project root to Python path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

# Optional imports for PDF and advanced parsing
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    from app.models.transaction import Transaction
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(project_root / "app"))
    from models.transaction import Transaction

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ParsedTransaction:
    """Intermediate data structure for parsed transactions before validation."""
    date: str
    description: str
    amount: float
    transaction_type: str  # 'debit', 'credit', 'expense', 'income'
    category: Optional[str] = None
    balance: Optional[float] = None
    additional_details: Optional[Dict[str, Any]] = None

class BankStatementParser:
    """Parser for various bank statement formats."""
    
    # Common date formats found in bank statements
    DATE_FORMATS = [
        "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y",
        "%Y/%m/%d", "%m/%d/%y", "%d/%m/%y", "%b %d, %Y", "%d %b %Y",
        "%B %d, %Y", "%d %B %Y", "%Y%m%d"
    ]
    
    # Common column name mappings for different banks
    COLUMN_MAPPINGS = {
        'date': ['date', 'transaction date', 'posting date', 'trans date', 'value date', 'effective date'],
        'description': ['description', 'memo', 'payee', 'transaction description', 'details', 'merchant', 'reference'],
        'amount': ['amount', 'transaction amount', 'value', 'credit', 'debit'],
        'credit': ['credit', 'credit amount', 'deposits', 'cr', 'credit (+)'],
        'debit': ['debit', 'debit amount', 'withdrawals', 'dr', 'debit (-)'],
        'balance': ['balance', 'running balance', 'account balance', 'closing balance'],
        'type': ['type', 'transaction type', 'trans type', 'category']
    }
    
    def __init__(self, user_id: str):
        """Initialize parser with user ID."""
        self.user_id = user_id
    
    def parse_file(self, file_path: Union[str, Path], file_type: Optional[str] = None, **kwargs) -> List[Transaction]:
        """
        Parse a financial statement file and return structured transactions.
        
        Args:
            file_path: Path to the file to parse
            file_type: Optional file type ('csv', 'pdf', 'xlsx', 'json'). If None, inferred from extension.
            **kwargs: Additional parsing options
            
        Returns:
            List of Transaction objects
            
        Raises:
            ValueError: If file type is unsupported or parsing fails
            FileNotFoundError: If file doesn't exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Infer file type from extension if not provided
        if file_type is None:
            file_type = file_path.suffix.lower().lstrip('.')
        
        logger.info(f"Parsing {file_type.upper()} file: {file_path}")
        
        try:
            if file_type == 'csv':
                parsed_transactions = self._parse_csv(file_path, **kwargs)
            elif file_type == 'xlsx' or file_type == 'xls':
                parsed_transactions = self._parse_excel(file_path, **kwargs)
            elif file_type == 'pdf':
                parsed_transactions = self._parse_pdf(file_path, **kwargs)
            elif file_type == 'json':
                parsed_transactions = self._parse_json(file_path, **kwargs)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Convert to Transaction objects
            transactions = self._convert_to_transactions(parsed_transactions)
            
            logger.info(f"Successfully parsed {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            raise ValueError(f"Failed to parse file: {str(e)}")
    
    def _parse_csv(self, file_path: Path, encoding: str = 'utf-8', delimiter: str = None, **kwargs) -> List[ParsedTransaction]:
        """Parse CSV bank statement."""
        transactions = []
        
        # Try different encodings if the default fails
        encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
        
        for enc in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=enc) as file:
                    # Auto-detect delimiter if not provided
                    if delimiter is None:
                        sample = file.read(1024)
                        file.seek(0)
                        sniffer = csv.Sniffer()
                        delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.DictReader(file, delimiter=delimiter)
                    
                    # Normalize column names
                    normalized_fieldnames = {field.lower().strip(): field for field in reader.fieldnames}
                    
                    for row in reader:
                        try:
                            parsed_transaction = self._parse_row(row, normalized_fieldnames)
                            if parsed_transaction:
                                transactions.append(parsed_transaction)
                        except Exception as e:
                            logger.warning(f"Skipping row due to error: {e}")
                            continue
                
                break  # Successfully read with this encoding
                
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if enc == encodings_to_try[-1]:  # Last encoding attempt
                    raise e
                continue
        
        return transactions
    
    def _parse_excel(self, file_path: Path, sheet_name: Optional[str] = None, **kwargs) -> List[ParsedTransaction]:
        """Parse Excel bank statement."""
        if not EXCEL_AVAILABLE:
            raise ValueError("openpyxl is required for Excel file parsing. Install with: pip install openpyxl")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Convert DataFrame to list of dictionaries
            transactions = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                # Convert any NaN values to None
                row_dict = {k: (None if pd.isna(v) else v) for k, v in row_dict.items()}
                
                try:
                    normalized_columns = {col.lower().strip(): col for col in row_dict.keys()}
                    parsed_transaction = self._parse_row(row_dict, normalized_columns)
                    if parsed_transaction:
                        transactions.append(parsed_transaction)
                except Exception as e:
                    logger.warning(f"Skipping row due to error: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")
    
    def _parse_pdf(self, file_path: Path, **kwargs) -> List[ParsedTransaction]:
        """Parse PDF bank statement."""
        if not PDF_AVAILABLE:
            raise ValueError("pdfplumber is required for PDF parsing. Install with: pip install pdfplumber")
        
        transactions = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract tables from the page
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:  # Skip empty or header-only tables
                            continue
                        
                        # Assume first row is header
                        headers = table[0]
                        headers = [h.lower().strip() if h else f"col_{i}" for i, h in enumerate(headers)]
                        
                        for row_data in table[1:]:
                            if not any(row_data):  # Skip empty rows
                                continue
                            
                            row_dict = {headers[i]: row_data[i] for i in range(min(len(headers), len(row_data)))}
                            
                            try:
                                normalized_columns = {col: col for col in headers}
                                parsed_transaction = self._parse_row(row_dict, normalized_columns)
                                if parsed_transaction:
                                    transactions.append(parsed_transaction)
                            except Exception as e:
                                logger.warning(f"Skipping row due to error: {e}")
                                continue
            
            return transactions
            
        except Exception as e:
            raise ValueError(f"Error reading PDF file: {str(e)}")
    
    def _parse_json(self, file_path: Path, **kwargs) -> List[ParsedTransaction]:
        """Parse JSON bank statement."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            transactions = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                # Array of transactions
                transaction_list = data
            elif isinstance(data, dict):
                # Object with transactions array
                if 'transactions' in data:
                    transaction_list = data['transactions']
                elif 'data' in data:
                    transaction_list = data['data']
                else:
                    # Assume the entire object is a single transaction
                    transaction_list = [data]
            else:
                raise ValueError("Unsupported JSON structure")
            
            for transaction_data in transaction_list:
                try:
                    if isinstance(transaction_data, dict):
                        normalized_columns = {k.lower().strip(): k for k in transaction_data.keys()}
                        parsed_transaction = self._parse_row(transaction_data, normalized_columns)
                        if parsed_transaction:
                            transactions.append(parsed_transaction)
                except Exception as e:
                    logger.warning(f"Skipping transaction due to error: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            raise ValueError(f"Error reading JSON file: {str(e)}")
    
    def _parse_row(self, row: Dict[str, Any], normalized_columns: Dict[str, str]) -> Optional[ParsedTransaction]:
        """Parse a single row of transaction data."""
        # Find date
        date_str = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['date'])
        if not date_str:
            return None
        
        # Parse date
        parsed_date = self._parse_date(date_str)
        if not parsed_date:
            return None
        
        # Find description
        description = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['description'])
        if not description:
            description = "Unknown Transaction"
        
        # Find amount and determine transaction type
        amount, transaction_type = self._extract_amount_and_type(row, normalized_columns)
        if amount is None:
            return None
        
        # Find balance (optional)
        balance_str = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['balance'])
        balance = self._parse_amount(balance_str) if balance_str else None
        
        # Find category (optional)
        category = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['type'])
        
        # Collect additional details
        additional_details = {}
        for key, value in row.items():
            if value and key.lower() not in ['date', 'description', 'amount', 'credit', 'debit', 'balance', 'type']:
                additional_details[key] = value
        
        return ParsedTransaction(
            date=parsed_date,
            description=str(description).strip(),
            amount=amount,
            transaction_type=transaction_type,
            category=category,
            balance=balance,
            additional_details=additional_details if additional_details else None
        )
    
    def _extract_field(self, row: Dict[str, Any], normalized_columns: Dict[str, str], possible_names: List[str]) -> Optional[str]:
        """Extract a field value using possible column names."""
        for name in possible_names:
            if name in normalized_columns:
                original_name = normalized_columns[name]
                value = row.get(original_name)
                if value is not None:
                    return str(value).strip()
        return None
    
    def _extract_amount_and_type(self, row: Dict[str, Any], normalized_columns: Dict[str, str]) -> tuple[Optional[float], str]:
        """Extract amount and determine transaction type."""
        # Try to find combined amount field first
        amount_str = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['amount'])
        
        if amount_str:
            amount = self._parse_amount(amount_str)
            if amount is not None:
                # Determine type based on sign
                if amount >= 0:
                    return amount, 'credit'
                else:
                    return abs(amount), 'debit'
        
        # Try separate credit/debit fields
        credit_str = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['credit'])
        debit_str = self._extract_field(row, normalized_columns, self.COLUMN_MAPPINGS['debit'])
        
        credit_amount = self._parse_amount(credit_str) if credit_str else None
        debit_amount = self._parse_amount(debit_str) if debit_str else None
        
        if credit_amount is not None and credit_amount > 0:
            return credit_amount, 'credit'
        elif debit_amount is not None and debit_amount > 0:
            return debit_amount, 'debit'
        
        return None, 'unknown'
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string into ISO format."""
        if not date_str:
            return None
        
        # Clean the date string
        date_str = str(date_str).strip()
        
        for date_format in self.DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_str, date_format)
                return parsed_date.isoformat()
            except ValueError:
                continue
        
        # Try parsing with pandas (more flexible)
        try:
            parsed_date = pd.to_datetime(date_str)
            return parsed_date.isoformat()
        except Exception:
            logger.warning(f"Could not parse date: {date_str}")
            return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """Parse amount string into float."""
        if not amount_str:
            return None
        
        # Clean the amount string
        amount_str = str(amount_str).strip()
        
        # Remove currency symbols and spaces
        amount_str = re.sub(r'[^\d.,\-+()]', '', amount_str)
        
        # Handle parentheses as negative (common in accounting)
        if amount_str.startswith('(') and amount_str.endswith(')'):
            amount_str = '-' + amount_str[1:-1]
        
        # Handle comma as thousands separator
        if ',' in amount_str and '.' in amount_str:
            # Assume comma is thousands separator if it appears before the dot
            if amount_str.rfind(',') < amount_str.rfind('.'):
                amount_str = amount_str.replace(',', '')
        elif ',' in amount_str:
            # Check if comma is decimal separator (European format)
            parts = amount_str.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                amount_str = amount_str.replace(',', '.')
            else:
                amount_str = amount_str.replace(',', '')
        
        try:
            return float(amount_str)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return None
    
    def _convert_to_transactions(self, parsed_transactions: List[ParsedTransaction]) -> List[Transaction]:
        """Convert ParsedTransaction objects to Transaction model objects."""
        transactions = []
        
        for parsed in parsed_transactions:
            try:
                # Normalize transaction type
                if parsed.transaction_type.lower() in ['credit', 'income', 'deposit']:
                    transaction_type = 'income'
                elif parsed.transaction_type.lower() in ['debit', 'expense', 'withdrawal']:
                    transaction_type = 'expense'
                else:
                    # Determine based on amount sign or description analysis
                    transaction_type = self._infer_transaction_type(parsed.description, parsed.amount)
                
                # Create Transaction object
                transaction = Transaction(
                    id=str(uuid4()),
                    user_id=self.user_id,
                    amount=parsed.amount,
                    type=transaction_type,
                    category=parsed.category or 'Uncategorized',
                    description=parsed.description,
                    date=datetime.fromisoformat(parsed.date.replace('Z', '+00:00')),
                    source='parsed_statement',
                    details=parsed.additional_details
                )
                
                transactions.append(transaction)
                
            except Exception as e:
                logger.warning(f"Skipping transaction due to validation error: {e}")
                continue
        
        return transactions
    
    def _infer_transaction_type(self, description: str, amount: float) -> str:
        """Infer transaction type from description and amount."""
        description_lower = description.lower()
        
        # Income keywords
        income_keywords = ['salary', 'deposit', 'interest', 'dividend', 'refund', 'credit', 'payment received', 'transfer in']
        
        # Expense keywords
        expense_keywords = ['withdrawal', 'purchase', 'payment', 'fee', 'charge', 'debit', 'transfer out']
        
        for keyword in income_keywords:
            if keyword in description_lower:
                return 'income'
        
        for keyword in expense_keywords:
            if keyword in description_lower:
                return 'expense'
        
        # If amount is positive and no keywords match, assume income
        # If amount is negative or zero, assume expense
        return 'income' if amount > 0 else 'expense'

class FinancialStatementProcessor:
    """High-level processor for financial statements with additional utilities."""
    
    def __init__(self, user_id: str):
        """Initialize processor with user ID."""
        self.user_id = user_id
        self.parser = BankStatementParser(user_id)
    
    def process_file(self, file_path: Union[str, Path], **kwargs) -> Dict[str, Any]:
        """
        Process a financial statement file and return comprehensive results.
        
        Returns:
            Dictionary containing transactions, summary statistics, and metadata
        """
        transactions = self.parser.parse_file(file_path, **kwargs)
        
        # Generate summary statistics
        summary = self._generate_summary(transactions)
        
        return {
            'transactions': [t.model_dump() for t in transactions],
            'summary': summary,
            'metadata': {
                'user_id': self.user_id,
                'source_file': str(file_path),
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'total_transactions': len(transactions)
            }
        }
    
    def _generate_summary(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """Generate summary statistics for transactions."""
        if not transactions:
            return {}
        
        total_income = sum(t.amount for t in transactions if t.type == 'income')
        total_expenses = sum(t.amount for t in transactions if t.type == 'expense')
        
        # Category breakdown
        categories = {}
        for transaction in transactions:
            category = transaction.category
            if category not in categories:
                categories[category] = {'count': 0, 'total_amount': 0.0}
            categories[category]['count'] += 1
            categories[category]['total_amount'] += transaction.amount
        
        # Date range
        dates = [t.date for t in transactions]
        date_range = {
            'start_date': min(dates).isoformat() if dates else None,
            'end_date': max(dates).isoformat() if dates else None
        }
        
        return {
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net_amount': round(total_income - total_expenses, 2),
            'transaction_count': len(transactions),
            'categories': categories,
            'date_range': date_range,
            'average_transaction_amount': round(sum(t.amount for t in transactions) / len(transactions), 2) if transactions else 0
        }

# Convenience functions for easy usage
def parse_bank_statement(file_path: Union[str, Path], user_id: str, **kwargs) -> List[Transaction]:
    """
    Convenience function to parse a bank statement file.
    
    Args:
        file_path: Path to the file to parse
        user_id: User ID for the transactions
        **kwargs: Additional parsing options
        
    Returns:
        List of Transaction objects
    """
    parser = BankStatementParser(user_id)
    return parser.parse_file(file_path, **kwargs)

def process_financial_statement(file_path: Union[str, Path], user_id: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to process a financial statement and get comprehensive results.
    
    Args:
        file_path: Path to the file to parse
        user_id: User ID for the transactions
        **kwargs: Additional parsing options
        
    Returns:
        Dictionary with transactions, summary, and metadata
    """
    processor = FinancialStatementProcessor(user_id)
    return processor.process_file(file_path, **kwargs) 