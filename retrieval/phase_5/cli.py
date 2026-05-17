#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from phase_3.hybrid_retriever import HybridRetriever
from phase_4.intent_classifier import IntentClassifier, IntentType
from phase_4.pii_detector import PIIDetector
from phase_4.refusal_composer import RefusalComposer
from phase_4.policy_enforcer import PolicyEnforcer
from phase_5.extractive_generator import ExtractiveGenerator
from phase_5.groq_generator import GroqGenerator
from phase_5.post_processor import PostProcessor
from phase_5.orchestrator import Orchestrator


class RetrievalCLI:
    """Complete CLI interface for Phase 3-5 system"""
    
    def __init__(self, use_groq: bool = None, groq_api_key: str = None):
        """
        Initialize complete retrieval system
        
        Args:
            use_groq: Force Groq usage (None = auto)
            groq_api_key: Override API key
        """
        self.orchestrator = Orchestrator(use_groq=use_groq, groq_api_key=groq_api_key)
        print("🚀 Complete Retrieval System Initialized")
        print(f"🤖 Using Groq: {self.orchestrator.use_groq}")
    
    def process_query(self, query: str, 
                   show_steps: bool = False,
                   output_format: str = "json",
                   save_logs: bool = False) -> Dict[str, Any]:
        """
        Process a complete query through all phases
        
        Args:
            query: User query string
            show_steps: Show intermediate processing steps
            output_format: Output format (json/text)
            save_logs: Save processing logs to file
            
        Returns:
            Complete processing result
        """
        print(f"🔍 Processing query: {query}")
        
        # Process through orchestrator
        result = self.orchestrator.process_query(query, show_steps=show_steps)
        
        # Format output
        if output_format.lower() == "json":
            output_text = json.dumps(result, indent=2, ensure_ascii=False)
        else:
            output_text = self._format_text_output(result)
        
        print(f"\n{'='*60}")
        print(output_text)
        
        # Save logs if requested
        if save_logs:
            self._save_processing_log(query, result)
        
        return result
    
    def _format_text_output(self, result: Dict[str, Any]) -> str:
        """Format result as human-readable text"""
        output_lines = []
        
        # Query info
        output_lines.append(f"Query: {result['query']}")
        output_lines.append(f"Method: {result.get('method', 'unknown')}")
        output_lines.append(f"Success: {result.get('success', False)}")
        
        # Response
        response = result.get('response', '')
        if response:
            output_lines.append(f"\nResponse:")
            output_lines.append(f"{response}")
        else:
            error = result.get('error', 'Unknown error')
            output_lines.append(f"\nError: {error}")
        
        # Metadata
        metadata = result.get('metadata', {})
        if metadata:
            output_lines.append(f"\nMetadata:")
            for key, value in metadata.items():
                if key == 'processing_steps':
                    output_lines.append(f"  Steps: {' → '.join(value)}")
                else:
                    output_lines.append(f"  {key}: {value}")
        
        return '\n'.join(output_lines)
    
    def _save_processing_log(self, query: str, result: Dict[str, Any]):
        """Save processing log to file"""
        try:
            logs_dir = Path(__file__).resolve().parent / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = logs_dir / f"processing_{timestamp}.json"
            
            log_entry = {
                'timestamp': __import__('datetime').datetime.now().isoformat(),
                'query': query,
                'result': result
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2)
            
            print(f"📝 Processing log saved to: {log_file}")
            
        except Exception as e:
            print(f"⚠️  Failed to save processing log: {e}")
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("🚀 Complete Retrieval System - Interactive Mode")
        print("Type 'quit' or 'exit' to stop")
        print("Type 'help' for available commands")
        print("=" * 60)
        
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
                
                # Process query
                result = self.process_query(user_input, show_steps=True)
                
                if result.get('success'):
                    print(f"✅ Query processed successfully")
                else:
                    print(f"❌ Query processing failed")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
📚 Complete Retrieval System Help

🔍 QUERY PROCESSING:
  Just type your question about HDFC mutual funds
  Examples:
    • "What is the expense ratio of HDFC Mid Cap Fund?"
    • "What is the minimum SIP amount?"
    • "ELSS tax saver fund lock-in period"
    • "Risk rating of HDFC Focused Fund"

⚙️  AVAILABLE OPTIONS:
  --method METHOD           Choose generation method (extractive/groq/auto)
  --output FORMAT         Output format (json/text)
  --show-steps           Show all processing steps
  --save-logs           Save processing logs to file
  --use-groq            Force Groq usage
  --no-groq              Force extractive-only mode

🎯  PROCESSING FLOW:
  Query → PII Detection → Intent Classification → Retrieval → Answer Generation → Policy Enforcement

🛡️  SAFETY FEATURES:
  • PII detection and blocking
  • Intent classification (factual/advisory/comparison/prediction)
  • URL policy enforcement (exactly one whitelisted URL)
  • Banned token detection
  • Sentence count limits (≤3 sentences)
  • Post-processing validation

💡  TIPS:
  • For factual questions, the system will retrieve relevant information
  • For advisory/comparative questions, you'll get educational responses
  • PII (PAN, Aadhaar, etc.) will be blocked for security
  • All responses include source URLs when available
        """
        print(help_text)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get complete system status"""
        return self.orchestrator.get_system_status()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Complete Retrieval System - Phase 3-5 Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single query
  python retrieval/phase-5/cli.py "What is the expense ratio of HDFC Mid Cap Fund?"
  
  # With options
  python retrieval/phase-5/cli.py "ELSS lock-in period" --show-steps --output-format text
  
  # Interactive mode
  python retrieval/phase-5/cli.py --interactive
  
  # Force Groq usage
  python retrieval/phase-5/cli.py "NAV details" --use-groq --save-logs
        """
    )
    
    parser.add_argument(
        'query',
        nargs='?',
        help='Query to process (use quotes for multi-word queries)'
    )
    
    parser.add_argument(
        '--method',
        choices=['extractive', 'groq', 'auto'],
        default='auto',
        help='Answer generation method (default: auto)'
    )
    
    parser.add_argument(
        '--output-format',
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--show-steps',
        action='store_true',
        help='Show detailed processing steps'
    )
    
    parser.add_argument(
        '--save-logs',
        action='store_true',
        help='Save processing logs to file'
    )
    
    parser.add_argument(
        '--use-groq',
        action='store_true',
        help='Force Groq usage (overrides auto-detection)'
    )
    
    parser.add_argument(
        '--no-groq',
        action='store_true',
        help='Force extractive-only mode (no Groq)'
    )
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show system status'
    )
    
    args = parser.parse_args()
    
    # Handle conflicting Groq options
    if args.use_groq and args.no_groq:
        parser.error("Cannot specify both --use-groq and --no-groq")
    
    # Initialize CLI
    try:
        use_groq = args.use_groq if args.use_groq else (not args.no_groq if args.no_groq else None)
        cli = RetrievalCLI(use_groq=use_groq, groq_api_key=None)
        
        # Show system status
        if args.status:
            status = cli.get_system_status()
            print("🔧 System Status:")
            print(json.dumps(status, indent=2))
            return
        
        # Run interactive mode
        if args.interactive:
            cli.interactive_mode()
            return
        
        # Need a query for single processing
        if not args.query:
            parser.error("Query is required when not in interactive mode")
            parser.print_help()
            return
        
        # Process single query
        result = cli.process_query(
            query=args.query,
            show_steps=args.show_steps,
            output_format=args.output_format,
            save_logs=args.save_logs
        )
        
        # Exit with appropriate code
        sys.exit(0 if result.get('success', False) else 1)
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
