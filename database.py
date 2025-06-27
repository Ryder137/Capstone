import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_path='unicare.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Assessment results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                answers TEXT NOT NULL,
                total_score INTEGER NOT NULL,
                level TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Journal entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                mood TEXT NOT NULL,
                anxiety_level INTEGER NOT NULL,
                stress_level INTEGER NOT NULL,
                entry_text TEXT,
                helpful_activities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Game scores table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                level INTEGER DEFAULT 1,
                duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Breathing sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breathing_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                technique TEXT NOT NULL,
                duration INTEGER NOT NULL,
                completed BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Chat messages table (for chatbot history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    
    # User management methods
    def create_user(self, name, email, password):
        """Create a new user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = generate_password_hash(password)
        
        try:
            cursor.execute('''
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?)
            ''', (name, email, password_hash))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None  # Email already exists
    
    def get_user_by_email(self, email):
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def verify_password(self, email, password):
        """Verify user password"""
        user = self.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None
    
    def update_last_login(self, user_id):
        """Update user's last login time"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    # Assessment methods
    def save_assessment_result(self, user_id, answers, total_score, level, recommendation):
        """Save assessment result"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO assessment_results (user_id, answers, total_score, level, recommendation)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, str(answers), total_score, level, recommendation))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_assessments(self, user_id, limit=10):
        """Get user's assessment history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM assessment_results 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        assessments = cursor.fetchall()
        conn.close()
        
        return [dict(assessment) for assessment in assessments]
    
    # Journal methods
    def save_journal_entry(self, user_id, mood, anxiety_level, stress_level, entry_text, helpful_activities):
        """Save journal entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO journal_entries (user_id, mood, anxiety_level, stress_level, entry_text, helpful_activities)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, mood, anxiety_level, stress_level, entry_text, str(helpful_activities)))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_journal_entries(self, user_id, limit=50):
        """Get user's journal entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM journal_entries 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        entries = cursor.fetchall()
        conn.close()
        
        return [dict(entry) for entry in entries]
    
    def get_journal_stats(self, user_id, days=30):
        """Get journal statistics for the user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_entries,
                AVG(anxiety_level) as avg_anxiety,
                AVG(stress_level) as avg_stress,
                mood,
                COUNT(mood) as mood_count
            FROM journal_entries 
            WHERE user_id = ? 
            AND created_at >= date('now', '-{} days')
            GROUP BY mood
            ORDER BY mood_count DESC
        '''.format(days), (user_id,))
        stats = cursor.fetchall()
        conn.close()
        
        return [dict(stat) for stat in stats]
    
    # Game scores methods
    def save_game_score(self, user_id, game_type, score, level=1, duration=None):
        """Save game score"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO game_scores (user_id, game_type, score, level, duration)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, game_type, score, level, duration))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_game_scores(self, user_id, game_type=None, limit=10):
        """Get user's game scores"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if game_type:
            cursor.execute('''
                SELECT * FROM game_scores 
                WHERE user_id = ? AND game_type = ?
                ORDER BY score DESC, created_at DESC 
                LIMIT ?
            ''', (user_id, game_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM game_scores 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
        
        scores = cursor.fetchall()
        conn.close()
        
        return [dict(score) for score in scores]
    
    def get_leaderboard(self, game_type, limit=10):
        """Get game leaderboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.name, gs.score, gs.level, gs.created_at
            FROM game_scores gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.game_type = ?
            ORDER BY gs.score DESC
            LIMIT ?
        ''', (game_type, limit))
        leaderboard = cursor.fetchall()
        conn.close()
        
        return [dict(entry) for entry in leaderboard]
    
    # Breathing sessions methods
    def save_breathing_session(self, user_id, technique, duration, completed=True):
        """Save breathing session"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO breathing_sessions (user_id, technique, duration, completed)
            VALUES (?, ?, ?, ?)
        ''', (user_id, technique, duration, completed))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_breathing_sessions(self, user_id, limit=20):
        """Get user's breathing sessions"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM breathing_sessions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        sessions = cursor.fetchall()
        conn.close()
        
        return [dict(session) for session in sessions]
    
    def get_breathing_stats(self, user_id, days=30):
        """Get breathing session statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration) as total_duration,
                AVG(duration) as avg_duration,
                technique,
                COUNT(technique) as technique_count
            FROM breathing_sessions 
            WHERE user_id = ? 
            AND created_at >= date('now', '-{} days')
            AND completed = 1
            GROUP BY technique
        '''.format(days), (user_id,))
        stats = cursor.fetchall()
        conn.close()
        
        return [dict(stat) for stat in stats]
    
    # Chat history methods
    def save_chat_message(self, user_id, message, response):
        """Save chat message and response"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO chat_messages (user_id, message, response)
            VALUES (?, ?, ?)
        ''', (user_id, message, response))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_chat_history(self, user_id, limit=50):
        """Get user's chat history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM chat_messages 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        messages = cursor.fetchall()
        conn.close()
        
        return [dict(message) for message in messages]