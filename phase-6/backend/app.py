#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add retrieval system to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "retrieval" / "phase-5"))

from phase_5.orchestrator import Orchestrator


def create_app(config=None):
    """
    Create Flask application for Phase 6 backend
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Configure app
    if config:
        app.config.update(config)
    
    # Configure logging
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Enable CORS for frontend
    CORS(app, origins=["http://localhost:3000", "http://localhost:8080"])
    
    # Initialize orchestrator
    try:
        use_groq = os.environ.get('USE_GROQ', '').lower() == 'true'
        groq_api_key = os.environ.get('GROQ_API_KEY')
        
        orchestrator = Orchestrator(use_groq=use_groq, groq_api_key=groq_api_key)
        app.logger.info("Orchestrator initialized successfully")
        app.logger.info(f"Using Groq: {orchestrator.use_groq}")
    except Exception as e:
        app.logger.error(f"Failed to initialize orchestrator: {e}")
        orchestrator = None
    
    # Store orchestrator in app context
    app.orchestrator = orchestrator
    
    # Register blueprints
    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'version': '6.0.0',
            'orchestrator': 'initialized' if orchestrator else 'failed'
        })
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with API info"""
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
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': str(error)}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error', 'message': 'Something went wrong'}), 500
    
    return app


if __name__ == '__main__':
    # Run development server
    app = create_app()
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', '').lower() == 'true'
    
    print(f"🚀 Starting Phase 6 Backend Server")
    print(f"🌐 Host: {host}")
    print(f"🚪 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print(f"📊 Health check: http://{host}:{port}/health")
    print(f"📚 API docs: http://{host}:{port}/api")
    
    app.run(host=host, port=port, debug=debug)
