#!/usr/bin/env python3

"""
Phase 6 Frontend Development Server

Simple HTTP server for development and testing of the frontend.
"""

import os
import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import urlparse


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom handler with CORS support for development"""
    
    def end_headers(self):
        # Add CORS headers for development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """Custom logging"""
        if '/favicon.ico' not in format:
            print(f"[{self.log_date_time_string()}] {format % args}")


def find_free_port(start_port=8080, max_attempts=10):
    """Find a free port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with TCPServer(("", port), None) as s:
                if s.socket.getsockname()[1] == port:
                    return port
        except OSError:
            continue
    return None


def main():
    """Main development server function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 6 Frontend Development Server')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port to run the server on (default: 8080)')
    parser.add_argument('--host', default='localhost',
                       help='Host to bind to (default: localhost)')
    parser.add_argument('--open', action='store_true',
                       help='Open browser automatically')
    parser.add_argument('--directory', default='.',
                       help='Directory to serve (default: current directory)')
    
    args = parser.parse_args()
    
    # Change to the specified directory
    if args.directory != '.':
        os.chdir(args.directory)
    
    # Find a free port if the specified port is taken
    port = args.port
    if not find_free_port(port, 1):
        print(f"Port {port} is already in use, finding an alternative...")
        port = find_free_port(port + 1)
        if not port:
            print("Could not find a free port")
            sys.exit(1)
        print(f"Using port {port}")
    
    # Create server
    try:
        server = HTTPServer((args.host, port), CustomHTTPRequestHandler)
        
        print("🚀 Phase 6 Frontend Development Server")
        print("=" * 50)
        print(f"🌐 Server: http://{args.host}:{port}")
        print(f"📁 Directory: {os.path.abspath(args.directory)}")
        print(f"🔧 CORS: Enabled for development")
        print("=" * 50)
        print("Press Ctrl+C to stop the server")
        print()
        
        # Open browser if requested
        if args.open:
            url = f"http://{args.host}:{port}"
            print(f"🌐 Opening browser: {url}")
            webbrowser.open(url)
        
        # Start server
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
