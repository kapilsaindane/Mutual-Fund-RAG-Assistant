#!/usr/bin/env python3

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone


class GroqGenerator:
    """
    Groq-powered answer generator with fallback
    Uses OpenAI-compatible Chat Completions API via Groq
    """
    
    def __init__(self, model_name: str = "llama3-70b-8192"):
        self.model_name = model_name
        self.api_key = os.environ.get('GROQ_API_KEY')
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Check if Groq should be used
        self.use_groq = bool(self.api_key)
        
        if not self.use_groq:
            print("Groq API key not found, will use extractive fallback")
    
    def _make_api_request(self, messages: List[Dict[str, str]], 
                         temperature: float = 0.1) -> Optional[Dict[str, Any]]:
        """
        Make API request to Groq
        
        Args:
            messages: Chat messages
            temperature: Generation temperature
            
        Returns:
            API response or None if failed
        """
        import urllib.request
        import urllib.error
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model_name,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': 150,  # Keep responses concise
            'top_p': 0.9,
            'stream': False
        }
        
        try:
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                return json.loads(response_data)
                
        except urllib.error.HTTPError as e:
            print(f"Groq API HTTP error: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"Groq API URL error: {e.reason}")
            return None
        except Exception as e:
            print(f"Groq API error: {e}")
            return None
    
    def generate_groq_answer(self, 
                           query: str,
                           retrieved_chunks: List[Dict[str, Any]],
                           source_url: str,
                           last_updated: str) -> Dict[str, Any]:
        """
        Generate answer using Groq API
        
        Args:
            query: Original user query
            retrieved_chunks: Retrieved chunks for context
            source_url: Source URL to cite
            last_updated: Last updated date
            
        Returns:
            Generation result with metadata
        """
        if not self.use_groq:
            return {
                'success': False,
                'error': 'Groq API key not configured',
                'answer': '',
                'method': 'groq'
            }
        
        # Prepare context from retrieved chunks
        context_text = ""
        if retrieved_chunks:
            # Use top 3 chunks for context
            for i, chunk in enumerate(retrieved_chunks[:3], 1):
                chunk_text = chunk.get('text', '')
                context_text += f"Context {i}: {chunk_text}\n"
        else:
            context_text = "No relevant information found."
        
        # System prompt for factual-only responses
        system_prompt = """You are a mutual fund assistant that provides ONLY factual information from official sources.

Rules:
1. Answer ONLY using the provided context
2. Maximum 3 sentences
3. No investment advice, recommendations, or comparisons
4. No predictions about future performance
5. Include exactly one source URL
6. Add "Last updated from sources: <date>" footer
7. If context is insufficient, say "I don't have enough information"

Context is from official HDFC mutual fund sources."""
        
        user_prompt = f"""Query: {query}

Context:
{context_text}

Requirements:
- Answer using only the provided context
- Maximum 3 sentences
- Factual information only
- No advice or recommendations
- Include source URL: {source_url}
- Add footer: "Last updated from sources: {last_updated}"

Answer:"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Make API request
        response = self._make_api_request(messages, temperature=0.1)
        
        if not response:
            return {
                'success': False,
                'error': 'Groq API request failed',
                'answer': '',
                'method': 'groq'
            }
        
        # Extract answer
        answer = response.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
        if not answer:
            return {
                'success': False,
                'error': 'Empty response from Groq',
                'answer': '',
                'method': 'groq'
            }
        
        # Post-process answer to ensure compliance
        processed_answer = self._post_process_groq_answer(answer, source_url, last_updated)
        
        return {
            'success': True,
            'answer': processed_answer,
            'method': 'groq',
            'model': self.model_name,
            'tokens_used': response.get('usage', {}).get('total_tokens', 0),
            'raw_response': answer
        }
    
    def _post_process_groq_answer(self, answer: str, source_url: str, last_updated: str) -> str:
        """
        Post-process Groq answer to ensure policy compliance
        
        Args:
            answer: Raw answer from Groq
            source_url: Source URL to include
            last_updated: Last updated date
            
        Returns:
            Processed answer
        """
        if not answer:
            return "I don't have enough information to answer this question."
        
        # Ensure exactly one source URL
        processed_answer = answer
        
        # Remove any existing URLs and add the correct one
        import re
        url_pattern = r'https?://[^\s<>"\')]+'
        existing_urls = re.findall(url_pattern, processed_answer)
        
        if existing_urls:
            # Remove all existing URLs
            processed_answer = re.sub(url_pattern, '', processed_answer)
        
        # Add the required source URL
        processed_answer += f"\n\nSource: {source_url}"
        
        # Add required footer
        processed_answer += f"\n\nLast updated from sources: {last_updated}"
        
        # Ensure sentence count limit
        sentences = processed_answer.split('.')
        if len(sentences) > 3:
            processed_answer = '. '.join(sentences[:3]) + '.'
        
        return processed_answer.strip()
    
    def generate_extractive_fallback(self, 
                                   query: str,
                                   retrieved_chunks: List[Dict[str, Any]],
                                   source_url: str,
                                   last_updated: str) -> Dict[str, Any]:
        """
        Generate extractive fallback answer
        
        Args:
            query: Original user query
            retrieved_chunks: Retrieved chunks for context
            source_url: Source URL to cite
            last_updated: Last updated date
            
        Returns:
            Extractive answer result
        """
        if not retrieved_chunks:
            return {
                'success': False,
                'error': 'No chunks available for extractive generation',
                'answer': '',
                'method': 'extractive_fallback'
            }
        
        # Use top chunk for extractive answer
        top_chunk = retrieved_chunks[0]
        chunk_text = top_chunk.get('text', '')
        
        if not chunk_text:
            return {
                'success': False,
                'error': 'Empty chunk text',
                'answer': '',
                'method': 'extractive_fallback'
            }
        
        # Simple extractive processing (first 1-2 sentences)
        sentences = chunk_text.split('.')
        extractive_answer = '. '.join(sentences[:2]) + '.'
        
        # Add source URL and footer
        extractive_answer += f"\n\nSource: {source_url}"
        extractive_answer += f"\n\nLast updated from sources: {last_updated}"
        
        return {
            'success': True,
            'answer': extractive_answer,
            'method': 'extractive_fallback',
            'chunk_used': top_chunk.get('chunk_id', ''),
            'sentences_extracted': len(sentences[:2])
        }
    
    def generate_answer(self, 
                    query: str,
                    retrieved_chunks: List[Dict[str, Any]],
                    source_url: str,
                    last_updated: str,
                    use_groq: Optional[bool] = None) -> Dict[str, Any]:
        """
        Main answer generation method
        
        Args:
            query: Original user query
            retrieved_chunks: Retrieved chunks
            source_url: Source URL to cite
            last_updated: Last updated date
            use_groq: Force Groq usage (None = auto)
            
        Returns:
            Generated answer
        """
        # Determine whether to use Groq
        should_use_groq = use_groq if use_groq is not None else self.use_groq
        
        if should_use_groq:
            print("Using Groq for answer generation")
            return self.generate_groq_answer(query, retrieved_chunks, source_url, last_updated)
        else:
            print("Using extractive fallback for answer generation")
            return self.generate_extractive_fallback(query, retrieved_chunks, source_url, last_updated)
    
    def is_groq_available(self) -> bool:
        """Check if Groq is available"""
        return self.use_groq
    
    def get_model_info(self) -> Dict[str, str]:
        """Get model information"""
        return {
            'provider': 'Groq',
            'model': self.model_name,
            'available': self.use_groq,
            'api_endpoint': self.base_url
        }


def main():
    """Test Groq generator"""
    generator = GroqGenerator()
    
    print("Groq Generator Test:")
    print("=" * 50)
    print(f"Model Info: {generator.get_model_info()}")
    print(f"Groq Available: {generator.is_groq_available()}")
    print()
    
    # Test data
    test_query = "What is the expense ratio of HDFC Mid Cap Fund?"
    test_chunks = [
        {
            'text': 'HDFC Mid Cap Fund has an expense ratio of 0.45% and exit load of 1% for redemption within 1 year.',
            'metadata': {
                'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
                'source_date': '2026-05-05T17:38:50.172818+00:00',
                'scheme': 'HDFC Mid Cap Fund Direct Growth',
                'section_heading': 'Fund Details',
                'chunk_id': 'c-01-002-001'
            }
        }
    ]
    
    # Test with Groq (if available)
    if generator.is_groq_available():
        print("Testing with Groq...")
        result = generator.generate_answer(
            query=test_query,
            retrieved_chunks=test_chunks,
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            last_updated="2026-05-05",
            use_groq=True
        )
        print(f"Success: {result['success']}")
        print(f"Method: {result['method']}")
        print(f"Answer: {result['answer'][:200]}...")
    else:
        print("Testing extractive fallback...")
        result = generator.generate_answer(
            query=test_query,
            retrieved_chunks=test_chunks,
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            last_updated="2026-05-05",
            use_groq=False
        )
        print(f"Success: {result['success']}")
        print(f"Method: {result['method']}")
        print(f"Answer: {result['answer'][:200]}...")


if __name__ == "__main__":
    main()
