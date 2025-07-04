import json
import os
from supabase import create_client
from flask import Flask, request, jsonify, send_from_directory
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Check environment variables at startup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing required environment variables")
    if not SUPABASE_URL:
        logger.error("SUPABASE_URL is not set")
    if not SUPABASE_KEY:
        logger.error("SUPABASE_KEY is not set")
    
    @app.route('/api/test', methods=['GET'])
    def test_supabase():
        return jsonify({
            "success": False,
            "error": "Missing required environment variables",
            "details": {
                "SUPABASE_URL": "Set in Vercel environment variables",
                "SUPABASE_KEY": "Set in Vercel environment variables"
            }
        }), 500
    
    # Initialize with dummy client to prevent immediate failure
    supabase = create_client("", "")
else:
    # Initialize Supabase client
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info(f"Supabase client initialized with URL: {SUPABASE_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        
        @app.route('/api/test', methods=['GET'])
        def test_supabase():
            return jsonify({
                "success": False,
                "error": "Failed to initialize Supabase client",
                "details": str(e)
            }), 500
        
        # Initialize with dummy client to prevent immediate failure
        supabase = create_client("", "")

# Serve static files from templates directory
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    try:
        logger.info(f"Serving static file: {path}")
        
        # First try to serve from templates directory
        try:
            return send_from_directory('../templates', path)
        except Exception as e:
            logger.error(f"Error serving from templates: {str(e)}")
            
        # If not found in templates, try static directory
        try:
            return send_from_directory('../static', path)
        except Exception as e:
            logger.error(f"Error serving from static: {str(e)}")
            
        # If not found in either directory, return 404
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error serving static file: {str(e)}")
        return jsonify({"error": "File not found"}), 404

@app.route('/api/test', methods=['GET'])
def test_supabase():
    try:
        logger.info("Testing Supabase connection")
        # Test by querying the users table
        result = supabase.table('users').select('*').limit(1).execute()
        logger.info("Supabase test successful")
        return jsonify({"success": True, "data": result.data})
    except Exception as e:
        logger.error(f"Supabase test failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        logger.info("Processing login request")
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # Your login logic here
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        logger.info("Processing signup request")
        data = request.get_json()
        # Your signup logic here
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Signup failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    logger.error(f"404 error: {str(e)}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"500 error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
