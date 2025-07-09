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
        """Get assessment history for a user"""
        try:
            result = self.client.table('assessment_results')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            return result.data if hasattr(result, 'data') else []
        except Exception as e:
            print(f"Error getting user assessments: {str(e)}")
            return []
            
    def get_latest_assessment_summary(self, user_id):
        """Get the latest assessment summary for a user"""
        try:
            result = self.client.table('assessment_results')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
                
            if not result.data or len(result.data) == 0:
                return None
                
            latest = result.data[0]
            return {
                'id': latest.get('id'),
                'date': latest.get('created_at'),
                'total_score': latest.get('total_score'),
                'level': latest.get('level'),
                'recommendation': latest.get('recommendation')
            }
        except Exception as e:
            print(f"Error getting latest assessment summary: {str(e)}")
            return None

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
            
    def get_total_game_points(self, user_id):
        """Calculate the user's total points from all game scores
        
        Args:
            user_id: The ID of the user
            
        Returns:
            int: Total points (sum of all game scores)
        """
        try:
            # First try to use the RPC function if it exists
            try:
                result = self.client.rpc(
                    'get_total_game_points',
                    {'p_user_id': user_id}
                ).execute()
                
                if result.data and isinstance(result.data, (int, float)):
                    return max(0, int(result.data))  # Ensure non-negative points
            except Exception as e:
                print(f"RPC call failed, falling back to direct query: {str(e)}")
            
            # Fallback to direct query if RPC fails
            result = self.client.table('game_scores') \
                .select('score') \
                .eq('user_id', user_id) \
                .execute()
                
            total = sum(score['score'] for score in result.data if score and 'score' in score)
            return max(0, total)  # Ensure non-negative points
            
        except Exception as e:
            print(f"Error calculating total game points: {str(e)}")
            return 0
            
    def get_available_game_points(self, user_id):
        """Calculate the user's available points for plant care actions
        
        Args:
            user_id: The ID of the user
            
        Returns:
            int: Available points (total points - points spent on plant care)
        """
        try:
            # First try to use the RPC function if it exists
            try:
                result = self.client.rpc(
                    'get_available_points',
                    {'p_user_id': user_id}
                ).execute()
                
                if result.data and isinstance(result.data, (int, float)):
                    return max(0, int(result.data))  # Ensure non-negative points
            except Exception as e:
                print(f"RPC call failed, falling back to direct calculation: {str(e)}")
            
            # Fallback to direct calculation if RPC fails
            try:
                # Get all positive points (from games)
                positive_result = self.client.table('game_scores') \
                    .select('score') \
                    .eq('user_id', user_id) \
                    .gt('score', 0) \
                    .execute()
                
                # Get all negative points (from plant care)
                negative_result = self.client.table('game_scores') \
                    .select('score') \
                    .eq('user_id', user_id) \
                    .lt('score', 0) \
                    .execute()
                
                total_positive = sum(score['score'] for score in positive_result.data if score and 'score' in score)
                total_negative = sum(abs(score['score']) for score in negative_result.data if score and 'score' in score)
                
                available = max(0, total_positive - total_negative)
                return available
                
            except Exception as e:
                print(f"Error calculating available game points: {str(e)}")
                return 0
                
        except Exception as e:
            print(f"Unexpected error in get_available_game_points: {str(e)}")
            return 0
            
    # Plant care methods
    def get_user_plant(self, user_id):
        """Get the user's plant data with graceful fallback for missing columns"""
        try:
            # First, try to get all columns that exist
            try:
                # Get the list of all columns in the table
                columns = [
                    'id', 'user_id', 'plant_type', 'growth_stage', 'water_count',
                    'is_wilting', 'last_watered', 'last_sunlight', 'last_fertilized',
                    'sunlight_level', 'fertilizer_level', 'created_at', 'updated_at'
                ]
                
                # Try to select all columns that exist
                result = self.client.table('user_plants') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .execute()
                    
                if result.data:
                    plant = result.data[0]
                    
                    # Ensure all expected fields exist with defaults
                    defaults = {
                        'plant_type': 'sunflower',
                        'growth_stage': 0,
                        'water_count': 0,
                        'is_wilting': False,
                        'last_watered': None,
                        'last_sunlight': None,
                        'last_fertilized': None,
                        'sunlight_level': 50,
                        'fertilizer_level': 50,
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    
                    # Set defaults for any missing fields
                    for key, default in defaults.items():
                        if key not in plant:
                            plant[key] = default
                    
                    return plant
                    
            except Exception as e:
                print(f"Error getting plant data: {str(e)}")
            
            # If we get here, something went wrong with the query
            # Return a default plant object
            return {
                'id': 'temp_' + str(hash(str(user_id))),
                'user_id': user_id,
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'water_count': 0,
                'is_wilting': False,
                'last_watered': None,
                'last_sunlight': None,
                'last_fertilized': None,
                'sunlight_level': 50,
                'fertilizer_level': 50,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Critical error in get_user_plant: {str(e)}")
            # Return a minimal plant object to prevent frontend errors
            return {
                'id': 'error_' + str(hash(str(user_id))),
                'user_id': user_id,
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'water_count': 0,
                'is_wilting': False,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
    def create_user_plant(self, user_id):
        """Create a new plant for the user"""
        try:
            # First, try to get any existing plant for this user
            try:
                existing_plant = self.client.table('user_plants') \
                    .select('id') \
                    .eq('user_id', user_id) \
                    .execute()
                if existing_plant.data:
                    # Return existing plant if found
                    return self.get_user_plant(user_id)
            except:
                pass  # Continue to create new plant if query fails
            
            # Start with minimal required fields
            plant_data = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Add optional fields if they exist
            optional_fields = {
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'water_count': 0,
                'is_wilting': False,
                'last_watered': None,
                'last_sunlight': None,
                'last_fertilized': None,
                'sunlight_level': 50,
                'fertilizer_level': 50
            }
            
            # Check each optional field and add if the column exists
            for field, default_value in optional_fields.items():
                try:
                    # Try to select the column to see if it exists
                    self.client.table('user_plants') \
                        .select(field) \
                        .limit(1) \
                        .execute()
                    # If no error, add the field to our insert data
                    plant_data[field] = default_value
                except Exception as e:
                    print(f"Column {field} not found, skipping...")
            
            # Insert the new plant
            result = self.client.table('user_plants').insert(plant_data).execute()
            
            if not result.data:
                raise Exception("Failed to create plant: No data returned from insert")
                
            # Get the full plant data to return
            return self.get_user_plant(user_id)
            
        except Exception as e:
            print(f"Error in create_user_plant: {str(e)}")
            # Try to return a minimal plant object even if the insert failed
            return {
                'id': 'temp_' + str(hash(str(user_id))),
                'user_id': user_id,
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'water_count': 0,
                'is_wilting': False,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
    def water_plant(self, user_id, points):
        """Water the user's plant and update growth
        
        Args:
            user_id: The ID of the user
            points: Number of points to spend on watering
            
        Returns:
            tuple: (success: bool, plant_data: dict, message: str)
        """
        try:
            # Get the user's plant or create a new one if it doesn't exist
            plant = self.get_user_plant(user_id)
            if not plant or 'id' not in plant or plant['id'].startswith(('temp_', 'error_')):
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate new water count (cap at 100)
            current_water = plant.get('water_count', 0)
            water_increase = min(points // 10, 10)  # Max 10 points per action
            new_water_count = min(current_water + water_increase, 100)
            
            # Prepare update data with only existing columns
            update_data = {
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Check and add each field if it exists in the schema
            try:
                self.client.table('user_plants').select('water_count').limit(1).execute()
                update_data['water_count'] = new_water_count
            except:
                print("water_count column not found, skipping...")
            
            try:
                self.client.table('user_plants').select('last_watered').limit(1).execute()
                update_data['last_watered'] = datetime.utcnow().isoformat()
            except:
                print("last_watered column not found, skipping...")
                
            try:
                self.client.table('user_plants').select('is_wilting').limit(1).execute()
                update_data['is_wilting'] = False
            except:
                print("is_wilting column not found, skipping...")
            
            # Only proceed with update if we have fields to update
            if len(update_data) > 1:  # More than just updated_at
                updated_plant = self.client.table('user_plants') \
                    .update(update_data) \
                    .eq('user_id', user_id) \
                    .execute()
                    
                if not updated_plant.data:
                    return False, None, "Failed to update plant"
                
                # Get the updated plant data
                plant_data = updated_plant.data[0]
            else:
                # If no columns were updated, use the current plant data
                plant_data = plant
            
            # Deduct points if we have a valid plant
            if 'id' in plant_data and not plant_data['id'].startswith(('temp_', 'error_')):
                try:
                    self.save_game_score(
                        user_id=user_id,
                        game_type='plant_care',
                        score=-points,
                        level=1,
                        metadata={'action': 'water'}
                    )
                except Exception as e:
                    print(f"Warning: Could not save game score: {str(e)}")
            
            # Ensure all expected fields are in the response
            defaults = {
                'water_count': new_water_count,
                'is_wilting': False,
                'last_watered': datetime.utcnow().isoformat(),
                'plant_type': 'sunflower',
                'growth_stage': plant.get('growth_stage', 0)
            }
            
            for key, value in defaults.items():
                if key not in plant_data:
                    plant_data[key] = value
                
            return True, plant_data, "Plant watered successfully"
            
        except Exception as e:
            print(f"Error in water_plant: {str(e)}")
            # Return the best available plant data even in case of error
            error_plant = self.get_user_plant(user_id) or {
                'id': 'error',
                'user_id': user_id,
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'water_count': 0,
                'is_wilting': True,
                'error': str(e)
            }
            return False, error_plant, f"Error watering plant: {str(e)}"
            
    def give_sunlight(self, user_id, points):
        """Give sunlight to the user's plant
        
        Args:
            user_id: The ID of the user
            points: Number of points to spend on sunlight
            
        Returns:
            tuple: (success: bool, plant_data: dict, message: str)
        """
        try:
            # Get the user's plant or create a new one if it doesn't exist
            plant = self.get_user_plant(user_id)
            if not plant or 'id' not in plant or plant['id'].startswith(('temp_', 'error_')):
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate new sunlight level (cap at 100)
            current_sunlight = plant.get('sunlight_level', 50)
            sunlight_increase = min(points // 5, 20)  # Max 20 points per action
            new_sunlight = min(current_sunlight + sunlight_increase, 100)
            
            # Calculate potential growth stage increase (every 20 points)
            current_growth = plant.get('growth_stage', 0)
            growth_increase = min(points // 20, 10 - current_growth)
            new_growth_stage = current_growth + growth_increase
            
            # Prepare update data with only existing columns
            update_data = {
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Check and add each field if it exists in the schema
            try:
                self.client.table('user_plants').select('sunlight_level').limit(1).execute()
                update_data['sunlight_level'] = new_sunlight
            except:
                print("sunlight_level column not found, skipping...")
            
            try:
                self.client.table('user_plants').select('growth_stage').limit(1).execute()
                update_data['growth_stage'] = new_growth_stage
            except:
                print("growth_stage column not found, skipping...")
            
            try:
                self.client.table('user_plants').select('last_sunlight').limit(1).execute()
                update_data['last_sunlight'] = datetime.utcnow().isoformat()
            except:
                print("last_sunlight column not found, skipping...")
                
            try:
                self.client.table('user_plants').select('is_wilting').limit(1).execute()
                update_data['is_wilting'] = False
            except:
                print("is_wilting column not found, skipping...")
            
            # Only proceed with update if we have fields to update
            if len(update_data) > 1:  # More than just updated_at
                updated_plant = self.client.table('user_plants') \
                    .update(update_data) \
                    .eq('user_id', user_id) \
                    .execute()
                    
                if not updated_plant.data:
                    return False, None, "Failed to update plant"
                
                # Get the updated plant data
                plant_data = updated_plant.data[0]
            else:
                # If no columns were updated, use the current plant data
                plant_data = plant
            
            # Deduct points if we have a valid plant
            if 'id' in plant_data and not plant_data['id'].startswith(('temp_', 'error_')):
                try:
                    self.save_game_score(
                        user_id=user_id,
                        game_type='plant_care',
                        score=-points,
                        level=1,
                        metadata={'action': 'sunlight'}
                    )
                except Exception as e:
                    print(f"Warning: Could not save game score: {str(e)}")
            
            # Ensure all expected fields are in the response
            defaults = {
                'sunlight_level': new_sunlight,
                'growth_stage': new_growth_stage,
                'is_wilting': False,
                'last_sunlight': datetime.utcnow().isoformat(),
                'plant_type': plant.get('plant_type', 'sunflower'),
                'water_count': plant.get('water_count', 0)
            }
            
            for key, value in defaults.items():
                if key not in plant_data:
                    plant_data[key] = value
                
            return True, plant_data, "Sunlight given to plant successfully"
            
        except Exception as e:
            print(f"Error in give_sunlight: {str(e)}")
            # Return the best available plant data even in case of error
            error_plant = self.get_user_plant(user_id) or {
                'id': 'error',
                'user_id': user_id,
                'plant_type': 'sunflower',
                'growth_stage': 0,
                'sunlight_level': 0,
                'is_wilting': True,
                'error': str(e)
            }
            return False, error_plant, f"Error giving sunlight to plant: {str(e)}"
            
    def give_fertilizer(self, user_id, points):
        """Give fertilizer to the user's plant
        
        Args:
            user_id: The ID of the user
            points: Number of points to spend on fertilizer
            
        Returns:
            tuple: (success: bool, plant_data: dict, message: str)
        """
        try:
            # Get the user's plant
            plant = self.get_user_plant(user_id)
            if not plant:
                plant = self.create_user_plant(user_id)
                if not plant:
                    return False, None, "Failed to create plant"
            
            # Calculate growth boost (based on points spent)
            current_growth = plant.get('growth_stage', 0)
            growth_boost = points // 15
            new_growth_stage = min(current_growth + growth_boost, 10)
            
            # Prepare update data with only existing columns
            update_data = {
                'growth_stage': new_growth_stage,
                'updated_at': 'now()'
            }
            
            # Only include these fields if they exist in the schema
            try:
                self.client.table('user_plants').select('last_fertilized').limit(1).execute()
                update_data['last_fertilized'] = datetime.utcnow().isoformat()
            except:
                pass
                
            try:
                self.client.table('user_plants').select('is_wilting').limit(1).execute()
                update_data['is_wilting'] = False
            except:
                pass
            
            # Update the plant
            updated_plant = self.client.table('user_plants') \
                .update(update_data) \
                .eq('user_id', user_id) \
                .execute()
                
            if not updated_plant.data:
                return False, None, "Failed to update plant"
                
            # Deduct points
            self.save_game_score(
                user_id=user_id,
                game_type='plant_care',
                score=-points,
                level=1,
                metadata={'action': 'fertilizer'}
            )
            
            # Get the updated plant data
            updated_plant_data = updated_plant.data[0]
            
            # Ensure all expected fields are in the response
            if 'is_wilting' not in updated_plant_data:
                updated_plant_data['is_wilting'] = False
            if 'last_fertilized' not in updated_plant_data:
                updated_plant_data['last_fertilized'] = datetime.utcnow().isoformat()
                
            return True, updated_plant_data, "Fertilizer given to plant successfully"
            
        except Exception as e:
            print(f"Error in give_fertilizer: {str(e)}")
            return False, None, str(e)