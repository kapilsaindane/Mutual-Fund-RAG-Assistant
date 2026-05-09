#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add retrieval and phase directories to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase_3.hybrid_retriever import HybridRetriever
from phase_4.intent_classifier import IntentClassifier, IntentType
from phase_4.pii_detector import PIIDetector
from phase_4.refusal_composer import RefusalComposer
from phase_4.policy_enforcer import PolicyEnforcer
from phase_5.extractive_generator import ExtractiveGenerator
from phase_5.groq_generator import GroqGenerator
from phase_5.post_processor import PostProcessor


class Orchestrator:
    """
    Main orchestrator for Phase 4 (Guardrails) + Phase 5 (Answer Generation)
    Coordinates all phases from query to final compliant response
    """
    
    def __init__(self, 
                 use_groq: Optional[bool] = None,
                 groq_api_key: Optional[str] = None):
        """
        Initialize orchestrator
        
        Args:
            use_groq: Force Groq usage (None = auto)
            groq_api_key: Override API key
        """
        # Initialize all components
        self.intent_classifier = IntentClassifier()
        self.pii_detector = PIIDetector()
        self.refusal_composer = RefusalComposer()
        self.policy_enforcer = PolicyEnforcer()
        self.extractive_generator = ExtractiveGenerator()
        self.groq_generator = GroqGenerator(api_key=groq_api_key)
        self.post_processor = PostProcessor()
        
        # Initialize retrieval
        try:
            self.hybrid_retriever = HybridRetriever()
            print("✅ Hybrid retriever initialized")
        except Exception as e:
            print(f"❌ Failed to initialize hybrid retriever: {e}")
            self.hybrid_retriever = None
        
        # Determine Groq usage
        if use_groq is not None:
            self.use_groq = use_groq
        else:
            self.use_groq = self.groq_generator.is_groq_available()
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Main query processing pipeline
        
        Args:
            query: User query string
            
        Returns:
            Complete processing result
        """
        print(f"🚀 Processing query: {query}")
        print(f"🤖 Using Groq: {self.use_groq}")
        
        result = {
            'query': query,
            'success': False,
            'response': '',
            'method': '',
            'metadata': {},
            'error': None,
            'processing_steps': []
        }
        
        try:
            # Step 1: PII Detection
            print("🔍 Step 1: PII Detection")
            result['processing_steps'].append("PII Detection")
            
            pii_info = self.pii_detector.detect_pii(query)
            
            if pii_info['has_pii']:
                print(f"🚫 PII detected (confidence: {pii_info['confidence']:.2f})")
                
                # PII block response (no URL)
                pii_block = self.pii_detector.get_pii_block_template(pii_info)
                
                result.update({
                    'success': True,
                    'response': pii_block,
                    'method': 'pii_block',
                    'metadata': {
                        'pii_detected': True,
                        'pii_types': pii_info['pii_types'],
                        'confidence': pii_info['confidence']
                    }
                })
                return result
            
            print("✅ No PII detected")
            
            # Step 2: Intent Classification
            print("🎯 Step 2: Intent Classification")
            result['processing_steps'].append("Intent Classification")
            
            # Get query features from normalizer
            query_features = self.hybrid_retriever.query_normalizer.extract_numeric_features(query) if self.hybrid_retriever else {}
            
            classification = self.intent_classifier.classify_intent(query, query_features)
            
            print(f"Intent: {classification['intent'].value} (confidence: {classification['confidence']:.2f})")
            
            # Step 3: Retrieval (only for factual queries)
            if classification['intent'] != IntentType.FACTUAL_ALLOWED:
                print("📋 Non-factual intent - skipping retrieval")
                result['processing_steps'].append("Non-factual intent - no retrieval")
                
                # Step 4: Refusal Composition
                print("✍ Step 4: Refusal Composition")
                result['processing_steps'].append("Refusal Composition")
                
                refusal = self.refusal_composer.compose_refusal(
                    intent=classification['intent'],
                    confidence=classification['confidence'],
                    resolved_scheme=classification.get('resolved_scheme')
                )
                
                result.update({
                    'success': True,
                    'response': refusal['response'],
                    'method': 'refusal',
                    'metadata': {
                        'intent': classification['intent'].value,
                        'confidence': classification['confidence'],
                        'educational_url': refusal['educational_url'],
                        'type': refusal['type']
                    }
                })
                return result
            
            print("✅ Factual intent - proceeding with retrieval")
            
            # Step 3: Retrieval
            print("📚 Step 3: Retrieval")
            result['processing_steps'].append("Retrieval")
            
            if not self.hybrid_retriever:
                raise RuntimeError("Hybrid retriever not available")
            
            retrieval_result = self.hybrid_retriever.retrieve(query, top_k=3)
            
            if not retrieval_result.get('retrieved_docs'):
                print("📭 No documents retrieved")
                result['processing_steps'].append("No documents retrieved")
                
                # Step 5: Don't Know Response
                print("🤷 Step 5: Don't Know Response")
                result['processing_steps'].append("Don't Know Response")
                
                dont_know = self.refusal_composer.compose_dont_know(
                    query=query,
                    resolved_scheme=retrieval_result.get('resolved_scheme')
                )
                
                result.update({
                    'success': True,
                    'response': dont_know['response'],
                    'method': 'dont_know',
                    'metadata': {
                        'retrieval_confidence': retrieval_result.get('confidence_info', {}),
                        'scheme_hint': dont_know.get('scheme_hint'),
                        'type': dont_know['type']
                    }
                })
                return result
            
            print(f"✅ Retrieved {len(retrieval_result['retrieved_docs'])} documents")
            print(f"📊 Retrieval confidence: {retrieval_result.get('confidence_info', {}).get('top_score', 0):.3f}")
            
            # Step 4: Answer Generation
            print("✍ Step 4: Answer Generation")
            result['processing_steps'].append("Answer Generation")
            
            # Get source URL and last updated date
            top_chunk = retrieval_result['retrieved_docs'][0] if retrieval_result['retrieved_docs'] else {}
            source_url = top_chunk.get('metadata', {}).get('source_url', '')
            last_updated = top_chunk.get('metadata', {}).get('source_date', '')
            
            # Generate answer using appropriate method
            if self.use_groq:
                print("🤖 Using Groq for answer generation")
                generation_result = self.groq_generator.generate_answer(
                    query=query,
                    retrieved_chunks=retrieval_result['retrieved_docs'],
                    source_url=source_url,
                    last_updated=last_updated
                )
            else:
                print("📝 Using extractive generation")
                generation_result = self.extractive_generator.generate_extractive_answer(
                    top_chunk=top_chunk,
                    source_url=source_url,
                    last_updated=last_updated
                )
            
            if not generation_result.get('success', False):
                print(f"❌ Answer generation failed: {generation_result.get('error', 'Unknown error')}")
                result.update({
                    'success': False,
                    'response': '',
                    'method': generation_result.get('method', 'unknown'),
                    'error': generation_result.get('error', 'Answer generation failed'),
                    'metadata': {
                        'generation_error': generation_result.get('error', 'Unknown')
                    }
                })
                return result
            
            print(f"✅ Answer generated using {generation_result['method']}")
            result['response'] = generation_result['answer']
            result['method'] = generation_result['method']
            
            # Step 5: Post-Processing
            print("🔍 Step 5: Post-Processing")
            result['processing_steps'].append("Post-Processing")
            
            post_process_result = self.post_processor.process_response(
                response_text=generation_result['answer'],
                source_url=source_url,
                expected_intent="factual"
            )
            
            result['response'] = post_process_result['processed_response']
            result['metadata'].update(post_process_result['metadata'])
            
            if not post_process_result['is_compliant']:
                print(f"⚠️ Post-processing violations detected")
                result['metadata']['compliance_violations'] = post_process_result['violations']
                result['metadata']['corrections'] = post_process_result['corrections']
            
            print("✅ Processing complete")
            result['success'] = True
            result['metadata']['final_method'] = generation_result['method']
            
        except Exception as e:
            print(f"❌ Processing error: {e}")
            result.update({
                'success': False,
                'response': '',
                'error': str(e),
                'method': 'error',
                'metadata': {'error': str(e)}
            })
        
        return result
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and capabilities"""
        return {
            'components': {
                'intent_classifier': 'initialized',
                'pii_detector': 'initialized',
                'refusal_composer': 'initialized',
                'policy_enforcer': 'initialized',
                'extractive_generator': 'initialized',
                'groq_generator': self.groq_generator.get_model_info(),
                'post_processor': 'initialized',
                'hybrid_retriever': 'initialized' if self.hybrid_retriever else 'failed'
            },
            'configuration': {
                'use_groq': self.use_groq,
                'groq_available': self.groq_generator.is_groq_available()
            },
            'capabilities': {
                'query_classification': True,
                'pii_detection': True,
                'retrieval': self.hybrid_retriever is not None,
                'extractive_generation': True,
                'groq_generation': self.use_groq,
                'post_processing': True
            }
        }
    
    def explain_decision_flow(self, query: str) -> str:
        """Generate explanation of decision flow for a query"""
        explanation = f"Query: {query}\n\n"
        explanation += "Decision Flow:\n"
        explanation += "1. PII Detection → "
        
        # Simulate PII detection
        pii_info = self.pii_detector.detect_pii(query)
        if pii_info['has_pii']:
            explanation += f"PII DETECTED (confidence: {pii_info['confidence']:.2f})\n"
            explanation += "2. Intent Classification → SKIPPED\n"
            explanation += "3. Retrieval → SKIPPED\n"
            explanation += "4. Answer Generation → PII BLOCK\n"
            explanation += "5. Post-Processing → PII BLOCK\n"
            explanation += f"Result: PII Block Response\n"
        else:
            explanation += "NO PII\n"
            explanation += "2. Intent Classification → "
            
            # Simulate intent classification
            query_features = self.hybrid_retriever.query_normalizer.extract_numeric_features(query) if self.hybrid_retriever else {}
            classification = self.intent_classifier.classify_intent(query, query_features)
            
            explanation += f"{classification['intent'].value} (confidence: {classification['confidence']:.2f})\n"
            
            if classification['intent'] != IntentType.FACTUAL_ALLOWED:
                explanation += "3. Retrieval → SKIPPED\n"
                explanation += "4. Answer Generation → REFUSAL\n"
                explanation += "5. Post-Processing → REFUSAL\n"
                explanation += f"Result: Refusal Response\n"
            else:
                explanation += "3. Retrieval → PROCEED\n"
                explanation += "4. Answer Generation → "
                explanation += "Groq" if self.use_groq else "Extractive"
                explanation += "\n"
                explanation += "5. Post-Processing → COMPLIANCE CHECK\n"
                explanation += f"Result: Factual Response\n"
        
        return explanation


def main():
    """Test orchestrator"""
    orchestrator = Orchestrator()
    
    test_queries = [
        # PII test
        "My PAN is ABCDE1234F and I want to invest",
        
        # Factual test
        "What is the expense ratio of HDFC Mid Cap Fund?",
        
        # Advisory test
        "Should I invest in HDFC Equity Fund?",
        
        # Comparison test
        "Which fund is better: HDFC Mid Cap or HDFC Focused Fund?",
        
        # Prediction test
        "Will HDFC Mid Cap Fund perform well next year?"
    ]
    
    print("Orchestrator Test:")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        result = orchestrator.process_query(query)
        
        print(f"Success: {result['success']}")
        print(f"Method: {result['method']}")
        print(f"Response: {result['response'][:150]}...")
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        
        if result['metadata'].get('compliance_violations'):
            print(f"Violations: {', '.join(result['metadata']['compliance_violations'])}")
        
        print(f"Processing Steps: {' → '.join(result['processing_steps'])}")
        print("-" * 60)


if __name__ == "__main__":
    main()
