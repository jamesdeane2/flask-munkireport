#!/usr/bin/env python3
"""Development server runner."""

import sys
from src.flask_munkireport.app import create_app

if __name__ == "__main__":
    app = create_app()
    
    # Get config
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)
    
    print(f"Starting Flask MunkiReport API on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Database: {app.config.get('DATABASE_PATH')}")
    print(f"\nEndpoints available at http://{host}:{port}/api/v1/")
    
    app.run(host=host, port=port, debug=debug)
