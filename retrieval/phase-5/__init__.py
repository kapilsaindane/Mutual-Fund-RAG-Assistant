"""
Phase 5 - Controlled Answer Generation

Purpose: Turn a query + retrieved chunks into a compliant, ≤3-sentence answer — or a refusal — with URL policy enforced before anything is returned.
"""

from .extractive_generator import ExtractiveGenerator
from .groq_generator import GroqGenerator
from .post_processor import PostProcessor
from .orchestrator import Orchestrator

__all__ = [
    'ExtractiveGenerator',
    'GroqGenerator', 
    'PostProcessor',
    'Orchestrator'
]

__version__ = '5.0.0'
