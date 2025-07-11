from datetime import datetime, timezone, timedelta
from flask import jsonify
from supabase import Client

def get_user_stats(supabase: Client, user_id: str) -> dict:
    """
    Get comprehensive stats for a user
    """
    try:
        # Get basic user info
        user_data = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user_data.data:
            return {'error': 'User not found'}, 404
            
        user = user_data.data[0]
        
        # Get counts for each feature
        stats = {
            'assessments': 0,
            'journal_entries': 0,
            'game_sessions': 0,
            'breathing_sessions': 0,
            'last_active': user.get('last_login_at')
        }
        
        # Get assessment count
        try:
            assessment_count = supabase.table('assessments') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .execute()
            stats['assessments'] = assessment_count.count if hasattr(assessment_count, 'count') else 0
        except Exception as e:
            print(f"Error getting assessment count: {str(e)}")
            
        # Get journal entry count
        try:
            journal_count = supabase.table('journal_entries') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .execute()
            stats['journal_entries'] = journal_count.count if hasattr(journal_count, 'count') else 0
        except Exception as e:
            print(f"Error getting journal count: {str(e)}")
            
        # Get game session count
        try:
            game_sessions = supabase.table('game_sessions') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .execute()
            stats['game_sessions'] = game_sessions.count if hasattr(game_sessions, 'count') else 0
        except Exception as e:
            print(f"Error getting game sessions: {str(e)}")
            
        # Get breathing session count
        try:
            breathing_sessions = supabase.table('breathing_sessions') \
                .select('id', count='exact') \
                .eq('user_id', user_id) \
                .execute()
            stats['breathing_sessions'] = breathing_sessions.count if hasattr(breathing_sessions, 'count') else 0
        except Exception as e:
            print(f"Error getting breathing sessions: {str(e)}")
            
        return stats
        
    except Exception as e:
        print(f"Error in get_user_stats: {str(e)}")
        return {'error': str(e)}, 500

def update_user_status(supabase: Client, user_id: str, is_active: bool) -> tuple[dict, int]:
    """
    Update user active status
    """
    try:
        # Update the user's active status
        result = supabase.table('users') \
            .update({'is_active': is_active, 'updated_at': datetime.now(timezone.utc).isoformat()}) \
            .eq('id', user_id) \
            .execute()
            
        if not result.data:
            return {'error': 'User not found'}, 404
            
        return {'message': 'User status updated successfully'}, 200
        
    except Exception as e:
        print(f"Error updating user status: {str(e)}")
        return {'error': str(e)}, 500

def get_user_activity(supabase: Client, user_id: str, days: int = 30) -> dict:
    """
    Get user activity for the last N days
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get journal entries
        journal_entries = supabase.table('journal_entries') \
            .select('created_at') \
            .eq('user_id', user_id) \
            .gte('created_at', start_date.isoformat()) \
            .lte('created_at', end_date.isoformat()) \
            .execute()
            
        # Get assessment submissions
        assessments = supabase.table('assessments') \
            .select('created_at') \
            .eq('user_id', user_id) \
            .gte('created_at', start_date.isoformat()) \
            .lte('created_at', end_date.isoformat()) \
            .execute()
            
        # Format response
        return {
            'journal_entries': [entry['created_at'] for entry in journal_entries.data],
            'assessments': [assess['created_at'] for assess in assessments.data],
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
    except Exception as e:
        print(f"Error getting user activity: {str(e)}")
        return {'error': str(e)}
