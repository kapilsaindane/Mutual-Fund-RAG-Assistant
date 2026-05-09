#!/usr/bin/env python3

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class PostProcessor:
    """
    Post-processor with deterministic checks
    Enforces final compliance before returning response
    """
    
    def __init__(self):
        # Compliance checks
        self.sentence_count_limit = 3
        self.banned_tokens = [
            'recommend', 'suggest', 'advise', 'should', 'would', 'could', 'might',
            'better', 'best', 'worst', 'top', 'bottom', 'higher', 'lower',
            'will', 'expect', 'predict', 'forecast', 'outperform', 'underperform',
            'good', 'bad', 'safe', 'risky', 'excellent', 'poor'
        ]
        
        # URL patterns
        self.url_pattern = r'https?://[^\s<>"\'\)]+'
        
        # Footer pattern
        self.footer_pattern = r'Last updated from sources:\s*\d{4}-\d{2}-\d{2}'
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        if not text:
            return 0
        
        # Simple sentence counting
        sentences = 0
        for char in text:
            if char in '.!?':
                sentences += 1
        
        return max(1, sentences)  # At least 1 if text exists
    
    def _extract_urls(self, text: str) -> List[str]:
        """Extract all URLs from text"""
        return re.findall(self.url_pattern, text.lower())
    
    def _check_banned_tokens(self, text: str) -> List[str]:
        """Check for banned tokens in text"""
        found_banned = []
        text_lower = text.lower()
        
        for token in self.banned_tokens:
            if token in text_lower:
                found_banned.append(token)
        
        return found_banned
    
    def _check_footer_present(self, text: str) -> bool:
        """Check if required footer is present"""
        return bool(re.search(self.footer_pattern, text))
    
    def _get_safe_template(self, source_url: str) -> str:
        """Get safe fallback template"""
        return f"""I apologize, but I'm unable to process your request at this time. For accurate information about HDFC mutual funds, please visit: {source_url}"""
    
    def process_response(self, 
                      response_text: str,
                      source_url: str,
                      expected_intent: str = "factual",
                      pii_detected: bool = False) -> Dict[str, Any]:
        """
        Process response with deterministic compliance checks
        
        Args:
            response_text: Generated response text
            source_url: Source URL that should be cited
            expected_intent: Expected intent type ("factual" or "refusal")
            pii_detected: Whether PII was detected in original query
            
        Returns:
            Processing result with compliance status
        """
        result = {
            'original_response': response_text,
            'processed_response': response_text,
            'is_compliant': True,
            'violations': [],
            'warnings': [],
            'corrections': [],
            'final_url': source_url,
            'metadata': {}
        }
        
        # PII responses should have no URLs
        if pii_detected and expected_intent == "refusal":
            urls_found = self._extract_urls(response_text)
            if urls_found:
                result['is_compliant'] = False
                result['violations'].append("PII response contains URLs")
                # Fallback to safe template
                safe_url = "https://www.amfiindia.com/mutual-funds-investor-education"
                result['processed_response'] = self._get_safe_template(safe_url)
                result['final_url'] = None
            else:
                result['warnings'].append("PII response with no URLs (compliant)")
        
        # Factual responses should have exactly one URL
        elif expected_intent == "factual":
            urls_found = self._extract_urls(response_text)
            sentence_count = self._count_sentences(response_text)
            
            if len(urls_found) == 0:
                result['is_compliant'] = False
                result['violations'].append("Missing required source URL in factual answer")
                # Fallback to safe template
                safe_url = source_url or "https://www.amfiindia.com/mutual-funds-investor-education"
                result['processed_response'] = self._get_safe_template(safe_url)
                result['final_url'] = None
            elif len(urls_found) > 1:
                result['is_compliant'] = False
                result['violations'].append(f"Too many URLs: {len(urls_found)} (exactly 1 required)")
                # Keep only first URL
                first_url = urls_found[0]
                # Remove all URLs and add the correct one
                response_without_urls = re.sub(self.url_pattern, '', response_text)
                result['processed_response'] = f"{response_without_urls}\n\nSource: {first_url}"
                result['final_url'] = first_url
                result['corrections'].append(f"Reduced URLs from {len(urls_found)} to 1: {first_url}")
            else:
                # Exactly one URL - compliant
                result['final_url'] = urls_found[0]
                result['warnings'].append("URL policy compliant")
        
        # Don't know responses should have no URLs (policy enforcement)
        elif expected_intent == "dont_know":
            urls_found = self._extract_urls(response_text)
            if urls_found:
                result['is_compliant'] = False
                result['violations'].append("Don't know response contains URLs (should be zero)")
                # Remove URLs and keep no URL
                response_without_urls = re.sub(self.url_pattern, '', response_text)
                result['processed_response'] = response_without_urls
                result['final_url'] = None
                result['corrections'].append("Removed URLs from don't know response")
            else:
                result['warnings'].append("Don't know response with no URLs (compliant)")
        
        # Check sentence count for factual responses
        if expected_intent == "factual":
            sentence_count = self._count_sentences(response_text)
            if sentence_count > self.sentence_count_limit:
                result['is_compliant'] = False
                result['violations'].append(f"Too many sentences: {sentence_count} (max: {self.sentence_count_limit})")
                # Truncate to limit
                sentences = response_text.split('.')
                truncated_sentences = sentences[:self.sentence_count_limit]
                result['processed_response'] = '. '.join(truncated_sentences)
                result['corrections'].append(f"Truncated from {sentence_count} to {self.sentence_count_limit} sentences")
        
        # Check for banned tokens
        banned_tokens = self._check_banned_tokens(response_text)
        if banned_tokens:
            result['is_compliant'] = False
            result['violations'].append(f"Banned tokens detected: {', '.join(banned_tokens)}")
            # Fallback to safe template
            safe_url = source_url or "https://www.amfiindia.com/mutual-funds-investor-education"
            result['processed_response'] = self._get_safe_template(safe_url)
            result['final_url'] = None
        
        # Check footer presence for factual responses
        if expected_intent == "factual":
            if not self._check_footer_present(response_text):
                result['is_compliant'] = False
                result['violations'].append("Missing required footer")
                # Add footer
                current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                result['processed_response'] = f"{response_text}\n\nLast updated from sources: {current_date}"
                result['corrections'].append("Added missing footer")
        
        # Update metadata
        result['metadata'] = {
            'sentence_count': self._count_sentences(result['processed_response']),
            'url_count': len(self._extract_urls(result['processed_response'])),
            'banned_tokens': banned_tokens,
            'footer_present': self._check_footer_present(result['processed_response']),
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return result
    
    def get_compliance_report(self, processing_result: Dict[str, Any]) -> str:
        """
        Generate compliance report
        
        Args:
            processing_result: Result from process_response
            
        Returns:
            Formatted compliance report
        """
        report = f"Post-Processing Compliance Report\n"
        report += f"=" * 40 + "\n"
        report += f"Compliant: {processing_result['is_compliant']}\n"
        report += f"Original Response: {processing_result['original_response'][:100]}...\n"
        report += f"Processed Response: {processing_result['processed_response'][:100]}...\n"
        report += f"Final URL: {processing_result['final_url']}\n"
        
        if processing_result['violations']:
            report += "Violations:\n"
            for violation in processing_result['violations']:
                report += f"  - {violation}\n"
        
        if processing_result['warnings']:
            report += "Warnings:\n"
            for warning in processing_result['warnings']:
                report += f"  - {warning}\n"
        
        if processing_result['corrections']:
            report += "Corrections:\n"
            for correction in processing_result['corrections']:
                report += f"  - {correction}\n"
        
        metadata = processing_result.get('metadata', {})
        report += f"Metadata:\n"
        report += f"  Sentences: {metadata.get('sentence_count', 0)}\n"
        report += f"  URLs: {metadata.get('url_count', 0)}\n"
        report += f"  Banned Tokens: {metadata.get('banned_tokens', [])}\n"
        report += f"  Footer Present: {metadata.get('footer_present', False)}\n"
        
        return report


def main():
    """Test post-processor"""
    processor = PostProcessor()
    
    test_cases = [
        # Compliant factual response
        {
            'response': 'The expense ratio is 0.45%. Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n\nLast updated from sources: 2026-05-05',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # Missing URL
        {
            'response': 'The expense ratio is 0.45%.',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # Too many URLs
        {
            'response': 'The expense ratio is 0.45%. Sources: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth https://example.com',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # Too many sentences
        {
            'response': 'The expense ratio is 0.45%. This is a very competitive rate. The fund has performed well over the past three years. Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n\nLast updated from sources: 2026-05-05',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # Banned tokens
        {
            'response': 'I would recommend investing in this fund as it has good performance.',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # Missing footer
        {
            'response': 'The expense ratio is 0.45%. Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'factual',
            'pii_detected': False
        },
        
        # PII with URLs (should be blocked)
        {
            'response': 'My PAN is ABCDE1234F. You can check my account at https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
            'expected_intent': 'refusal',
            'pii_detected': True
        }
    ]
    
    print("Post-Processor Test:")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Expected Intent: {test_case['expected_intent']}")
        print(f"PII Detected: {test_case['pii_detected']}")
        
        result = processor.process_response(
            response_text=test_case['response'],
            source_url=test_case['source_url'],
            expected_intent=test_case['expected_intent'],
            pii_detected=test_case['pii_detected']
        )
        
        print(f"Compliant: {result['is_compliant']}")
        print(f"Processed Response: {result['processed_response'][:100]}...")
        print(f"Final URL: {result['final_url']}")
        
        if result['violations']:
            print(f"Violations: {', '.join(result['violations'])}")
        
        if result['warnings']:
            print(f"Warnings: {', '.join(result['warnings'])}")
        
        if result['corrections']:
            print(f"Corrections: {', '.join(result['corrections'])}")
        
        print("-" * 30)


if __name__ == "__main__":
    main()
