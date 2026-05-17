#!/usr/bin/env python3

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import rank_bm25
except ImportError:
    rank_bm25 = None

from .query_normalizer import QueryNormalizer
from .scheme_resolver import SchemeResolver


class DenseRetriever:
    """Dense retrieval using sentence transformers"""
    
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is required for dense retrieval")
        
        self.model = SentenceTransformer(model_name)
        self.embeddings_cache = {}
        
    def encode_query(self, query: str) -> List[float]:
        """Encode query to embedding vector"""
        if query in self.embeddings_cache:
            return self.embeddings_cache[query]
        
        embedding = self.model.encode(query, convert_to_numpy=True)
        self.embeddings_cache[query] = embedding
        return embedding.tolist()
    
    def search(self, query_embedding: List[float], corpus_embeddings: List[List[float]], 
               top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Search using cosine similarity
        
        Args:
            query_embedding: Query embedding vector
            corpus_embeddings: List of document embeddings
            top_k: Number of top results to return
            
        Returns:
            List of (doc_index, score) tuples
        """
        import numpy as np
        
        query_vec = np.array(query_embedding)
        corpus_vecs = np.array(corpus_embeddings)
        
        # Calculate cosine similarity
        similarities = np.dot(corpus_vecs, query_vec) / (
            np.linalg.norm(corpus_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-8
        )
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        return [(int(idx), float(similarities[idx])) for idx in top_indices]


class SparseRetriever:
    """Sparse retrieval using BM25"""
    
    def __init__(self):
        if rank_bm25 is None:
            raise ImportError("rank-bm25 is required for sparse retrieval")
        
        self.bm25 = None
        self.documents = []
        self.tokenized_docs = []
        
    def index_documents(self, documents: List[str]):
        """Index documents for BM25"""
        self.documents = documents
        
        # Simple tokenization (same as used in chunking)
        self.tokenized_docs = []
        for doc in documents:
            tokens = self._tokenize(doc)
            self.tokenized_docs.append(tokens)
        
        self.bm25 = rank_bm25.BM25Okapi(self.tokenized_docs)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization matching chunking process"""
        import re
        
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        """
        Search using BM25
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of (doc_index, score) tuples
        """
        if not self.bm25:
            return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        return [(idx, float(scores[idx])) for idx in top_indices if scores[idx] > 0]


class HybridRetriever:
    """
    Hybrid retrieval combining dense and sparse retrieval with RRF
    """
    
    def __init__(self, 
                 chroma_path: Optional[Path] = None,
                 embeddings_path: Optional[Path] = None,
                 collection_name: str = "mutual_fund_faq_phase2"):
        
        # Initialize components
        self.query_normalizer = QueryNormalizer()
        self.scheme_resolver = SchemeResolver()
        
        # Initialize retrievers
        self.dense_retriever = DenseRetriever()
        self.sparse_retriever = SparseRetriever()
        
        # Load corpus and index
        self.chroma_path = chroma_path or Path(__file__).resolve().parents[2] / "ingestion" / "phase-2" / "2.6-indexerr" / "chroma-data"
        self.embeddings_path = embeddings_path or Path(__file__).resolve().parents[2] / "ingestion" / "phase-2" / "2.5-embedder" / "output" / "embeddings-latest.json"
        
        self.collection_name = collection_name
        self.corpus = []
        self.corpus_embeddings = []
        self.corpus_metadata = []
        
        self._load_corpus()
        self._setup_retrievers()
    
    def _load_corpus(self):
        """Load corpus from embeddings file"""
        try:
            with open(self.embeddings_path, 'r', encoding='utf-8') as f:
                embeddings_data = json.load(f)
            
            chunks = embeddings_data.get('chunks', [])
            
            for chunk in chunks:
                self.corpus.append(chunk.get('text', ''))
                self.corpus_embeddings.append(chunk.get('embedding', []))
                self.corpus_metadata.append(chunk.get('metadata', {}))
            
            print(f"Loaded {len(self.corpus)} chunks from corpus")
            
        except Exception as e:
            print(f"Error loading corpus: {e}")
            raise
    
    def _setup_retrievers(self):
        """Setup dense and sparse retrievers"""
        # Setup sparse retriever
        self.sparse_retriever.index_documents(self.corpus)
        
        # Setup dense retriever (corpus embeddings already loaded)
        print("Setup completed for both dense and sparse retrievers")
    
    def _reciprocal_rank_fusion(self, 
                              dense_results: List[Tuple[int, float]], 
                              sparse_results: List[Tuple[int, float]],
                              dense_weight: float = 0.7,
                              sparse_weight: float = 0.3,
                              k: int = 20) -> List[Tuple[int, float]]:
        """
        Weighted Reciprocal Rank Fusion (RRF)
        
        Args:
            dense_results: List of (doc_index, score) from dense retrieval
            sparse_results: List of (doc_index, score) from sparse retrieval
            dense_weight: Weight for dense results
            sparse_weight: Weight for sparse results
            k: RRF parameter (typically 60)
            
        Returns:
            List of (doc_index, fused_score) tuples
        """
        # Create score maps
        dense_scores = {}
        sparse_scores = {}
        
        # Rank dense results (1-based ranking)
        for rank, (doc_idx, score) in enumerate(dense_results, 1):
            dense_scores[doc_idx] = dense_weight / (k + rank)
        
        # Rank sparse results (1-based ranking)
        for rank, (doc_idx, score) in enumerate(sparse_results, 1):
            sparse_scores[doc_idx] = sparse_weight / (k + rank)
        
        # Combine scores
        fused_scores = {}
        all_doc_indices = set(dense_scores.keys()) | set(sparse_scores.keys())
        
        for doc_idx in all_doc_indices:
            fused_score = dense_scores.get(doc_idx, 0) + sparse_scores.get(doc_idx, 0)
            fused_scores[doc_idx] = fused_score
        
        # Sort by fused score (descending)
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_results
    
    def _apply_section_boost(self, 
                           results: List[Tuple[int, float]], 
                           query: str) -> List[Tuple[int, float]]:
        """
        Apply section hint boost based on keyword matching
        
        Args:
            results: List of (doc_index, score) tuples
            query: Normalized query
            
        Returns:
            List of (doc_index, boosted_score) tuples
        """
        query_tokens = set(query.lower().split())
        boosted_results = []
        
        for doc_idx, score in results:
            metadata = self.corpus_metadata[doc_idx]
            section = metadata.get('section_heading', '').lower()
            
            boost = 1.0
            
            # Check for section keyword matches with targeted boosts
            section_tokens = set(section.split())
            overlap = query_tokens.intersection(section_tokens)
            
            if overlap:
                # Targeted section boosts based on mutual fund terminology
                section_boosts = {
                    'expense': 1.3, 'ratio': 1.3,
                    'exit': 1.3, 'load': 1.3,
                    'sip': 1.2, 'systematic': 1.2,
                    'nav': 1.2, 'asset': 1.2,
                    'risk': 1.2, 'rating': 1.2,
                    'lockin': 1.3, 'lock': 1.3, 'period': 1.2
                }
                
                # Calculate boost based on overlap and specific terms
                boost = 1.0
                for token in overlap:
                    for key, value in section_boosts.items():
                        if key in token.lower():
                            boost = max(boost, value)
                
                # Add small overlap boost
                boost_factor = len(overlap) / max(len(query_tokens), 1)
                boost += (boost_factor * 0.1)  # Additional 10% max
            
            boosted_results.append((doc_idx, score * boost))
        
        # Re-sort after boosting
        boosted_results.sort(key=lambda x: x[1], reverse=True)
        return boosted_results
    
    def _filter_by_scheme(self, results: List[Tuple[int, float]], scheme_id: str) -> List[Tuple[int, float]]:
        """
        Filter results by scheme ID
        
        Args:
            results: List of (doc_index, score) tuples
            scheme_id: Scheme ID to filter by
            
        Returns:
            Filtered results
        """
        if not scheme_id:
            return results
        
        filtered_results = []
        for doc_idx, score in results:
            metadata = self.corpus_metadata[doc_idx]
            doc_scheme = metadata.get('scheme', '').lower()
            
            # Simple scheme matching (can be made more sophisticated)
            if scheme_id.lower() in doc_scheme:
                filtered_results.append((doc_idx, score))
        
        return filtered_results
    
    def retrieve(self, 
                query: str, 
                top_k: int = 10,
                scheme_filter: Optional[str] = None,
                dense_weight: float = 0.5,
                sparse_weight: float = 0.5) -> Dict[str, Any]:
        """
        Main retrieval method
        
        Args:
            query: User query
            top_k: Number of top results to return
            scheme_filter: Optional scheme ID to filter by
            dense_weight: Weight for dense retrieval
            sparse_weight: Weight for sparse retrieval
            
        Returns:
            Dictionary with retrieval results and metadata
        """
        # Normalize query
        normalized_query = self.query_normalizer.normalize(query)
        query_features = self.query_normalizer.extract_numeric_features(normalized_query)
        
        # Adjust weights for numeric-heavy queries (optimized for small corpus)
        if query_features['is_numeric_heavy']:
            # Bump sparse weight for exact fact matching
            sparse_weight = min(sparse_weight + 0.3, 0.7)  # Increased boost
            dense_weight = 1.0 - sparse_weight
        else:
            # Default dense-first weights for semantic queries
            dense_weight = 0.7
            sparse_weight = 0.3
        
        # Resolve scheme
        resolved_scheme, scheme_confidence = self.scheme_resolver.resolve_with_confidence(normalized_query)
        if scheme_filter:
            resolved_scheme = {'id': scheme_filter}
            scheme_confidence = 1.0
        
        # Encode query for dense retrieval
        if resolved_scheme and scheme_confidence > 0.7:
            # Use scheme name + query for better alignment
            scheme_name = resolved_scheme.get('name', '')
            enhanced_query = f"{scheme_name}\n{normalized_query}"
        else:
            enhanced_query = normalized_query
        
        query_embedding = self.dense_retriever.encode_query(enhanced_query)
        
        # Determine effective top_k for each channel (optimized for small corpus)
        effective_top_k = min(10, len(self.corpus))
        
        # Dense retrieval
        dense_results = self.dense_retriever.search(
            query_embedding, 
            self.corpus_embeddings, 
            top_k=effective_top_k
        )
        
        # Sparse retrieval
        sparse_results = self.sparse_retriever.search(
            normalized_query, 
            top_k=effective_top_k
        )
        
        # Apply scheme-first filtering for small corpus
        if resolved_scheme and scheme_confidence >= 0.8:
            # High confidence scheme: search only scheme-specific chunks (8-13 docs)
            scheme_id = resolved_scheme.get('id', '')
            dense_results = self._filter_by_scheme(dense_results, scheme_id)
            sparse_results = self._filter_by_scheme(sparse_results, scheme_id)
            # Reduce top_k for scheme-specific search
            effective_top_k = min(5, len(dense_results), len(sparse_results))
        elif resolved_scheme:
            # Medium confidence: apply filter but with fallback
            scheme_id = resolved_scheme.get('id', '')
            filtered_dense = self._filter_by_scheme(dense_results, scheme_id)
            filtered_sparse = self._filter_by_scheme(sparse_results, scheme_id)
            
            # If filter removes all results, relax and use full corpus
            if len(filtered_dense) == 0 and len(filtered_sparse) == 0:
                print(f"Scheme filter removed all results, relaxing to full corpus")
                # Use original results without filtering
            else:
                dense_results = filtered_dense
                sparse_results = filtered_sparse
        
        # Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            dense_weight, 
            sparse_weight
        )
        
        # Apply section boost
        boosted_results = self._apply_section_boost(fused_results, normalized_query)
        
        # Take top-k results
        final_results = boosted_results[:top_k]
        
        # Prepare result documents
        retrieved_docs = []
        for doc_idx, score in final_results:
            retrieved_docs.append({
                'text': self.corpus[doc_idx],
                'metadata': self.corpus_metadata[doc_idx],
                'score': score,
                'doc_index': doc_idx
            })
        
        return {
            'query': query,
            'normalized_query': normalized_query,
            'retrieved_docs': retrieved_docs,
            'resolved_scheme': resolved_scheme,
            'scheme_confidence': scheme_confidence,
            'query_features': query_features,
            'retrieval_weights': {
                'dense': dense_weight,
                'sparse': sparse_weight
            },
            'intermediate_results': {
                'dense_count': len(dense_results),
                'sparse_count': len(sparse_results),
                'fused_count': len(fused_results)
            }
        }


