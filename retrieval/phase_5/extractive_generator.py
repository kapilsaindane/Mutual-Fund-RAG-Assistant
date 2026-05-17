#!/usr/bin/env python3

import re
from typing import Dict, List, Optional
from datetime import datetime, timezone


class ExtractiveGenerator:
    """
    Extractive answer generator (≤3 sentences)
    Builds answer body from top reranked chunk only
    """
    
    def __init__(self):
        # Banned tokens for factual-only policy
        self.banned_tokens = [
            'recommend', 'suggest', 'advise', 'should', 'would', 'could', 'might',
            'better', 'best', 'worst', 'top', 'bottom', 'higher', 'lower',
            'will', 'expect', 'predict', 'forecast', 'outperform', 'underperform',
            'good', 'bad', 'safe', 'risky', 'excellent', 'poor'
        ]
        
        # Sentence splitters
        self.sentence_enders = ['.', '!', '?', '\n\n']
        
        # URL patterns to strip from chunks
        self.url_pattern = r'https?://[^\s<>"\'\)]+'
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text"""
        if not text:
            return 0
        
        # Simple sentence counting
        sentences = 0
        for char in text:
            if char in self.sentence_enders:
                sentences += 1
        
        return max(1, sentences)  # At least 1 if text exists
    
    def _strip_urls_from_chunk(self, chunk_text: str) -> str:
        """Strip any URLs embedded in chunk text"""
        # Remove URLs to avoid accidental inclusion in response
        return re.sub(self.url_pattern, '', chunk_text)
    
    def _check_banned_tokens(self, text: str) -> List[str]:
        """Check for banned tokens in text"""
        found_banned = []
        text_lower = text.lower()
        
        for token in self.banned_tokens:
            if token in text_lower:
                found_banned.append(token)
        
        return found_banned
    
    def generate_extractive_answer(self, 
                                top_chunk: Dict[str, any], 
                                max_sentences: int = 3,
                                source_url: Optional[str] = None) -> Dict[str, any]:
        """
        Generate extractive answer from top chunk
        
        Args:
            top_chunk: Top reranked chunk with metadata
            max_sentences: Maximum sentences allowed (default: 3)
            source_url: Source URL to use (overrides chunk URL)
            
        Returns:
            Dictionary with generated answer and metadata
        """
        if not top_chunk:
            return {
                'success': False,
                'answer': '',
                'error': 'No chunk provided for extractive generation',
                'metadata': {}
            }
        
        chunk_text = top_chunk.get('text', '')
        chunk_metadata = top_chunk.get('metadata', {})
        
        if not chunk_text:
            return {
                'success': False,
                'answer': '',
                'error': 'Empty chunk text',
                'metadata': chunk_metadata
            }
        
        # Strip URLs from chunk text to avoid accidental inclusion
        clean_text = self._strip_urls_from_chunk(chunk_text)
        
        # Check for banned tokens
        banned_tokens = self._check_banned_tokens(clean_text)
        
        if banned_tokens:
            return {
                'success': False,
                'answer': '',
                'error': f'Banned tokens detected: {", ".join(banned_tokens)}',
                'metadata': chunk_metadata,
                'banned_tokens': banned_tokens
            }
        
        # Extract sentences (simple approach)
        sentences = []
        current_sentence = ''
        
        for char in clean_text:
            current_sentence += char
            if char in self.sentence_enders:
                sentence = current_sentence.strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = ''
        
        # Add any remaining text
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # Limit to max_sentences
        limited_sentences = sentences[:max_sentences]
        
        # Join sentences back into answer
        answer = '. '.join(limited_sentences)
        
        # Get source URL
        if source_url:
            final_source_url = source_url
        else:
            final_source_url = chunk_metadata.get('source_url', '')
        
        # Get last updated date
        last_updated = chunk_metadata.get('source_date', '')
        
        # Format last updated date
        if last_updated:
            try:
                # Parse ISO date and format
                if 'T' in last_updated:
                    dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d')
                else:
                    formatted_date = last_updated
            except:
                formatted_date = last_updated
        else:
            formatted_date = 'Unknown'
        
        return {
            'success': True,
            'answer': answer,
            'metadata': {
                'source_url': final_source_url,
                'last_updated': formatted_date,
                'sentence_count': len(limited_sentences),
                'chunk_id': chunk_metadata.get('chunk_id', ''),
                'scheme': chunk_metadata.get('scheme', ''),
                'section': chunk_metadata.get('section_heading', ''),
                'original_sentences': len(sentences),
                'banned_tokens_found': banned_tokens
            }
        }
    
    def validate_extractive_answer(self, answer_data: Dict[str, any]) -> Dict[str, any]:
        """
        Validate extractive answer meets requirements
        
        Args:
            answer_data: Generated answer data
            
        Returns:
            Validation result
        """
        validation = {
            'is_valid': True,
            'violations': [],
            'warnings': []
        }
        
        if not answer_data.get('success', False):
            validation['is_valid'] = False
            validation['violations'].append('Answer generation failed')
            return validation
        
        answer = answer_data.get('answer', '')
        metadata = answer_data.get('metadata', {})
        
        # Check sentence count
        sentence_count = metadata.get('sentence_count', 0)
        if sentence_count > 3:
            validation['is_valid'] = False
            validation['violations'].append(f'Too many sentences: {sentence_count} (max: 3)')
        
        # Check for banned tokens
        banned_tokens = metadata.get('banned_tokens_found', [])
        if banned_tokens:
            validation['is_valid'] = False
            validation['violations'].append(f'Banned tokens: {", ".join(banned_tokens)}')
        
        # Check answer is not empty
        if not answer.strip():
            validation['is_valid'] = False
            validation['violations'].append('Empty answer generated')
        
        # Check for URLs in answer (should be none in extractive)
        if 'http' in answer.lower():
            validation['warnings'].append('URLs found in extractive answer')
        
        return validation
    
    def explain_generation(self, answer_data: Dict[str, any]) -> str:
        """
        Generate explanation of extractive generation process
        
        Args:
            answer_data: Generated answer data
            
        Returns:
            Explanation string
        """
        if not answer_data.get('success', False):
            return f"Extractive generation failed: {answer_data.get('error', 'Unknown error')}"
        
        metadata = answer_data.get('metadata', {})
        answer = answer_data.get('answer', '')
        
        explanation = f"Extractive Generation Summary:\n"
        explanation += f"Answer: {answer[:100]}{'...' if len(answer) > 100 else ''}\n"
        explanation += f"Sentences: {metadata.get('sentence_count', 0)}/3\n"
        explanation += f"Source URL: {metadata.get('source_url', 'None')}\n"
        explanation += f"Last Updated: {metadata.get('last_updated', 'Unknown')}\n"
        explanation += f"Chunk ID: {metadata.get('chunk_id', 'Unknown')}\n"
        explanation += f"Scheme: {metadata.get('scheme', 'Unknown')}\n"
        explanation += f"Section: {metadata.get('section', 'Unknown')}\n"
        
        if metadata.get('banned_tokens_found'):
            explanation += f"⚠️  Banned tokens detected: {metadata['banned_tokens_found']}\n"
        
        return explanation.strip()


def main():
    """Test extractive generator"""
    generator = ExtractiveGenerator()
    
    # Sample chunk data
    test_chunks = [
        {
            'text': 'HDFC Mid Cap Fund has an expense ratio of 0.45% and exit load of 1% for redemption within 1 year. The fund is categorized as Very High Risk.',
            'metadata': {
                'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
                'source_date': '2026-05-05T17:38:50.172818+00:00',
                'scheme': 'HDFC Mid Cap Fund Direct Growth',
                'section_heading': 'Fund Details',
                'chunk_id': 'c-01-002-001'
            }
        },
        {
            'text': 'The minimum SIP amount for HDFC Equity Fund is Rs 100 with no upper limit. This makes it accessible for small investors.',
            'metadata': {
                'source_url': 'https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth',
                'source_date': '2026-05-05T17:38:50.172818+00:00',
                'scheme': 'HDFC Equity Fund Direct Growth',
                'section_heading': 'Investment Details',
                'chunk_id': 'c-01-001-001'
            }
        },
        {
            'text': 'ELSS Tax Saver Fund has a lock-in period of 3 years as per tax regulations under Section 80C of the Income Tax Act.',
            'metadata': {
                'source_url': 'https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth',
                'source_date': '2026-05-05T17:38:50.172818+00:00',
                'scheme': 'HDFC ELSS Tax Saver Fund Direct Plan Growth',
                'section_heading': 'Tax Benefits',
                'chunk_id': 'c-01-004-001'
            }
        }
    ]
    
    print("Extractive Generator Test:")
    print("=" * 60)
    
    for i, chunk in enumerate(test_chunks, 1):
        print(f"\nTest Case {i}:")
        
        result = generator.generate_extractive_answer(chunk)
        
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Answer: {result['answer']}")
            print(f"Sentences: {result['metadata']['sentence_count']}")
            print(f"Source: {result['metadata']['source_url']}")
        else:
            print(f"Error: {result['error']}")
        
        # Validate
        validation = generator.validate_extractive_answer(result)
        print(f"Valid: {validation['is_valid']}")
        if validation['violations']:
            print(f"Violations: {', '.join(validation['violations'])}")
        if validation['warnings']:
            print(f"Warnings: {', '.join(validation['warnings'])}")
        
        print("-" * 40)


if __name__ == "__main__":
    main()
