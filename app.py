from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import json
import datetime
import random
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import google.generativeai as genai
from database import Database

db = Database()

# Load environment variables from .env
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    {
        'id': 1,
        'question': 'Over the last 2 weeks, how often have you been bothered by feeling down, depressed, or hopeless?',
        'options': ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
        'scores': [0, 1, 2, 3]
    },
    {
        'id': 2,
        'question': 'Over the last 2 weeks, how often have you been bothered by little interest or pleasure in doing things?',
        'options': ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
        'scores': [0, 1, 2, 3]
    },
    {
        'id': 3,
        'question': 'Over the last 2 weeks, how often have you been bothered by trouble falling or staying asleep?',
        'options': ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
        'scores': [0, 1, 2, 3]
    },
    {
        'id': 4,
        'question': 'Over the last 2 weeks, how often have you been bothered by feeling tired or having little energy?',
        'options': ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
        'scores': [0, 1, 2, 3]
    },
    {
        'id': 5,
        'question': 'Over the last 2 weeks, how often have you been bothered by poor appetite or overeating?',
        'options': ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'],
        'scores': [0, 1, 2, 3]
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

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login', methods=['POST'])
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
        
        if response.get('error'):
            flash(response['error']['message'], 'error')
            return redirect(url_for('login'))
        
        # Get user data
        user = response['user']
        
        # Check admin status using the users table
        user_data = supabase.table('users').select('is_admin').eq('id', user['id']).single().execute()
        is_admin = user_data['data'] and user_data['data'].get('is_admin', False)
        
        # Store user data in session
        session['user'] = {
            'id': user['id'],
            'email': user['email'],
            'is_admin': is_admin
        }
        
        flash('Welcome back!', 'success')
        if is_admin:
            return redirect(url_for('dashboard'))
        return redirect(url_for('index'))
        
    except Exception as e:
        flash('Authentication failed. Please try again.', 'error')
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
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validation
    if not all([name, email, password, confirm_password]):
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('signup'))
    
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('signup'))
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('signup'))
    
    # Create user in database
    user_id = db.create_user(name, email, password)
    
    if user_id:
        # Auto-login after signup
        session['user'] = {
            'id': user_id,
            'email': email,
            'name': name
        }
        db.update_last_login(user_id)
        flash(f'Account created successfully! Welcome to UniCare, {name}!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Email already registered. Please use a different email or login.', 'error')
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
def assessment():
    return render_template('assessment.html', questions=assessment_questions, active_page='assessment')

@app.route('/submit_assessment', methods=['POST'])
def submit_assessment():
    answers = request.json.get('answers', [])
    total_score = sum(answers)
    
    if total_score <= 4:
        level = 'Minimal'
        recommendation = 'Your responses suggest minimal signs of depression or anxiety. Continue with healthy lifestyle practices.'
        color = 'green'
    elif total_score <= 9:
        level = 'Mild'
        recommendation = 'Your responses suggest mild symptoms. Consider speaking with a mental health professional or trying our self-help resources.'
        color = 'yellow'
    elif total_score <= 14:
        level = 'Moderate'
        recommendation = 'Your responses suggest moderate symptoms. We recommend consulting with a mental health professional for proper evaluation and support.'
        color = 'orange'
    else:
        level = 'Severe'
        recommendation = 'Your responses suggest severe symptoms. Please seek immediate professional help from a mental health provider.'
        color = 'red'
    
    # Save to database if user is logged in
    if 'user' in session:
        db.save_assessment_result(
            session['user']['id'], 
            answers, 
            total_score, 
            level, 
            recommendation
        )
    
    result = {
        'score': total_score,
        'level': level,
        'recommendation': recommendation,
        'color': color
    }
    
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
    return render_template('games.html', active_page='games', games=mental_games)

@app.route('/game/<int:game_id>')
def play_game(game_id):
    game = next((g for g in mental_games if g['id'] == game_id), None)
    if not game:
        return redirect(url_for('games'))
    return render_template(f'game_{game["type"]}.html', active_page='games', game=game)
    return render_template(f'game_{game["type"]}.html', game=game)

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
def save_game_score():
    if 'user' in session:
        data = request.json
        score_id = db.save_game_score(
            session['user']['id'],
            data.get('game_type', ''),
            data.get('score', 0),
            data.get('level', 1),
            data.get('duration', None)
        )
        return jsonify({'success': True, 'score_id': score_id})
    else:
        return jsonify({'success': False, 'message': 'Please log in to save your scores'})

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

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access your dashboard.', 'info')
        return redirect(url_for('login'))
    
    user_id = session['user']['id']
    
    # Get user statistics
    recent_assessments = db.get_user_assessments(user_id, limit=5)
    recent_journal_entries = db.get_user_journal_entries(user_id, limit=5)
    journal_stats = db.get_journal_stats(user_id)
    breathing_stats = db.get_breathing_stats(user_id)
    recent_game_scores = db.get_user_game_scores(user_id, limit=10)
    
    return render_template('dashboard.html', 
                         assessments=recent_assessments,
                         journal_entries=recent_journal_entries,
                         journal_stats=journal_stats,
                         breathing_stats=breathing_stats,
                         game_scores=recent_game_scores)

@app.route('/book-appointment')
def book_appointment():
    doctor_id = request.args.get('doctor_id')
    selected_doctor = None
    if doctor_id:
        selected_doctor = next((d for d in doctors_data if d['id'] == int(doctor_id)), None)
    return render_template('book_appointment.html', doctors=doctors_data, selected_doctor=selected_doctor)

# --- ADMIN LOGIN ROUTES & PROTECTION ---
from functools import wraps

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
    users = supabase.table('users').select('id', 'email', 'is_admin').execute().data
    return render_template('admin_users.html', users=users)

@app.route('/admin/set-admin/<user_id>', methods=['POST'])
@admin_required
def set_admin(user_id):
    supabase.table('users').update({'is_admin': True}).eq('id', user_id).execute()
    flash('User promoted to admin.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/unset-admin/<user_id>', methods=['POST'])
@admin_required
def unset_admin(user_id):
    supabase.table('users').update({'is_admin': False}).eq('id', user_id).execute()
    flash('Admin rights removed.', 'success')
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
        return redirect(url_for('admin_dashboard'))
        
    # Original login logic for production
    email = request.form.get('email')
    password = request.form.get('password')
    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('admin_login'))
        
    # No email domain check - we'll only check the is_admin flag
    try:
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        print("Supabase admin login response:", response)  # Debug line
        if response.get('error'):
            flash(response['error']['message'], 'error')
            return redirect(url_for('admin_login'))
        user = response['user']
        user_id = user['id']
        # Check if user exists and is admin
        user_data = supabase.table('users').select('is_admin').eq('email', email).single().execute()
        if not user_data['data'] or not user_data['data'].get('is_admin'):
            flash('You are not authorized as admin.', 'error')
            return redirect(url_for('admin_login'))
            
        # Store user data in session
        session['user'] = {
            'id': user['id'],
            'email': user['email'],
            'is_admin': True
        }
        flash('Welcome, admin!', 'success')
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # You can customize this to show admin-specific stats
    return render_template('admin_dashboard.html')

if __name__ == '__main__':
    # Enable debug mode for development
    app.debug = True
    app.run(debug=True)