#!/usr/bin/env python3

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum


class IntentType(Enum):
    """Query intent types for classification"""
    FACTUAL_ALLOWED = "factual"
    ADVISORY_REFUSE = "advisory"
    COMPARISON_REFUSE = "comparison"
    PREDICTION_REFUSE = "prediction"
    UNSUPPORTED_REFUSE = "unsupported"


class IntentClassifier:
    """
    Query intent classifier for factual vs advisory/comparison/prediction detection
    Enforces facts-only behavior by identifying non-factual intents
    """
    
    def __init__(self):
        # Advisory patterns (investment advice, recommendations)
        self.advisory_patterns = [
            r'\b(should|would|could|recommend|suggest|advise)\b.*\b(invest|buy|sell|switch|choose|pick)\b',
            r'\b(is it|would it be)\s+(good|better|wise|smart|advisable)\s+to\s+(invest|buy)',
            r'\b(how much|what amount)\s+(should|would)\s+(i\s+)?(invest|allocate)',
            r'\b(best|top|recommended|ideal)\s+(mutual fund|scheme|investment)',
            r'\b(should i|can i)\s+(invest|put|allocate)\s+(money|rs|₹)',
            r'\b(is this|would this be)\s+(a\s+)?(good|bad|safe|risky)\s+(investment|choice)',
            r'\b(what|which)\s+(fund|scheme)\s+(should\s+)?(i\s+)?(choose|pick|select)',
            r'\b(are you|do you)\s+(think|believe|recommend)\s+(i\s+)?(should|should not)',
            r'\b(advice|guidance|suggestion)\b',
            r'\b(better than|worse than|outperform|underperform)\b',
            r'\b(will|would)\s+(likely|probably|definitely)\s+(perform|do|give)',
        ]
        
        # Comparison patterns (fund-to-fund comparisons)
        self.comparison_patterns = [
            r'\b(which|what)\s+(is\s+)?(better|worse|best|worst)',
            r'\b(compare|comparison|vs|versus)\b',
            r'\b(higher|lower|greater|less)\s+(return|performance|risk|expense)',
            r'\b(more|less)\s+(profitable|suitable|appropriate)',
            r'\b(top|bottom|rank|ranking)\b',
            r'\b(one|two|three|first|second)\s+(best|worst)',
            r'\b(between|among|across)\b.*\b(funds|schemes)',
        ]
        
        # Prediction patterns (future performance, market predictions)
        self.prediction_patterns = [
            r'\b(will|would|could|might|may|expect|predict|forecast)\b.*\b(future|next|coming)',
            r'\b(how|what)\s+(will|would|might)\s+(perform|do|be)',
            r'\b(market|economy|interest rate)\s+(will|would|likely)\s+(go|do|change)',
            r'\b(price|nav|return)\s+(will|would|should)\s+(increase|decrease|rise|fall)',
            r'\b(next|upcoming|future)\s+(quarter|year|month)',
            r'\b(target|goal|expectation)\b.*\b(return|performance)',
        ]
        
        # Unsupported patterns (out of scope queries)
        self.unsupported_patterns = [
            r'\b(tax|legal|account|bank)\s+(advice|planning|guidance)',
            r'\b(contact|support|customer service)\b',
            r'\b(login|password|access|account)\s+(issue|problem|help)',
            r'\b(other|different|another)\s+(AMC|fund house|company)',
            r'\b(international|global|us|europe)\s+(market|fund)',
            r'\b(crypto|bitcoin|cryptocurrency)\b',
            r'\b(insurance|policy|claim)\b',
        ]
        
        # Compile all patterns for efficiency
        self.compiled_advisory = [re.compile(pattern, re.IGNORECASE) for pattern in self.advisory_patterns]
        self.compiled_comparison = [re.compile(pattern, re.IGNORECASE) for pattern in self.comparison_patterns]
        self.compiled_prediction = [re.compile(pattern, re.IGNORECASE) for pattern in self.prediction_patterns]
        self.compiled_unsupported = [re.compile(pattern, re.IGNORECASE) for pattern in self.unsupported_patterns]
        
        # Factual indicators (positive signals)
        self.factual_indicators = [
            r'\b(what|how much|what is|what are)\s+(the\s+)?(nav|expense|ratio|aum)',
            r'\b(minimum|maximum|lock.?in|exit load|sip amount)',
            r'\b(risk|rating|category|type)\s+(level|category)',
            r'\b(scheme|fund)\s+(details|information|facts)',
            r'\b(when|how long)\s+(lock.?in|period|duration)',
            r'\b(where|how to)\s+(invest|buy|redeem)',
        ]
        
        self.compiled_factual = [re.compile(pattern, re.IGNORECASE) for pattern in self.factual_indicators]
    
    def classify_intent(self, query: str, query_features: Optional[Dict] = None) -> Dict[str, any]:
        """
        Classify query intent
        
        Args:
            query: User query string
            query_features: Optional features from query normalizer
            
        Returns:
            Dictionary with classification results
        """
        if not query:
            return {
                'intent': IntentType.UNSUPPORTED_REFUSE,
                'confidence': 0.0,
                'reason': 'Empty query',
                'matched_patterns': []
            }
        
        query_lower = query.lower()
        matches = {
            'advisory': [],
            'comparison': [],
            'prediction': [],
            'unsupported': [],
            'factual': []
        }
        
        # Check each category
        for pattern in self.compiled_advisory:
            if pattern.search(query):
                matches['advisory'].append(pattern.pattern)
        
        for pattern in self.compiled_comparison:
            if pattern.search(query):
                matches['comparison'].append(pattern.pattern)
        
        for pattern in self.compiled_prediction:
            if pattern.search(query):
                matches['prediction'].append(pattern.pattern)
        
        for pattern in self.compiled_unsupported:
            if pattern.search(query):
                matches['unsupported'].append(pattern.pattern)
        
        for pattern in self.compiled_factual:
            if pattern.search(query):
                matches['factual'].append(pattern.pattern)
        
        # Determine intent based on matches
        intent, confidence, reason = self._determine_intent(matches, query_lower)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'reason': reason,
            'matched_patterns': matches,
            'query_features': query_features or {}
        }
    
    def _determine_intent(self, matches: Dict[str, List[str]], query_lower: str) -> Tuple[IntentType, float, str]:
        """
        Determine final intent based on pattern matches
        
        Priority order: Unsupported > Advisory/Comparison/Prediction > Factual
        """
        
        # Check for unsupported content first (highest priority)
        if matches['unsupported']:
            return IntentType.UNSUPPORTED_REFUSE, 0.9, f"Unsupported content detected: {len(matches['unsupported'])} patterns"
        
        # Check for advisory content
        if matches['advisory']:
            advisory_count = len(matches['advisory'])
            # Higher confidence for multiple advisory patterns
            confidence = min(0.5 + (advisory_count * 0.1), 0.9)
            return IntentType.ADVISORY_REFUSE, confidence, f"Advisory content detected: {advisory_count} patterns"
        
        # Check for comparison content
        if matches['comparison']:
            comparison_count = len(matches['comparison'])
            confidence = min(0.6 + (comparison_count * 0.1), 0.9)
            return IntentType.COMPARISON_REFUSE, confidence, f"Comparison content detected: {comparison_count} patterns"
        
        # Check for prediction content
        if matches['prediction']:
            prediction_count = len(matches['prediction'])
            confidence = min(0.6 + (prediction_count * 0.1), 0.9)
            return IntentType.PREDICTION_REFUSE, confidence, f"Prediction content detected: {prediction_count} patterns"
        
        # Check for factual content
        if matches['factual']:
            factual_count = len(matches['factual'])
            # Higher confidence for more factual indicators
            confidence = min(0.4 + (factual_count * 0.1), 0.8)
            return IntentType.FACTUAL_ALLOWED, confidence, f"Factual content detected: {factual_count} patterns"
        
        # Default to factual if no strong refusals detected
        # But with lower confidence due to lack of clear indicators
        return IntentType.FACTUAL_ALLOWED, 0.3, "No clear refusal patterns detected, defaulting to factual"
    
    def is_factual_query(self, query: str, query_features: Optional[Dict] = None) -> bool:
        """
        Quick check if query is factual
        
        Args:
            query: User query string
            query_features: Optional features from query normalizer
            
        Returns:
            True if query appears factual
        """
        classification = self.classify_intent(query, query_features)
        return classification['intent'] == IntentType.FACTUAL_ALLOWED
    
    def get_refusal_reason(self, classification: Dict[str, any]) -> str:
        """
        Get human-readable refusal reason
        
        Args:
            classification: Classification result
            
        Returns:
            Human-readable refusal reason
        """
        intent = classification['intent']
        reason = classification['reason']
        
        if intent == IntentType.ADVISORY_REFUSE:
            return "I can only provide factual information about mutual funds and cannot give investment advice or recommendations."
        elif intent == IntentType.COMPARISON_REFUSE:
            return "I can provide individual fund information but cannot make comparisons or recommendations between funds."
        elif intent == IntentType.PREDICTION_REFUSE:
            return "I can provide historical information but cannot predict future performance or market movements."
        elif intent == IntentType.UNSUPPORTED_REFUSE:
            return "I can only answer questions about the specific HDFC mutual funds in my knowledge base."
        else:
            return "I'm designed to answer factual questions about mutual fund information only."
    
    def explain_classification(self, classification: Dict[str, any]) -> str:
        """
        Generate explanation of classification decision
        
        Args:
            classification: Classification result
            
        Returns:
            Detailed explanation string
        """
        intent = classification['intent']
        confidence = classification['confidence']
        reason = classification['reason']
        matches = classification['matched_patterns']
        
        explanation = f"Intent: {intent.value}\n"
        explanation += f"Confidence: {confidence:.2f}\n"
        explanation += f"Reason: {reason}\n"
        
        if any(matches.values()):
            explanation += "Matched patterns:\n"
            for category, patterns in matches.items():
                if patterns:
                    explanation += f"  {category}: {len(patterns)} patterns\n"
        
        return explanation


