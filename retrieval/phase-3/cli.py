#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the retrieval directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from query_normalizer import QueryNormalizer
from scheme_resolver import SchemeResolver
from hybrid_retriever import HybridRetriever
from cross_encoder_reranker import CrossEncoderReranker, ConfidenceGate


class RetrievalCLI:
    """Command-line interface for Phase 3 retrieval system"""
    
    def __init__(self):
        self.query_normalizer = QueryNormalizer()
        self.scheme_resolver = SchemeResolver()
        self.hybrid_retriever = None
        self.reranker = None
        self.confidence_gate = None
        
        self._setup_components()
    
    def _setup_components(self):
        """Setup all retrieval components"""
        try:
            self.hybrid_retriever = HybridRetriever()
            print("✅ Hybrid retriever initialized")
        except Exception as e:
            print(f"❌ Failed to initialize hybrid retriever: {e}")
            sys.exit(1)
        
        try:
            self.reranker = CrossEncoderReranker()
            print("✅ Cross-encoder reranker initialized")
        except Exception as e:
            print(f"❌ Failed to initialize reranker: {e}")
            sys.exit(1)
        
        try:
            self.confidence_gate = ConfidenceGate()
            print("✅ Confidence gate initialized")
        except Exception as e:
            print(f"❌ Failed to initialize confidence gate: {e}")
            sys.exit(1)
    
    def retrieve(self, 
                query: str, 
                top_k: int = 3,
                scheme_filter: str = None,
                show_intermediate: bool = False,
                output_format: str = "json") -> Dict[str, Any]:
        """
        Main retrieval method
        
        Args:
            query: User query
            top_k: Number of top results to return
            scheme_filter: Optional scheme ID to filter by
            show_intermediate: Show intermediate retrieval steps
            output_format: Output format (json, text)
            
        Returns:
            Retrieval results dictionary
        """
        # Step 1: Query Normalization
        normalized_query = self.query_normalizer.normalize(query)
        query_features = self.query_normalizer.extract_numeric_features(normalized_query)
        
        if show_intermediate:
            print(f"🔍 Normalized Query: {normalized_query}")
            print(f"📊 Query Features: {query_features}")
        
        # Step 2: Scheme Resolution
        resolved_scheme, scheme_confidence = self.scheme_resolver.resolve_with_confidence(normalized_query)
        
        if show_intermediate:
            if resolved_scheme:
                print(f"🎯 Resolved Scheme: {resolved_scheme['name']} (confidence: {scheme_confidence:.3f})")
            else:
                print("🎯 No scheme resolved")
        
        # Step 3: Hybrid Retrieval
        retrieval_results = self.hybrid_retriever.retrieve(
            query=normalized_query,
            top_k=10,  # Get more for reranking
            scheme_filter=scheme_filter
        )
        
        if show_intermediate:
            print(f"📚 Retrieved {len(retrieval_results['retrieved_docs'])} candidates")
            print(f"⚖️  Retrieval weights: dense={retrieval_results['retrieval_weights']['dense']:.2f}, sparse={retrieval_results['retrieval_weights']['sparse']:.2f}")
        
        # Step 4: Cross-encoder Reranking
        reranked_docs, confidence_info = self.reranker.rerank_with_confidence(
            query=normalized_query,
            documents=retrieval_results['retrieved_docs'],
            top_k=top_k
        )
        
        if show_intermediate:
            print(f"🔄 Reranked to top {len(reranked_docs)} results")
            print(f"📈 Confidence: top={confidence_info['top_score']:.3f}, margin={confidence_info['margin']:.3f}")
        
        # Step 5: Confidence Gate
        gate_decision = self.confidence_gate.evaluate_confidence(reranked_docs, confidence_info)
        
        if show_intermediate:
            print(f"🚪 Gate Decision: {gate_decision['should_proceed']}")
            print(f"💭 Reason: {gate_decision['reason']}")
        
        # Prepare final results
        final_results = {
            'query': query,
            'normalized_query': normalized_query,
            'query_features': query_features,
            'resolved_scheme': resolved_scheme,
            'scheme_confidence': scheme_confidence,
            'gate_decision': gate_decision,
            'confidence_info': confidence_info,
            'retrieval_stats': retrieval_results.get('intermediate_results', {}),
            'results': reranked_docs if gate_decision['should_proceed'] else []
        }
        
        return final_results
    
    def format_output(self, results: Dict[str, Any], output_format: str = "json") -> str:
        """Format retrieval results for output"""
        if output_format.lower() == "json":
            return json.dumps(results, indent=2, ensure_ascii=False)
        
        elif output_format.lower() == "text":
            output_lines = []
            
            # Query info
            output_lines.append(f"Query: {results['query']}")
            output_lines.append(f"Normalized: {results['normalized_query']}")
            
            # Scheme info
            if results['resolved_scheme']:
                output_lines.append(f"Scheme: {results['resolved_scheme']['name']} (confidence: {results['scheme_confidence']:.3f})")
            else:
                output_lines.append("Scheme: Not resolved")
            
            # Gate decision
            gate = results['gate_decision']
            if gate['should_proceed']:
                output_lines.append(f"Status: ✅ Confident retrieval")
                output_lines.append(f"Results ({len(results['results'])}):")
                
                for i, doc in enumerate(results['results'], 1):
                    output_lines.append(f"\n{i}. Score: {doc['rerank_score']:.3f}")
                    output_lines.append(f"   Text: {doc['text']}")
                    output_lines.append(f"   Scheme: {doc['metadata'].get('scheme', 'Unknown')}")
                    output_lines.append(f"   Section: {doc['metadata'].get('section_heading', 'Unknown')}")
            else:
                output_lines.append(f"Status: ❌ Low confidence")
                output_lines.append(f"Reason: {gate['reason']}")
                output_lines.append("Response: I don't have enough information to answer this question.")
            
            return "\n".join(output_lines)
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("🚀 Phase 3 Retrieval System - Interactive Mode")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'help' for available commands")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n❓ Enter your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                
                if not user_input:
                    continue
                
                # Retrieve and display results
                results = self.retrieve(user_input, show_intermediate=True)
                output = self.format_output(results, "text")
                print("\n" + "=" * 50)
                print(output)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
