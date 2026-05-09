#!/usr/bin/env python3

import re
from typing import Dict, List, Tuple, Optional


class PIIDetector:
    """
    PII (Personally Identifiable Information) detection system
    Detects sensitive information in user messages for policy enforcement
    """
    
    def __init__(self):
        # PII patterns for Indian context
        self.pii_patterns = {
            'pan': [
                r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',  # Standard PAN format
                r'\b\d{3}-\d{2}-\d{4}\b',      # Alternative format
                r'\bpan\b.*\b\d{10}\b',            # PAN with numbers
            ],
            'aadhaar': [
                r'\b\d{4}\s?\d{4}\s?\d{4}\b',  # 12-digit Aadhaar
                r'\b\d{12}\b',                     # Plain 12-digit
                r'\baadhaar\b.*\b\d{12}\b',       # Aadhaar with keyword
            ],
            'email': [
                r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
                r'\bemail\b.*\b@\b',                 # Email with keyword
            ],
            'phone': [
                r'\b(?:\+91[-\s]?)?[6-9]\d{9}\b',  # Indian mobile
                r'\b\d{10}\b',                      # Plain 10-digit
                r'\b(?:0|91)?[-\s]?\d{10}\b',      # With country code
            ],
            'otp': [
                r'\botp\b.*\b\d{4,8}\b',           # OTP with keyword
                r'\b(one time|one-time)\s+password\b',  # OTP description
                r'\bverification\s+code\b.*\b\d',      # Verification code
            ],
            'account': [
                r'\baccount\s+(number|no|num)\b.*\b\d',
                r'\b(demat|folio|client)\s+(id|number)\b',
                r'\bportfolio\s+id\b',
            ],
            'address': [
                r'\b\d+\s+[^,]+\s+[a-z]+\s+(street|road|nagar)\b',
                r'\b(pin|postal)\s+code\b.*\b\d',
                r'\baddress\b.*\b\d{6}\b',           # PIN code
            ],
            'bank': [
                r'\b(ifsc|bank)\s+(code|branch)\b',
                r'\baccount\s+(number|no)\b.*\bbank\b',
                r'\b(neft|rtgs|imps)\s+details\b',
            ],
            'financial_sensitive': [
                r'\b(income|salary|credit|debit)\s+(card|number)\b',
                r'\batm\s+(pin|password)\b',
                r'\bnet\s+banking\s+(password|pin)\b',
                r'\bcredit\s+card\s+(number|cvv)\b',
            ]
        }
        
        # Compile patterns for efficiency
        self.compiled_patterns = {}
        for pii_type, patterns in self.pii_patterns.items():
            self.compiled_patterns[pii_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        # High-confidence indicators
        self.high_confidence_keywords = [
            'pan', 'aadhaar', 'email', 'phone', 'mobile', 'otp', 'password', 'pin',
            'account number', 'bank account', 'ifsc', 'atm', 'credit card', 'debit card',
            'demat account', 'folio number', 'portfolio id', 'address', 'pin code'
        ]
        
        # Medium-confidence patterns (context-dependent)
        self.medium_confidence_patterns = [
            r'\b\d{10,12}\b',                    # Long numbers (could be ID)
            r'\b\d{4}\s*-\s*\d{4}\s*-\s*\d{4}\b',  # ID-like format
            r'\b[a-zA-Z]{2,}\d{2,4}\b',          # Alphanumeric codes
        ]
        
        self.compiled_medium = [re.compile(pattern, re.IGNORECASE) for pattern in self.medium_confidence_patterns]
    
    def detect_pii(self, text: str) -> Dict[str, any]:
        """
        Detect PII in text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with PII detection results
        """
        if not text:
            return {
                'has_pii': False,
                'pii_types': [],
                'confidence': 0.0,
                'matches': []
            }
        
        text_lower = text.lower()
        detected_pii = {}
        all_matches = []
        
        # Check each PII type
        for pii_type, compiled_patterns in self.compiled_patterns.items():
            type_matches = []
            for pattern in compiled_patterns:
                matches = pattern.findall(text)
                if matches:
                    type_matches.extend(matches[:3])  # Limit matches per type
            
            if type_matches:
                detected_pii[pii_type] = type_matches
                all_matches.extend([(pii_type, match) for match in type_matches])
        
        # Check medium confidence patterns
        medium_matches = []
        for pattern in self.compiled_medium:
            matches = pattern.findall(text)
            if matches:
                medium_matches.extend(matches[:2])
        
        # Calculate overall confidence
        has_high_confidence = any(pii_type in detected_pii for pii_type in self.high_confidence_keywords)
        has_medium_confidence = len(medium_matches) > 0
        
        if has_high_confidence:
            confidence = 0.9
        elif has_medium_confidence:
            confidence = 0.6
        elif detected_pii:
            confidence = 0.4
        else:
            confidence = 0.0
        
        return {
            'has_pii': len(detected_pii) > 0 or len(medium_matches) > 0,
            'pii_types': list(detected_pii.keys()),
            'high_confidence_pii': list(detected_pii.keys()),
            'medium_confidence_matches': medium_matches,
            'confidence': confidence,
            'all_matches': all_matches
        }
    
    def get_pii_block_template(self, pii_info: Dict[str, any]) -> str:
        """
        Generate PII block response template
        
        Args:
            pii_info: PII detection result
            
        Returns:
            PII block response
        """
        if not pii_info['has_pii']:
            return ""
        
        pii_types = pii_info['pii_types']
        confidence = pii_info['confidence']
        
        # Customize response based on PII type
        if 'pan' in pii_types:
            return "I cannot process requests containing PAN card numbers for security and privacy reasons."
        elif 'aadhaar' in pii_types:
            return "I cannot process requests containing Aadhaar numbers for security and privacy reasons."
        elif 'email' in pii_types:
            return "I cannot process requests containing email addresses for security and privacy reasons."
        elif 'phone' in pii_types:
            return "I cannot process requests containing phone numbers for security and privacy reasons."
        elif 'otp' in pii_types:
            return "I cannot process requests containing OTP codes or verification codes for security reasons."
        elif 'account' in pii_types:
            return "I cannot process requests containing account numbers for security and privacy reasons."
        elif 'bank' in pii_types:
            return "I cannot process requests containing banking details for security and privacy reasons."
        elif confidence >= 0.8:
            return "I cannot process this request as it contains sensitive personal information for security and privacy reasons."
        else:
            return "I cannot process this request as it may contain sensitive personal information for security and privacy reasons."
    
    def redact_pii(self, text: str, mask_char: str = '***') -> str:
        """
        Redact PII from text for logging purposes
        
        Args:
            text: Text to redact
            mask_char: Character to use for masking
            
        Returns:
            Redacted text
        """
        if not text:
            return text
        
        redacted_text = text
        
        # Redact detected PII patterns
        for pii_type, compiled_patterns in self.compiled_patterns.items():
            for pattern in compiled_patterns:
                matches = pattern.findall(redacted_text)
                for match in matches:
                    if isinstance(match, tuple):
                        # For regex groups
                        for group in match:
                            if group:
                                redacted_text = redacted_text.replace(group, mask_char * len(group))
                    else:
                        # For full match
                        redacted_text = redacted_text.replace(match, mask_char * len(match))
                    else:
                        # For string match
                        redacted_text = redacted_text.replace(match, mask_char * len(match))
        
        return redacted_text
    
    def is_safe_for_processing(self, text: str) -> bool:
        """
        Check if text is safe for processing (no PII)
        
        Args:
            text: Text to check
            
        Returns:
            True if safe, False if PII detected
        """
        pii_info = self.detect_pii(text)
        return not pii_info['has_pii']
    
    def explain_detection(self, pii_info: Dict[str, any]) -> str:
        """
        Generate explanation of PII detection
        
        Args:
            pii_info: PII detection result
            
        Returns:
            Explanation string
        """
        if not pii_info['has_pii']:
            return "No PII detected"
        
        explanation = f"PII Detected (Confidence: {pii_info['confidence']:.1f})\n"
        
        if pii_info['high_confidence_pii']:
            explanation += f"High-confidence PII types: {', '.join(pii_info['high_confidence_pii'])}\n"
        
        if pii_info['medium_confidence_matches']:
            explanation += f"Medium-confidence matches: {len(pii_info['medium_confidence_matches'])} patterns\n"
        
        if pii_info['all_matches']:
            explanation += "Specific matches:\n"
            for pii_type, match in pii_info['all_matches'][:5]:  # Limit output
                explanation += f"  {pii_type}: {str(match)[:50]}...\n"
        
        return explanation


def main():
    """Test PII detector"""
    detector = PIIDetector()
    
    test_cases = [
        # High confidence PII
        "My PAN is ABCDE1234F and email is user@example.com",
        "Call me at 9876543210 for account details",
        "My Aadhaar number is 123456789012",
        "The OTP is 123456 for verification",
        
        # Medium confidence PII
        "My ID is 1234-5678-9012",
        "Code is AB1234",
        
        # No PII
        "What is the expense ratio of HDFC Mid Cap Fund?",
        "NAV details for mutual fund",
        "SIP investment information",
    ]
    
    print("PII Detector Test:")
    print("=" * 50)
    
    for text in test_cases:
        print(f"\nText: {text}")
        
        pii_info = detector.detect_pii(text)
        print(f"Has PII: {pii_info['has_pii']}")
        print(f"Confidence: {pii_info['confidence']:.2f}")
        print(f"PII Types: {pii_info['pii_types']}")
        
        if pii_info['has_pii']:
            block_template = detector.get_pii_block_template(pii_info)
            print(f"Block Response: {block_template}")
        
        print(f"Safe for processing: {detector.is_safe_for_processing(text)}")
        print(f"Redacted: {detector.redact_pii(text)}")
        print("-" * 30)


if __name__ == "__main__":
    main()
