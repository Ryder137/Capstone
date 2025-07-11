from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, make_response
import json
from datetime import datetime, timezone, timedelta
import random
import os
import requests  # Added missing import
import csv
import io
from dotenv import load_dotenv
from supabase import create_client, Client
from flask_wtf.csrf import CSRFProtect, generate_csrf
from config import SUPABASE_URL, SUPABASE_KEY
import google.generativeai as genai
from database import Database
from functools import wraps
from routes.plants import plants_bp

def login_required(f):
    """
    Decorator to ensure a user is logged in.
    If not logged in, redirects to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session['user'].get('id'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator to ensure a user is admin.
    If not admin, redirects to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session['user'].get('is_admin'):
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY', 'your-csrf-secret-key-here')
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour in seconds

# Add custom filters to Jinja2
import markupsafe
from datetime import datetime

# Escape JavaScript strings
app.jinja_env.filters['escapejs'] = lambda s: markupsafe.Markup(json.dumps(str(s))[1:-1])

# Format datetime objects
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if value is None:
        return ''
    if isinstance(value, str):
        # Try to parse the string into a datetime object
        try:
            # Handle ISO format strings
            if 'T' in value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            else:
                # Handle other date string formats if needed
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return value
    return value.strftime(format)

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Add CSRF token to all templates
@app.after_request
def add_csrf_token(response):
    if 'text/html' in response.content_type:
        response.set_cookie('csrf_token', generate_csrf())
    return response

# Initialize Supabase clients
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Initialize Supabase clients with service role for admin operations
if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError("Missing required Supabase configuration. Please check your environment variables.")

# Initialize main Supabase client for regular operations
app.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
if hasattr(app.supabase, 'postgrest'):
    app.supabase.postgrest.auth(SUPABASE_KEY)
    if hasattr(app.supabase.postgrest, 'session'):
        app.supabase.postgrest.session.timeout = 30  # 30 seconds timeout

# Initialize admin Supabase client with service role for admin operations
app.supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
if hasattr(app.supabase_admin, 'postgrest'):
    app.supabase_admin.postgrest.auth(SUPABASE_SERVICE_ROLE_KEY)
    if hasattr(app.supabase_admin.postgrest, 'session'):
        app.supabase_admin.postgrest.session.timeout = 30  # 30 seconds timeout

# Initialize service role client for admin operations
service_role_supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
if hasattr(service_role_supabase, 'postgrest'):
    service_role_supabase.postgrest.auth(SUPABASE_SERVICE_ROLE_KEY)
    if hasattr(service_role_supabase.postgrest, 'session'):
        service_role_supabase.postgrest.session.timeout = 30  # 30 seconds timeout

# Set Google API Key
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Initialize database
db = Database()

# Import API blueprints
from api.admin_api import admin_bp as admin_api_bp

# Register blueprints
app.register_blueprint(plants_bp, url_prefix='')
app.register_blueprint(admin_api_bp, url_prefix='/api')

# Set global supabase client
supabase = app.supabase

# Test Supabase connection
def test_supabase_connection():
    try:
        # Test by querying the users table
        result = supabase.table('users').select('*').limit(1).execute()
        return True, result.data
    except Exception as e:
        return False, str(e)

# Sample data for doctors (keeping existing data structure)
doctors_data = [
    {
        'id': 1,
        'name': 'Dr. Sarah Johnson',
        'specialty': 'Psychology',
        'rating': 4.9,
        'experience': '15+ years',
        'availability': 'Mon-Fri 9AM-6PM'
    },
    {
        'id': 2,
        'name': 'Dr. Michael Chen',
        'specialty': 'Psychiatry',
        'rating': 4.8,
        'experience': '12+ years',
        'availability': 'Tue-Sat 10AM-7PM'
    },
    {
        'id': 3,
        'name': 'Dr. Emily Rodriguez',
        'specialty': 'Clinical Psychology',
        'rating': 4.9,
        'experience': '10+ years',
        'availability': 'Mon-Thu 8AM-5PM'
    }
]

# Big Five Personality Assessment Questions (50 items)
# Using a 5-point Likert scale for all questions
# Categories: openness, conscientiousness, extraversion, agreeableness, neuroticism

assessment_questions = [
    # Openness (1-10)
    {
        'id': 1,
        'question': 'I am someone who is original, comes up with new ideas.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 2,
        'question': 'I am curious about many different things.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 3,
        'question': 'I am quick to understand things.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 4,
        'question': 'I have a rich vocabulary.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 5,
        'question': 'I have a vivid imagination.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 6,
        'question': 'I have excellent ideas.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 7,
        'question': 'I spend time reflecting on things.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 8,
        'question': 'I use difficult words.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 9,
        'question': 'I am full of ideas.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    {
        'id': 10,
        'question': 'I am fascinated by patterns and abstract ideas.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'openness'
    },
    
    # Conscientiousness (11-20)
    {
        'id': 11,
        'question': 'I am always prepared.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 12,
        'question': 'I pay attention to details.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 13,
        'question': 'I get chores done right away.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 14,
        'question': 'I like order and organization.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 15,
        'question': 'I follow a schedule.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 16,
        'question': 'I am exacting in my work.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'conscientiousness'
    },
    {
        'id': 17,
        'question': 'I leave my belongings around. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'conscientiousness'
    },
    {
        'id': 18,
        'question': 'I make a mess of things. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'conscientiousness'
    },
    {
        'id': 19,
        'question': 'I often forget to put things back in their proper place. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'conscientiousness'
    },
    {
        'id': 20,
        'question': 'I shirk my duties. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'conscientiousness'
    },
    
    # Extraversion (21-30)
    {
        'id': 21,
        'question': 'I am the life of the party.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'extraversion'
    },
    {
        'id': 22,
        'question': 'I feel comfortable around people.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'extraversion'
    },
    {
        'id': 23,
        'question': 'I start conversations.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'extraversion'
    },
    {
        'id': 24,
        'question': 'I talk to a lot of different people at parties.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'extraversion'
    },
    {
        'id': 25,
        'question': 'I don\'t mind being the center of attention.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'extraversion'
    },
    {
        'id': 26,
        'question': 'I am quiet around strangers. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'extraversion'
    },
    {
        'id': 27,
        'question': 'I don\'t like to draw attention to myself. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'extraversion'
    },
    {
        'id': 28,
        'question': 'I don\'t talk a lot. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'extraversion'
    },
    {
        'id': 29,
        'question': 'I have little to say. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'extraversion'
    },
    {
        'id': 30,
        'question': 'I keep in the background. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'extraversion'
    },
    
    # Agreeableness (31-40)
    {
        'id': 31,
        'question': 'I am interested in people.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 32,
        'question': 'I sympathize with others\' feelings.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 33,
        'question': 'I have a soft heart.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 34,
        'question': 'I take time out for others.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 35,
        'question': 'I feel others\' emotions.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 36,
        'question': 'I make people feel at ease.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'agreeableness'
    },
    {
        'id': 37,
        'question': 'I am not interested in other people\'s problems. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'agreeableness'
    },
    {
        'id': 38,
        'question': 'I am not really interested in others. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'agreeableness'
    },
    {
        'id': 39,
        'question': 'I feel little concern for others. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'agreeableness'
    },
    {
        'id': 40,
        'question': 'I insult people. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'agreeableness'
    },
    
    # Neuroticism (41-50)
    {
        'id': 41,
        'question': 'I get stressed out easily.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 42,
        'question': 'I worry about things.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 43,
        'question': 'I am easily disturbed.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 44,
        'question': 'I get upset easily.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 45,
        'question': 'I change my mood a lot.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 46,
        'question': 'I have frequent mood swings.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 47,
        'question': 'I get irritated easily.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 48,
        'question': 'I often feel blue.',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [1, 2, 3, 4, 5],
        'category': 'neuroticism'
    },
    {
        'id': 49,
        'question': 'I am relaxed most of the time. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'neuroticism'
    },
    {
        'id': 50,
        'question': 'I seldom feel blue. (R)',
        'options': ['Strongly Disagree', 'Disagree', 'Neutral', 'Agree', 'Strongly Agree'],
        'scores': [5, 4, 3, 2, 1],  # Reverse scored
        'category': 'neuroticism'
    }
]

# Mental health games
mental_games = [
    {
        'id': 1,
        'name': 'Memory Match',
        'description': 'Improve your memory and concentration with this card matching game',
        'icon': 'bi-brain',
        'type': 'memory'
    },
    {
        'id': 2,
        'name': 'Number Puzzle',
        'description': 'Challenge your mind with number sequencing puzzles',
        'icon': 'bi-grid-3x3',
        'type': 'puzzle'
    },
    {
        'id': 3,
        'name': 'Word Association',
        'description': 'Enhance cognitive flexibility with word association exercises',
        'icon': 'bi-chat-square-text',
        'type': 'cognitive'
    },
    {
        'id': 4,
        'name': 'Pattern Recognition',
        'description': 'Train your brain to recognize and complete patterns',
        'icon': 'bi-diagram-3',
        'type': 'pattern'
    }
]

@app.route('/')
def index():
    return render_template('index.html', active_page='index')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If it's a POST request, handle the login
    if request.method == 'POST':
        return login_post()
    # If it's a GET request, show the login form
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('login'))
    
    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        # Handle the response properly based on the Supabase client version
        if hasattr(response, 'error') and response.error:
            flash(str(response.error), 'error')
            return redirect(url_for('login'))
            
        # Get user data - handle both response formats
        user = response.user if hasattr(response, 'user') else response.get('user')
        
        if not user:
            flash('Authentication failed. User not found.', 'error')
            return redirect(url_for('login'))
        
        # Check admin status using the users table
        user_data = supabase.table('users').select('is_admin,full_name').eq('id', user.id).execute()
        
        # Handle the response format
        if hasattr(user_data, 'data'):
            user_data = user_data.data
        elif hasattr(user_data, 'data') and hasattr(user_data.data, 'data'):
            user_data = user_data.data.data
            
        is_admin = user_data and len(user_data) > 0 and user_data[0].get('is_admin', False)
        full_name = user_data[0].get('full_name', '') if user_data and len(user_data) > 0 else ''
        
        # Store user data in session
        session['user'] = {
            'id': user.id,
            'email': user.email,
            'name': full_name or email.split('@')[0],
            'is_admin': is_admin
        }
        
        flash('Welcome back!', 'success')
        if is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        flash('Authentication failed. Please check your credentials and try again.', 'error')
        return redirect(url_for('login'))
        return redirect(url_for('login'))

@app.route('/test-supabase')
def test_supabase():
    """Test Supabase connection"""
    try:
        # Test by querying the users table
        result = supabase.table('users').select('*').limit(1).execute()
        return jsonify({
            'status': 'success',
            'message': 'Connected to Supabase successfully!',
            'data': result.data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Supabase connection failed: {str(e)}'
        }), 500

@app.route('/signup', methods=['POST'])
def signup_post():
    print("Signup request received")
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        print(f"Form data - Name: {name}, Email: {email}")
        
        # Validation
        if not all([name, email, password, confirm_password]):
            print("Validation failed: Missing required fields")
            flash('Please fill in all fields.', 'error')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            print("Validation failed: Passwords do not match")
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))
        
        if len(password) < 6:
            print("Validation failed: Password too short")
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('signup'))
        
        # 1. Create user in Supabase Auth and users table
        try:
            print("Checking if user already exists...")
            existing_user = supabase.table('users').select('*').eq('email', email).execute()
            
            if hasattr(existing_user, 'error') and existing_user.error:
                print(f"Error checking existing user: {existing_user.error}")
                
            if existing_user.data and len(existing_user.data) > 0:
                print(f"User with email {email} already exists")
                flash('Email already registered. Please use a different email or login.', 'error')
                return redirect(url_for('signup'))
            
            print("Creating user in Supabase Auth...")
            auth_response = supabase.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': {
                        'full_name': name,
                        'email': email
                    }
                }
            })
            
            print(f"Auth response: {auth_response}")
            
            if hasattr(auth_response, 'error') and auth_response.error:
                error_message = str(auth_response.error)
                print(f"Auth error: {error_message}")
                flash(f'Registration failed: {error_message}', 'error')
                return redirect(url_for('signup'))
            
            # Get the user from the response
            user = auth_response.user if hasattr(auth_response, 'user') else None
            print(f"User object from auth: {user}")
            
            if not user:
                print("No user object in auth response")
                flash('Registration failed: Could not create user', 'error')
                return redirect(url_for('signup'))
                
            # 2. Create user profile in users table
            user_data = {
                'id': user.id,
                'email': email,
                'full_name': name,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            print(f"Inserting user data into users table: {user_data}")
            
            try:
                # Try to insert the user, or update if they already exist
                # Use service role client to bypass RLS
                if not service_role_supabase:
                    raise Exception('Service role key not configured')
                    
                result = service_role_supabase.table('users').upsert(user_data).execute()
                print(f"Upsert result: {result}")
                
                # If we get here, the user was either created or updated successfully
                
            except Exception as db_error:
                print(f"Database error: {str(db_error)}")
                if 'duplicate key' in str(db_error).lower():
                    # User already exists in the database, so just log them in
                    print(f"User {user.id} already exists in users table, proceeding with login")
                else:
                    # Some other database error occurred
                    print(f"Error inserting into users table: {str(db_error)}")
                    # If user creation in users table fails, delete the auth user to keep them in sync
                    try:
                        print(f"Attempting to delete auth user {user.id} due to failed profile creation")
                        delete_result = supabase.auth.admin.delete_user(user.id)
                        print(f"Delete auth user result: {delete_result}")
                    except Exception as delete_error:
                        print(f"Error deleting auth user: {str(delete_error)}")
                    
                    flash('Failed to create user profile. Please try again.', 'error')
                    return redirect(url_for('signup'))
            
            # 3. Log the user in
            session['user'] = {
                'id': user.id,
                'email': email,
                'name': name,
                'is_admin': False
            }
            
            print(f"User {email} created and logged in successfully")
            flash(f'Account created successfully! Welcome to UniCare, {name}!', 'success')
            return redirect(url_for('index'))
            
        except Exception as auth_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error during signup process: {str(auth_error)}\n{error_trace}")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('signup'))
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Unexpected error during signup: {str(e)}\n{error_trace}")
        flash('An unexpected error occurred. Please try again.', 'error')
        return redirect(url_for('signup'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/doctors')
def doctors():
    return render_template('doctors.html', doctors=doctors_data)

@app.route('/personality-test')
@app.route('/assessment')  # Keep for backward compatibility
def personality_test():
    """Render the personality test page with error handling for database timeouts."""
    from flask import session as flask_session
    from requests.exceptions import RequestException
    
    user_id = flask_session.get('user', {}).get('id')
    last_test = None
    
    # Only check for admin status if user is logged in
    if user_id:
        try:
            # First check if user is admin
            user_data = db.client.table('users').select('is_admin').eq('id', user_id).execute()
            if user_data.data and user_data.data[0].get('is_admin'):
                flash('Admins cannot take personality tests. Please use a regular user account.', 'error')
                return redirect(url_for('admin_dashboard'))
                
            # Get user's last test date if they're logged in
            try:
                # Use Supabase client directly instead of requests
                result = supabase.table('personality_tests') \
                    .select('created_at') \
                    .eq('user_id', user_id) \
                    .order('created_at', desc=True) \
                    .limit(1) \
                    .execute()
                    
                if result and hasattr(result, 'data') and result.data:
                    last_test = result.data[0].get('created_at')
                    
            except Exception as e:
                print(f"Error fetching last test: {e}")
                
        except Exception as e:
            print(f"Error checking admin status: {e}")
            # Don't block the test if there's an error checking admin status
    
    # Group questions by Big Five personality traits
    categories = {
        'openness': {
            'name': 'Openness',
            'description': 'Measures your openness to new experiences, creativity, and curiosity.',
            'questions': [q for q in assessment_questions if q['category'] == 'openness']
        },
        'conscientiousness': {
            'name': 'Conscientiousness',
            'description': 'Assesses your level of organization, responsibility, and self-discipline.',
            'questions': [q for q in assessment_questions if q['category'] == 'conscientiousness']
        },
        'extraversion': {
            'name': 'Extraversion',
            'description': 'Measures your sociability, talkativeness, and assertiveness.',
            'questions': [q for q in assessment_questions if q['category'] == 'extraversion']
        },
        'agreeableness': {
            'name': 'Agreeableness',
            'description': 'Examines your level of cooperation, kindness, and empathy.',
            'questions': [q for q in assessment_questions if q['category'] == 'agreeableness']
        },
        'neuroticism': {
            'name': 'Neuroticism',
            'description': 'Assesses your emotional stability and tendency toward negative emotions.',
            'questions': [q for q in assessment_questions if q['category'] == 'neuroticism']
        }
    }
    
    return render_template('personality_test.html', 
                         categories=categories, 
                         questions=assessment_questions,  # Still pass all questions for backward compatibility
                         last_test=last_test, 
                         is_authenticated=user_id is not None)
@app.route('/submit-personality-test', methods=['POST'])
def submit_personality_test():
    try:
        from flask import session as flask_session
        
        answers = request.json.get('answers', {})
        user_id = flask_session.get('user', {}).get('id')
        
        print(f"Received answers: {answers}")
        
        # Initialize category scores
        category_scores = {
            'resilience': 0,
            'depression': 0,
            'anxiety': 0,
            'stress': 0
        }
        
        # Map from question categories to score categories
        category_mapping = {
            'openness': 'resilience',
            'conscientiousness': 'resilience',
            'extraversion': 'resilience',
            'agreeableness': 'resilience',
            'neuroticism': 'stress',
            'depression': 'depression',
            'anxiety': 'anxiety'
        }
        
        # Calculate scores for each question
        for question in assessment_questions:
            q_id = str(question['id'])
            if q_id in answers:
                answer_idx = answers[q_id]
                if isinstance(answer_idx, str):
                    answer_idx = int(answer_idx)
                    
                if 0 <= answer_idx < len(question.get('scores', [])):
                    # Get the question's category and map it to a score category
                    question_category = question.get('category')
                    score_category = category_mapping.get(question_category, 'resilience')
                    
                    # Add the score to the appropriate category
                    category_scores[score_category] += question['scores'][answer_idx]
                    
                    print(f"Question {q_id} (category: {question_category} -> {score_category}): "
                          f"answer={answer_idx}, score={question['scores'][answer_idx]}, "
                          f"total {score_category}={category_scores[score_category]}")
        
        print(f"Final category scores: {category_scores}")
        
        # Define maximum possible scores for each category
        max_scores = {
            'resilience': 50,  # 10 questions * max 5 points
            'depression': 35,  # 7 questions * max 5 points
            'anxiety': 35,     # 7 questions * max 5 points
            'stress': 35       # 7 questions * max 5 points
        }
        
        # Calculate normalized scores (0-100 scale)
        # For resilience, higher is better; for others, lower is better
        normalized_scores = {
            'resilience': (category_scores['resilience'] / max_scores['resilience']) * 100,
            'depression': 100 - ((category_scores['depression'] / max_scores['depression']) * 100),
            'anxiety': 100 - ((category_scores['anxiety'] / max_scores['anxiety']) * 100),
            'stress': 100 - ((category_scores['stress'] / max_scores['stress']) * 100)
        }
        
        # Calculate weighted scores with adjusted weights
        weights = {
            'resilience': 0.4,   # 40% weight
            'depression': 0.25,  # 25% weight
            'anxiety': 0.25,     # 25% weight
            'stress': 0.1        # 10% weight (reduced as it's somewhat captured by anxiety)
        }
        
        # Calculate overall score (0-100)
        overall_score = sum(
            normalized_scores[category] * weight 
            for category, weight in weights.items()
        )
        
        # Ensure score is within bounds
        overall_score = max(0, min(100, overall_score))
        
        # Log the scores for debugging
        print(f"Raw scores - Resilience: {category_scores['resilience']}/{max_scores['resilience']}, "
              f"Depression: {category_scores['depression']}/{max_scores['depression']}, "
              f"Anxiety: {category_scores['anxiety']}/{max_scores['anxiety']}, "
              f"Stress: {category_scores['stress']}/{max_scores['stress']}")
        
        print(f"Normalized scores - Resilience: {normalized_scores['resilience']:.1f}%, "
              f"Depression: {normalized_scores['depression']:.1f}%, "
              f"Anxiety: {normalized_scores['anxiety']:.1f}%, "
              f"Stress: {normalized_scores['stress']:.1f}%")
        
        print(f"Overall score: {overall_score:.1f}%")
        
        # Determine level and recommendation based on overall score
        if overall_score >= 80:
            level = 'Exceptional Well-being'
            recommendation = ('Your responses indicate excellent mental well-being with high resilience and low distress levels. '
                            'You demonstrate strong coping skills. Consider sharing your strategies with others or mentoring.')
            color = 'emerald'
        elif overall_score >= 65:
            level = 'Strong Resilience'
            recommendation = ('Your responses suggest strong resilience and good mental well-being. '
                            'You handle challenges effectively. Continue practicing self-care and consider exploring new growth opportunities.')
            color = 'green'
        elif overall_score >= 50:
            level = 'Balanced'
            recommendation = ('Your responses indicate a balanced state with room for growth in some areas. '
                            'You might benefit from additional stress-management techniques or social support.')
            color = 'lime'
        elif overall_score >= 35:
            level = 'Needs Support'
            recommendation = ('Your responses suggest you may be experiencing some challenges. '
                            'Consider reaching out to friends, family, or a mental health professional for support. '
                            'Small, consistent steps can lead to meaningful improvements.')
            color = 'yellow'
        else:
            level = 'Seek Professional Help'
            recommendation = ('Your responses indicate significant distress. Please consider reaching out to a mental health professional '
                            'for support. You don\'t have to go through this alone, and help is available. Contact a counselor or therapist.')
            color = 'red'
            
        # Only save results if user is logged in
        test_id = None
        if user_id:
            try:
                test_data = {
                    'user_id': user_id,
                    'resilience_score': normalized_scores['resilience'],
                    'depression_score': normalized_scores['depression'],
                    'anxiety_score': normalized_scores['anxiety'],
                    'stress_score': normalized_scores['stress'],
                    'overall_score': overall_score,
                    'level': level,
                    'recommendation': recommendation,
                    'answers': answers,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Ensure the table exists and has the correct permissions
                try:
                    result = supabase.table('personality_tests').insert(test_data).execute()
                    if hasattr(result, 'data') and result.data:
                        test_id = result.data[0].get('id')
                    print(f"Test results saved successfully with ID: {test_id}")
                except Exception as e:
                    print(f"Error saving to database: {str(e)}")
                    # Log the full error for debugging
                    import traceback
                    traceback.print_exc()
                    
            except Exception as e:
                print(f"Error preparing test data: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Prepare detailed results for each category
        category_results = {
            'resilience': {
                'score': normalized_scores['resilience'],
                'level': 'High' if normalized_scores['resilience'] >= 70 else 'Moderate' if normalized_scores['resilience'] >= 40 else 'Low'
            },
            'depression': {
                'score': normalized_scores['depression'],
                'level': 'Severe' if normalized_scores['depression'] >= 67 else 'Moderate' if normalized_scores['depression'] >= 34 else 'Mild' if normalized_scores['depression'] > 0 else 'None'
            },
            'anxiety': {
                'score': normalized_scores['anxiety'],
                'level': 'Severe' if normalized_scores['anxiety'] >= 67 else 'Moderate' if normalized_scores['anxiety'] >= 34 else 'Mild' if normalized_scores['anxiety'] > 0 else 'None'
            },
            'stress': {
                'score': normalized_scores['stress'],
                'level': 'Severe' if normalized_scores['stress'] >= 67 else 'Moderate' if normalized_scores['stress'] >= 34 else 'Mild' if normalized_scores['stress'] > 0 else 'None'
            }
        }
        
        # Prepare recommendations list
        recommendations = [
            f"Resilience: Your score indicates {category_results['resilience']['level'].lower()} resilience. " +
            ("Continue building on your strengths." if category_results['resilience']['score'] >= 70 
             else "Consider practicing mindfulness and stress management techniques."),
            
            f"Depression: Your responses suggest {category_results['depression']['level'].lower()} symptoms. " +
            ("This is a positive sign." if category_results['depression']['score'] < 34 
             else "Consider speaking with a mental health professional."),
            
            f"Anxiety: Your responses indicate {category_results['anxiety']['level'].lower()} anxiety levels. " +
            ("This is within a healthy range." if category_results['anxiety']['score'] < 34 
             else "Breathing exercises may help manage these feelings."),
            
            f"Stress: You're experiencing {category_results['stress']['level'].lower()} stress. " +
            ("This is manageable." if category_results['stress']['score'] < 34 
             else "Consider regular breaks and relaxation techniques.")
        ]
        
        # Save to database if user is logged in
        if 'user' in session:
            try:
                # Save the main test result
                test_id = supabase.table('personality_tests').insert({
                    'user_id': session['user']['id'],
                    'resilience_score': normalized_scores['resilience'],
                    'depression_score': normalized_scores['depression'],
                    'anxiety_score': normalized_scores['anxiety'],
                    'stress_score': normalized_scores['stress'],
                    'overall_score': overall_score,
                    'level': level,
                    'recommendation': recommendation,
                    'answers': answers
                }).execute()
                
                print(f"Test results saved with ID: {test_id}")
                
            except Exception as e:
                print(f"Error saving test results: {str(e)}")
                import traceback
                traceback.print_exc()
        
        return jsonify({
            'success': True,
            'overall_score': overall_score,
            'overall_level': level,
            'overall_description': recommendation,
            'resilience': {
                'score': normalized_scores['resilience'],
                'level': category_results['resilience']['level']
            },
            'depression': {
                'score': normalized_scores['depression'],
                'level': category_results['depression']['level']
            },
            'anxiety': {
                'score': normalized_scores['anxiety'],
                'level': category_results['anxiety']['level']
            },
            'stress': {
                'score': normalized_scores['stress'],
                'level': category_results['stress']['level']
            },
            'recommendations': recommendations
        })
        
    except Exception as e:
        print(f"Error processing personality test: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your personality test. Please try again.'}), 500
    
    return jsonify(result)

@app.route('/journal')
@login_required
def journal():
    """Render the journal page with the user's recent entries"""
    try:
        # Get recent journal entries
        entries = db.get_journal_entries(session['user']['id'], limit=5)
        # Get journal statistics
        stats = db.get_journal_stats(session['user']['id'])
        
        return render_template(
            'journal.html',
            active_page='journal',
            entries=entries,
            stats=stats
        )
    except Exception as e:
        app.logger.error(f"Error loading journal page: {str(e)}")
        flash('An error occurred while loading your journal. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/journal/entries', methods=['GET'])