Available commands:
- Just type your question about HDFC mutual funds
- 'quit' or 'exit': Exit the program
- 'help': Show this help message

Example questions:
- What is the expense ratio of HDFC Mid Cap Fund?
- ELSS tax saver lock-in period?
- Minimum SIP amount for equity fund?
- Exit load for focused fund?
        """
        print(help_text)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Phase 3 Retrieval System - Mutual Fund FAQ Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "What is the expense ratio of HDFC Mid Cap Fund?"
  python cli.py "ELSS lock-in period" --scheme-filter hdfc-elss-tax-saver-fund-direct-plan-growth
  python cli.py --interactive
  python cli.py "NAV details" --output-format text --show-intermediate
        """
    )
    
    parser.add_argument(
        'query', 
        nargs='?', 
        help='Query to process (use quotes for multi-word queries)'
    )
    
    parser.add_argument(
        '--top-k', 
        type=int, 
        default=3,
        help='Number of top results to return (default: 3)'
    )
    
    parser.add_argument(
        '--scheme-filter', 
        type=str,
        help='Filter results by specific scheme ID'
    )
    
    parser.add_argument(
        '--output-format', 
        choices=['json', 'text'], 
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--show-intermediate', 
        action='store_true',
        help='Show intermediate retrieval steps'
    )
    
    parser.add_argument(
        '--interactive', 
        action='store_true',
        help='Run in interactive mode'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    try:
        cli = RetrievalCLI()
    except Exception as e:
        print(f"❌ Failed to initialize retrieval system: {e}")
        sys.exit(1)
    
    # Run in interactive mode
    if args.interactive:
        cli.interactive_mode()
        return
    
    # Need a query if not interactive
    if not args.query:
        print("❌ Query is required when not in interactive mode")
        print("Use --interactive for interactive mode or provide a query")
        parser.print_help()
        sys.exit(1)
    
    # Process single query
    try:
        results = cli.retrieve(
            query=args.query,
            top_k=args.top_k,
            scheme_filter=args.scheme_filter,
            show_intermediate=args.show_intermediate
        )
        
        output = cli.format_output(results, args.output_format)
        print(output)
        
        # Exit with error code if confidence gate blocked
        if not results['gate_decision']['should_proceed']:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error processing query: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
