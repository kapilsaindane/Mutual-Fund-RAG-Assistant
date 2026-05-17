#!/usr/bin/env python3

import math
from typing import List, Dict, Any, Tuple, Optional

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None


class CrossEncoderReranker:
    """
    Cross-encoder re-ranker for improving retrieval precision
    Uses BAAI/bge-reranker-base by default
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        if CrossEncoder is None:
            raise ImportError("sentence-transformers is required for cross-encoder reranking")
        
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model"""
        try:
            self.model = CrossEncoder(self.model_name)
            print(f"Loaded cross-encoder model: {self.model_name}")
        except Exception as e:
            print(f"Error loading cross-encoder model {self.model_name}: {e}")
            # Fallback to a simpler model
            try:
                self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                print(f"Fallback to model: cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception as fallback_error:
                print(f"Error loading fallback model: {fallback_error}")
                raise
    
    def rerank(self, 
               query: str, 
               documents: List[Dict[str, Any]], 
               top_k: int = 3,
               batch_size: int = 16) -> List[Dict[str, Any]]:
        """
        Re-rank documents using cross-encoder
        
        Args:
            query: Search query
            documents: List of document dictionaries with 'text' and 'metadata'
            top_k: Number of top results to return
            batch_size: Batch size for inference
            
        Returns:
            List of re-ranked documents with rerank scores
        """
        if not self.model:
            raise RuntimeError("Cross-encoder model not loaded")
        
        if not documents:
            return []
        
        # Prepare query-document pairs
        pairs = [(query, doc['text']) for doc in documents]
        
        # Get relevance scores
        try:
            scores = self.model.predict(pairs, batch_size=batch_size)
        except Exception as e:
            print(f"Error during cross-encoder prediction: {e}")
            # Fallback: return original documents with score 0
            for doc in documents:
                doc['rerank_score'] = 0.0
            return documents[:top_k]
        
        # Combine scores with original documents
        reranked_docs = []
        for doc, score in zip(documents, scores):
            reranked_doc = doc.copy()
            reranked_doc['rerank_score'] = float(score)
            reranked_docs.append(reranked_doc)
        
        # Sort by rerank score (descending)
        reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        # Return top-k results
        return reranked_docs[:top_k]
    
    def rerank_with_confidence(self, 
                             query: str, 
                             documents: List[Dict[str, Any]], 
                             top_k: int = 3,
                             confidence_threshold: float = 0.1,
                             margin_threshold: float = 0.05) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Re-rank with confidence analysis
        
        Args:
            query: Search query
            documents: List of document dictionaries
            top_k: Number of top results to return
            confidence_threshold: Minimum score for confident retrieval
            margin_threshold: Minimum margin between top and second result
            
        Returns:
            Tuple of (reranked_docs, confidence_info)
        """
        reranked_docs = self.rerank(query, documents, top_k)
        
        confidence_info = {
            'top_score': 0.0,
            'second_score': 0.0,
            'margin': 0.0,
            'is_confident': False,
            'confidence_reason': ''
        }
        
        if len(reranked_docs) >= 1:
            confidence_info['top_score'] = reranked_docs[0]['rerank_score']
        
        if len(reranked_docs) >= 2:
            confidence_info['second_score'] = reranked_docs[1]['rerank_score']
            confidence_info['margin'] = confidence_info['top_score'] - confidence_info['second_score']
        
        # Determine confidence
        if confidence_info['top_score'] < confidence_threshold:
            confidence_info['is_confident'] = False
            confidence_info['confidence_reason'] = f"Top score {confidence_info['top_score']:.3f} below threshold {confidence_threshold}"
        elif confidence_info['margin'] < margin_threshold:
            confidence_info['is_confident'] = False
            confidence_info['confidence_reason'] = f"Margin {confidence_info['margin']:.3f} below threshold {margin_threshold}"
        else:
            confidence_info['is_confident'] = True
            confidence_info['confidence_reason'] = "Confident retrieval"
        
        return reranked_docs, confidence_info
    
    def get_rerank_statistics(self, 
                             query: str, 
                             documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get detailed statistics about reranking process
        
        Args:
            query: Search query
            documents: List of documents to analyze
            
        Returns:
            Dictionary with reranking statistics
        """
        if not documents:
            return {'error': 'No documents provided'}
        
        # Rerank documents
        reranked_docs = self.rerank(query, documents, len(documents))
        
        # Calculate statistics
        scores = [doc['rerank_score'] for doc in reranked_docs]
        
        stats = {
            'total_documents': len(documents),
            'query': query,
            'score_statistics': {
                'mean': sum(scores) / len(scores) if scores else 0,
                'std': math.sqrt(sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)) if len(scores) > 1 else 0,
                'min': min(scores) if scores else 0,
                'max': max(scores) if scores else 0,
                'median': sorted(scores)[len(scores)//2] if scores else 0
            },
            'top_3_scores': scores[:3] if len(scores) >= 3 else scores,
            'score_distribution': {
                'high_confidence': len([s for s in scores if s > 0.5]),
                'medium_confidence': len([s for s in scores if 0.2 <= s <= 0.5]),
                'low_confidence': len([s for s in scores if s < 0.2])
            }
        }
        
        return stats
    
    def batch_rerank(self, 
                    queries_documents: List[Tuple[str, List[Dict[str, Any]]], 
                    top_k: int = 3) -> List[List[Dict[str, Any]]]:
        """
        Batch reranking for multiple queries
        
        Args:
            queries_documents: List of (query, documents) tuples
            top_k: Number of top results per query
            
        Returns:
            List of re-ranked document lists
        """
        if not self.model:
            raise RuntimeError("Cross-encoder model not loaded")
        
        all_results = []
        
        for query, documents in queries_documents:
            reranked = self.rerank(query, documents, top_k)
            all_results.append(reranked)
        
        return all_results


class ConfidenceGate:
    """
    Confidence gate for determining when to proceed vs. say "I don't know"
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.1,
                 margin_threshold: float = 0.05,
                 min_score_threshold: float = -1.0):
        self.confidence_threshold = confidence_threshold
        self.margin_threshold = margin_threshold
        self.min_score_threshold = min_score_threshold
    
    def evaluate_confidence(self, 
                         reranked_docs: List[Dict[str, Any]], 
                         confidence_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate confidence and determine if retrieval should proceed
        
        Args:
            reranked_docs: Re-ranked documents
            confidence_info: Confidence information from reranker
            
        Returns:
            Dictionary with gate decision and reasoning
        """
        gate_decision = {
            'should_proceed': True,
            'reason': '',
            'fallback_action': 'use_top_result',
            'confidence_level': 'high'
        }
        
        # Check minimum score threshold
        if confidence_info['top_score'] < self.min_score_threshold:
            gate_decision['should_proceed'] = False
            gate_decision['reason'] = f"Top score {confidence_info['top_score']:.3f} below minimum threshold {self.min_score_threshold}"
            gate_decision['fallback_action'] = 'say_dont_know'
            gate_decision['confidence_level'] = 'very_low'
            return gate_decision
        
        # Check confidence threshold
        if not confidence_info['is_confident']:
            gate_decision['should_proceed'] = False
            gate_decision['reason'] = confidence_info['confidence_reason']
            gate_decision['fallback_action'] = 'say_dont_know'
            gate_decision['confidence_level'] = 'low'
            return gate_decision
        
        # Check for very low margin (close results)
        if confidence_info['margin'] < self.margin_threshold / 2:
            gate_decision['confidence_level'] = 'medium'
            gate_decision['reason'] = f"Low margin {confidence_info['margin']:.3f}, results are close"
        
        # Check for single result
        if len(reranked_docs) == 1:
            gate_decision['confidence_level'] = 'medium'
            gate_decision['reason'] = "Only one result available"
        
        return gate_decision
    
    def adaptive_threshold(self, 
                        query_features: Dict[str, bool]) -> Tuple[float, float]:
        """
        Adapt thresholds based on query characteristics
        
        Args:
            query_features: Features extracted from query
            
        Returns:
            Tuple of (confidence_threshold, margin_threshold)
        """
        confidence_threshold = self.confidence_threshold
        margin_threshold = self.margin_threshold
        
        # Relax thresholds for numeric-heavy queries (exact facts)
        if query_features.get('is_numeric_heavy', False):
            confidence_threshold *= 0.8  # Lower threshold
            margin_threshold *= 0.5  # Lower margin requirement
        
        # Tighten thresholds for vague queries
        if not query_features.get('has_financial_terms', False):
            confidence_threshold *= 1.2  # Higher threshold
            margin_threshold *= 1.5  # Higher margin requirement
        
        # Adjust for scheme-specific queries
        if query_features.get('scheme_specific', False):
            confidence_threshold *= 0.9  # Slightly lower threshold
        
        return confidence_threshold, margin_threshold


def main():
    """Test cross-encoder reranker and confidence gate"""
    try:
        reranker = CrossEncoderReranker()
        confidence_gate = ConfidenceGate()
        
        # Sample documents for testing
        sample_docs = [
            {
                'text': 'HDFC Mid Cap Fund has an expense ratio of 0.45% and exit load of 1% for redemption within 1 year.',
                'metadata': {'scheme': 'HDFC Mid Cap Fund', 'section': 'Expenses'},
                'score': 0.85
            },
            {
                'text': 'ELSS Tax Saver Fund has a lock-in period of 3 years as per tax regulations.',
                'metadata': {'scheme': 'HDFC ELSS Tax Saver', 'section': 'Lock-in Period'},
                'score': 0.75
            },
            {
                'text': 'The minimum SIP amount for HDFC Equity Fund is Rs 100 with no upper limit.',
                'metadata': {'scheme': 'HDFC Equity Fund', 'section': 'Investment'},
                'score': 0.65
            }
        ]
        
        test_queries = [
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "ELSS lock-in period duration",
            "Minimum SIP amount for equity fund",
        ]
        
        print("Cross-Encoder Reranker Test:")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            
            # Rerank with confidence
            reranked_docs, confidence_info = reranker.rerank_with_confidence(query, sample_docs)
            
            print(f"Top score: {confidence_info['top_score']:.3f}")
            print(f"Second score: {confidence_info['second_score']:.3f}")
            print(f"Margin: {confidence_info['margin']:.3f}")
            print(f"Is confident: {confidence_info['is_confident']}")
            print(f"Reason: {confidence_info['confidence_reason']}")
            
            print(f"\nReranked Results:")
            for i, doc in enumerate(reranked_docs, 1):
                print(f"{i}. Score: {doc['rerank_score']:.3f}")
                print(f"   Text: {doc['text'][:80]}...")
            
            # Apply confidence gate
            gate_decision = confidence_gate.evaluate_confidence(reranked_docs, confidence_info)
            print(f"\nGate Decision: {gate_decision['should_proceed']}")
            print(f"Reason: {gate_decision['reason']}")
            print(f"Confidence Level: {gate_decision['confidence_level']}")
            print(f"Fallback Action: {gate_decision['fallback_action']}")
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error testing cross-encoder reranker: {e}")
        print("Make sure sentence-transformers is installed")


if __name__ == "__main__":
    main()