@login_required
def get_journal_entries():
    """Get paginated journal entries for the current user"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        entries = db.get_journal_entries(
            user_id=session['user']['id'],
            limit=per_page,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'entries': entries,
            'page': page,
            'per_page': per_page
        })
    except Exception as e:
        app.logger.error(f"Error fetching journal entries: {str(e)}")
        return jsonify({'error': 'Failed to fetch journal entries'}), 500

@app.route('/api/journal/stats', methods=['GET'])
@login_required
def journal_stats():
    """Get journal statistics for the current user"""
    try:
        days = int(request.args.get('days', 30))
        stats = db.get_journal_stats(
            user_id=session['user']['id'],
            days=min(days, 365)  # Cap at 1 year for performance
        )
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        app.logger.error(f"Error fetching journal stats: {str(e)}")
        return jsonify({'error': 'Failed to fetch journal statistics'}), 500

@app.route('/api/journal/entries', methods=['POST'])
@login_required
def save_journal():
    """Save a new journal entry"""
    app.logger.info("Received request to save journal entry")
    app.logger.info(f"Session data: {session}")
    app.logger.info(f"Request headers: {request.headers}")
    app.logger.info(f"Request data: {request.get_data(as_text=True)[:500]}")  # Log first 500 chars of request
    
    if not request.is_json:
        app.logger.error("Request is not JSON")
        return jsonify({'error': 'Request must be JSON', 'type': 'invalid_content_type'}), 400
    
    try:
        data = request.get_json()
        app.logger.info(f"Raw request data: {data}")
        
        # Log session user info
        user_id = session.get('user', {}).get('id')
        app.logger.info(f"Current user ID from session: {user_id}")
        
        if not user_id:
            app.logger.error("No user ID found in session")
        
        required_fields = ['content', 'mood', 'anxiety_level', 'stress_level']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            app.logger.error(f"Missing required fields: {', '.join(missing_fields)}")
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields,
                'type': 'missing_fields'
            }), 400
            
        # Validate field types
        try:
            anxiety_level = int(data['anxiety_level'])
            stress_level = int(data['stress_level'])
            
            if not (1 <= anxiety_level <= 10) or not (1 <= stress_level <= 10):
                return jsonify({
                    'error': 'Anxiety and stress levels must be between 1 and 10',
                    'type': 'invalid_range'
                }), 400
                
        except (ValueError, TypeError) as e:
            app.logger.error(f"Invalid number format: {str(e)}")
            return jsonify({
                'error': 'Anxiety and stress levels must be valid numbers',
                'type': 'invalid_number_format'
            }), 400
    
        try:
            # Log before saving
            app.logger.info(f"Attempting to save journal entry for user {user_id}")
            app.logger.info(f"Entry data - Title: {data.get('title', '')}, Mood: {data.get('mood')}, Anxiety: {anxiety_level}, Stress: {stress_level}")
            
            # Save the journal entry
            entry = db.save_journal_entry(
                user_id=user_id,
                title=data.get('title', '').strip(),
                content=data['content'].strip(),
                mood=data['mood'].strip(),
                anxiety_level=anxiety_level,
                stress_level=stress_level,
                helpful_activities=data.get('helpful_activities', [])
            )
            
            app.logger.info(f"Database save result: {entry}")
            
            if not entry:
                app.logger.error("Failed to save journal entry: No entry returned from database")
                return jsonify({
                    'error': 'Failed to save journal entry - no entry returned from database',
                    'type': 'database_error',
                    'user_id': user_id,
                    'has_title': 'title' in data,
                    'has_content': 'content' in data,
                    'has_mood': 'mood' in data
                }), 500
                
            app.logger.info(f"Successfully saved journal entry with ID: {entry.get('id')}")
            return jsonify({
                'success': True,
                'entry': {
                    'id': entry.get('id'),
                    'title': entry.get('title'),
                    'content': entry.get('content'),
                    'mood': entry.get('mood'),
                    'anxiety_level': entry.get('anxiety_level'),
                    'stress_level': entry.get('stress_level'),
                    'created_at': entry.get('created_at')
                }
            }), 201
            
        except Exception as e:
            app.logger.error(f"Error saving to database: {str(e)}", exc_info=True)
            return jsonify({
                'error': 'An error occurred while saving your entry',
                'type': 'database_error',
                'details': str(e) if app.debug else None
            }), 500
            
    except Exception as e:
        app.logger.error(f"Unexpected error in save_journal: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'An unexpected error occurred',
            'type': 'unexpected_error',
            'details': str(e) if app.debug else None
        }), 500



@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html', active_page='chatbot')

@app.route('/chat', methods=['POST'])
@csrf.exempt  # Explicitly exempt CSRF for this endpoint since we're handling it in the frontend
def chat():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
        
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    # Validate message
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    if len(user_message) > 2000:
        return jsonify({'error': 'Message is too long (max 2000 characters)'}), 400
    
    try:
        # Build context from chat and journal history
        context = ""
        user_id = None
        
        if 'user' in session and 'id' in session['user']:
            try:
                user_id = session['user']['id']
                # Get last 5 chat messages
                chat_history = db.get_user_chat_history(user_id, limit=5)
                for chat in reversed(chat_history):  # Oldest first for context
                    context += f"User: {chat.get('message','')}\nAI: {chat.get('response','')}\n"
                # Get last 2 journal entries
                journal_entries = db.get_user_journal_entries(user_id, limit=2)
                # Add most recent mood/anxiety/stress summary if available
                if journal_entries:
                    latest = journal_entries[0]
                    context += f"Recent mood: {latest.get('mood','-')}, " \
                              f"Anxiety: {latest.get('anxiety_level','-')}, " \
                              f"Stress: {latest.get('stress_level','-')}\n"
                for entry in reversed(journal_entries):
                    context += f"[Journal Entry] {entry.get('title','')}: {entry.get('content','')}\n"
            except Exception as e:
                app.logger.error(f"Error fetching user context: {str(e)}")
                # Continue without context if there's an error

        # System instructions with crisis support information
        crisis_support = """
        CRISIS SUPPORT RESOURCES (Philippines):
        - National Center for Mental Health Crisis Hotline: 1553 (toll-free)
        - Mobile Numbers: 0917-8998726, 0966-3514518, 0908-6392672
        - Landline: (02) 7989-8727 (available 24/7)
        
        If you're in crisis, please reach out to a mental health professional or one of the resources above immediately.
        """
        
        system_instruction = f"""You are UniCare, a supportive mental health assistant. 
        Be kind, empathetic, and non-judgmental. long response
        If someone mentions self-harm, suicide, or is in crisis, immediately provide crisis support resources and encourage them to contact a professional.
        
        {crisis_support}
        
        For non-crisis conversations, provide general mental health support and encouragement.
        Don't provide medical advice - always recommend consulting a healthcare professional.
        Keep responses concise and focused on the user's well-being.
        """
        
        # Build the prompt for Gemini
        prompt = f"{system_instruction}\n\n{context}User: {user_message}\nAI:"

        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            bot_reply = response.text if hasattr(response, 'text') else "I'm sorry, I couldn't process that request."
        except Exception as e:
            app.logger.error(f"Error generating AI response: {str(e)}")
            bot_reply = "I'm having trouble generating a response right now. Please try again later."

        # Save the chat message if user is logged in
        if user_id:
            try:
                db.save_chat_message(user_id, user_message, bot_reply)
            except Exception as e:
                app.logger.error(f"Error saving chat message: {str(e)}")
                # Continue even if saving fails

        # Replace newlines with <br> for HTML display
        bot_reply_html = bot_reply.replace('\n', '<br>')
        return jsonify({'response': bot_reply_html})
        
    except Exception as e:
        app.logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/chat_history')
def chat_history():
    if 'user' in session:
        history = db.get_user_chat_history(session['user']['id'])
        return jsonify(history)
    else:
        return jsonify([])

@app.route('/games')
def games():
    total_points = 0
    if 'user' in session:
        total_points = get_total_game_points()
    return render_template('games.html', 
                         active_page='games', 
                         games=mental_games,
                         total_points=total_points)

@app.route('/game/<int:game_id>')
def play_game(game_id):
    game = next((g for g in mental_games if g['id'] == game_id), None)
    if not game:
        return redirect(url_for('games'))
    return render_template(f'game_{game["type"]}.html', active_page='games', game=game)

@app.route('/breathing')
def breathing():
    return render_template('breathing.html', active_page='breathing')

@app.route('/save_breathing_session', methods=['POST'])
def save_breathing_session():
    if 'user' in session:
        data = request.json
        session_id = db.save_breathing_session(
            session['user']['id'],
            data.get('technique', ''),
            data.get('duration', 0),
            data.get('completed', True)
        )
        return jsonify({'success': True, 'session_id': session_id})
    else:
        return jsonify({'success': False, 'message': 'Please log in to save your progress'})

@app.route('/breathing_stats')
def breathing_stats():
    if 'user' in session:
        stats = db.get_breathing_stats(session['user']['id'])
        return jsonify(stats)
    else:
        return jsonify([])

@app.route('/save_game_score', methods=['POST'])
@csrf.exempt  # We'll handle CSRF manually
@login_required
def save_game_score():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Verify CSRF token manually
    csrf_token = request.headers.get('X-CSRFToken') or request.json.get('csrf_token')
    if not csrf_token or csrf_token != request.cookies.get('csrf_token'):
        return jsonify({'success': False, 'message': 'Invalid CSRF token'}), 403
    
    data = request.get_json()
    game_type = data.get('game_type')
    score = data.get('score', 0)
    level = data.get('level', 1)
    correct_answers = data.get('correct_answers', 0)
    
    try:
        db.save_game_score(
            user_id=session['user']['id'],
            game_type=game_type,
            score=score,
            level=level,
            source=f'game_{game_type}',
            metadata=json.dumps({'correct_answers': correct_answers}) if correct_answers else None
        )
        return jsonify({'success': True, 'message': 'Score saved successfully'})
    except Exception as e:
        print(f"Error saving game score: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to save score'}), 500

@app.route('/game_scores/<game_type>')
def game_scores(game_type):
    if 'user' in session:
        scores = db.get_user_game_scores(session['user']['id'], game_type)
        return jsonify(scores)
    else:
        return jsonify([])

@app.route('/leaderboard/<game_type>')
def leaderboard(game_type):
    leaderboard_data = db.get_leaderboard(game_type)
    return jsonify(leaderboard_data)

@app.route('/api/game/points')
def get_user_points():
    """API endpoint to get the current user's total points"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
    try:
        total_points = db.get_total_game_points(session['user']['id'])
        return jsonify({
            'success': True,
            'points': total_points
        })
    except Exception as e:
        print(f"Error getting user points: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to get points'}), 500

@app.route('/api/points/balance')
@login_required
def get_points_balance():
    """API endpoint to get the current user's total points balance for plant care"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401
        
    try:
        # Get all game scores for the user
        scores = db.get_user_game_scores(session['user']['id'])
        
        # Calculate total points from all scores
        total_points = sum(score.get('score', 0) for score in scores if score and score.get('score') is not None)
        
        return jsonify({
            'success': True,
            'points': total_points
        })
    except Exception as e:
        print(f"Error getting points balance: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to get points balance'}), 500

@app.route('/api/game/available-points')
def get_available_game_points():
    """API endpoint to get the current user's points from game wins only"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
    try:
        available_points = db.get_available_game_points(session['user']['id'])
        return jsonify({
            'success': True,
            'points': available_points
        })
    except Exception as e:
        print(f"Error getting available game points: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to get available points'}), 500

@app.route('/api/games/scores')
def get_total_game_points():
    if 'user' not in session:
        return jsonify([])
        
    try:
        # Get all game scores for the user
        scores = db.get_user_game_scores(session['user']['id'])
        
        # Calculate total points
        total_points = sum(score['score'] for score in scores if score.get('score') is not None)
        
        # Return as an array with a single object to match the frontend expectation
        return jsonify([{'score': total_points}])
    except Exception as e:
        print(f"Error getting total game points: {str(e)}")
        return jsonify([{'score': 0}])

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access your dashboard.', 'info')
        return redirect(url_for('login'))

    user_id = session['user'].get('id')
    
    # Get user's latest personality test summary
    latest_summary = db.get_latest_personality_test_summary(user_id)

    # Get recent personality tests (last 5)
    personality_tests = db.get_user_personality_tests(user_id, limit=5)

    # Get journal stats and calculate width percentages
    journal_stats = db.get_journal_stats(user_id=user_id, days=30)
    if journal_stats and len(journal_stats) > 0:
        # Add width properties for the progress bars
        journal_stats[0]['anxiety_width'] = int((journal_stats[0].get('avg_anxiety', 0) / 10) * 100)
        journal_stats[0]['stress_width'] = int((journal_stats[0].get('avg_stress', 0) / 10) * 100)

    # Get user's game scores (limit to top 5 scores)
    game_scores = db.get_user_game_scores(user_id, limit=5)

    # Get total game points for the user
    total_points = db.get_total_game_points(user_id)
    
    # Get published content
    published_content = db.get_published_content(limit=3)  # Get 3 most recent published items

    return render_template('dashboard.html', 
                         latest_summary=latest_summary,
                         personality_tests=personality_tests,
                         journal_stats=journal_stats,
                         game_scores=game_scores,
                         total_points=total_points,
                         published_content=published_content,
                         active_page='dashboard')

@app.route('/plant')
@login_required
def plant():
    # Get user data
    user_id = session.get('user', {}).get('id')
    if not user_id:
        return redirect(url_for('login'))

    # Get user's plant data
    plant_data = db.get_user_plant(user_id)
    
    # If no plant exists, create a default one
    if not plant_data:
        plant_data = db.create_user_plant(user_id)
    
    # Get total game points for the watering functionality
    total_points = db.get_total_game_points(user_id)
    
    # Prepare template variables with defaults if plant_data is None
    template_vars = {
        'plant_type': plant_data.get('plant_type', 'sunflower') if plant_data else 'sunflower',
        'growth_stage': plant_data.get('growth_stage', 0) if plant_data else 0,
        'total_points': total_points,
        'last_watered': plant_data.get('last_watered', 'Never') if plant_data else 'Never',
        'water_count': plant_data.get('water_count', 0) if plant_data else 0,
        'is_wilting': plant_data.get('is_wilting', False) if plant_data else False,
        'total_points': total_points,
        'active_page': 'plant'
    }
    
    return render_template('plant_new.html', **template_vars)

@app.route('/book-appointment')
def book_appointment():
    doctor_id = request.args.get('doctor_id')
    selected_doctor = None
    if doctor_id:
        selected_doctor = next((d for d in doctors_data if d['id'] == int(doctor_id)), None)
    return render_template('book_appointment.html', doctors=doctors_data, selected_doctor=selected_doctor)

# --- ADMIN AUTHENTICATION & DECORATORS ---

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Bypass admin check in development
        if app.debug:
            # Set dummy admin user in session if not set
            if 'user' not in session:
                session['user'] = {
                    'id': 'dev_admin',
                    'email': 'dev@example.com',
                    'is_admin': True
                }
            return f(*args, **kwargs)
            
        # Original admin check for production
        user = session.get('user')
        if not user or not user.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function
@app.route('/admin/users')
@admin_required
def admin_users():
    # Initialize default values
    users = []
    page = 1
    per_page = 20
    search = ''
    total_pages = 1
    
    try:
        # Get pagination and search parameters
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        search = request.args.get('search', '').strip().lower()
        
        # Build the base query
        query = service_role_supabase.table('users').select('*')
        
        # Apply search filter if provided
        if search:
            query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")
        
        # Get paginated results with count
        query = query.order('created_at', desc=True).range(offset, offset + per_page - 1)
        result = query.execute()
        
        # Get total count for pagination
        count_result = service_role_supabase.rpc('count_users', {'search_term': search if search else None}).execute()
        total_users = count_result.data[0]['count'] if hasattr(count_result, 'data') and count_result.data else 0
        total_pages = (total_users + per_page - 1) // per_page if per_page > 0 else 1
        
        # Process users with stats
        for user in result.data if hasattr(result, 'data') else []:
            try:
                # Get user stats using our utility function
                stats = get_user_stats(service_role_supabase, user['id'])
                
                # Format user data
                user_data = {
                    'id': user['id'],
                    'email': user.get('email', 'No email'),
                    'full_name': user.get('full_name', 'No name'),
                    'is_admin': user.get('is_admin', False),
                    'is_active': user.get('is_active', False),
                    'created_at': user.get('created_at'),
                    'last_login': user.get('last_sign_in_at', 'Never'),
                    'personality_test_count': stats.get('personality_tests', 0),
                    'journal_count': stats.get('journal_entries', 0),
                    'game_sessions': stats.get('game_sessions', 0),
                    'breathing_sessions': stats.get('breathing_sessions', 0)
                }
                users.append(user_data)
            except Exception as e:
                print(f"Error processing user {user.get('id', 'unknown')}: {str(e)}")
                continue
                
        # Get today's date and 7 days ago for the template
        today = datetime.now(timezone.utc).date()
        today_minus_7_days = today - timedelta(days=7)
        
        return render_template('admin_users.html', 
                            users=users,
                            current_page=page,
                            total_pages=total_pages,
                            search=search,
                            active_today_count=0,  # These should be calculated or passed as parameters
                            new_this_week_count=0,  # These should be calculated or passed as parameters
                            admin_count=0,  # This should be calculated or passed as parameters
                            average_activity=0,  # Placeholder
                            today_minus_7_days=today_minus_7_days,
                            today=today)
                            
    except Exception as e:
        print(f"Error in admin_users: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while fetching users.', 'error')
        
        # Return default values in case of error
        today = datetime.now(timezone.utc).date()
        today_minus_7_days = today - timedelta(days=7)
        
        return render_template('admin_users.html', 
                            users=[], 
                            current_page=page, 
                            total_pages=total_pages, 
                            search=search,
                            active_today_count=0,
                            new_this_week_count=0,
                            admin_count=0,
                            average_activity=0,
                            today_minus_7_days=today_minus_7_days,
                            today=today)
    except Exception as e:
        print(f"Error in admin_users: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('An error occurred while fetching users.', 'error')
        return render_template('admin_users.html', 
                            users=[], 
                            current_page=1, 
                            total_pages=1, 
                            search='',
                            active_today_count=0,
                            new_this_week_count=0,
                            admin_count=0,
                            average_activity=0)

@app.route('/admin/users/<user_id>/promote', methods=['POST'])
@admin_required
def promote_user(user_id):
    try:
        # First verify the user exists
        user = service_role_supabase.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
            
        if not user.data:
            flash('User not found.', 'error')
            return redirect(url_for('admin_users'))
            
        # Update user to admin
        service_role_supabase.table('users')\
            .update({
                'is_admin': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            })\
            .eq('id', user_id)\
            .execute()
            
        # Log the action
        admin_id = session['user'].get('id')
        log_admin_action(admin_id, f'Promoted user {user_id} to admin')
        
        flash('User promoted to admin successfully.', 'success')
    except Exception as e:
        print(f"Error promoting user: {str(e)}")
        flash('An error occurred while promoting the user.', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<user_id>/demote', methods=['POST'])
@admin_required
def demote_user(user_id):
    try:
        # Prevent demoting the last admin
        admin_count = service_role_supabase.table('users')\
            .select('*', count='exact')\
            .eq('is_admin', True)\
            .execute()
            
        if admin_count.count == 1:
            flash('Cannot remove the last admin.', 'error')
            return redirect(url_for('admin_users'))
            
        # Update user to remove admin
        service_role_supabase.table('users')\
            .update({
                'is_admin': False,
                'updated_at': datetime.now(timezone.utc).isoformat()
            })\
            .eq('id', user_id)\
            .execute()
            
        # Log the action
        admin_id = session['user'].get('id')
        log_admin_action(admin_id, f'Demoted user {user_id} from admin')
        
        flash('Admin rights removed successfully.', 'success')
    except Exception as e:
        print(f"Error demoting user: {str(e)}")
        flash('An error occurred while removing admin rights.', 'error')
    
    return redirect(url_for('admin_users'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Bypass admin check in development
        if app.debug:
            # Set dummy admin user in session if not set
            if 'user' not in session:
                session['user'] = {
                    'id': 'dev_admin',
                    'email': 'dev@example.com',
                    'is_admin': True
                }
            return f(*args, **kwargs)
            
        # Original admin check for production
        user = session.get('user')
        if not user or not user.get('is_admin'):
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET'])
def admin_login():
    # Redirect to dashboard if already logged in as admin
    if 'user' in session and session['user'].get('is_admin', False):
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    # Auto-login in development mode
    if app.debug:
        session['user'] = {
            'id': 'dev_admin',
            'email': 'dev@example.com',
            'is_admin': True
        }
        flash('Welcome, admin! (Development Mode)', 'success')
        return redirect(url_for('admin_dashboard'))
        
    # Original login logic for production
    email = request.form.get('email')
    password = request.form.get('password')
    
    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('admin_login'))
    
    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        if response.get('error'):
            flash(response['error']['message'], 'error')
            return redirect(url_for('admin_login'))
            
        user = response['user']
        user_id = user['id']
        
        # Check if user exists and is admin using the user ID
        user_data = supabase.table('users')\
            .select('is_admin,email')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not user_data.data or not user_data.data.get('is_admin'):
            flash('You are not authorized as an administrator.', 'error')
            return redirect(url_for('admin_login'))
        
        # Store user data in session
        session['user'] = {
            'id': user_id,
            'email': user_data.data.get('email', email),  # Use email from DB if available
            'is_admin': True
        }
        
        flash('Welcome, admin!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    except Exception as e:
        print(f"Admin login error: {str(e)}")  # Debug log
        flash('Authentication failed. Please check your credentials and try again.', 'error')
        return redirect(url_for('admin_login'))

def table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        result = service_role_supabase.rpc('execute_sql', {
            'query': f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table_name}');"
        }).execute()
        return result.data[0].get('exists', False) if result.data and len(result.data) > 0 else False
    except Exception as e:
        print(f"Error checking if table {table_name} exists: {str(e)}")
        return False
        
def get_user_growth_data(days=30):
    """Get user growth data for the last N days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Generate date range
        date_range = [start_date + timedelta(days=i) for i in range(days + 1)]
        date_labels = [d.strftime('%b %d') for d in date_range]
        
        # Get user counts for each day
        user_counts = []
        for date in date_range:
            next_date = date + timedelta(days=1)
            count = service_role_supabase.table('users')\
                .select('id', count='exact')\
                .lt('created_at', next_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))\
                .execute()
            user_counts.append(count.count if hasattr(count, 'count') else 0)
            
        return {
            'labels': date_labels,
            'data': user_counts
        }
    except Exception as e:
        print(f"Error getting user growth data: {str(e)}")
        return {'labels': [], 'data': []}
        
def get_feature_usage_data():
    """Get feature usage data for charts"""
    try:
        # Get counts for each feature
        journal_count = service_role_supabase.table('journal_entries')\
            .select('id', count='exact')\
            .execute()
            
        personality_test_count = service_role_supabase.table('personality_tests')\
            .select('id', count='exact')\
            .execute()
            
        breathing_count = service_role_supabase.table('breathing_sessions')\
            .select('id', count='exact')\
            .execute()
            
        game_count = service_role_supabase.table('game_sessions')\
            .select('id', count='exact')\
            .execute()
            
        return {
            'labels': ['Journal', 'Personality Tests', 'Breathing', 'Games'],
            'data': [
                journal_count.count if hasattr(journal_count, 'count') else 0,
                personality_test_count.count if hasattr(personality_test_count, 'count') else 0,
                breathing_count.count if hasattr(breathing_count, 'count') else 0,
                game_count.count if hasattr(game_count, 'count') else 0
            ]
        }
    except Exception as e:
        print(f"Error getting feature usage data: {str(e)}")
        return {'labels': [], 'data': []}

def get_user_stats():
    """Helper function to get user statistics"""
    try:
        # Get total users using a direct count query
        total_users = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .execute()
        
        # Get active users (last 7 days)
        active_users = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .gt('last_login', (datetime.now(timezone.utc) - timedelta(days=7)).isoformat())\
            .execute()
            
        # Get new users today
        today = datetime.utcnow().strftime('%Y-%m-%d')
        new_users_today = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .gte('created_at', f"{today}T00:00:00.000Z")\
            .lt('created_at', f"{today}T23:59:59.999Z")\
            .execute()
            
        # Get total admins
        total_admins = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .eq('is_admin', True)\
            .execute()
            
        return {
            'total_users': total_users.count if hasattr(total_users, 'count') else 0,
            'active_users': active_users.count if hasattr(active_users, 'count') else 0,
            'new_users_today': new_users_today.count if hasattr(new_users_today, 'count') else 0,
            'total_admins': total_admins.count if hasattr(total_admins, 'count') else 0
        }
    except Exception as e:
        print(f"Error getting user stats: {str(e)}")
        return {
            'total_users': 0,
            'active_users': 0,
            'new_users_today': 0,
            'total_admins': 0
        }

def get_feature_usage():
    """Helper function to get feature usage statistics"""
    result = {
        'journal': 0,
        'personality_tests': 0,
        'breathing': 0,
        'games': 0
    }
    
    try:
        # Get journal entries count if table exists
        if table_exists('journal_entries'):
            journal_entries = service_role_supabase.table('journal_entries')\
                .select('id', count='exact')\
                .execute()
            result['journal'] = journal_entries.count if hasattr(journal_entries, 'count') else 0
            
        # Get personality tests count if table exists
        if table_exists('personality_tests'):
            personality_tests = service_role_supabase.table('personality_tests')\
                .select('id', count='exact')\
                .execute()
            result['personality_tests'] = personality_tests.count if hasattr(personality_tests, 'count') else 0
            
        # Get breathing sessions count if table exists
        if table_exists('breathing_sessions'):
            breathing_sessions = service_role_supabase.table('breathing_sessions')\
                .select('id', count='exact')\
                .execute()
            result['breathing'] = breathing_sessions.count if hasattr(breathing_sessions, 'count') else 0
            
        # Get game sessions count if table exists
        if table_exists('game_sessions'):
            game_sessions = service_role_supabase.table('game_sessions')\
                .select('id', count='exact')\
                .execute()
            result['games'] = game_sessions.count if hasattr(game_sessions, 'count') else 0
            
        return result
    except Exception as e:
        print(f"Error getting feature usage: {str(e)}")
        return result

def get_recent_signups(limit=5):
    """Helper function to get recent user signups"""
    try:
        # First, get the user IDs and basic info
        result = service_role_supabase.table('users')\
            .select('id, email, created_at, last_login')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
            
        if not hasattr(result, 'data') or not result.data:
            return []
            
        # Get user metadata from auth.users for these users
        user_ids = [user['id'] for user in result.data]
        auth_users = service_role_supabase.auth.admin.list_users()
        
        # Create a mapping of user_id to user metadata
        auth_users_map = {}
        if hasattr(auth_users, 'users'):
            for user in auth_users.users:
                auth_users_map[user.id] = {
                    'full_name': getattr(user.user_metadata, 'full_name', ''),
                    'username': getattr(user.user_metadata, 'user_name', '')
                }
        
        # Combine the data
        signups = []
        for user in result.data:
            auth_data = auth_users_map.get(user['id'], {})
            signups.append({
                'id': user.get('id'),
                'email': user.get('email'),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login'),
                'full_name': auth_data.get('full_name', ''),
                'username': auth_data.get('username', '')
            })
            
        return signups
        
    except Exception as e:
        print(f"Error getting recent signups: {str(e)}")
        return []

def initialize_admin_activities(user_id, user_email):
    """Initialize admin activities table with a welcome entry if empty"""
    try:
        # Check if admin_activities table has any entries
        activities = service_role_supabase.table('admin_activities') \
            .select('id', count='exact') \
            .execute()
            
        if hasattr(activities, 'count') and activities.count == 0:
            # Add initial activity
            service_role_supabase.table('admin_activities').insert({
                'user_id': user_id,
                'action': 'System Initialization',
                'details': 'Admin dashboard initialized',
                'user_email': user_email,
                'user_full_name': 'System',
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent')
            }).execute()
            print("Initialized admin activities table with welcome entry")
            
    except Exception as e:
        print(f"Error initializing admin activities: {str(e)}")

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Initialize default values
    stats = {}
    feature_usage = {}
    recent_signups = []
    activities = []
    user_growth = {}
    feature_usage_data = {}
    emotion_stats = {}
    
    # Skip emotion stats since we're simplifying the dashboard
    emotion_stats = {
        'total_entries': 0,
        'avg_mood': 0,
        'mood_distribution': {},
        'avg_anxiety': 0,
        'avg_stress': 0
    }
    
    try:
        print("Starting admin dashboard...")
        
        # Get current user info
        user_id = session.get('user', {}).get('id')
        user_email = session.get('user', {}).get('email', 'system@example.com')
        
        # Initialize admin activities if needed
        if user_id and table_exists('admin_activities'):
            initialize_admin_activities(user_id, user_email)
        
        # Get user statistics with additional metrics for the new dashboard
        stats = get_user_stats()
        
        # Add additional stats needed for the new dashboard
        stats.update({
            'engagement_rate': 75,  # Example value - calculate based on your metrics
            'avg_session_duration': 8.5,  # Example value - calculate based on your metrics
            'user_growth': random.randint(5, 15),  # Example value
            'active_users_change': random.randint(-5, 10),  # Example value
            'engagement_change': random.randint(-2, 5),  # Example value
            'session_change': random.randint(-3, 4)  # Example value
        })
        
        # Get feature usage with additional metrics
        feature_usage = get_feature_usage()
        
        # Get recent signups with more details
        recent_signups = get_recent_signups(5)
        
        # Get recent activities with icons
        if table_exists('admin_activities'):
            try:
                activities_data = service_role_supabase.table('admin_activities') \
                    .select('*') \
                    .order('created_at', desc=True) \
                    .limit(5) \
                    .execute()
                    
                if hasattr(activities_data, 'data') and activities_data.data:
                    for activity in activities_data.data:
                        activities.append({
                            'title': activity.get('action', 'Activity'),
                            'description': activity.get('details', ''),
                            'created_at': activity.get('created_at'),
                            'icon': get_activity_icon(activity.get('action', '')),
                            'user_email': activity.get('user_email', 'system'),
                            'user_full_name': activity.get('user_full_name', 'System')
                        })
            except Exception as e:
                print(f"Error fetching activities: {str(e)}")
        
        # Add a welcome activity if no activities exist
        if not activities and 'user' in session:
            activities.append({
                'title': 'Welcome to Admin Dashboard',
                'description': 'Start managing your application from here.',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'icon': 'info-circle',
                'user_email': user_email,
                'user_full_name': 'System'
            })
        
        # Get user growth data for the chart
        user_growth = get_user_growth_last_30_days()
        feature_usage_data = get_feature_usage_data()
        
        # Check if v2 template exists, fall back to v1 if not
        template_name = 'admin_dashboard_v2.html' if os.path.exists(os.path.join('templates', 'admin_dashboard_v2.html')) else 'admin_dashboard.html'
        
        return render_template(template_name,
                           stats=stats,
                           feature_usage=feature_usage,
                           recent_signups=recent_signups,
                           activities=activities,
                           user_growth=user_growth,
                           feature_usage_data=feature_usage_data,
                           current_user={
                               'email': user_email,
                               'is_admin': session.get('user', {}).get('is_admin', False)
                           })
                           
    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Prepare fallback data
        if not activities:
            activities = [{
                'title': 'System Notification',
                'description': 'An error occurred while loading the dashboard.',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'user': {
                    'email': session.get('user', {}).get('email', 'system'),
                    'full_name': 'System'
                }
            }]
        
        # Try to get basic stats even if there was an error
        try:
            stats = {
                'total_users': get_total_users() or 0,
                'active_users': get_active_users() or 0,
                'new_users_today': get_new_users_today() or 0,
                'total_admins': get_admin_count() or 0,
                'total_journal_entries': get_total_journal_entries() or 0,
                'total_personality_tests': get_total_personality_tests() or 0,
                'engagement_rate': 0,
                'avg_session_duration': 0,
                'user_growth': 0,
                'active_users_change': 0,
                'engagement_change': 0,
                'session_change': 0
            }
            
            user_growth = get_user_growth_data() or {}
            feature_usage_data = get_feature_usage_data() or {}
            
        except Exception as inner_e:
            print(f"Error getting fallback data: {str(inner_e)}")
        
        # Always render a template, even in case of error
        return render_template('admin_dashboard.html',
                           stats=stats,
                           feature_usage=feature_usage,
                           recent_signups=recent_signups[:5],  # Only show 5 most recent
                           activities=activities[:5],  # Only show 5 most recent
                           user_growth=user_growth,
                           feature_usage_data=feature_usage_data,
                           current_user={
                               'email': session.get('user', {}).get('email', 'system@example.com'),
                               'is_admin': session.get('user', {}).get('is_admin', False)
                           })
            
        try:
            stats['total_breathing_sessions'] = get_total_breathing_sessions() or 0
            print(f"Total breathing sessions: {stats['total_breathing_sessions']}")
        except Exception as e:
            print(f"Error getting total_breathing_sessions: {str(e)}")
            
        try:
            stats['total_game_sessions'] = get_total_game_sessions() or 0
            print(f"Total game sessions: {stats['total_game_sessions']}")
        except Exception as e:
            print(f"Error getting total_game_sessions: {str(e)}")
        
        # Initialize recent activities with empty list
        activities = []
        
        # Get recent activities with user info
        activities = []
        if table_exists('admin_activities'):
            try:
                activities_data = service_role_supabase.table('admin_activities') \
                    .select('*, users:user_id(email, full_name, username)') \
                    .order('created_at', desc=True) \
                    .limit(5) \
                    .execute()
                    
                if hasattr(activities_data, 'data') and activities_data.data:
                    for activity in activities_data.data:
                        user_info = activity.get('users', {}) or {}
                        activities.append({
                            'title': activity.get('action', 'Activity'),
                            'description': activity.get('details', ''),
                            'timestamp': activity.get('created_at'),
                            'user': {
                                'email': user_info.get('email', 'system'),
                                'full_name': user_info.get('full_name', 'System'),
                                'username': user_info.get('username', 'system')
                            }
                        })
            except Exception as e:
                print(f"Error fetching activities: {str(e)}")
                # Log the error but continue with empty activities
                activities = []
        else:
            print("admin_activities table does not exist, skipping activities fetch")
        
        # Get user growth data for the chart
        user_growth = {'labels': [], 'data': []}
        try:
            growth_data = get_user_growth_last_30_days() or []
            user_growth = {
                'labels': [item.get('date', '') for item in growth_data],
                'data': [item.get('count', 0) for item in growth_data]
            }
        except Exception as e:
            print(f"Error getting growth data: {str(e)}")
        
        # Get recent signups for the table
        recent_signups = []
        try:
            print("Fetching recent signups...")
            # Use raw SQL to avoid issues with column selection
            result = service_role_supabase.rpc('execute_sql', {
                'query': '''
                    SELECT id, email, created_at, last_login, 
                           raw_user_meta_data->>'full_name' as full_name,
                           raw_user_meta_data->>'username' as username
                    FROM auth.users 
                    ORDER BY created_at DESC 
                    LIMIT 5
                '''
            }).execute()
            
            print(f"Recent signups query result: {result}")
            
            if hasattr(result, 'data') and result.data:
                recent_signups = [{
                    'id': user.get('id'),
                    'email': user.get('email'),
                    'created_at': user.get('created_at'),
                    'last_login': user.get('last_login'),
                    'full_name': user.get('full_name'),
                    'username': user.get('username')
                } for user in result.data if user]
                print(f"Found {len(recent_signups)} recent signups")
            else:
                print("No signups data found")
        except Exception as e:
            error_msg = f"Error fetching recent signups: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            app.logger.error(error_msg)
            app.logger.error(traceback.format_exc())
            recent_signups = []
        
        # Initialize default feature usage statistics
        default_feature_stats = {
            'total': 0,
            'recent': 0,
            'users': 0,
            'trend': 'stable'
        }
        
        # Get feature usage statistics with error handling
        feature_usage = {}
        try:
            feature_usage['journal'] = get_journal_usage_stats() or default_feature_stats
        except Exception as e:
            print(f"Error getting journal stats: {str(e)}")
            feature_usage['journal'] = default_feature_stats.copy()
            
        try:
            feature_usage['personality_tests'] = get_personality_test_usage_stats() or default_feature_stats
        except Exception as e:
            print(f"Error getting personality test stats: {str(e)}")
            feature_usage['personality_tests'] = default_feature_stats.copy()
            
        try:
            feature_usage['games'] = get_game_usage_stats() or default_feature_stats
        except Exception as e:
            print(f"Error getting game stats: {str(e)}")
            feature_usage['games'] = default_feature_stats.copy()
            
        try:
            feature_usage['breathing'] = get_breathing_usage_stats() or default_feature_stats
        except Exception as e:
            print(f"Error getting breathing stats: {str(e)}")
            feature_usage['breathing'] = default_feature_stats.copy()
        
        # Ensure all feature usage has required fields
        for feature in feature_usage.values():
            for key in default_feature_stats:
                if key not in feature:
                    feature[key] = default_feature_stats[key]
        
        # Render the new dashboard template with all required data
        return render_template('admin_dashboard_new.html',
                            stats=stats,
                            activities=activities,
                            user_growth=user_growth,
                            recent_signups=recent_signups,
                            feature_usage=feature_usage,
                            page_title="Dashboard Overview")
                            
    except Exception as e:
        error_msg = f"Error in admin_dashboard: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Log the full error to server logs
        app.logger.error(error_msg)
        app.logger.error(traceback.format_exc())
        
        flash('An error occurred while loading the dashboard. Please check the server logs for details.', 'error')
        
        # Default values for error case
        default_feature_stats = {
            'total': 0,
            'recent': 0,
            'users': 0,
            'trend': 'stable'
        }
        
        return render_template('admin_dashboard.html', 
                            stats={
                                'total_users': 0,
                                'active_users': 0,
                                'new_users_today': 0,
                                'total_admins': 0,
                                'total_journal_entries': 0,
                                'total_personality_tests': 0,
                                'total_breathing_sessions': 0,
                                'total_game_sessions': 0
                            },
                            activities=[],
                            user_growth={'labels': [], 'data': []},
                            recent_signups=[],
                            feature_usage={
                                'journal': default_feature_stats,
                                'personality_tests': default_feature_stats,
                                'games': default_feature_stats,
                                'breathing': default_feature_stats
                            },
                            page_title="Dashboard")

@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400
        
        # Send password reset email using Supabase
        response = supabase.auth.reset_password_for_email(email)
        
        if response.get('error'):
            return jsonify({"success": False, "error": response['error']['message']}), 400
            
        return jsonify({"success": True, "message": "Password reset email sent"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Helper functions for admin dashboard
def get_total_users():
    """Get total number of users"""
    try:
        result = service_role_supabase.table('users').select('id', count='exact').execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting total users: {str(e)}")
        return 0

def get_active_users(days=7):
    """Get number of active users in the last N days"""
    try:
        date_threshold = datetime.now(timezone.utc) - timedelta(days=days)
        # Format the timestamp in ISO format with timezone
        formatted_date = date_threshold.isoformat(timespec='milliseconds')
        if '+' not in formatted_date:  # Ensure timezone is included
            formatted_date += 'Z'
            
        result = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .gt('last_login', formatted_date)\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting active users: {str(e)}")
        return 0

def get_new_users_today():
    """Get number of new users registered today"""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
        
        result = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .gte('created_at', today)\
            .lt('created_at', tomorrow)\
            .execute()
            
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting new users: {str(e)}")
        return 0

def get_admin_count():
    """Get total number of admin users"""
    try:
        result = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .eq('is_admin', True)\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting admin count: {str(e)}")
        return 0

def get_total_journal_entries():
    """Get total number of journal entries"""
    try:
        result = service_role_supabase.table('journal_entries')\
            .select('id', count='exact')\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting total journal entries: {str(e)}")
        return 0

def get_total_personality_tests():
    """Get total number of personality tests completed"""
    try:
        result = service_role_supabase.table('personality_tests')\
            .select('id', count='exact')\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting total personality tests: {str(e)}")
        return 0

def get_total_breathing_sessions():
    """Get total number of breathing sessions"""
    try:
        result = service_role_supabase.table('breathing_sessions')\
            .select('id', count='exact')\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting total breathing sessions: {str(e)}")
        return 0

def get_total_game_sessions():
    """Get total number of game sessions"""
    try:
        result = service_role_supabase.table('game_sessions')\
            .select('id', count='exact')\
            .execute()
        return result.count if hasattr(result, 'count') else 0
    except Exception as e:
        print(f"Error getting total game sessions: {str(e)}")
        return 0

def get_journal_usage_stats(days=30):
    """Get journal usage statistics"""
    try:
        date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get total entries
        total = service_role_supabase.table('journal_entries')\
            .select('id', count='exact')\
            .execute()
            
        # Get recent entries
        recent = service_role_supabase.table('journal_entries')\
            .select('id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        # Get unique users
        users = service_role_supabase.table('journal_entries')\
            .select('user_id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'recent': recent.count if hasattr(recent, 'count') else 0,
            'users': users.count if hasattr(users, 'count') else 0,
            'trend': 'up' if recent.count > 0 else 'stable'
        }
    except Exception as e:
        print(f"Error getting journal usage stats: {str(e)}")
        return {'total': 0, 'recent': 0, 'users': 0, 'trend': 'stable'}

def get_personality_test_usage_stats(days=30):
    """Get personality test usage statistics"""
    try:
        date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get total tests
        total = service_role_supabase.table('personality_tests')\
            .select('id', count='exact')\
            .execute()
            
        # Get recent tests
        recent = service_role_supabase.table('personality_tests')\
            .select('id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        # Get unique users
        users = service_role_supabase.table('personality_tests')\
            .select('user_id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'recent': recent.count if hasattr(recent, 'count') else 0,
            'users': users.count if hasattr(users, 'count') else 0,
            'trend': 'up' if recent.count > 0 else 'stable'
        }
    except Exception as e:
        print(f"Error getting personality test usage stats: {str(e)}")
        return {'total': 0, 'recent': 0, 'users': 0, 'trend': 'stable'}

def get_breathing_usage_stats(days=30):
    """Get breathing exercise usage statistics"""
    try:
        date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get total sessions
        total = service_role_supabase.table('breathing_sessions')\
            .select('id', count='exact')\
            .execute()
            
        # Get recent sessions
        recent = service_role_supabase.table('breathing_sessions')\
            .select('id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        # Get unique users
        users = service_role_supabase.table('breathing_sessions')\
            .select('user_id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'recent': recent.count if hasattr(recent, 'count') else 0,
            'users': users.count if hasattr(users, 'count') else 0,
            'trend': 'up' if recent.count > 0 else 'stable',
            'avg_duration': '2:30'  # Placeholder
        }
    except Exception as e:
        print(f"Error getting breathing usage stats: {str(e)}")
        return {'total': 0, 'recent': 0, 'users': 0, 'trend': 'stable', 'avg_duration': '0:00'}

def get_game_usage_stats(days=30):
    """Get game usage statistics"""
    try:
        date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get total sessions
        total = service_role_supabase.table('game_sessions')\
            .select('id', count='exact')\
            .execute()
            
        # Get recent sessions
        recent = service_role_supabase.table('game_sessions')\
            .select('id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        # Get unique users
        users = service_role_supabase.table('game_sessions')\
            .select('user_id', count='exact')\
            .gt('created_at', date_threshold)\
            .execute()
            
        # Get top game
        top_game = service_role_supabase.table('game_sessions')\
            .select('game_type', count='exact')\
            .group('game_type')\
            .order('count', desc=True)\
            .limit(1)\
            .execute()
            
        top_game_name = top_game.data[0]['game_type'] if hasattr(top_game, 'data') and top_game.data else 'None'
            
        return {
            'total': total.count if hasattr(total, 'count') else 0,
            'recent': recent.count if hasattr(recent, 'count') else 0,
            'users': users.count if hasattr(users, 'count') else 0,
            'trend': 'up' if recent.count > 0 else 'stable',
            'top_game': top_game_name
        }
    except Exception as e:
        print(f"Error getting game usage stats: {str(e)}")
        return {'total': 0, 'recent': 0, 'users': 0, 'trend': 'stable', 'top_game': 'None'}

def get_recent_activities(limit=10):
    """Get recent admin activities"""
    try:
        result = service_role_supabase.table('admin_activities')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        return result.data if hasattr(result, 'data') else []
    except Exception as e:
        print(f"Error getting recent activities: {str(e)}")
        return []

def get_user_growth_last_30_days():
    """Get user growth data for the last 30 days"""
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=29)  # 30 days including today
        
        # Generate date range
        date_range = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        date_strs = [d.isoformat() for d in date_range]
        
        # Initialize result with zeros
        result = {date: 0 for date in date_strs}
        
        try:
            # Get user counts by signup date
            query = f"""
            SELECT 
                DATE(created_at) as signup_date, 
                COUNT(*) as user_count
            FROM users
            WHERE created_at >= '{start_date.isoformat()}'
            GROUP BY DATE(created_at)
            ORDER BY signup_date
            """
            
            # Execute raw query
            query_result = service_role_supabase.rpc('execute_sql', {'query': query}).execute()
            
            # Process results
            if hasattr(query_result, 'data') and isinstance(query_result.data, list):
                for row in query_result.data:
                    try:
                        if isinstance(row, dict) and 'signup_date' in row and 'user_count' in row:
                            date_str = str(row['signup_date']).split('T')[0]  # Handle datetime strings
                            if date_str in result:
                                result[date_str] = int(row['user_count'])
                    except (ValueError, KeyError, AttributeError) as e:
                        print(f"Warning: Error processing row {row}: {str(e)}")
                        continue

        except Exception as e:
            print(f"Warning: Error fetching user growth data: {str(e)}")

        # Convert to list of values in date order
        return [{'date': date, 'count': result[date]} for date in date_strs]

    except Exception as e:
        print(f"Error in get_user_growth_last_30_days: {str(e)}")
        # Return empty list on error
        return []

def log_admin_action(admin_id, action):
    """Log an admin action to the database"""
    try:
        service_role_supabase.table('admin_activities').insert({
            'admin_id': admin_id,
            'action': action,
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')
        }).execute()
    except Exception as e:
        print(f"Error logging admin action: {str(e)}")

@app.route('/personality-test/history')
@app.route('/assessment/history')  # Keep for backward compatibility
@login_required
def personality_test_history():
    """Render the personality test history page with user's test results."""
    try:
        user_id = session['user']['id']
        
        # Get all tests for the current user
        result = supabase.table('personality_tests') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(50) \
            .execute()
        
        tests = []
        for test in result.data:
            # Ensure all required fields exist
            if not all(k in test for k in ['id', 'created_at', 'total_score', 'level', 'category_scores']):
                continue
                
            # Format the test data
            formatted_test = {
                'id': test['id'],
                'total_score': test['total_score'],
                'level': test['level'],
                'category_scores': test['category_scores'],
                'created_at': test['created_at']
            }
            
            # Format the date for display
            created_at = test['created_at']
            if isinstance(created_at, str):
                if 'T' in created_at:  # ISO format
                    formatted_test['formatted_date'] = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%B %d, %Y %H:%M')
                else:  # Just date
                    formatted_test['formatted_date'] = datetime.strptime(created_at, '%Y-%m-%d').strftime('%B %d, %Y')
            elif hasattr(created_at, 'strftime'):  # Already a datetime object
                formatted_test['formatted_date'] = created_at.strftime('%B %d, %Y %H:%M')
            else:
                formatted_test['formatted_date'] = 'Date not available'
            
            tests.append(formatted_test)
        
        # Get the latest test summary if available
        latest_summary = None
        if tests:
            latest_test = tests[0]
            latest_summary = {
                'total_score': latest_test['total_score'],
                'level': latest_test['level'],
                'category_scores': latest_test['category_scores']
            }
        
        return render_template('personality_test_history.html',
                             personality_tests=tests,
                             latest_summary=latest_summary,
                             active_page='personality-test-history')
    
    except Exception as e:
        print(f"Error fetching personality test history: {e}")
        flash('Error loading test history. Please try again later.', 'error')
        return render_template('personality_test_history.html',
                             personality_tests=[],
                             latest_summary=None,
                             active_page='personality-test-history')

@app.route('/export/personality-tests')
@admin_required
def export_personality_tests():
    """Export personality tests data as CSV"""
    try:
        # Get all tests with user info
        response = app.supabase.table('personality_tests') \
            .select('*, users(email, name)') \
            .order('created_at', desc=True) \
            .execute()
            
        tests = response.data if hasattr(response, 'data') else []
        
        if not tests:
            flash('No personality test data available to export', 'info')
            return redirect(url_for('admin_personality_tests'))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'User ID', 'User Email', 'User Name', 'Total Score', 
            'Openness Score', 'Conscientiousness Score', 'Extraversion Score', 
            'Agreeableness Score', 'Neuroticism Score', 'Created At', 'Updated At'
        ])
        
        # Write data
        for t in tests:
            writer.writerow([
                t.get('id'),
                t.get('user_id'),
                t.get('users', {}).get('email', 'N/A'),
                t.get('users', {}).get('name', 'N/A'),
                t.get('total_score', 0),
                t.get('openness_score', 0),
                t.get('conscientiousness_score', 0),
                t.get('extraversion_score', 0),
                t.get('agreeableness_score', 0),
                t.get('neuroticism_score', 0),
                t.get('created_at', ''),
                t.get('updated_at', '')
            ])
        
        # Create response with CSV data
        output.seek(0)
        return Response(
            output,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=personality_tests_export.csv',
                'Content-type': 'text/csv'
            }
        )
        
    except Exception as e:
        print(f"Error exporting personality tests: {e}")
        flash('Failed to export personality test data', 'error')
        return redirect(url_for('admin_personality_tests'))
@admin_required
def get_user_details(user_id):
    try:
        # Get user details
        user_result = service_role_supabase.table('users') \
            .select('*') \
            .eq('id', user_id) \
            .single() \
            .execute()
        
        if 'error' in user_result.data:
            flash('User not found', 'error')
            return redirect(url_for('admin_users'))
            
        user = user_result.data
        
        # Get user stats
        journal_count = service_role_supabase.rpc('count_user_journal_entries', {'user_uuid': user_id}).execute()
        test_count = service_role_supabase.rpc('count_user_personality_tests', {'user_uuid': user_id}).execute()
        breathing_sessions = service_role_supabase.rpc('count_user_breathing_sessions', {'user_uuid': user_id}).execute()
        
        # Get recent activities
        recent_activities = service_role_supabase.rpc('get_user_recent_activities', {'user_uuid': user_id, 'limit': 10}).execute()
        
        # Calculate overview stats
        overview = {
            'journal_entries': journal_count.data[0]['count'] if journal_count.data and len(journal_count.data) > 0 else 0,
            'personality_tests': test_count.data[0]['count'] if test_count.data and len(test_count.data) > 0 else 0,
            'breathing_sessions': breathing_sessions.data[0]['count'] if breathing_sessions.data and len(breathing_sessions.data) > 0 else 0,
            'last_active': user.get('last_sign_in_at') or 'Never'
        }
        
        return render_template('admin_user_details.html',
                             user=user,
                             activities=recent_activities.data if recent_activities.data else [],
                             overview=overview,
                             current_user=session.get('user'))
    except Exception as e:
        print(f"Error in get_user_details: {e}")
        flash('An error occurred while fetching user details. Please try again later.', 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/personality-tests')
@app.route('/admin/assessments')  # Keep for backward compatibility
@admin_required
def admin_personality_tests():
    """Admin view of all personality tests taken by users."""
    try:
        # Get personality tests with user information
        result = service_role_supabase.rpc('get_personality_tests_with_users').execute()
        
        if not result.data:
            return render_template('admin/personality_tests.html',
                                personality_tests=[],
                                current_user=session.get('user'),
                                active_page='admin-personality-tests')
        
        # Format the test data
        tests = []
        for test in result.data:
            # Ensure all required fields exist
            if not all(k in test for k in ['id', 'user_id', 'email', 'created_at', 'total_score', 'level']):
                continue
                
            # Format the test data
            formatted_test = {
                'id': test['id'],
                'user_id': test['user_id'],
                'user_email': test.get('email', 'Unknown'),
                'total_score': test['total_score'],
                'level': test['level'],
                'category_scores': test.get('category_scores', {}),
                'created_at': test['created_at']
            }
            
            # Format the date for display
            created_at = test['created_at']
            if isinstance(created_at, str):
                if 'T' in created_at:  # ISO format
                    formatted_test['formatted_date'] = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
                else:  # Just date
                    formatted_test['formatted_date'] = datetime.strptime(created_at, '%Y-%m-%d').strftime('%Y-%m-%d')
            elif hasattr(created_at, 'strftime'):  # Already a datetime object
                formatted_test['formatted_date'] = created_at.strftime('%Y-%m-%d %H:%M')
            else:
                formatted_test['formatted_date'] = 'Date not available'
            
            tests.append(formatted_test)
        
        # Sort by most recent first
        tests.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        # Pagination (if needed)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        total_tests = len(tests)
        total_pages = (total_tests + per_page - 1) // per_page
        
        # Get tests for current page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_tests = tests[start_idx:end_idx]
        
        return render_template('admin/personality_tests.html',
                             personality_tests=paginated_tests,
                             current_user=session.get('user'),
                             active_page='admin-personality-tests',
                             page=page,
                             total_pages=total_pages,
                             total_tests=total_tests)
        
    except Exception as e:
        print(f"Error in admin_personality_tests: {e}")
        flash('An error occurred while fetching personality test data. Please try again later.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/content')
@admin_required
def admin_content():
    try:
        # Try to get content items
        content = supabase.table('content')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        
        return render_template('admin_content.html',
                            content=content.data or [],
                            current_user=session.get('user'))
    except Exception as e:
        if 'relation "public.content" does not exist' in str(e):
            flash('The content table does not exist. Please run database migrations.', 'error')
            return render_template('admin_content.html',
                                content=[],
                                current_user=session.get('user'))
        raise  # Re-raise other exceptions

@app.route('/admin/admins')
@admin_required
def admin_admins():
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page
    
    # Get total count of admin users
    count_response = supabase.table('users')\
        .select('count', count='exact')\
        .eq('is_admin', True)\
        .execute()
    total_items = count_response.count if hasattr(count_response, 'count') else 0
    
    # Calculate pagination values
    total_pages = (total_items + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Get paginated admin users
    response = supabase.table('users')\
        .select('id, email, created_at, last_login, is_admin')\
        .eq('is_admin', True)\
        .order('created_at', desc=True)\
        .range(offset, offset + per_page - 1)\
        .execute()
    
    # Prepare admin data with all required fields
    current_user_id = session.get('user', {}).get('id')
    admins = []
    for admin in response.data:
        admins.append({
            'id': admin['id'],
            'email': admin['email'],
            'created_at': admin.get('created_at'),
            'last_login': admin.get('last_login'),
            'is_admin': admin.get('is_admin', False),
            'is_current_user': admin['id'] == current_user_id,
            'admin_since': admin.get('created_at'),
            'role': 'Super Admin' if admin.get('is_admin') else 'Admin',
            'permissions': ['users', 'content', 'analytics', 'settings'] if admin.get('is_admin') else ['content']
        })
    
    # Create pagination object
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None,
        'first_item': offset + 1,
        'last_item': min(offset + per_page, total_items) if total_items > 0 else 0,
        'items': admins,
        'pages': total_pages,
        'iter_pages': range(1, total_pages + 1)  # For page number iteration in template
    }
    
    return render_template('admin_admins.html',
                         admins=admins,
                         pagination=pagination,
                         current_user=session.get('user'))

@app.route('/admin/track')
@admin_required
def admin_track():
    # Get analytics data
    user_count = get_total_users()
    active_users = get_active_users(7)
    new_users = get_new_users_today()
    
    return render_template('admin_track.html',
                         user_count=user_count,
                         active_users=active_users,
                         new_users=new_users,
                         current_user=session.get('user'))

@app.route('/debug/tables')
def debug_tables():
    """Debug endpoint to check table status"""
    try:
        # Check if game_sessions table exists
        result = service_role_supabase.rpc('execute_sql', {
            'query': """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'game_sessions'
            ) as game_sessions_exists,
            EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'journal_entries'
            ) as journal_entries_exists,
            EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            ) as users_exists;
            """
        }).execute()
        
        tables = result.data[0] if result.data else {}
        
        # Get current migrations
        migrations = service_role_supabase.rpc('execute_sql', {
            'query': "SELECT * FROM pg_migrations ORDER BY id DESC LIMIT 5;"
        }).execute()
        
        return jsonify({
            'tables': tables,
            'recent_migrations': migrations.data if hasattr(migrations, 'data') else []
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/test/create_test_entries')
def create_test_entries():
    """Endpoint to create test journal entries for development"""
    try:
        # Get all users
        users = supabase.table('users').select('id').execute()
        if not hasattr(users, 'data') or not users.data:
            return jsonify({'success': False, 'error': 'No users found'}), 400
            
        # Test entries with minimal required fields
        test_entries = [
            {'content': 'Feeling great today!'},
            {'content': 'Not feeling too well...'},
            {'content': 'Had an okay day'},
            {'content': 'Really struggling today'},
            {'content': 'Best day ever!'}
        ]
        
        created_count = 0
        for user in users.data:
            user_id = user['id']
            for entry in test_entries:
                # Add some variation to the entries
                entry_copy = entry.copy()
                entry_copy['user_id'] = user_id
                entry_copy['created_at'] = datetime.now(timezone.utc).isoformat()
                
                # Insert the entry
                result = app.supabase_admin.table('journal_entries').insert(entry_copy).execute()
                if hasattr(result, 'data') and result.data:
                    created_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Created {created_count} test journal entries',
            'test_entries': test_entries
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Enable debug mode for development
    app.debug = True
    app.run(debug=True)