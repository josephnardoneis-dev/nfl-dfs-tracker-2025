#!/usr/bin/env python3
"""
Production startup script for NFL DFS Tracker on Render
"""

import os
import sys
from web_interface import app

if __name__ == "__main__":
    # Get port from environment variable (Render provides this)
    port = int(os.environ.get("PORT", 5000))
    
    # Set production configuration
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Run the app
    app.run(host="0.0.0.0", port=port)