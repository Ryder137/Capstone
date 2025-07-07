import json
import os
from supabase import create_client
from flask import Flask, request, jsonify, send_from_directory
import logging
from functools import wraps
import jwt

# Initialize Flask app
app = Flask(__name__)

# Admin authentication decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get the token from headers
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({"success": False, "error": "Missing authorization token"}), 401

            # Verify the token with Supabase
            try:
                user = supabase.auth.get_user(token.replace('Bearer ', ''))
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                return jsonify({"success": False, "error": "Invalid token"}), 401

            # Check if user is admin
            user_data = supabase.table('users').select('is_admin').eq('id', user['user']['id']).single().execute()
            if not user_data['data'] or not user_data['data']['is_admin']:
                return jsonify({"success": False, "error": "Admin access required"}), 403

            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Admin authentication failed: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    return decorated_function

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
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        # Authenticate user with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.get('error'):
            logger.error(f"Login failed: {response['error']['message']}")
            return jsonify({"success": False, "error": response['error']['message']}), 401

        # Get user data
        user = supabase.auth.get_user(response['session']['access_token'])
        user_id = user['user']['id']
        
        # Check admin status using the admins table
        admin_check = supabase.table('admins').select('id').eq('id', user_id).single().execute()
        is_admin = admin_check['data'] is not None
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['user']['id'],
                "email": user['user']['email'],
                "is_admin": is_admin
            }
        })
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    try:
        logger.info("Processing signup request")
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        is_admin = data.get('is_admin', False)  # Admin creation should be controlled
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        # Create user in Supabase
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if response.get('error'):
            logger.error(f"Signup failed: {response['error']['message']}")
            return jsonify({"success": False, "error": response['error']['message']}), 400

        # Create user profile with admin status
        user_id = response['user']['id']
        supabase.table('users').insert({
            'id': user_id,
            'email': email,
            'is_admin': is_admin
        }).execute()

        return jsonify({
            "success": True,
            "user": {
                "id": user_id,
                "email": email,
                "is_admin": is_admin
            }
        })
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
