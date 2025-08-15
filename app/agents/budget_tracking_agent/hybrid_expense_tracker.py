import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.configs.config import settings
from app.models.transaction import Transaction
from app.utils.smart_categorizer import SmartCategorizer

class CategorizedTransaction(BaseModel):
    """Represents a single transaction with an assigned category."""
    transaction_id: str = Field(..., description="ID of the original transaction")
    amount: float = Field(..., description="Amount of the transaction")
    type: str = Field(..., description="Type of transaction (e.g., 'expense', 'income')")
    category: str = Field(..., description="Assigned category for the transaction")
    description: Optional[str] = Field(None, description="Description of the transaction")
    date: datetime = Field(..., description="Date of the transaction")
    categorization_method: str = Field(..., description="Method used for categorization (rule_based or llm)")
    categorization_confidence: float = Field(..., description="Confidence score for categorization")

class ExpenseTrackingSummary(BaseModel):
    """Summary of expense tracking and categorization."""
    user_id: str = Field(..., description="UUID of the user")
    total_expenses: float = Field(..., description="Total sum of all categorized expenses")
    total_income: float = Field(..., description="Total sum of all categorized income")
    categorized_transactions: List[CategorizedTransaction] = Field(..., description="List of all transactions with their assigned categories")
    spending_by_category: Dict[str, float] = Field(..., description="Dictionary summarizing spending per category")
    uncategorized_transactions_count: int = Field(..., description="Number of transactions that could not be categorized")
    tracking_timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of expense tracking summary creation")
    insights: List[str] = Field(..., description="Key insights from the expense tracking")
    categorization_stats: Dict[str, Any] = Field(..., description="Statistics about rule-based vs LLM categorization")

