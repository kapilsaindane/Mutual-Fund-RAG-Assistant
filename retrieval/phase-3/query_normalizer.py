#!/usr/bin/env python3

import re
import unicodedata
from typing import Dict, List, Set


class QueryNormalizer:
    """Normalizes user queries for consistent retrieval"""
    
    # Mutual fund specific tokens and patterns
    MF_TOKENS = {
        # Fund types
        'elss', 'sip', 'nav', 'aum', 'etf', 'liquid', 'debt', 'equity', 'hybrid',
        'arbitrage', 'index', 'large-cap', 'mid-cap', 'small-cap', 'multi-cap',
        'focused', 'value', 'growth', 'dividend', 'direct', 'regular',
        
        # Financial terms
        'expense', 'ratio', 'exit', 'load', 'lock-in', 'lockin', 'tenure', 'duration',
        'returns', 'risk', 'rating', 'crisil', 'amfi', 'sebi', 'amc',
        
        # Time periods
        '1yr', '1y', '1year', '3yr', '3y', '3year', '5yr', '5y', '5year',
        '10yr', '10y', '10year', 'ytd', 'ytd', 'annual', 'monthly', 'weekly', 'daily',
        
        # Amount/percentage indicators
        'rs', '₹', 'inr', 'percent', '%', 'basis', 'points', 'bps',
        
        # Actions
        'invest', 'buy', 'sell', 'redeem', 'switch', 'withdraw', 'deposit',
    }
    
    # Common abbreviations and their expansions
    ABBREVIATIONS = {
        'elss': 'equity linked savings scheme',
        'sip': 'systematic investment plan',
        'nav': 'net asset value',
        'aum': 'assets under management',
        'etf': 'exchange traded fund',
        'amc': 'asset management company',
        'amfi': 'association of mutual funds in india',
        'sebi': 'securities and exchange board of india',
        'crisil': 'credit rating information services of india limited',
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self.currency_pattern = re.compile(r'[₹$€£]|(?:rs|inr)\b', re.IGNORECASE)
        self.percentage_pattern = re.compile(r'%|percent|percentage', re.IGNORECASE)
        self.number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
        self.whitespace_pattern = re.compile(r'\s+')
        
    def normalize(self, query: str) -> str:
        """
        Normalize query using NFKC, lowercase, and MF token handling
        
        Args:
            query: Raw user query
            
        Returns:
            Normalized query string
        """
        if not query or not isinstance(query, str):
            return ""
        
        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize('NFKC', query)
        
        # 2. Convert to lowercase
        normalized = normalized.lower()
        
        # 3. Collapse whitespace
        normalized = self.whitespace_pattern.sub(' ', normalized).strip()
        
        # 4. Handle MF-specific tokens and abbreviations
        normalized = self._handle_mf_tokens(normalized)
        
        # 5. Normalize common patterns
        normalized = self._normalize_patterns(normalized)
        
        # 6. Final cleanup
        normalized = self.whitespace_pattern.sub(' ', normalized).strip()
        
        return normalized
    
    def _handle_mf_tokens(self, text: str) -> str:
        """Handle mutual fund specific tokens and abbreviations"""
        words = text.split()
        processed_words = []
        
        for word in words:
            # Check for MF tokens (case-insensitive)
            if word.lower() in self.MF_TOKENS:
                # Keep the token as-is (already lowercase)
                processed_words.append(word.lower())
            elif word.lower() in self.ABBREVIATIONS:
                # Expand common abbreviations
                expanded = self.ABBREVIATIONS[word.lower()]
                processed_words.extend(expanded.split())
            else:
                processed_words.append(word)
        
        return ' '.join(processed_words)
    
    def _normalize_patterns(self, text: str) -> str:
        """Normalize common patterns in financial queries"""
        # Normalize currency symbols to standard form
        text = self.currency_pattern.sub(' rs ', text)
        
        # Normalize percentage indicators
        text = self.percentage_pattern.sub(' percent ', text)
        
        # Normalize time period patterns
        text = re.sub(r'\b(\d+)(?:y|yr|year)s?\b', r'\1 year', text)
        text = re.sub(r'\b(\d+)(?:m|month)s?\b', r'\1 month', text)
        text = re.sub(r'\b(\d+)(?:d|day)s?\b', r'\1 day', text)
        
        # Normalize lock-in patterns
        text = re.sub(r'\block[-\s]?in\b', 'lockin', text)
        
        # Normalize expense ratio patterns
        text = re.sub(r'\bexpense[-\s]?ratio\b', 'expense ratio', text)
        
        # Normalize exit load patterns
        text = re.sub(r'\bexit[-\s]?load\b', 'exit load', text)
        
        return text
    
    def extract_numeric_features(self, query: str) -> Dict[str, bool]:
        """
        Extract numeric features from query for weight adjustment
        
        Args:
            query: Normalized query
            
        Returns:
            Dictionary with numeric feature flags
        """
        features = {
            'has_numbers': bool(self.number_pattern.search(query)),
            'has_currency': bool(self.currency_pattern.search(query)),
            'has_percentage': bool(self.percentage_pattern.search(query)),
            'has_time_periods': any(period in query for period in ['year', 'month', 'day', 'ytd']),
            'has_financial_terms': any(term in query for term in ['expense', 'ratio', 'exit', 'load', 'lockin', 'returns'])
        }
        
        # Determine if query is numeric-heavy
        features['is_numeric_heavy'] = (
            features['has_numbers'] and 
            (features['has_currency'] or features['has_percentage'] or features['has_time_periods'])
        )
        
        return features
    
    def get_mf_tokens(self, query: str) -> Set[str]:
        """
        Extract mutual fund specific tokens from query
        
        Args:
            query: Normalized query
            
        Returns:
            Set of MF tokens found in query
        """
        words = set(query.split())
        mf_tokens = words.intersection(self.MF_TOKENS)
        
        # Also check for expanded forms
        for word in words:
            for abbr, expansion in self.ABBREVIATIONS.items():
                if word in expansion.split():
                    mf_tokens.add(abbr)
        
        return mf_tokens
    
    def is_scheme_specific(self, query: str) -> bool:
        """
        Check if query is scheme-specific (contains scheme name or fund type)
        
        Args:
            query: Normalized query
            
        Returns:
            True if query appears to be about a specific scheme
        """
        scheme_indicators = [
            'mid cap', 'large cap', 'small cap', 'focused', 'equity', 'debt',
            'hybrid', 'elss', 'tax saver', 'liquid', 'arbitrage', 'index'
        ]
        
        return any(indicator in query for indicator in scheme_indicators)


def main():
    """Test the query normalizer"""
    normalizer = QueryNormalizer()
    
    test_queries = [
        "What is the exit load for HDFC Mid Cap Fund?",
        "How much is the expense ratio % for ELSS?",
        "₹500 SIP for 3 years returns?",
        "1 year lockin period for tax saver fund",
        "NAV of HDFC Equity Fund Direct Growth",
        "What's the AUM of focused fund?",
        "0.45% expense ratio comparison",
    ]
    
    print("Query Normalization Test:")
    print("=" * 50)
    
    for query in test_queries:
        normalized = normalizer.normalize(query)
        features = normalizer.extract_numeric_features(normalized)
        mf_tokens = normalizer.get_mf_tokens(normalized)
        scheme_specific = normalizer.is_scheme_specific(normalized)
        
        print(f"Original: {query}")
        print(f"Normalized: {normalized}")
        print(f"Numeric features: {features}")
        print(f"MF tokens: {mf_tokens}")
        print(f"Scheme specific: {scheme_specific}")
        print("-" * 30)


if __name__ == "__main__":
    main()
