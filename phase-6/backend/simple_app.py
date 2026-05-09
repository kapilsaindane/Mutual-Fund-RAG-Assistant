#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add retrieval system to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retrieval" / "phase-5"))

# Simple mock orchestrator for testing
class MockOrchestrator:
    def __init__(self):
        self.use_groq = os.environ.get('USE_GROQ', '').lower() == 'true'
        self.hybrid_retriever = True  # Mock
    
    def process_query(self, query, show_steps=False, save_logs=False):
        # Mock response for testing
        return {
            'success': True,
            'response': f'This is a mock response for: "{query}". Source: https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth\n\nLast updated from sources: 2026-05-05',
            'method': 'groq' if self.use_groq else 'extractive',
            'metadata': {
                'source_url': 'https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth',
                'last_updated': '2026-05-05'
            },
            'processing_steps': ['PII Detection', 'Intent Classification', 'Retrieval', 'Answer Generation', 'Post-Processing']
        }


def create_simple_app():
    """Create simple Flask app for testing"""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])
    
    # Initialize mock orchestrator
    orchestrator = MockOrchestrator()
    app.orchestrator = orchestrator
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': '6.0.0',
            'orchestrator': 'initialized'
        })
    
    @app.route('/api/ui-data', methods=['GET'])
    def get_ui_data():
        return jsonify({
            'welcome_message': 'Welcome to HDFC Mutual Fund Assistant',
            'disclaimer': 'Facts-only. No investment advice.',
            'example_questions': [
                'What is the expense ratio of HDFC Mid Cap Fund?',
                'What is the minimum SIP amount for HDFC Equity Fund?',
                'What is the lock-in period for ELSS Tax Saver Fund?'
            ],
            'system_status': {
                'orchestrator': 'initialized',
                'groq_available': orchestrator.use_groq,
                'retrieval_available': True
            }
        })
    
    @app.route('/api/query', methods=['POST'])
    def process_query():
        try:
            data = request.get_json()
            if not data or 'query' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Missing query in request body',
                    'response': '',
                    'method': 'error'
                }), 400
            
            query = data.get('query', '').strip()
            if not query:
                return jsonify({
                    'success': False,
                    'error': 'Empty query',
                    'response': '',
                    'method': 'error'
                }), 400
            
            # Process query using mock orchestrator
            result = orchestrator.process_query(query)
            
            # Format UI data
            ui_data = {
                'type': 'factual',
                'source_url': result['metadata']['source_url'],
                'last_updated': result['metadata']['last_updated'],
                'processing_steps': result['processing_steps']
            }
            
            response_data = {
                'success': result['success'],
                'response': result['response'],
                'method': result['method'],
                'metadata': result['metadata'],
                'ui_data': ui_data
            }
            
            return jsonify(response_data)
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'response': '',
                'method': 'error',
                'ui_data': {
                    'type': 'error',
                    'error_message': str(e)
                }
            }), 500
    
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'name': 'Phase 6 Backend API',
            'version': '6.0.0',
            'description': 'Minimal UI and User Experience Backend',
            'endpoints': {
                'health': '/health',
                'api': '/api',
                'query': '/api/query',
                'ui_data': '/api/ui-data'
            }
        })
    
    return app


if __name__ == '__main__':
    app = create_simple_app()
    
    host = os.environ.get('HOST', 'localhost')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', '').lower() == 'true'
    
    print("Phase 6 Backend Server (Simple)")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"API docs: http://{host}:{port}/api")
    print("=" * 50)
    
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