class HybridExpenseTracker:
    """Hybrid expense tracker using rules + LLM for categorization."""
    
    def __init__(self):
        """Initialize the hybrid expense tracker."""
        self.smart_categorizer = SmartCategorizer()
        self.llm_agent = self._initialize_llm_agent()
    
    def _initialize_llm_agent(self):
        """Initialize the LLM agent for uncategorized transactions."""
        if settings.LLM_PROVIDER == "openai":
            model = OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.LLM_BASE_URL if settings.LLM_BASE_URL else None
                )
            )
        elif settings.LLM_PROVIDER == "groq":
            model = GroqModel(
                model_name=settings.LLM_MODEL,
                provider=GroqProvider(api_key=settings.GROQ_API_KEY)
            )
        elif settings.LLM_PROVIDER == "ollama":
            model = OpenAIModel(
                model_name=settings.LLM_MODEL,
                provider=OpenAIProvider(
                    base_url=settings.LLM_BASE_URL,
                    api_key="dummy"
                )
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

        return Agent(
            model=model,
            system_prompt=self._get_llm_system_prompt(),
            result_type=List[CategorizedTransaction]
        )
    
    def _get_llm_system_prompt(self) -> str:
        """System prompt for LLM categorization of uncategorized transactions."""
        return """
        You are an Expense Categorization Specialist. You receive transactions that couldn't be categorized by rule-based systems and need to assign appropriate categories.

        Input: JSON array of transactions, each with:
        - transaction_id: string
        - amount: float  
        - description: string
        - date: string (ISO format)
        - type: string ('expense' or 'income')

        Available categories: Transportation, Food, Groceries, Shopping, Entertainment, Mobile/Internet, Utilities, Healthcare, Education, Housing, Banking, Travel, Insurance, Miscellaneous, Uncategorized

        For each transaction, analyze the description and assign the most appropriate category. Consider:
        - Merchant names and services
        - Transaction context and patterns
        - Amount ranges typical for categories
        - Indian payment patterns (UPI, NEFT, etc.)

        Output: Array of CategorizedTransaction objects with:
        - All original fields
        - category: assigned category
        - categorization_method: "llm"  
        - categorization_confidence: 0.6-0.9 based on certainty

        Rules:
        - Be conservative with confidence scores (0.6-0.9 range)
        - Use "Miscellaneous" for unclear transactions
        - Ensure all input transactions are included in output
        - Dates must be in ISO format with timezone (e.g., "2025-06-07T00:00:00+00:00")
        """
    
    def track_expenses(self, user_id: str, transactions: List[Dict[str, Any]], 
                      available_categories: List[str] = None, 
                      min_confidence: float = 0.5) -> ExpenseTrackingSummary:
        """
        Track expenses using hybrid rule-based + LLM categorization.
        
        Args:
            user_id: User ID
            transactions: List of transaction dictionaries
            available_categories: List of available categories (optional)
            min_confidence: Minimum confidence for rule-based categorization
            
        Returns:
            ExpenseTrackingSummary with categorization results
        """
        print(f"🔄 Processing {len(transactions)} transactions...")
        
        # Step 1: Rule-based categorization
        print("📋 Applying rule-based categorization...")
        rule_categorized, needs_llm = self.smart_categorizer.categorize_transactions(
            transactions, min_confidence=min_confidence
        )
        
        rule_stats = self.smart_categorizer.get_categorization_stats()
        print(f"   ✅ Rule-based: {len(rule_categorized)} transactions ({rule_stats['rule_based_percentage']:.1f}%)")
        print(f"   🤖 Needs LLM: {len(needs_llm)} transactions")
        
        # Step 2: LLM categorization for remaining transactions
        llm_categorized = []
        if needs_llm:
            print("🤖 Processing uncategorized transactions with LLM...")
            
            # Process in smaller batches to avoid token limits
            batch_size = 20
            for i in range(0, len(needs_llm), batch_size):
                batch = needs_llm[i:i+batch_size]
                print(f"   Processing batch {i//batch_size + 1}/{(len(needs_llm) + batch_size - 1)//batch_size}")
                
                try:
                    # Prepare input for LLM
                    llm_input = []
                    for tx in batch:
                        llm_input.append({
                            'transaction_id': tx['id'],
                            'amount': tx['amount'],
                            'description': tx['description'],
                            'date': tx['date'],
                            'type': tx['type']
                        })
                    
                    # Call LLM
                    result = self.llm_agent.run_sync(json.dumps(llm_input, default=str))
                    
                    # Process LLM results
                    for llm_tx in result.data:
                        llm_tx.categorization_method = "llm"
                        llm_categorized.append(llm_tx.model_dump())
                        
                except Exception as e:
                    print(f"   ⚠️ LLM batch failed: {e}")
                    # Fallback: mark as uncategorized
                    for tx in batch:
                        fallback_tx = CategorizedTransaction(
                            transaction_id=tx['id'],
                            amount=tx['amount'],
                            type=tx['type'],
                            category='Uncategorized',
                            description=tx['description'],
                            date=datetime.fromisoformat(tx['date'].replace('Z', '+00:00')),
                            categorization_method='fallback',
                            categorization_confidence=0.0
                        )
                        llm_categorized.append(fallback_tx.model_dump())
        
        # Step 3: Combine results
        all_categorized = []
        
        # Add rule-based results
        for tx in rule_categorized:
            categorized_tx = CategorizedTransaction(
                transaction_id=tx['id'],
                amount=tx['amount'],
                type=tx['type'],
                category=tx['category'],
                description=tx['description'],
                date=datetime.fromisoformat(tx['date'].replace('Z', '+00:00')),
                categorization_method=tx['categorization_method'],
                categorization_confidence=tx['categorization_confidence']
            )
            all_categorized.append(categorized_tx)
        
        # Add LLM results
        for tx_dict in llm_categorized:
            if isinstance(tx_dict['date'], str):
                tx_dict['date'] = datetime.fromisoformat(tx_dict['date'].replace('Z', '+00:00'))
            categorized_tx = CategorizedTransaction(**tx_dict)
            all_categorized.append(categorized_tx)
        
        # Step 4: Calculate summary statistics
        total_expenses = sum(tx.amount for tx in all_categorized if tx.type == 'expense')
        total_income = sum(tx.amount for tx in all_categorized if tx.type == 'income')
        
        spending_by_category = {}
        for tx in all_categorized:
            if tx.type == 'expense':
                spending_by_category[tx.category] = spending_by_category.get(tx.category, 0) + tx.amount
        
        uncategorized_count = sum(1 for tx in all_categorized if tx.category == 'Uncategorized')
        
        # Generate insights
        insights = self._generate_insights(all_categorized, spending_by_category)
        
        # Categorization statistics
        categorization_stats = {
            'total_transactions': len(all_categorized),
            'rule_based_count': len(rule_categorized),
            'llm_categorized_count': len(llm_categorized),
            'rule_based_percentage': (len(rule_categorized) / len(all_categorized) * 100) if all_categorized else 0,
            'llm_percentage': (len(llm_categorized) / len(all_categorized) * 100) if all_categorized else 0,
            'uncategorized_percentage': (uncategorized_count / len(all_categorized) * 100) if all_categorized else 0
        }
        
        print(f"📊 Final Results:")
        print(f"   Total: {len(all_categorized)} transactions")
        print(f"   Rule-based: {categorization_stats['rule_based_percentage']:.1f}%")
        print(f"   LLM-categorized: {categorization_stats['llm_percentage']:.1f}%")
        print(f"   Uncategorized: {categorization_stats['uncategorized_percentage']:.1f}%")
        
        return ExpenseTrackingSummary(
            user_id=user_id,
            total_expenses=round(total_expenses, 2),
            total_income=round(total_income, 2),
            categorized_transactions=all_categorized,
            spending_by_category={k: round(v, 2) for k, v in spending_by_category.items()},
            uncategorized_transactions_count=uncategorized_count,
            insights=insights,
            categorization_stats=categorization_stats
        )
    
    def _generate_insights(self, transactions: List[CategorizedTransaction], 
                          spending_by_category: Dict[str, float]) -> List[str]:
        """Generate insights from categorized transactions."""
        insights = []
        
        if not transactions:
            return ["No transactions to analyze."]
        
        # Top spending categories
        sorted_categories = sorted(spending_by_category.items(), key=lambda x: x[1], reverse=True)
        if sorted_categories:
            top_category, top_amount = sorted_categories[0]
            insights.append(f"Highest spending category: {top_category} (₹{top_amount:.2f})")
        
        # Rule-based vs LLM categorization efficiency
        rule_based_count = sum(1 for tx in transactions if tx.categorization_method == 'rule_based')
        llm_count = sum(1 for tx in transactions if tx.categorization_method == 'llm')
        
        if rule_based_count > 0:
            rule_percentage = (rule_based_count / len(transactions)) * 100
            insights.append(f"Rule-based categorization handled {rule_percentage:.1f}% of transactions")
        
        # High confidence categorizations
        high_confidence = sum(1 for tx in transactions if tx.categorization_confidence >= 0.8)
        if high_confidence > 0:
            confidence_percentage = (high_confidence / len(transactions)) * 100
            insights.append(f"{confidence_percentage:.1f}% of categorizations have high confidence (≥0.8)")
        
        # Uncategorized transactions warning
        uncategorized_count = sum(1 for tx in transactions if tx.category == 'Uncategorized')
        if uncategorized_count > len(transactions) * 0.1:  # More than 10%
            insights.append(f"High number of uncategorized transactions ({uncategorized_count}). Consider adding more categorization rules.")
        
        return insights

def main():
    """Run the hybrid expense tracker from command line."""
    import argparse
    from uuid import uuid4
    
    parser = argparse.ArgumentParser(description='Track expenses using hybrid rule-based + LLM categorization')
    parser.add_argument('--user_id', type=str, default=str(uuid4()), help='UUID of the user')
    parser.add_argument('--transactions_file', type=str, required=True, help='Path to JSON file with transactions')
    parser.add_argument('--min_confidence', type=float, default=0.5, help='Minimum confidence for rule-based categorization')
    parser.add_argument('--output_file', type=str, help='Path to save results JSON file')
    
    args = parser.parse_args()
    
    # Load transactions
    if not os.path.exists(args.transactions_file):
        print(f"❌ Error: File {args.transactions_file} not found")
        return
    
    with open(args.transactions_file, 'r') as f:
        data = json.load(f)
    
    # Handle both raw_data.json format and pure transactions array
    if 'transactions' in data:
        transactions = data['transactions']
    else:
        transactions = data
    
    # Initialize and run tracker
    tracker = HybridExpenseTracker()
    
    try:
        print(f"🚀 Starting Hybrid Expense Tracking for {len(transactions)} transactions...")
        
        result = tracker.track_expenses(
            user_id=args.user_id,
            transactions=transactions,
            min_confidence=args.min_confidence
        )
        
        print("\n" + "=" * 60)
        print("📋 EXPENSE TRACKING SUMMARY")
        print("=" * 60)
        print(f"User ID: {result.user_id}")
        print(f"Total Income: ₹{result.total_income:,.2f}")
        print(f"Total Expenses: ₹{result.total_expenses:,.2f}")
        print(f"Net Amount: ₹{result.total_income - result.total_expenses:,.2f}")
        print(f"Transactions Processed: {len(result.categorized_transactions)}")
        print(f"Uncategorized: {result.uncategorized_transactions_count}")
        
        print(f"\n📊 Spending by Category:")
        for category, amount in sorted(result.spending_by_category.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: ₹{amount:,.2f}")
        
        print(f"\n🔍 Insights:")
        for insight in result.insights:
            print(f"   • {insight}")
        
        print(f"\n⚙️ Categorization Stats:")
        stats = result.categorization_stats
        print(f"   Rule-based: {stats['rule_based_count']} ({stats['rule_based_percentage']:.1f}%)")
        print(f"   LLM-processed: {stats['llm_categorized_count']} ({stats['llm_percentage']:.1f}%)")
        print(f"   Uncategorized: {result.uncategorized_transactions_count} ({stats['uncategorized_percentage']:.1f}%)")
        
        # Save results if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(result.model_dump(), f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output_file}")
        
        print("\n✅ Hybrid expense tracking completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during expense tracking: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 