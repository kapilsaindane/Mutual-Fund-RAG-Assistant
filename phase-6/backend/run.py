#!/usr/bin/env python3

"""
Phase 6 Backend Startup Script

Usage:
    python run.py [--host HOST] [--port PORT] [--debug] [--no-debug]
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment from {env_path}")
else:
    print("⚠️  No .env file found, using environment variables")

from app import create_app


def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description='Phase 6 Backend Server')
    parser.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0'),
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5000)),
                       help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    parser.add_argument('--no-debug', action='store_true',
                       help='Disable debug mode')
    
    args = parser.parse_args()
    
    # Determine debug mode
    debug = args.debug
    if args.no_debug:
        debug = False
    elif os.environ.get('DEBUG', '').lower() == 'true':
        debug = True
    
    # Create Flask app
    app = create_app()
    
    # Print startup information
    print("Phase 6 Backend Server")
    print("=" * 50)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Debug: {debug}")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print(f"API docs: http://{args.host}:{args.port}/api")
    print("=" * 50)
    print(f"Query: http://{args.host}:{args.port}/api/query")
    print(f"UI Data: http://{args.host}:{args.port}/api/ui-data")
    print("=" * 50)
    
    # Start server
    try:
        app.run(host=args.host, port=args.port, debug=debug)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
