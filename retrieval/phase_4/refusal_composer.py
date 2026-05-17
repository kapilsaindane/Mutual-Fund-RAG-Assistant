#!/usr/bin/env python3

from typing import Dict, List, Optional
from .intent_classifier import IntentType


class RefusalComposer:
    """
    Composes refusal responses with appropriate educational links
    Provides polite, facts-only responses for non-factual queries
    """
    
    def __init__(self):
        # Educational URLs for different refusal types
        self.educational_urls = {
            'advisory': "https://www.amfiindia.com/mutual-funds-investor-education",
            'comparison': "https://www.amfiindia.com/mutual-funds-investor-education", 
            'prediction': "https://www.sebi.gov.in/sebiweb/home/HomeActionAction?Q=investor%20education",
            'unsupported': "https://www.amfiindia.com/mutual-funds-investor-education"
        }
        
        # Refusal templates
        self.refusal_templates = {
            'advisory': [
                "I can only provide factual information about mutual funds and cannot give investment advice or recommendations.",
                "For investment guidance, please consult a qualified financial advisor.",
                "I'm designed to answer factual questions about mutual fund information only.",
                "I cannot provide investment advice, but I can share factual details about fund performance and characteristics."
            ],
            'comparison': [
                "I can provide individual fund information but cannot make comparisons or recommendations between funds.",
                "Each fund has different risk-return profiles suitable for different investor needs.",
                "For fund comparisons, please review the fact sheets or consult a financial advisor.",
                "I can share factual details about individual funds but cannot rank or compare them."
            ],
            'prediction': [
                "I can provide historical information but cannot predict future performance or market movements.",
                "Past performance is not indicative of future results.",
                "For future outlook, please consult market research reports or financial advisors.",
                "I can share historical data and current facts but cannot make predictions about future performance."
            ],
            'unsupported': [
                "This assistant supports only factual, source-backed mutual fund queries.\nInvestment advice, recommendations, comparisons, predictions, or unrelated queries are not supported."
            ]
        }
        
        # Safe template for don't know responses
        self.dont_know_templates = [
            "I don't have enough information to answer this question accurately.",
            "I don't have specific information about that in my knowledge base.",
            "I'm not able to find relevant information to answer your question.",
            "I don't have sufficient details about that particular aspect.",
            "My knowledge base doesn't contain information to address your specific question."
        ]
    
    def compose_refusal(self, intent: IntentType, confidence: float = 0.5, 
                      resolved_scheme: Optional[str] = None) -> Dict[str, str]:
        """
        Compose refusal response based on intent
        
        Args:
            intent: Detected intent type
            confidence: Classification confidence
            resolved_scheme: Optional resolved scheme name
            
        Returns:
            Dictionary with refusal response and metadata
        """
        if intent == IntentType.FACTUAL_ALLOWED:
            # This shouldn't happen, but handle gracefully
            return {
                'response': "I can help with factual questions about mutual funds.",
                'type': 'factual_acknowledgment',
                'url': None
            }
        
        # Get appropriate template and educational URL
        templates = self.refusal_templates.get(intent.value, self.refusal_templates['unsupported'])
        educational_url = self.educational_urls.get(intent.value, self.educational_urls['unsupported'])
        
        # Select template based on confidence and context
        if confidence >= 0.8:
            template = templates[0]  # Most direct
        elif confidence >= 0.6:
            template = templates[1] if len(templates) > 1 else templates[0]
        else:
            template = templates[-1] if templates else templates[0]
        
        # Add scheme-specific context if available
        if resolved_scheme and intent in [IntentType.ADVISORY_REFUSE, IntentType.COMPARISON_REFUSE]:
            template += f" I can share factual details about {resolved_scheme} though."
        
        response = template
        
        # Add educational link
        if educational_url:
            response += f" For educational resources, visit: {educational_url}"
        
        return {
            'response': response,
            'type': 'refusal',
            'intent': intent.value,
            'educational_url': educational_url,
            'confidence': confidence
        }
    
    def compose_dont_know(self, query: str, resolved_scheme: Optional[str] = None) -> Dict[str, str]:
        """
        Compose "I don't know" response
        
        Args:
            query: Original user query
            resolved_scheme: Optional resolved scheme name
            
        Returns:
            Dictionary with dont_know response and metadata
        """
        # Select template based on context
        if resolved_scheme:
            template = f"I don't have enough information about {resolved_scheme} to answer this question accurately."
        else:
            # Use hash of query for consistent selection
            query_hash = hash(query) % len(self.dont_know_templates)
            template = self.dont_know_templates[query_hash]
        
        # Add suggestion to name a scheme
        if not resolved_scheme:
            template += " Could you specify which HDFC fund you're asking about?"
        
        return {
            'response': template,
            'type': 'dont_know',
            'url': None,  # Explicitly no URL for dont_know responses
            'scheme_hint': resolved_scheme
        }
    
    def get_safe_template(self) -> str:
        """
        Get the safe fallback template for post-processor failures
        
        Returns:
            Safe template with educational link
        """
        safe_response = "I apologize, but I'm unable to process your request at this time."
        educational_url = self.educational_urls['unsupported']
        return f"{safe_response} For educational resources about mutual funds, visit: {educational_url}"
    
    def validate_refusal_response(self, response: str) -> Dict[str, any]:
        """
        Validate that a refusal response meets policy requirements
        
        Args:
            response: Generated refusal response
            
        Returns:
            Validation result
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'word_count': len(response.split()),
            'has_url': 'http' in response.lower(),
            'has_advisory_language': False,
            'has_comparison_language': False
        }
        
        # Check word count (should be reasonable)
        if validation['word_count'] > 50:
            validation['is_valid'] = False
            validation['issues'].append("Response too long")
        
        # Check for banned advisory language
        advisory_terms = ['recommend', 'suggest', 'advise', 'should', 'better', 'best', 'worst']
        for term in advisory_terms:
            if term in response.lower():
                validation['has_advisory_language'] = True
                validation['is_valid'] = False
                validation['issues'].append(f"Contains advisory term: {term}")
        
        # Check for comparison language
        comparison_terms = ['better than', 'worse than', 'compare', 'vs', 'versus']
        for term in comparison_terms:
            if term in response.lower():
                validation['has_comparison_language'] = True
                validation['is_valid'] = False
                validation['issues'].append(f"Contains comparison term: {term}")
        
        return validation
    
    def explain_refusal_logic(self, intent: IntentType, confidence: float) -> str:
        """
        Generate explanation of refusal decision
        
        Args:
            intent: Detected intent
            confidence: Classification confidence
            
        Returns:
            Explanation string
        """
        explanation = f"Refusal Reason: {intent.value}\n"
        explanation += f"Confidence: {confidence:.2f}\n"
        
        if intent == IntentType.ADVISORY_REFUSE:
            explanation += "Policy: Cannot provide investment advice or recommendations\n"
        elif intent == IntentType.COMPARISON_REFUSE:
            explanation += "Policy: Cannot compare funds or make recommendations\n"
        elif intent == IntentType.PREDICTION_REFUSE:
            explanation += "Policy: Cannot predict future performance\n"
        elif intent == IntentType.UNSUPPORTED_REFUSE:
            explanation += "Policy: Limited to specific HDFC funds in knowledge base\n"
        
        return explanation


def main():
    """Test refusal composer"""
    composer = RefusalComposer()
    
    test_cases = [
        # Advisory cases
        {
            'intent': IntentType.ADVISORY_REFUSE,
            'confidence': 0.8,
            'query': "Should I invest in HDFC Mid Cap Fund?",
            'resolved_scheme': "HDFC Mid Cap Fund"
        },
        {
            'intent': IntentType.ADVISORY_REFUSE,
            'confidence': 0.6,
            'query': "Is it good to invest in ELSS now?",
            'resolved_scheme': None
        },
        
        # Comparison cases
        {
            'intent': IntentType.COMPARISON_REFUSE,
            'confidence': 0.9,
            'query': "Which is better: HDFC Mid Cap or HDFC Focused Fund?",
            'resolved_scheme': None
        },
        
        # Prediction cases
        {
            'intent': IntentType.PREDICTION_REFUSE,
            'confidence': 0.7,
            'query': "Will HDFC Equity Fund perform well next year?",
            'resolved_scheme': "HDFC Equity Fund"
        },
        
        # Unsupported cases
        {
            'intent': IntentType.UNSUPPORTED_REFUSE,
            'confidence': 0.8,
            'query': "What about US mutual funds?",
            'resolved_scheme': None
        },
        
        # Don't know case
        {
            'query': "What is the exact NAV from January 2020?",
            'resolved_scheme': None
        }
    ]
    
    print("Refusal Composer Test:")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['query']}")
        
        if 'intent' in test_case:
            result = composer.compose_refusal(
                intent=test_case['intent'],
                confidence=test_case['confidence'],
                resolved_scheme=test_case.get('resolved_scheme')
            )
            print(f"Intent: {test_case['intent'].value}")
            print(f"Response: {result['response']}")
            print(f"Type: {result['type']}")
            print(f"Educational URL: {result['educational_url']}")
        else:
            # Don't know case
            result = composer.compose_dont_know(
                query=test_case['query'],
                resolved_scheme=test_case.get('resolved_scheme')
            )
            print(f"Response: {result['response']}")
            print(f"Type: {result['type']}")
        
        # Validate response
        validation = composer.validate_refusal_response(result['response'])
        print(f"Valid: {validation['is_valid']}")
        if validation['issues']:
            print(f"Issues: {', '.join(validation['issues'])}")
        
        print("-" * 40)


if __name__ == "__main__":
    main()
