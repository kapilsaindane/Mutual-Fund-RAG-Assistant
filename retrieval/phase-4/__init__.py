"""
Phase 4 - Query Classification and Policy Guardrails

Purpose: Turn a query + retrieved chunks into a compliant, ≤3-sentence answer — or a refusal — with URL policy enforced before anything is returned.
"""

from .intent_classifier import IntentClassifier
from .pii_detector import PIIDetector
from .refusal_composer import RefusalComposer
from .policy_enforcer import PolicyEnforcer

__all__ = [
    'IntentClassifier',
    'PIIDetector', 
    'RefusalComposer',
    'PolicyEnforcer'
]

__version__ = '4.0.0'
