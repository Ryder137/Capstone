from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import json
import datetime
import random
import os
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
import google.generativeai as genai

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configure your API key
genai.configure(api_key="AIzaSyBsGyRDXKX5X1tmi3Tf8VrjyucqU6NgRkw")

# Initialize the model (you can switch to 'gemini-pro' or 'gemini-1.5-flash' to avoid quota issues)
model = genai.GenerativeModel("gemini-1.5-pro")

# Set system instructions (this is like telling the AI how to behave)
chat = model.start_chat(
    system_instruction="You are a friendly mental health chatbot that responds briefly, empathetically, and uses easy-to-understand language."
)



# Initialize database
db = Database()

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
    return render_template('index.html')

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
    
    # Verify user credentials using database
    user = db.verify_password(email, password)
    
    if user:
        session['user'] = {
            'id': user['id'],
            'email': user['email'],
            'name': user['name']
        }
        db.update_last_login(user['id'])
        flash(f'Welcome back, {user["name"]}!', 'success')
        return redirect(url_for('index'))
    else:
        flash('Invalid email or password.', 'error')
        return redirect(url_for('login'))

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
    return render_template('assessment.html', questions=assessment_questions)

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
    return render_template('journal.html')

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
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        response = model.generate_content(user_message)

        bot_reply = response.text if hasattr(response, 'text') else "Sorry, I couldn't understand that."

    except Exception as e:
        bot_reply = f"An error occurred: {str(e)}"

    if 'user' in session:
        db.save_chat_message(session['user']['id'], user_message, bot_reply)

    return jsonify({'response': bot_reply})

@app.route('/chat_history')
def chat_history():
    if 'user' in session:
        history = db.get_user_chat_history(session['user']['id'])
        return jsonify(history)
    else:
        return jsonify([])

@app.route('/games')
def games():
    return render_template('games.html', games=mental_games)

@app.route('/game/<int:game_id>')
def play_game(game_id):
    game = next((g for g in mental_games if g['id'] == game_id), None)
    if not game:
        return redirect(url_for('games'))
    return render_template(f'game_{game["type"]}.html', game=game)

@app.route('/breathing')
def breathing():
    return render_template('breathing.html')

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

if __name__ == '__main__':
    app.run(debug=True)