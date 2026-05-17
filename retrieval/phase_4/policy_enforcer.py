#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse


class PolicyEnforcer:
    """
    URL policy enforcement system
    Ensures exactly one whitelisted URL appears in factual answers
    """
    
    def __init__(self, sources_registry_path: Optional[Path] = None):
        if sources_registry_path is None:
            self.sources_registry_path = Path(__file__).resolve().parents[2] / "docs" / "phases" / "phase-1" / "source-registry.json"
        else:
            self.sources_registry_path = sources_registry_path
        
        self.whitelisted_urls = self._load_whitelisted_urls()
        self.scheme_url_mapping = self._create_scheme_url_mapping()
    
    def _load_whitelisted_urls(self) -> Set[str]:
        """Load whitelisted URLs from sources registry"""
        try:
            with open(self.sources_registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            urls = set()
            for source in registry.get('sources', []):
                url = source.get('url', '')
                if url:
                    urls.add(url)
            
            return urls
        except Exception as e:
            print(f"Warning: Failed to load sources registry: {e}")
            # Fallback to empty set
            return set()
    
    def _create_scheme_url_mapping(self) -> Dict[str, str]:
        """Create mapping from scheme names to their URLs"""
        try:
            with open(self.sources_registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            
            mapping = {}
            for source in registry.get('sources', []):
                scheme_name = source.get('scheme_name', '')
                url = source.get('url', '')
                if scheme_name and url:
                    mapping[scheme_name.lower()] = url
            
            return mapping
        except Exception as e:
            print(f"Warning: Failed to create scheme mapping: {e}")
            return {}
    
    def is_whitelisted_url(self, url: str) -> bool:
        """
        Check if URL is in whitelist
        
        Args:
            url: URL to check
            
        Returns:
            True if whitelisted, False otherwise
        """
        return url in self.whitelisted_urls
    
    def get_scheme_url(self, scheme_name: str) -> Optional[str]:
        """
        Get URL for a scheme name
        
        Args:
            scheme_name: Name of the scheme
            
        Returns:
            URL if found, None otherwise
        """
        return self.scheme_url_mapping.get(scheme_name.lower())
    
    def extract_urls_from_text(self, text: str) -> List[str]:
        """
        Extract all URLs from text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of URLs found in text
        """
        import re
        
        # URL pattern
        url_pattern = r'https?://[^\s<>"\'\)]+'
        urls = re.findall(url_pattern, text.lower())
        
        # Clean and deduplicate
        cleaned_urls = []
        seen_urls = set()
        
        for url in urls:
            # Remove trailing punctuation
            clean_url = url.rstrip('.,;:!?')
            if clean_url not in seen_urls:
                cleaned_urls.append(clean_url)
                seen_urls.add(clean_url)
        
        return cleaned_urls
    
    def validate_url_policy(self, response_text: str, expected_intent: str = "factual") -> Dict[str, any]:
        """
        Validate URL policy compliance
        
        Args:
            response_text: Generated response text
            expected_intent: Expected intent type ("factual" or "refusal")
            
        Returns:
            Validation result
        """
        extracted_urls = self.extract_urls_from_text(response_text)
        
        validation = {
            'is_compliant': True,
            'url_count': len(extracted_urls),
            'extracted_urls': extracted_urls,
            'whitelisted_urls': [],
            'non_whitelisted_urls': [],
            'policy_violations': [],
            'expected_intent': expected_intent
        }
        
        # For factual answers: exactly one whitelisted URL
        if expected_intent == "factual":
            if len(extracted_urls) == 0:
                validation['is_compliant'] = False
                validation['policy_violations'].append("Missing required URL in factual answer")
            elif len(extracted_urls) > 1:
                validation['is_compliant'] = False
                validation['policy_violations'].append(f"Too many URLs: {len(extracted_urls)} (exactly 1 required)")
            else:
                # Check if the single URL is whitelisted
                url = extracted_urls[0]
                if self.is_whitelisted_url(url):
                    validation['whitelisted_urls'] = [url]
                else:
                    validation['is_compliant'] = False
                    validation['non_whitelisted_urls'] = [url]
                    validation['policy_violations'].append(f"Non-whitelisted URL: {url}")
        
        # For refusals: zero URLs
        elif expected_intent == "refusal":
            if len(extracted_urls) > 0:
                validation['is_compliant'] = False
                validation['policy_violations'].append(f"Refusal contains URLs: {len(extracted_urls)} (should be 0)")
        
        return validation
    
    def enforce_url_policy(self, response_text: str, expected_intent: str = "factual") -> Dict[str, any]:
        """
        Enforce URL policy and suggest corrections
        
        Args:
            response_text: Generated response text
            expected_intent: Expected intent type
            
        Returns:
            Policy enforcement result with suggestions
        """
        validation = self.validate_url_policy(response_text, expected_intent)
        
        if not validation['is_compliant']:
            # Generate suggestions
            suggestions = []
            
            if "Missing required URL" in validation['policy_violations']:
                suggestions.append("Add exactly one whitelisted source URL")
            
            if "Too many URLs" in validation['policy_violations']:
                suggestions.append("Remove extra URLs, keep only the most relevant source")
                suggestions.append("Use the scheme's official Groww URL if scheme-specific")
            
            if "Non-whitelisted URL" in validation['policy_violations']:
                suggestions.append("Replace with URL from sources registry")
                suggestions.append("Use official Groww URLs for HDFC schemes")
            
            if "Refusal contains URLs" in validation['policy_violations']:
                suggestions.append("Remove all URLs from refusal responses")
            
            validation['suggestions'] = suggestions
        
        return validation
    
    def get_safe_fallback_url(self, resolved_scheme: Optional[str] = None) -> str:
        """
        Get safe fallback URL for post-processor failures
        
        Args:
            resolved_scheme: Optional resolved scheme name
            
        Returns:
            Safe whitelisted URL
        """
        if resolved_scheme:
            scheme_url = self.get_scheme_url(resolved_scheme)
            if scheme_url:
                return scheme_url
        
        # Fallback to first whitelisted URL
        if self.whitelisted_urls:
            return list(self.whitelisted_urls)[0]
        
        # No URLs available
        return "https://www.amfiindia.com/mutual-funds-investor-education"
    
    def explain_policy_violation(self, validation: Dict[str, any]) -> str:
        """
        Generate human-readable explanation of policy violation
        
        Args:
            validation: Policy validation result
            
        Returns:
            Explanation string
        """
        if validation['is_compliant']:
            return "URL policy compliance: PASSED"
        
        explanation = "URL policy compliance: FAILED\n"
        explanation += f"Intent: {validation['expected_intent']}\n"
        explanation += f"URLs found: {validation['url_count']}\n"
        explanation += f"Violations: {', '.join(validation['policy_violations'])}\n"
        
        if validation['non_whitelisted_urls']:
            explanation += f"Non-whitelisted URLs: {validation['non_whitelisted_urls']}\n"
        
        if validation['suggestions']:
            explanation += "Suggestions:\n"
            for suggestion in validation['suggestions']:
                explanation += f"- {suggestion}\n"
        
        return explanation.strip()
    
    def check_response_compliance(self, response_text: str, expected_intent: str = "factual") -> bool:
        """
        Quick check if response complies with URL policy
        
        Args:
            response_text: Response text to check
            expected_intent: Expected intent type
            
        Returns:
            True if compliant, False otherwise
        """
        validation = self.validate_url_policy(response_text, expected_intent)
        return validation['is_compliant']


def main():
    """Test policy enforcer"""
    enforcer = PolicyEnforcer()
    
    test_cases = [
        # Compliant cases
        {
            'text': 'The expense ratio is 0.45%. Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'intent': 'factual',
            'expected': 'compliant'
        },
        {
            'text': 'I cannot provide investment advice. For educational resources, visit: https://www.amfiindia.com/mutual-funds-investor-education',
            'intent': 'refusal',
            'expected': 'compliant'
        },
        
        # Non-compliant cases
        {
            'text': 'The expense ratio is 0.45%',
            'intent': 'factual',
            'expected': 'missing_url'
        },
        {
            'text': 'The expense ratio is 0.45%. Sources: https://example.com https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'intent': 'factual',
            'expected': 'too_many_urls'
        },
        {
            'text': 'I cannot provide investment advice. Visit: https://example.com',
            'intent': 'refusal',
            'expected': 'non_whitelisted_url'
        },
        {
            'text': 'I cannot provide investment advice. Visit: https://www.amfiindia.com/mutual-funds-investor-education https://example.com',
            'intent': 'refusal',
            'expected': 'refusal_with_urls'
        }
    ]
    
    print("Policy Enforcer Test:")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['expected']}")
        print(f"Text: {test_case['text'][:100]}...")
        
        validation = enforcer.enforce_url_policy(test_case['text'], test_case['intent'])
        
        print(f"Compliant: {validation['is_compliant']}")
        if validation['policy_violations']:
            print(f"Violations: {', '.join(validation['policy_violations'])}")
        if validation['suggestions']:
            print(f"Suggestions: {', '.join(validation['suggestions'])}")
        
        print("-" * 30)


if __name__ == "__main__":
    main()
