"""
Phase 3 - Retrieval Layer

Given a user query, surface the minimum set of chunks needed to answer factually
using hybrid retrieval with cross-encoder re-ranking.
"""

from .query_normalizer import QueryNormalizer
from .scheme_resolver import SchemeResolver
from .hybrid_retriever import HybridRetriever
from .cross_encoder_reranker import CrossEncoderReranker, ConfidenceGate

__all__ = [
    'QueryNormalizer',
    'SchemeResolver', 
    'HybridRetriever',
    'CrossEncoderReranker',
    'ConfidenceGate'
]

__version__ = '3.0.0'
