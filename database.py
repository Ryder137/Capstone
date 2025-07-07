import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY

class Database:
    def __init__(self):
        """Initialize Supabase client"""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def init_db(self):
        """Initialize Supabase tables if they don't exist"""
        # Supabase tables are created through the Supabase dashboard or API
        # This method is kept for compatibility but does nothing in Supabase
        pass

    # User management methods
    def create_user(self, name, email, password):
        """Create a new user using Supabase Auth and sync profile info to users table"""
        try:
            # Register user with Supabase Auth
            result = self.client.auth.sign_up({
                'email': email,
                'password': password
            })
            print("Supabase sign_up result:", result)
            if result.user:
                user_id = result.user.id
                # Insert profile info into users table (no password)
                insert_result = self.client.table('users').insert({
                    'id': user_id,
                    'user_id': user_id,
                    'email': email
                }).execute()
                print("Insert result:", insert_result)
                if getattr(insert_result, 'error', None):
                    print("Insert error:", insert_result.error)
                    return None
                return user_id
            elif result.error:
                print("Error: Supabase Auth registration failed:", result.error)
                return None
            else:
                print("Unknown error during Supabase Auth registration.")
                return None
        except Exception as e:
            print(f"Error creating user with Supabase Auth: {str(e)}")
            return None

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            result = self.client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by email: {str(e)}")
            return None

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            result = self.client.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None

    def verify_password(self, email, password):
        """Verify user password"""
        user = self.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None

    def update_last_login(self, user_id):
        """Update user's last login time"""
        try:
            self.client.table('users').update({
                'last_login': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()
        except Exception as e:
            print(f"Error updating last login: {str(e)}")

    # Assessment methods
    def save_assessment_result(self, user_id, answers, total_score, level, recommendation):
        """Save assessment result"""
        try:
            result = self.client.table('assessment_results').insert({
                'user_id': user_id,
                'answers': str(answers),
                'total_score': total_score,
                'level': level,
                'recommendation': recommendation,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            return result.data[0]['id']
        except Exception as e:
            print(f"Error saving assessment result: {str(e)}")
            return None

    def get_user_assessments(self, user_id, limit=10):
        """Get user's assessment history"""
        try:
            result = self.client.table('assessment_results') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting user assessments: {str(e)}")
            return []

    # Journal methods
    def save_journal_entry(self, user_id, mood, anxiety_level, stress_level, entry_text, helpful_activities):
        """Save journal entry"""
        try:
            result = self.client.table('journal_entries').insert({
                'user_id': user_id,
                'mood': mood,
                'anxiety_level': anxiety_level,
                'stress_level': stress_level,
                'entry_text': entry_text,
                'helpful_activities': str(helpful_activities),
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            return result.data[0]['id']
        except Exception as e:
            print(f"Error saving journal entry: {str(e)}")
            return None

        
        cursor.execute('''
            INSERT INTO journal_entries (user_id, mood, anxiety_level, stress_level, entry_text, helpful_activities)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, mood, anxiety_level, stress_level, entry_text, str(helpful_activities)))
        conn.commit()
        conn.close()
        
        return cursor.lastrowid
    
    def get_user_journal_entries(self, user_id, limit=50):
        """Get user's journal entries"""
        try:
            result = self.client.table('journal_entries') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting journal entries: {str(e)}")
            return []

    
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
        try:
            result = self.client.table('chat_messages').insert({
                'user_id': user_id,
                'message': message,
                'response': response,
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            return result.data[0]['id'] if result.data else None
        except Exception as e:
            print(f"Error saving chat message: {str(e)}")
            return None
    
    def get_user_chat_history(self, user_id, limit=50):
        """Get user's chat history"""
        try:
            result = self.client.table('chat_messages') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            return result.data
        except Exception as e:
            print(f"Error getting chat history: {str(e)}")
            return []