def main():
    """Test hybrid retriever"""
    try:
        retriever = HybridRetriever()
        
        test_queries = [
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "ELSS tax saver fund lock-in period",
            "NAV of HDFC Equity Fund",
            "Exit load for focused fund",
            "0.45% expense ratio which fund?",
        ]
        
        print("Hybrid Retriever Test:")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = retriever.retrieve(query, top_k=3)
            
            print(f"Normalized: {result['normalized_query']}")
            if result['resolved_scheme']:
                print(f"Scheme: {result['resolved_scheme']['name']} (confidence: {result['scheme_confidence']:.3f})")
            print(f"Query features: {result['query_features']}")
            print(f"Retrieval weights: {result['retrieval_weights']}")
            
            print(f"\nTop {len(result['retrieved_docs'])} results:")
            for i, doc in enumerate(result['retrieved_docs'], 1):
                print(f"{i}. Score: {doc['score']:.4f}")
                print(f"   Text: {doc['text'][:100]}...")
                print(f"   Scheme: {doc['metadata'].get('scheme', 'Unknown')}")
                print()
            
            print("-" * 50)
            
    except Exception as e:
        print(f"Error testing hybrid retriever: {e}")
        print("Make sure all dependencies are installed and corpus is available")


if __name__ == "__main__":
    main()
