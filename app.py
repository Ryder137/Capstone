from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, make_response
import json
from datetime import datetime, timezone, timedelta
import random
import os
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

# Load environment variables from .env
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.getenv('CSRF_SECRET_KEY', 'your-csrf-secret-key-here')
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour in seconds

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

# Assessment questions
assessment_questions = [
    # Resilience Scale (1-10)
    {
        'id': 1,
        'question': 'I am able to adapt to change.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 2,
        'question': 'I can deal with whatever comes my way.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 3,
        'question': 'I try to see the humorous side of things when I face problems.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 4,
        'question': 'I can achieve my goals, despite difficulties.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 5,
        'question': 'I can remain focused under pressure.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 6,
        'question': 'I don\'t give up easily when I face challenges.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 7,
        'question': 'I believe I can handle unpleasant or painful feelings.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 8,
        'question': 'I tend to bounce back after difficult situations.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 9,
        'question': 'I can think clearly under stress.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    {
        'id': 10,
        'question': 'I take control of my life during tough times.',
        'options': ['Not true at all', 'Rarely true', 'Sometimes true', 'Often true', 'True nearly all the time'],
        'scores': [0, 1, 2, 3, 4],
        'category': 'resilience'
    },
    # Depression Scale (11-17)
    {
        'id': 11,
        'question': 'I couldn\'t seem to experience any positive feelings at all.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 12,
        'question': 'I found it difficult to work up the initiative to do things.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 13,
        'question': 'I felt that I had nothing to look forward to.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 14,
        'question': 'I felt down-hearted and blue.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 15,
        'question': 'I was unable to become enthusiastic about anything.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 16,
        'question': 'I felt I wasn\'t worth much as a person.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    {
        'id': 17,
        'question': 'I felt that life was meaningless.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'depression'
    },
    # Anxiety Scale (18-24)
    {
        'id': 18,
        'question': 'I experienced breathing difficulty (e.g., excessively rapid breathing, breathlessness).',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 19,
        'question': 'I experienced trembling (e.g., in the hands).',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 20,
        'question': 'I was worried about situations where I might panic or make a fool of myself.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 21,
        'question': 'I felt I was close to panic.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 22,
        'question': 'I was aware of the beating of my heart in the absence of physical exertion (e.g., heart racing or pounding).',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 23,
        'question': 'I felt scared without any good reason.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    {
        'id': 24,
        'question': 'I experienced dryness of my mouth.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'anxiety'
    },
    # Stress Scale (25-31)
    {
        'id': 25,
        'question': 'I found it hard to wind down.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 26,
        'question': 'I tended to over-react to situations.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 27,
        'question': 'I felt that I was using a lot of nervous energy.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 28,
        'question': 'I found myself getting agitated.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 29,
        'question': 'I found it difficult to relax.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 30,
        'question': 'I was intolerant of anything that kept me from getting on with what I was doing.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
    },
    {
        'id': 31,
        'question': 'I felt that I was rather touchy.',
        'options': ['Did not apply to me at all', 'Applied to me to some degree', 'Applied to me to a considerable degree', 'Applied to me very much or most of the time'],
        'scores': [0, 1, 2, 3],
        'category': 'stress'
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

@app.route('/assessment')
@login_required
def assessment():
    # Check if user is an admin
    user_id = session.get('user', {}).get('id')
    if user_id:
        user_data = db.client.table('users').select('is_admin').eq('id', user_id).execute()
        if user_data.data and user_data.data[0].get('is_admin'):
            flash('Admins cannot take assessments. Please use a regular user account.', 'error')
            return redirect(url_for('admin_dashboard'))
    
    return render_template('assessment.html', questions=assessment_questions, active_page='assessment')

@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    try:
        answers = request.json.get('answers', {})
        
        # Calculate scores for each category
        category_scores = {
            'resilience': 0,
            'depression': 0,
            'anxiety': 0,
            'stress': 0
        }
        
        # Get scores for each question based on the answer index
        for question in assessment_questions:
            q_id = str(question['id'])
            if q_id in answers:
                answer_idx = answers[q_id]
                if 0 <= answer_idx < len(question['scores']):
                    category = question['category']
                    category_scores[category] += question['scores'][answer_idx]
        
        # Calculate total score (normalized to 0-100 for consistency)
        # Resilience is reversed scored (higher is better) while others are direct (lower is better)
        resilience_score = (category_scores['resilience'] / 40) * 100  # 10 questions * max 4 points = 40
        depression_score = (category_scores['depression'] / 21) * 100  # 7 questions * max 3 points = 21
        anxiety_score = (category_scores['anxiety'] / 21) * 100  # 7 questions * max 3 points = 21
        stress_score = (category_scores['stress'] / 21) * 100  # 7 questions * max 3 points = 21
        
        # Calculate overall score (0-100, lower is better for depression/anxiety/stress, higher for resilience)
        # We'll weight resilience as 40% and the others as 20% each
        overall_score = (resilience_score * 0.4) + (depression_score * -0.2) + (anxiety_score * -0.2) + (stress_score * -0.2)
        
        # Normalize to 0-100 scale
        overall_score = max(0, min(100, 50 + (overall_score / 2)))
        
        # Determine level based on overall score
        if overall_score >= 75:
            level = 'Very High Resilience'
            recommendation = 'Your responses suggest very high levels of resilience and low levels of distress. You seem to be managing challenges well. Continue with your healthy coping strategies.'
            color = 'green'
        elif overall_score >= 50:
            level = 'High Resilience'
            recommendation = 'Your responses suggest good resilience and relatively low levels of distress. You appear to be coping well with challenges. Consider exploring additional self-care strategies.'
            color = 'light-green'
        elif overall_score >= 25:
            level = 'Moderate Resilience'
            recommendation = 'Your responses suggest moderate resilience. You may be experiencing some challenges. Consider trying our self-help resources or speaking with a mental health professional for additional support.'
            color = 'yellow'
        else:
            level = 'Low Resilience'
            recommendation = 'Your responses suggest you may be experiencing significant distress. We recommend consulting with a mental health professional for proper evaluation and support.'
            color = 'red'
        
        # Prepare detailed results for each category
        category_results = {
            'resilience': {
                'score': resilience_score,
                'level': 'High' if resilience_score >= 70 else 'Moderate' if resilience_score >= 40 else 'Low'
            },
            'depression': {
                'score': depression_score,
                'level': 'Severe' if depression_score >= 67 else 'Moderate' if depression_score >= 34 else 'Mild' if depression_score > 0 else 'None'
            },
            'anxiety': {
                'score': anxiety_score,
                'level': 'Severe' if anxiety_score >= 67 else 'Moderate' if anxiety_score >= 34 else 'Mild' if anxiety_score > 0 else 'None'
            },
            'stress': {
                'score': stress_score,
                'level': 'Severe' if stress_score >= 67 else 'Moderate' if stress_score >= 34 else 'Mild' if stress_score > 0 else 'None'
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
            db.save_assessment_result(
                user_id=session['user']['id'],
                answers=answers,
                total_score=overall_score,
                level=level,
                recommendation=recommendation,
                category_scores={
                    'resilience': resilience_score,
                    'depression': depression_score,
                    'anxiety': anxiety_score,
                    'stress': stress_score
                },
                category_levels={
                    'resilience': category_results['resilience']['level'],
                    'depression': category_results['depression']['level'],
                    'anxiety': category_results['anxiety']['level'],
                    'stress': category_results['stress']['level']
                },
                recommendations=recommendations
            )
        
        return jsonify({
            'success': True,
            'overall_score': overall_score,
            'overall_level': level,
            'overall_description': recommendation,
            'resilience': {
                'score': resilience_score,
                'level': category_results['resilience']['level']
            },
            'depression': {
                'score': depression_score,
                'level': category_results['depression']['level']
            },
            'anxiety': {
                'score': anxiety_score,
                'level': category_results['anxiety']['level']
            },
            'stress': {
                'score': stress_score,
                'level': category_results['stress']['level']
            },
            'recommendations': recommendations
        })
        
    except Exception as e:
        print(f"Error processing assessment: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your assessment. Please try again.'}), 500
    
    return jsonify(result)

@app.route('/journal')
def journal():
    return render_template('journal.html', active_page='journal')

@app.route('/save_journal', methods=['POST'])
def save_journal():
    entry = request.json
    
    # Save to database if user is logged in
    if 'user' in session:
        db.save_journal_entry(
            session['user']['id'],
            entry.get('mood', ''),
            entry.get('anxiety', 0),
            entry.get('stress', 0),
            entry.get('entry', ''),
            entry.get('activities', [])
        )
        return jsonify({'success': True, 'message': 'Journal entry saved successfully!'})
    else:
        # For non-logged in users, store in session as before
        if 'journal_entries' not in session:
            session['journal_entries'] = []
        
        entry['timestamp'] = datetime.datetime.now().isoformat()
        session['journal_entries'].append(entry)
        session.modified = True
        return jsonify({'success': True, 'message': 'Journal entry saved to session'})

@app.route('/get_journal_entries')
def get_journal_entries():
    if 'user' in session:
        # Get entries from database for logged-in users
        entries = db.get_user_journal_entries(session['user']['id'])
        # Convert database entries to the format expected by frontend
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                'mood': entry['mood'],
                'anxiety': entry['anxiety_level'],
                'stress': entry['stress_level'],
                'entry': entry['entry_text'],
                'activities': eval(entry['helpful_activities']) if entry['helpful_activities'] else [],
                'timestamp': entry['created_at']
            })
        return jsonify(formatted_entries)
    else:
        # Return session-stored entries for non-logged in users
        return jsonify(session.get('journal_entries', []))

@app.route('/journal_stats')
def journal_stats():
    if 'user' in session:
        stats = db.get_journal_stats(session['user']['id'])
        return jsonify(stats)
    else:
        return jsonify([])

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html', active_page='chatbot')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')

    # Build context from chat and journal history
    context = ""
    user_id = None
    if 'user' in session:
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
            context += f"Recent mood: {latest.get('mood','-')}, Anxiety: {latest.get('anxiety_level','-')}, Stress: {latest.get('stress_level','-')}\n"
        for entry in reversed(journal_entries):
            context += f"[Journal Entry] {entry.get('title','')}: {entry.get('content','')}\n"

    # Build the prompt for Gemini
    prompt = f"{context}User: {user_message}\nAI:"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        bot_reply = response.text if hasattr(response, 'text') else "Sorry, I couldn't understand that."
    except Exception as e:
        bot_reply = f"An error occurred: {str(e)}"

    if user_id:
        db.save_chat_message(user_id, user_message, bot_reply)

    # Replace newlines with <br> for HTML display
    bot_reply_html = bot_reply.replace('\n', '<br>')
    return jsonify({'response': bot_reply_html})


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

    # Get user's latest assessment summary
    latest_summary = db.get_latest_assessment_summary(user_id)

    # Get recent assessments (last 5)
    assessments = db.get_user_assessments(user_id, limit=5)

    # Get journal stats
    journal_stats = db.journal_stats()

    # Get game scores
    game_scores = db.game_scores('all')

    # Get total game points
    total_points = db.get_total_game_points()

    return render_template('dashboard.html', 
                         latest_summary=latest_summary,
                         assessments=assessments,
                         journal_stats=journal_stats,
                         game_scores=game_scores,
                         total_points=total_points,
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
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        # Get search query if any
        search = request.args.get('search', '')
        
        # Calculate date for active users (last 24 hours)
        today = datetime.now(timezone.utc)
        today_minus_7_days = today - timedelta(days=7)
        
        # Get user activity data
        user_activity_query = """
        SELECT 
            u.id,
            u.email,
            u.created_at,
            u.last_login,
            u.is_admin,
            u.is_active,
            COUNT(DISTINCT a.id) as assessment_count,
            COUNT(DISTINCT j.id) as journal_count,
            COUNT(DISTINCT g.id) as game_sessions
        FROM users u
        LEFT JOIN assessments a ON a.user_id = u.id
        LEFT JOIN journal_entries j ON j.user_id = u.id
        LEFT JOIN game_sessions g ON g.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
        
        # Execute the query
        result = service_role_supabase.rpc('execute_sql', {'query': user_activity_query}).execute()
        all_users = result.data if hasattr(result, 'data') else []
        
        # Calculate activity scores and add to user data
        for user in all_users:
            # Simple activity score based on engagement metrics
            score = 0
            if user.get('last_login') and user['last_login']:
                days_since_active = (today - datetime.fromisoformat(user['last_login'])).days
                if days_since_active <= 1:
                    score += 50
                elif days_since_active <= 7:
                    score += 25
            
            # Add points for engagement
            score += min(20, user.get('assessment_count', 0) * 2)
            score += min(15, user.get('journal_count', 0) * 1.5)
            score += min(15, user.get('game_sessions', 0) * 1)
            
            user['activity_score'] = min(100, score)  # Cap at 100%
        
        # Filter users based on search
        if search:
            all_users = [u for u in all_users if search in u.get('email', '').lower()]
        
        # Calculate metrics for stats cards
        total_users = len(all_users)
        active_today_count = sum(1 for u in all_users 
                              if u.get('last_login') 
                              and (today - datetime.fromisoformat(u['last_login'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)).days == 0)
        
        new_this_week_count = sum(1 for u in all_users 
                                if datetime.fromisoformat(u['created_at'].replace('Z', '+00:00')) >= today_minus_7_days)
        
        admin_count = sum(1 for u in all_users if u.get('is_admin'))
        
        # Pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = all_users[start_idx:end_idx]
        total_pages = (total_users + per_page - 1) // per_page if total_users > 0 else 1
        
        return render_template('admin_users.html', 
                            users=paginated_users,
                            current_page=page,
                            total_pages=total_pages,
                            search=search,
                            active_today_count=active_today_count,
                            new_this_week_count=new_this_week_count,
                            admin_count=admin_count,
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
                            admin_count=0)

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

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    try:
        # Get dashboard statistics
        stats = {
            'total_users': get_total_users(),
            'active_users': get_active_users(),
            'new_users_today': get_new_users_today(),
            'total_admins': get_admin_count()
        }
        
        # Get recent activities
        activities = get_recent_activities(limit=5)
        
        # Get user growth data for the chart
        user_growth = get_user_growth_last_30_days()
        
        # Get recent signups for the table
        recent_signups = service_role_supabase.table('users')\
            .select('id,email,created_at,last_login')\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        return render_template('admin_dashboard.html', 
                            stats=stats,
                            activities=activities,
                            user_growth=user_growth,
                            recent_signups=recent_signups.data if hasattr(recent_signups, 'data') else [])
    except Exception as e:
        print(f"Error in admin_dashboard: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('admin_dashboard.html', 
                            stats={},
                            activities=[],
                            user_growth=[],
                            recent_signups=[])

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
        date_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = service_role_supabase.table('users')\
            .select('id', count='exact')\
            .gt('last_login', date_threshold)\
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
        if hasattr(query_result, 'data'):
            for row in query_result.data:
                if row['signup_date'] in result:
                    result[row['signup_date']] = row['user_count']
        
        # Convert to list of values in date order
        return [{'date': date, 'count': result[date]} for date in date_strs]
        
    except Exception as e:
        print(f"Error getting user growth data: {str(e)}")
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

@app.route('/assessment/history')
def assessment_history():
    if 'user' not in session:
        flash('Please log in to view your assessment history.', 'info')
        return redirect(url_for('login'))
    
    user_id = session['user']['id']
    assessments = db.get_user_assessments(user_id, limit=50)  # Limit to 50 most recent
    latest_summary = db.get_latest_assessment_summary(user_id)
    
    return render_template('assessment_history.html', 
                         assessments=assessments,
                         latest_summary=latest_summary)

@app.route('/api/assessments/export')
def export_assessments():
    if 'user' not in session:
        return jsonify({'error': 'Please log in to export your assessment data.'}), 401
    
    user_id = session['user']['id']
    assessments = db.get_user_assessments(user_id, limit=1000)  # Export up to 1000 most recent
    
    if not assessments:
        return jsonify({'error': 'No assessment data found to export.'}), 404
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Date', 'Resilience Score', 'Resilience Level', 
        'Depression Score', 'Depression Level',
        'Anxiety Score', 'Anxiety Level',
        'Stress Score', 'Stress Level',
        'Total Score', 'Overall Level'
    ])
    
    # Write data rows
    for assessment in assessments:
        writer.writerow([
            assessment.get('created_at', ''),
            assessment.get('resilience_score', ''),
            assessment.get('resilience_level', ''),
            assessment.get('depression_score', ''),
            assessment.get('depression_level', ''),
            assessment.get('anxiety_score', ''),
            assessment.get('anxiety_level', ''),
            assessment.get('stress_score', ''),
            assessment.get('stress_level', ''),
            assessment.get('total_score', ''),
            assessment.get('overall_level', '')
        ])
    
    # Prepare the response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'assessment_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/admin/api/user/<user_id>')
@admin_required
def get_user_details(user_id):
    try:
        # Get user details
        user_result = service_role_supabase.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not user_result.data:
            return jsonify({'error': 'User not found'}), 404
        
        user = user_result.data
        
        # Get user's assessment count and recent assessments
        assessment_result = service_role_supabase.table('assessments')\
            .select('id, created_at, assessment_type, score')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        # Get user's journal entries count and recent entries
        journal_result = service_role_supabase.table('journal_entries')\
            .select('id, created_at, title, mood')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        # Get user's game sessions count and recent sessions
        game_result = service_role_supabase.table('game_sessions')\
            .select('id, created_at, game_type, duration_seconds')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        # Get login history (last 5 logins)
        login_history = service_role_supabase.table('auth_logs')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('event_name', 'login')\
            .order('created_at', desc=True)\
            .limit(5)\
            .execute()
        
        # Calculate activity score (same as in admin_users)
        today = datetime.now(timezone.utc)
        score = 0
        
        if user.get('last_login'):
            last_login = datetime.fromisoformat(user['last_login'].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            days_since_active = (today - last_login).days
            if days_since_active == 0:
                score += 50
            elif days_since_active <= 7:
                score += 30
            elif days_since_active <= 30:
                score += 15
        
        # Count total activities for scoring
        total_assessments = len(assessment_result.data) if hasattr(assessment_result, 'data') else 0
        total_journals = len(journal_result.data) if hasattr(journal_result, 'data') else 0
        total_games = len(game_result.data) if hasattr(game_result, 'data') else 0
        
        engagement_score = 0
        engagement_score += min(20, total_assessments * 2)
        engagement_score += min(15, total_journals * 1.5)
        engagement_score += min(15, total_games * 1)
        
        # Prepare activity timeline
        activities = []
        
        # Add assessments to timeline
        for a in assessment_result.data:
            activities.append({
                'type': 'assessment',
                'id': a['id'],
                'title': f"Completed {a.get('assessment_type', 'assessment').title()}",
                'description': f"Score: {a.get('score', 'N/A')}",
                'timestamp': a['created_at'],
                'icon': 'clipboard2-check',
                'color': 'text-blue-500'
            })
        
        # Add journal entries to timeline
        for j in journal_result.data:
            activities.append({
                'type': 'journal',
                'id': j['id'],
                'title': f"Journal: {j.get('title', 'Untitled Entry')}",
                'description': f"Mood: {j.get('mood', 'N/A')}",
                'timestamp': j['created_at'],
                'icon': 'journal-text',
                'color': 'text-green-500'
            })
        
        # Add game sessions to timeline
        for g in game_result.data:
            minutes = int(g.get('duration_seconds', 0) / 60)
            activities.append({
                'type': 'game',
                'id': g['id'],
                'title': f"Played {g.get('game_type', 'game').title()}",
                'description': f"Duration: {minutes} min",
                'timestamp': g['created_at'],
                'icon': 'controller',
                'color': 'text-purple-500'
            })
        
        # Add logins to timeline
        for login in login_history.data:
            activities.append({
                'type': 'login',
                'id': login['id'],
                'title': 'Logged in',
                'description': f"From {login.get('ip_address', 'unknown IP')}",
                'timestamp': login['created_at'],
                'icon': 'box-arrow-in-right',
                'color': 'text-yellow-500'
            })
        
        # Sort activities by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        user['activity_score'] = min(100, score + engagement_score)
        user['assessment_count'] = total_assessments
        user['journal_count'] = total_journals
        user['game_sessions'] = total_games
        user['recent_activities'] = activities[:10]  # Limit to 10 most recent activities
        
        return jsonify(user)
        
    except Exception as e:
        print(f"Error fetching user details: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch user details'}), 500

@app.route('/admin/api/users/send-email', methods=['POST'])
@admin_required
def send_bulk_email():
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        subject = data.get('subject', '')
        content = data.get('content', '')
        
        if not user_ids:
            return jsonify({'success': False, 'error': 'No users selected'}), 400
            
        if not subject or not content:
            return jsonify({'success': False, 'error': 'Subject and content are required'}), 400
        
        # Get user emails
        result = service_role_supabase.table('users')\
            .select('email')\
            .in_('id', user_ids)\
            .execute()
        
        emails = [user['email'] for user in result.data]
        
        # In a real app, you would send the email here
        # For now, we'll just log it
        print(f"Sending email to {len(emails)} users")
        print(f"Subject: {subject}")
        print(f"Content: {content}")
        print("Recipients:", ', '.join(emails))
        
        # Simulate sending delay
        import time
        time.sleep(1)
        
        return jsonify({
            'success': True,
            'message': f'Email sent to {len(emails)} users'
        })
        
    except Exception as e:
        print(f"Error sending bulk email: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/users/activate', methods=['POST'])
@admin_required
def activate_users():
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'error': 'No users selected'}), 400
        
        # Update users to active
        result = service_role_supabase.table('users')\
            .update({'is_active': True})\
            .in_('id', user_ids)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': f'Activated {len(user_ids)} users'
        })
        
    except Exception as e:
        print(f"Error activating users: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/users/deactivate', methods=['POST'])
@admin_required
def deactivate_users():
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'error': 'No users selected'}), 400
        
        # Don't allow deactivating yourself
        current_user_id = session.get('user_id')
        if current_user_id in user_ids:
            return jsonify({
                'success': False,
                'error': 'You cannot deactivate your own account'
            }), 400
        
        # Update users to inactive
        result = service_role_supabase.table('users')\
            .update({'is_active': False})\
            .in_('id', user_ids)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': f'Deactivated {len(user_ids)} users'
        })
        
    except Exception as e:
        print(f"Error deactivating users: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/users/delete', methods=['POST'])
@admin_required
def delete_users():
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'error': 'No users selected'}), 400
        
        # Don't allow deleting yourself
        current_user_id = session.get('user_id')
        if current_user_id in user_ids:
            return jsonify({
                'success': False,
                'error': 'You cannot delete your own account'
            }), 400
        
        # In a production app, you might want to soft delete instead
        # or handle related data cleanup
        result = service_role_supabase.table('users')\
            .delete()\
            .in_('id', user_ids)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {len(user_ids)} users'
        })
        
    except Exception as e:
        print(f"Error deleting users: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/wellbeing/overview')
@admin_required
def get_wellbeing_overview():
    try:
        # Get all users with their journal entries
        result = service_role_supabase.rpc('execute_sql', {
            'query': """
            SELECT 
                u.id as user_id,
                u.email,
                u.full_name,
                COUNT(je.id) as journal_count,
                AVG(je.mood) as avg_mood,
                AVG(je.sleep_quality) as avg_sleep_quality,
                AVG(je.stress_level) as avg_stress_level,
                MAX(je.created_at) as last_entry_date,
                COUNT(CASE WHEN je.needs_follow_up = TRUE THEN 1 END) as needs_follow_up_count,
                COUNT(CASE WHEN je.sentiment_score < -0.3 THEN 1 END) as negative_entries_count
            FROM users u
            LEFT JOIN journal_entries je ON je.user_id = u.id
            GROUP BY u.id, u.email, u.full_name
            ORDER BY needs_follow_up_count DESC, negative_entries_count DESC
            """
        }).execute()
        
        users = result.data if hasattr(result, 'data') else []
        
        # Calculate overall statistics
        total_users = len(users)
        active_users = sum(1 for u in users if u.get('journal_count', 0) > 0)
        needs_attention = sum(1 for u in users if u.get('needs_follow_up_count', 0) > 0 or u.get('negative_entries_count', 0) >= 3)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'needs_attention': needs_attention,
                'engagement_rate': (active_users / total_users * 100) if total_users > 0 else 0
            },
            'users': users
        })
        
    except Exception as e:
        print(f"Error fetching wellbeing overview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/wellbeing/user/<user_id>')
@admin_required
def get_user_wellbeing(user_id):
    try:
        # Get user details
        user_result = service_role_supabase.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not user_result.data:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get journal entries with sentiment analysis
        entries_result = service_role_supabase.table('journal_entries')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('created_at', desc=True)\
            .limit(50)\
            .execute()
        
        entries = entries_result.data if hasattr(entries_result, 'data') else []
        
        # Calculate trends
        mood_trend = []
        stress_trend = []
        sleep_trend = []
        
        for entry in entries:
            mood_trend.append({
                'date': entry.get('created_at'),
                'value': entry.get('mood')
            })
            
            if 'stress_level' in entry:
                stress_trend.append({
                    'date': entry.get('created_at'),
                    'value': entry.get('stress_level')
                })
                
            if 'sleep_quality' in entry:
                sleep_trend.append({
                    'date': entry.get('created_at'),
                    'value': entry.get('sleep_quality')
                })
        
        # Get concerning patterns
        concerning_entries = [e for e in entries if e.get('needs_follow_up') or (e.get('sentiment_score', 0) < -0.3)]
        
        # Get resource recommendations
        recommendations = []
        if any(e.get('sentiment_score', 0) < -0.5 for e in entries[-3:]):
            recommendations.append({
                'type': 'resource',
                'title': 'Crisis Support',
                'description': 'User has shown multiple negative entries recently',
                'link': '/resources/crisis-support',
                'priority': 'high'
            })
        
        if any(e.get('sleep_quality', 5) < 3 for e in entries[-7:]):
            recommendations.append({
                'type': 'resource',
                'title': 'Sleep Hygiene Resources',
                'description': 'User has reported poor sleep quality',
                'link': '/resources/sleep-hygiene',
                'priority': 'medium'
            })
        
        return jsonify({
            'success': True,
            'user': user_result.data,
            'stats': {
                'total_entries': len(entries),
                'avg_mood': sum(e.get('mood', 0) for e in entries) / len(entries) if entries else 0,
                'concern_level': min(100, len(concerning_entries) * 10),  # Scale 0-100
                'last_entry': entries[0].get('created_at') if entries else None
            },
            'trends': {
                'mood': mood_trend,
                'stress': stress_trend,
                'sleep': sleep_trend
            },
            'concerning_entries': concerning_entries[:5],
            'recommendations': recommendations
        })
        
    except Exception as e:
        print(f"Error fetching user wellbeing: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/wellbeing')
@admin_required
def admin_wellbeing():
    # Get wellbeing overview data
    overview = get_wellbeing_overview()
    return render_template('admin_wellbeing.html', 
                         overview=overview,
                         current_user=session.get('user'))

@app.route('/admin/assessments')
@admin_required
def admin_assessments():
    # Get assessment history
    assessments = supabase.table('assessments')\
        .select('*')\
        .order('completed_at', desc=True)\
        .limit(100)\
        .execute()
    
    return render_template('assessment_history.html',
                         assessments=assessments.data,
                         current_user=session.get('user'))

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
    # Get all admin users
    admins = supabase.table('users')\
        .select('*')\
        .eq('is_admin', True)\
        .order('created_at', desc=True)\
        .execute()
    
    return render_template('admin_admins.html',
                         admins=admins.data,
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

if __name__ == '__main__':
    # Enable debug mode for development
    app.debug = True
    app.run(debug=True)