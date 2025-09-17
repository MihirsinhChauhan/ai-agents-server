import re
import json
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class SmartCategorizer:
    """
    Hybrid rule-based + LLM categorization system for Indian financial transactions.
    Uses pattern matching, keywords, and merchant recognition to categorize transactions.
    """
    
    def __init__(self):
        """Initialize the smart categorizer with comprehensive rules."""
        self.rules = self._load_categorization_rules()
        self.merchant_cache = {}
        self.stats = defaultdict(int)
    
    def _load_categorization_rules(self) -> Dict[str, Dict]:
        """Load comprehensive categorization rules for Indian transactions."""
        return {
            'Transportation': {
                'keywords': [
                    'metro', 'dmrc', 'uber', 'ola', 'rapido', 'bounce', 'vogo',
                    'petrol', 'fuel', 'gas', 'hp', 'ioc', 'bpcl', 'shell',
                    'bus', 'taxi', 'auto', 'rickshaw', 'railway', 'irctc',
                    'parking', 'toll', 'fastag', 'paytm fastag', 'metro card'
                ],
                'patterns': [
                    r'.*metro.*card.*',
                    r'.*dmrc.*',
                    r'.*uber.*',
                    r'.*ola.*',
                    r'.*petrol.*pump.*',
                    r'.*fuel.*station.*',
                    r'.*toll.*plaza.*',
                    r'.*metro.*recharge.*',
                    r'.*transport.*card.*'
                ],
                'merchant_names': [
                    'uber', 'ola', 'rapido', 'dmrc', 'irctc', 'redbus'
                ]
            },
            
            'Food': {
                'keywords': [
                    'zomato', 'swiggy', 'foodpanda', 'ubereats', 'dominos', 'pizza',
                    'mcdonald', 'kfc', 'subway', 'starbucks', 'cafe', 'restaurant',
                    'hotel', 'dhaba', 'canteen', 'mess', 'tiffin'
                ],
                'patterns': [
                    r'.*zomato.*',
                    r'.*swiggy.*',
                    r'.*food.*delivery.*',
                    r'.*restaurant.*',
                    r'.*cafe.*',
                    r'.*pizza.*'
                ],
                'merchant_names': [
                    'zomato', 'swiggy', 'dominos', 'pizzahut', 'kfc', 'mcdonalds',
                    'starbucks', 'ccd', 'barista'
                ]
            },
            
            'Groceries': {
                'keywords': [
                    'blinkit', 'grofers', 'bigbasket', 'amazon fresh', 'reliance fresh',
                    'dmart', 'more', 'spencer', 'grocery', 'supermarket',
                    'vegetable', 'fruit', 'milk', 'bread', 'rice', 'dal',
                    'zepto', 'dunzo', 'instamart'
                ],
                'patterns': [
                    r'.*blinkit.*',
                    r'.*grofers.*',
                    r'.*bigbasket.*',
                    r'.*grocery.*',
                    r'.*supermarket.*',
                    r'.*fresh.*mart.*'
                ],
                'merchant_names': [
                    'blinkit', 'grofers', 'bigbasket', 'dmart', 'reliance', 'zepto'
                ]
            },
            
            'Mobile/Internet': {
                'keywords': [
                    'airtel', 'jio', 'vodafone', 'idea', 'bsnl', 'mtnl',
                    'broadband', 'wifi', 'internet', 'mobile', 'recharge',
                    'prepaid', 'postpaid', 'data', 'plan'
                ],
                'patterns': [
                    r'.*airtel.*',
                    r'.*jio.*',
                    r'.*vodafone.*',
                    r'.*mobile.*recharge.*',
                    r'.*broadband.*',
                    r'.*internet.*bill.*'
                ],
                'merchant_names': [
                    'airtel', 'jio', 'vodafone', 'idea', 'bsnl'
                ]
            },
            
            'Shopping': {
                'keywords': [
                    'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'lenskart',
                    'shopping', 'mall', 'store', 'retail', 'clothes', 'fashion',
                    'electronics', 'mobile', 'laptop', 'meesho', 'snapdeal'
                ],
                'patterns': [
                    r'.*amazon.*',
                    r'.*flipkart.*',
                    r'.*myntra.*',
                    r'.*shopping.*',
                    r'.*retail.*',
                    r'.*mall.*'
                ],
                'merchant_names': [
                    'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'lenskart'
                ]
            },
            
            'Entertainment': {
                'keywords': [
                    'netflix', 'amazon prime', 'hotstar', 'spotify', 'youtube',
                    'movie', 'cinema', 'theatre', 'pvr', 'inox', 'ticket',
                    'book my show', 'bookmyshow', 'paytm movies', 'game',
                    'steam', 'playstore', 'appstore'
                ],
                'patterns': [
                    r'.*netflix.*',
                    r'.*prime.*video.*',
                    r'.*hotstar.*',
                    r'.*spotify.*',
                    r'.*movie.*ticket.*',
                    r'.*bookmyshow.*'
                ],
                'merchant_names': [
                    'netflix', 'amazon', 'hotstar', 'spotify', 'pvr', 'inox', 'bookmyshow'
                ]
            },
            
            'Utilities': {
                'keywords': [
                    'electricity', 'water', 'gas', 'cylinder', 'lpg',
                    'utility', 'bill', 'power', 'current', 'municipal',
                    'corporation', 'bescom', 'mseb', 'kseb', 'pseb'
                ],
                'patterns': [
                    r'.*electricity.*bill.*',
                    r'.*water.*bill.*',
                    r'.*gas.*bill.*',
                    r'.*utility.*payment.*',
                    r'.*municipal.*corp.*'
                ],
                'merchant_names': [
                    'bescom', 'mseb', 'kseb', 'pseb', 'bwssb'
                ]
            },
            
            'Healthcare': {
                'keywords': [
                    'hospital', 'clinic', 'doctor', 'medical', 'pharmacy',
                    'medicine', 'apollo', 'max', 'fortis', 'manipal',
                    'netmeds', 'pharmeasy', 'medlife', 'health', 'diagnostic'
                ],
                'patterns': [
                    r'.*hospital.*',
                    r'.*medical.*',
                    r'.*pharmacy.*',
                    r'.*doctor.*',
                    r'.*clinic.*'
                ],
                'merchant_names': [
                    'apollo', 'max', 'fortis', 'manipal', 'netmeds', 'pharmeasy'
                ]
            },
            
            'Education': {
                'keywords': [
                    'school', 'college', 'university', 'course', 'tuition',
                    'fees', 'education', 'training', 'coaching', 'institute',
                    'udemy', 'coursera', 'byju', 'unacademy', 'vedantu'
                ],
                'patterns': [
                    r'.*school.*fees.*',
                    r'.*college.*fees.*',
                    r'.*course.*payment.*',
                    r'.*tuition.*',
                    r'.*coaching.*'
                ],
                'merchant_names': [
                    'byju', 'unacademy', 'vedantu', 'udemy', 'coursera'
                ]
            },
            
            'Housing': {
                'keywords': [
                    'rent', 'maintenance', 'society', 'apartment', 'flat',
                    'housing', 'pg', 'hostel', 'accommodation', 'deposit'
                ],
                'patterns': [
                    r'.*rent.*payment.*',
                    r'.*maintenance.*charge.*',
                    r'.*society.*maintenance.*',
                    r'.*housing.*'
                ],
                'merchant_names': []
            },
            
            'Banking': {
                'keywords': [
                    'bank', 'atm', 'charge', 'fee', 'penalty', 'interest',
                    'loan', 'emi', 'credit card', 'debit card', 'annual fee'
                ],
                'patterns': [
                    r'.*bank.*charge.*',
                    r'.*atm.*fee.*',
                    r'.*annual.*fee.*',
                    r'.*emi.*',
                    r'.*loan.*payment.*'
                ],
                'merchant_names': [
                    'sbi', 'hdfc', 'icici', 'axis', 'kotak', 'pnb', 'bob'
                ]
            },
            
            'Travel': {
                'keywords': [
                    'hotel', 'flight', 'train', 'bus', 'booking', 'travel',
                    'makemytrip', 'goibibo', 'cleartrip', 'yatra', 'oyo',
                    'airbnb', 'treebo', 'fab hotels'
                ],
                'patterns': [
                    r'.*hotel.*booking.*',
                    r'.*flight.*ticket.*',
                    r'.*travel.*booking.*',
                    r'.*makemytrip.*'
                ],
                'merchant_names': [
                    'makemytrip', 'goibibo', 'cleartrip', 'yatra', 'oyo', 'airbnb'
                ]
            },
            
            'Insurance': {
                'keywords': [
                    'insurance', 'premium', 'policy', 'lic', 'health insurance',
                    'car insurance', 'bike insurance', 'term insurance'
                ],
                'patterns': [
                    r'.*insurance.*premium.*',
                    r'.*policy.*payment.*',
                    r'.*lic.*premium.*'
                ],
                'merchant_names': [
                    'lic', 'hdfc life', 'icici prudential', 'bajaj allianz'
                ]
            },
            
            'Personal Transfers': {
                'keywords': [
                    'ram veer', 'yatendra', 'dinesh', 'mohan', 'yoonis', 'sonu',
                    'anand', 'deepak', 'rahul', 'priya', 'amit', 'ravi'
                ],
                'patterns': [
                    r'.*upi.*dr.*[a-z]+\s[a-z]+.*',  # UPI to person names
                    r'.*transfer.*to.*[a-z]+.*[a-z]+.*',  # Transfer to person
                    r'.*/[a-z]+/[a-z]+/.*payment.*',  # Person payment patterns
                ],
                'merchant_names': []
            },
            
            'Salary': {
                'keywords': [
                    'nextbillion tech', 'salary', 'payroll', 'wages', 'income',
                    'company', 'tech', 'technologies', 'pvt ltd', 'limited'
                ],
                'patterns': [
                    r'.*nextbillion.*tech.*',
                    r'.*salary.*credit.*',
                    r'.*payroll.*deposit.*',
                    r'.*neft.*.*tech.*',
                    r'.*company.*transfer.*'
                ],
                'merchant_names': [
                    'nextbillion', 'tech'
                ]
            }
        }
    
    def normalize_description(self, description: str) -> str:
        """Normalize transaction description for better matching."""
        if not description:
            return ""
        
        # Convert to lowercase and remove extra whitespace
        normalized = description.lower().strip()
        
        # Remove common transaction prefixes/suffixes
        prefixes_to_remove = [
            'transfer to', 'transfer from', 'upi/dr/', 'upi/cr/',
            'neft*', 'imps*', 'rtgs*', 'pos*', 'atm*'
        ]
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove UPI transaction IDs and reference numbers
        normalized = re.sub(r'\d{10,}', '', normalized)  # Remove long numbers
        normalized = re.sub(r'/[A-Z0-9]{6,}/', ' ', normalized)  # Remove reference codes
        normalized = re.sub(r'[A-Z0-9]{10,}', '', normalized)  # Remove long alphanumeric codes
        normalized = re.sub(r'\*[A-Z0-9]{4,}\*', ' ', normalized)  # Remove *CODE* patterns
        normalized = re.sub(r'-\s*$', '', normalized)  # Remove trailing dashes
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        return normalized.strip()
    
    def extract_merchant_name(self, description: str) -> str:
        """Extract merchant name from transaction description."""
        normalized = self.normalize_description(description)
        
        # Common patterns for merchant extraction
        patterns = [
            r'([a-zA-Z][a-zA-Z0-9\s]{2,20})',  # General merchant name pattern
            r'([A-Z][A-Z\s]{3,15})',  # Uppercase merchant names
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, normalized)
            if matches:
                return matches[0].strip()
        
        return normalized[:30]  # Fallback to first 30 chars
    
    def categorize_by_rules(self, transaction: Dict[str, Any]) -> Tuple[str, float]:
        """
        Categorize transaction using rules and return category with confidence score.
        
        Returns:
            Tuple of (category, confidence_score) where confidence is 0.0 to 1.0
        """
        description = transaction.get('description', '')
        amount = transaction.get('amount', 0)
        
        if not description:
            return 'Uncategorized', 0.0
        
        normalized_desc = self.normalize_description(description)
        merchant = self.extract_merchant_name(description)
        
        # Check cache first
        cache_key = f"{normalized_desc}:{amount}"
        if cache_key in self.merchant_cache:
            cached_result = self.merchant_cache[cache_key]
            return cached_result['category'], cached_result['confidence']
        
        best_category = 'Uncategorized'
        best_score = 0.0
        
        for category, rules in self.rules.items():
            score = 0.0
            matches = 0
            
            # Check keyword matches
            keywords = rules.get('keywords', [])
            for keyword in keywords:
                if keyword in normalized_desc:
                    score += 1.0
                    matches += 1
            
            # Check pattern matches
            patterns = rules.get('patterns', [])
            for pattern in patterns:
                if re.search(pattern, normalized_desc, re.IGNORECASE):
                    score += 1.5  # Patterns get higher weight
                    matches += 1
            
            # Check merchant name matches
            merchant_names = rules.get('merchant_names', [])
            for merchant_name in merchant_names:
                if merchant_name in normalized_desc or merchant_name in merchant:
                    score += 2.0  # Merchant matches get highest weight
                    matches += 1
            
            # Normalize score based on number of possible matches
            total_possible = len(keywords) + len(patterns) + len(merchant_names)
            if total_possible > 0 and matches > 0:
                normalized_score = min(score / total_possible, 1.0)
                
                # Boost score if multiple matches
                if matches > 1:
                    normalized_score = min(normalized_score * 1.2, 1.0)
                
                if normalized_score > best_score:
                    best_score = normalized_score
                    best_category = category
        
        # Apply confidence thresholds
        if best_score >= 0.7:
            confidence = 0.9  # High confidence
        elif best_score >= 0.4:
            confidence = 0.7  # Medium confidence
        elif best_score >= 0.2:
            confidence = 0.5  # Low confidence
        else:
            confidence = 0.0  # No confidence, keep as uncategorized
            best_category = 'Uncategorized'
        
        # Cache the result
        self.merchant_cache[cache_key] = {
            'category': best_category,
            'confidence': confidence,
            'merchant': merchant
        }
        
        return best_category, confidence
    
    def categorize_transactions(self, transactions: List[Dict[str, Any]], 
                              min_confidence: float = 0.5) -> Tuple[List[Dict], List[Dict]]:
        """
        Categorize a list of transactions, separating high-confidence from low-confidence.
        
        Args:
            transactions: List of transaction dictionaries
            min_confidence: Minimum confidence threshold for auto-categorization
            
        Returns:
            Tuple of (categorized_transactions, needs_llm_transactions)
        """
        categorized = []
        needs_llm = []
        
        for transaction in transactions:
            category, confidence = self.categorize_by_rules(transaction)
            
            # Add categorization metadata
            transaction_copy = transaction.copy()
            transaction_copy['category'] = category
            transaction_copy['categorization_confidence'] = confidence
            transaction_copy['categorization_method'] = 'rule_based'
            
            if confidence >= min_confidence:
                categorized.append(transaction_copy)
                self.stats['rule_based_categorized'] += 1
            else:
                needs_llm.append(transaction_copy)
                self.stats['needs_llm'] += 1
        
        return categorized, needs_llm
    
    def get_categorization_stats(self) -> Dict[str, Any]:
        """Get statistics about the categorization process."""
        total = sum(self.stats.values())
        return {
            'total_processed': total,
            'rule_based_categorized': self.stats['rule_based_categorized'],
            'needs_llm': self.stats['needs_llm'],
            'rule_based_percentage': (self.stats['rule_based_categorized'] / total * 100) if total > 0 else 0,
            'cache_size': len(self.merchant_cache)
        }
    
    def add_custom_rule(self, category: str, keywords: List[str] = None, 
                       patterns: List[str] = None, merchants: List[str] = None):
        """Add custom categorization rules."""
        if category not in self.rules:
            self.rules[category] = {'keywords': [], 'patterns': [], 'merchant_names': []}
        
        if keywords:
            self.rules[category]['keywords'].extend(keywords)
        if patterns:
            self.rules[category]['patterns'].extend(patterns)
        if merchants:
            self.rules[category]['merchant_names'].extend(merchants)
    
    def save_cache(self, filepath: str):
        """Save merchant cache to file."""
        with open(filepath, 'w') as f:
            json.dump(self.merchant_cache, f, indent=2)
    
    def load_cache(self, filepath: str):
        """Load merchant cache from file."""
        try:
            with open(filepath, 'r') as f:
                self.merchant_cache = json.load(f)
        except FileNotFoundError:
            logger.info(f"Cache file {filepath} not found, starting with empty cache")

# Convenience functions
def categorize_transactions_smart(transactions: List[Dict[str, Any]], 
                                min_confidence: float = 0.5) -> Tuple[List[Dict], List[Dict]]:
    """Convenience function to categorize transactions with smart rules."""
    categorizer = SmartCategorizer()
    return categorizer.categorize_transactions(transactions, min_confidence)

def batch_categorize_with_stats(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Categorize transactions and return detailed stats."""
    categorizer = SmartCategorizer()
    categorized, needs_llm = categorizer.categorize_transactions(transactions)
    stats = categorizer.get_categorization_stats()
    
    return {
        'categorized_transactions': categorized,
        'needs_llm_transactions': needs_llm,
        'stats': stats
    } 