def main():
    """Test intent classifier"""
    classifier = IntentClassifier()
    
    test_queries = [
        # Factual queries
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "What is the minimum SIP amount?",
        "What is the lock-in period for ELSS?",
        "NAV details for HDFC Equity Fund",
        "Risk rating of focused fund",
        
        # Advisory queries
        "Should I invest in HDFC Mid Cap Fund?",
        "Which fund should I choose for long term?",
        "Is it good to invest in ELSS now?",
        "How much should I invest in mutual funds?",
        "Can you recommend the best fund?",
        
        # Comparison queries
        "Which is better: HDFC Mid Cap or HDFC Focused Fund?",
        "Compare HDFC Equity vs HDFC Large Cap",
        "What has higher returns: mid cap or large cap?",
        "Rank these funds by performance",
        
        # Prediction queries
        "Will HDFC Mid Cap Fund perform well next year?",
        "What will be the NAV in 6 months?",
        "Will interest rates affect mutual fund returns?",
        "Predict the market for next quarter",
        
        # Unsupported queries
        "How to file tax returns for mutual funds?",
        "Contact customer service for HDFC",
        "What about international mutual funds?",
        "Bitcoin investment advice",
    ]
    
    print("Intent Classifier Test:")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        classification = classifier.classify_intent(query)
        
        print(f"Intent: {classification['intent'].value}")
        print(f"Confidence: {classification['confidence']:.2f}")
        print(f"Reason: {classification['reason']}")
        print(f"Factual: {classifier.is_factual_query(query)}")
        print("-" * 40)


if __name__ == "__main__":
    main()
