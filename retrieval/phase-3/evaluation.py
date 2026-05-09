#!/usr/bin/env python3

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cli import RetrievalCLI


class RetrievalEvaluator:
    """Evaluation framework for Phase 3 retrieval system"""
    
    def __init__(self):
        self.cli = RetrievalCLI()
        self.eval_set = self._load_eval_set()
    
    def _load_eval_set(self) -> List[Dict[str, Any]]:
        """Load evaluation set with 30 questions"""
        return [
            # HDFC Mid Cap Fund questions
            {
                "id": 1,
                "query": "What is the expense ratio of HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["expense ratio", "0.45%", "fees"],
                "difficulty": "easy"
            },
            {
                "id": 2,
                "query": "What is the minimum SIP amount for HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth", 
                "expected_keywords": ["sip", "100", "minimum"],
                "difficulty": "easy"
            },
            {
                "id": 3,
                "query": "What is the risk level of HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["risk", "very high risk"],
                "difficulty": "easy"
            },
            {
                "id": 4,
                "query": "What is the 3-year return of HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["3y", "annualised", "23.69%"],
                "difficulty": "medium"
            },
            {
                "id": 5,
                "query": "What is the AUM of HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["aum", "85,357.92", "fund size"],
                "difficulty": "medium"
            },
            {
                "id": 6,
                "query": "What is the NAV of HDFC Mid Cap Fund?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["nav", "218.53", "04 may"],
                "difficulty": "medium"
            },
            
            # HDFC Equity Fund questions
            {
                "id": 7,
                "query": "What is the expense ratio of HDFC Equity Fund?",
                "expected_scheme": "HDFC Equity Fund Direct Growth",
                "expected_keywords": ["expense ratio", "fees"],
                "difficulty": "easy"
            },
            {
                "id": 8,
                "query": "Minimum SIP investment for HDFC Equity Fund",
                "expected_scheme": "HDFC Equity Fund Direct Growth",
                "expected_keywords": ["sip", "minimum", "investment"],
                "difficulty": "easy"
            },
            {
                "id": 9,
                "query": "Risk rating of HDFC Equity Fund",
                "expected_scheme": "HDFC Equity Fund Direct Growth",
                "expected_keywords": ["risk", "rating"],
                "difficulty": "easy"
            },
            {
                "id": 10,
                "query": "HDFC Equity Fund performance 1 year",
                "expected_scheme": "HDFC Equity Fund Direct Growth",
                "expected_keywords": ["1y", "1 year", "returns", "performance"],
                "difficulty": "medium"
            },
            
            # HDFC Focused Fund questions
            {
                "id": 11,
                "query": "What is the exit load for HDFC Focused Fund?",
                "expected_scheme": "HDFC Focused Fund Direct Growth",
                "expected_keywords": ["exit load", "withdrawal", "fees"],
                "difficulty": "easy"
            },
            {
                "id": 12,
                "query": "Minimum investment amount HDFC Focused Fund",
                "expected_scheme": "HDFC Focused Fund Direct Growth",
                "expected_keywords": ["minimum", "investment", "amount"],
                "difficulty": "easy"
            },
            {
                "id": 13,
                "query": "HDFC Focused Fund risk level",
                "expected_scheme": "HDFC Focused Fund Direct Growth",
                "expected_keywords": ["risk", "level"],
                "difficulty": "easy"
            },
            {
                "id": 14,
                "query": "3 year returns HDFC Focused Fund",
                "expected_scheme": "HDFC Focused Fund Direct Growth",
                "expected_keywords": ["3 year", "3y", "returns"],
                "difficulty": "medium"
            },
            
            # HDFC ELSS Tax Saver Fund questions
            {
                "id": 15,
                "query": "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
                "expected_scheme": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                "expected_keywords": ["lock-in", "lockin", "3 years", "tax"],
                "difficulty": "easy"
            },
            {
                "id": 16,
                "query": "ELSS tax saving benefits HDFC fund",
                "expected_scheme": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                "expected_keywords": ["tax", "saving", "benefits", "80c"],
                "difficulty": "medium"
            },
            {
                "id": 17,
                "query": "Minimum SIP for ELSS tax saver fund",
                "expected_scheme": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                "expected_keywords": ["sip", "minimum", "elss"],
                "difficulty": "easy"
            },
            {
                "id": 18,
                "query": "Expense ratio HDFC ELSS fund",
                "expected_scheme": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                "expected_keywords": ["expense ratio", "fees"],
                "difficulty": "easy"
            },
            
            # HDFC Large Cap Fund questions
            {
                "id": 19,
                "query": "What is the expense ratio of HDFC Large Cap Fund?",
                "expected_scheme": "HDFC Large Cap Fund Direct Growth",
                "expected_keywords": ["expense ratio", "fees"],
                "difficulty": "easy"
            },
            {
                "id": 20,
                "query": "Minimum investment HDFC Large Cap Fund",
                "expected_scheme": "HDFC Large Cap Fund Direct Growth",
                "expected_keywords": ["minimum", "investment"],
                "difficulty": "easy"
            },
            {
                "id": 21,
                "query": "Risk profile HDFC Large Cap Fund",
                "expected_scheme": "HDFC Large Cap Fund Direct Growth",
                "expected_keywords": ["risk", "profile"],
                "difficulty": "easy"
            },
            {
                "id": 22,
                "query": "1 year returns HDFC Large Cap Fund",
                "expected_scheme": "HDFC Large Cap Fund Direct Growth",
                "expected_keywords": ["1 year", "1y", "returns"],
                "difficulty": "medium"
            },
            
            # Comparative and specific questions
            {
                "id": 23,
                "query": "Which HDFC fund has the lowest expense ratio?",
                "expected_scheme": None,  # Could be multiple
                "expected_keywords": ["expense ratio", "lowest", "comparison"],
                "difficulty": "hard"
            },
            {
                "id": 24,
                "query": "What is the minimum SIP amount across all HDFC funds?",
                "expected_scheme": None,  # Could be multiple
                "expected_keywords": ["sip", "minimum", "all funds"],
                "difficulty": "medium"
            },
            {
                "id": 25,
                "query": "Exit load charges for HDFC mutual funds",
                "expected_scheme": None,  # Could be multiple
                "expected_keywords": ["exit load", "charges", "fees"],
                "difficulty": "medium"
            },
            
            # Numeric and specific queries
            {
                "id": 26,
                "query": "What fund has 0.45% expense ratio?",
                "expected_scheme": "HDFC Mid-Cap Fund Direct Growth",
                "expected_keywords": ["0.45%", "expense ratio"],
                "difficulty": "medium"
            },
            {
                "id": 27,
                "query": "Fund with Rs 100 minimum SIP",
                "expected_scheme": None,  # Could be multiple
                "expected_keywords": ["rs 100", "minimum sip"],
                "difficulty": "medium"
            },
            {
                "id": 28,
                "query": "NAV value as of May 4 2026",
                "expected_scheme": None,  # Could be multiple
                "expected_keywords": ["nav", "may 4", "2026"],
                "difficulty": "hard"
            },
            
            # Edge cases
            {
                "id": 29,
                "query": "Tax benefits of ELSS investment",
                "expected_scheme": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
                "expected_keywords": ["tax", "benefits", "elss", "deduction"],
                "difficulty": "medium"
            },
            {
                "id": 30,
                "query": "Risk rating comparison mid cap vs large cap",
                "expected_scheme": None,  # Comparative
                "expected_keywords": ["risk", "rating", "comparison", "mid cap", "large cap"],
                "difficulty": "hard"
            }
        ]
    
    def evaluate_single_query(self, eval_item: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single query"""
        query = eval_item['query']
        
        try:
            # Get retrieval results
            results = self.cli.retrieve(query, show_intermediate=False)
            
            # Evaluation metrics
            evaluation = {
                'query_id': eval_item['id'],
                'query': query,
                'expected_scheme': eval_item['expected_scheme'],
                'expected_keywords': eval_item['expected_keywords'],
                'difficulty': eval_item['difficulty'],
                'timestamp': datetime.now().isoformat(),
                'retrieval_success': False,
                'scheme_correct': False,
                'keywords_found': [],
                'top_result_relevant': False,
                'confidence_adequate': False,
                'gate_passed': False,
                'num_results': 0,
                'top_score': 0.0,
                'errors': []
            }
            
            # Check if retrieval succeeded
            if results and 'gate_decision' in results:
                evaluation['gate_passed'] = results['gate_decision']['should_proceed']
                evaluation['confidence_adequate'] = results['gate_decision']['should_proceed']
                
                if results['gate_decision']['should_proceed'] and results.get('results'):
                    evaluation['retrieval_success'] = True
                    evaluation['num_results'] = len(results['results'])
                    
                    if results['results']:
                        top_result = results['results'][0]
                        evaluation['top_score'] = top_result.get('rerank_score', 0.0)
                        
                        # Check scheme correctness
                        resolved_scheme = results.get('resolved_scheme')
                        if resolved_scheme and eval_item['expected_scheme']:
                            if eval_item['expected_scheme'].lower() in resolved_scheme.get('name', '').lower():
                                evaluation['scheme_correct'] = True
                        
                        # Check keyword relevance
                        top_text = top_result.get('text', '').lower()
                        found_keywords = []
                        for keyword in eval_item['expected_keywords']:
                            if keyword.lower() in top_text:
                                found_keywords.append(keyword)
                        evaluation['keywords_found'] = found_keywords
                        
                        # Determine relevance (at least 50% keywords found)
                        if len(found_keywords) >= len(eval_item['expected_keywords']) * 0.5:
                            evaluation['top_result_relevant'] = True
            
            return evaluation
            
        except Exception as e:
            return {
                'query_id': eval_item['id'],
                'query': query,
                'error': str(e),
                'retrieval_success': False,
                'errors': [str(e)]
            }
    
    def run_evaluation(self, output_file: str = None) -> Dict[str, Any]:
        """Run full evaluation on all 30 questions"""
        print("🚀 Starting Phase 3 Retrieval Evaluation")
        print(f"📊 Evaluating {len(self.eval_set)} questions")
        print("=" * 60)
        
        results = []
        success_count = 0
        scheme_correct_count = 0
        confidence_adequate_count = 0
        
        for i, eval_item in enumerate(self.eval_set, 1):
            print(f"📝 Question {i}/{len(self.eval_set)}: {eval_item['query'][:60]}...")
            
            evaluation = self.evaluate_single_query(eval_item)
            results.append(evaluation)
            
            if evaluation['retrieval_success']:
                success_count += 1
                print(f"   ✅ Success (Score: {evaluation['top_score']:.3f})")
            else:
                print(f"   ❌ Failed")
            
            if evaluation['scheme_correct']:
                scheme_correct_count += 1
                
            if evaluation['confidence_adequate']:
                confidence_adequate_count += 1
            
            # Show progress
            if i % 5 == 0:
                current_success_rate = success_count / i * 100
                print(f"📈 Current success rate: {current_success_rate:.1f}%")
        
        # Calculate overall metrics
        total_questions = len(self.eval_set)
        success_rate = success_count / total_questions * 100
        scheme_accuracy = scheme_correct_count / total_questions * 100
        confidence_rate = confidence_adequate_count / total_questions * 100
        
        # Calculate difficulty breakdown
        difficulty_stats = {}
        for difficulty in ['easy', 'medium', 'hard']:
            diff_results = [r for r in results if r.get('difficulty') == difficulty]
            if diff_results:
                diff_success = sum(1 for r in diff_results if r['retrieval_success'])
                difficulty_stats[difficulty] = {
                    'total': len(diff_results),
                    'success': diff_success,
                    'rate': diff_success / len(diff_results) * 100
                }
        
        # Final evaluation report
        report = {
            'evaluation_timestamp': datetime.now().isoformat(),
            'total_questions': total_questions,
            'overall_metrics': {
                'success_rate': success_rate,
                'scheme_accuracy': scheme_accuracy,
                'confidence_adequacy': confidence_rate,
                'successful_retrievals': success_count,
                'failed_retrievals': total_questions - success_count
            },
            'difficulty_breakdown': difficulty_stats,
            'exit_criteria_met': success_rate >= 85.0,
            'detailed_results': results
        }
        
        # Display summary
        print("\n" + "=" * 60)
        print("📊 EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Questions: {total_questions}")
        print(f"Successful Retrievals: {success_count}")
        print(f"Overall Success Rate: {success_rate:.1f}%")
        print(f"Scheme Accuracy: {scheme_accuracy:.1f}%")
        print(f"Confidence Adequacy: {confidence_rate:.1f}%")
        print(f"Exit Criteria (≥85%): {'✅ MET' if report['exit_criteria_met'] else '❌ NOT MET'}")
        
        print("\n📈 Difficulty Breakdown:")
        for difficulty, stats in difficulty_stats.items():
            print(f"  {difficulty.capitalize()}: {stats['success']}/{stats['total']} ({stats['rate']:.1f}%)")
        
        # Save report
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Detailed report saved to: {output_path}")
        
        return report
    
    def analyze_failures(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze failed retrievals for insights"""
        failed_results = [r for r in report['detailed_results'] if not r['retrieval_success']]
        
        failure_analysis = {
            'total_failures': len(failed_results),
            'failure_reasons': {},
            'difficulty_failures': {},
            'scheme_resolution_failures': 0,
            'confidence_gate_failures': 0,
            'no_results_failures': 0
        }
        
        for failure in failed_results:
            # Difficulty breakdown
            difficulty = failure.get('difficulty', 'unknown')
            failure_analysis['difficulty_failures'][difficulty] = failure_analysis['difficulty_failures'].get(difficulty, 0) + 1
            
            # Reason breakdown
            if not failure.get('gate_passed', False):
                failure_analysis['confidence_gate_failures'] += 1
                reason = failure.get('gate_decision', {}).get('reason', 'unknown')
                failure_analysis['failure_reasons'][reason] = failure_analysis['failure_reasons'].get(reason, 0) + 1
            elif failure.get('num_results', 0) == 0:
                failure_analysis['no_results_failures'] += 1
            
            if not failure.get('scheme_correct', False):
                failure_analysis['scheme_resolution_failures'] += 1
        
        return failure_analysis


def main():
    """Main evaluation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase 3 Retrieval Evaluation")
    parser.add_argument(
        '--output', 
        default='retrieval/phase-3/output/evaluation-report.json',
        help='Output file for evaluation report'
    )
    parser.add_argument(
        '--analyze-failures',
        action='store_true',
        help='Analyze failure patterns in detail'
    )
    
    args = parser.parse_args()
    
    try:
        evaluator = RetrievalEvaluator()
        report = evaluator.run_evaluation(args.output)
        
        if args.analyze_failures:
            print("\n🔍 FAILURE ANALYSIS")
            print("=" * 40)
            failure_analysis = evaluator.analyze_failures(report)
            
            print(f"Total Failures: {failure_analysis['total_failures']}")
            print(f"Confidence Gate Failures: {failure_analysis['confidence_gate_failures']}")
            print(f"No Results Failures: {failure_analysis['no_results_failures']}")
            print(f"Scheme Resolution Failures: {failure_analysis['scheme_resolution_failures']}")
            
            print("\nFailure by Difficulty:")
            for difficulty, count in failure_analysis['difficulty_failures'].items():
                print(f"  {difficulty}: {count}")
            
            print("\nFailure Reasons:")
            for reason, count in failure_analysis['failure_reasons'].items():
                print(f"  {reason}: {count}")
        
        # Exit with appropriate code
        sys.exit(0 if report['exit_criteria_met'] else 1)
        
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
