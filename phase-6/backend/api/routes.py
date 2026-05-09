#!/usr/bin/env python3

import logging
from flask import request, jsonify, current_app
from . import api_bp


@api_bp.route('/', methods=['GET'])
def api_info():
    """API information endpoint"""
    return jsonify({
        'name': 'Phase 6 Backend API',
        'version': '6.0.0',
        'description': 'Minimal UI and User Experience Backend',
        'endpoints': {
            'query': '/api/query',
            'ui_data': '/api/ui-data',
            'health': '/health'
        },
        'methods': {
            'query': 'POST - Process user query',
            'ui_data': 'GET - Get UI configuration data',
            'health': 'GET - Health check'
        }
    })


@api_bp.route('/query', methods=['POST'])
def process_query():
    """
    Process user query through complete Phase 3-5 system
    
    Request body:
    {
        "query": "What is the expense ratio of HDFC Mid Cap Fund?",
        "method": "auto|extractive|groq",  # optional
        "show_steps": false,  # optional
        "save_logs": false   # optional
    }
    
    Response:
    {
        "success": true,
        "response": "Answer text...",
        "method": "groq",
        "metadata": {...},
        "ui_data": {
            "type": "factual|refusal|dont_know|error",
            "source_url": "https://...",
            "last_updated": "2026-05-05",
            "processing_steps": [...]
        }
    }
    """
    try:
        # Get orchestrator from app context
        orchestrator = current_app.orchestrator
        if not orchestrator:
            return jsonify({
                'success': False,
                'error': 'Orchestrator not initialized',
                'response': '',
                'method': 'error'
            }), 500
        
        # Parse request
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing query in request body',
                'response': '',
                'method': 'error'
            }), 400
        
        query = data.get('query', '').strip()
        method = data.get('method', 'auto')
        show_steps = data.get('show_steps', False)
        save_logs = data.get('save_logs', False)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Empty query',
                'response': '',
                'method': 'error'
            }), 400
        
        current_app.logger.info(f"Processing query: {query}")
        
        # Process query through orchestrator
        result = orchestrator.process_query(query, show_steps=show_steps, save_logs=save_logs)
        
        # Format response for UI
        ui_data = format_ui_response(result)
        
        response_data = {
            'success': result.get('success', False),
            'response': result.get('response', ''),
            'method': result.get('method', 'unknown'),
            'metadata': result.get('metadata', {}),
            'ui_data': ui_data
        }
        
        if result.get('error'):
            response_data['error'] = result['error']
        
        current_app.logger.info(f"Query processed: {result.get('method', 'unknown')}")
        
        return jsonify(response_data)
    
    except Exception as e:
        current_app.logger.error(f"Query processing error: {e}")
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


@api_bp.route('/ui-data', methods=['GET'])
def get_ui_data():
    """
    Get UI configuration data for the frontend
    
    Response:
    {
        "welcome_message": "Welcome to HDFC Mutual Fund Assistant",
        "disclaimer": "Facts-only. No investment advice.",
        "example_questions": [
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "What is the minimum SIP amount for HDFC Equity Fund?",
            "What is the lock-in period for ELSS Tax Saver Fund?"
        ],
        "system_status": {
            "orchestrator": "initialized",
            "groq_available": true,
            "retrieval_available": true
        }
    }
    """
    try:
        orchestrator = current_app.orchestrator
        
        # Get system status
        system_status = {
            'orchestrator': 'initialized' if orchestrator else 'failed',
            'groq_available': orchestrator.use_groq if orchestrator else False,
            'retrieval_available': orchestrator.hybrid_retriever is not None if orchestrator else False
        }
        
        ui_data = {
            'welcome_message': 'Welcome to HDFC Mutual Fund Assistant',
            'disclaimer': 'Facts-only. No investment advice.',
            'example_questions': [
                'What is the expense ratio of HDFC Mid Cap Fund?',
                'What is the minimum SIP amount for HDFC Equity Fund?',
                'What is the lock-in period for ELSS Tax Saver Fund?'
            ],
            'system_status': system_status
        }
        
        current_app.logger.info("UI data requested")
        
        return jsonify(ui_data)
    
    except Exception as e:
        current_app.logger.error(f"UI data error: {e}")
        return jsonify({
            'error': 'Failed to get UI data',
            'message': str(e)
        }), 500


def format_ui_response(result):
    """
    Format orchestrator result for UI consumption
    
    Args:
        result: Orchestrator processing result
        
    Returns:
        UI-formatted response data
    """
    ui_data = {
        'type': 'unknown',
        'source_url': None,
        'last_updated': None,
        'processing_steps': result.get('processing_steps', [])
    }
    
    # Determine response type
    method = result.get('method', '')
    response = result.get('response', '')
    metadata = result.get('metadata', {})
    
    if method == 'pii_block':
        ui_data['type'] = 'pii_block'
    elif method in ['refusal', 'advisory_refuse', 'comparison_refuse', 'prediction_refuse']:
        ui_data['type'] = 'refusal'
    elif method == 'dont_know':
        ui_data['type'] = 'dont_know'
    elif method in ['extractive', 'groq', 'extractive_fallback']:
        ui_data['type'] = 'factual'
        # Extract source URL and last updated from response
        ui_data['source_url'] = metadata.get('source_url') or extract_url_from_response(response)
        ui_data['last_updated'] = metadata.get('last_updated') or extract_date_from_response(response)
    elif method == 'error':
        ui_data['type'] = 'error'
        ui_data['error_message'] = result.get('error', 'Unknown error')
    
    return ui_data


def extract_url_from_response(response):
    """Extract source URL from response text"""
    import re
    url_pattern = r'https?://[^\s<>"\')]+'
    urls = re.findall(url_pattern, response)
    return urls[0] if urls else None


def extract_date_from_response(response):
    """Extract last updated date from response text"""
    import re
    date_pattern = r'Last updated from sources:\s*(\d{4}-\d{2}-\d{2})'
    match = re.search(date_pattern, response)
    return match.group(1) if match else None
