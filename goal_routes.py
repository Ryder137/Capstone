from flask import Blueprint, jsonify, request, session
from database import Database
from datetime import datetime, timedelta
import json

goal_bp = Blueprint('goals', __name__)
db = Database()

@goal_bp.route('/api/goals/categories', methods=['GET'])
def get_goal_categories():
    """Get all goal categories"""
    try:
        result = db.client.table('goal_categories') \
            .select('*') \
            .order('name') \
            .execute()
            
        return jsonify(result.data or [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals', methods=['GET'])
def get_user_goals():
    """Get all goals for the current user"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        user_id = session['user']['id']
        
        # Get active goals (not completed and not past due)
        result = db.client.table('user_goals') \
            .select('*, goal_categories(name, icon)') \
            .eq('user_id', user_id) \
            .eq('is_completed', False) \
            .order('created_at', desc=True) \
            .execute()
            
        return jsonify(result.data or [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals/completed', methods=['GET'])
def get_completed_goals():
    """Get completed goals for the current user"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    try:
        user_id = session['user']['id']
        
        # Get completed goals
        result = db.client.table('user_goals') \
            .select('*, goal_categories(name, icon)') \
            .eq('user_id', user_id) \
            .eq('is_completed', True) \
            .order('completed_at', desc=True) \
            .limit(20) \
            .execute()
            
        return jsonify(result.data or [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals', methods=['POST'])
def create_goal():
    """Create a new goal"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    data = request.get_json()
    user_id = session['user']['id']
    
    required_fields = ['title', 'category_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        goal_data = {
            'user_id': user_id,
            'title': data['title'],
            'description': data.get('description', ''),
            'category_id': data['category_id'],
            'target_value': data.get('target_value'),
            'current_value': data.get('current_value', 0),
            'frequency': data.get('frequency', 'once'),
            'xp_reward': data.get('xp_reward', 10),
            'is_completed': False
        }
        
        # Set target date if provided
        if 'target_date' in data:
            goal_data['target_date'] = data['target_date']
        
        result = db.client.table('user_goals') \
            .insert(goal_data) \
            .execute()
            
        if not result.data:
            return jsonify({'error': 'Failed to create goal'}), 500
            
        # Get the full goal data with category info
        new_goal = db.client.table('user_goals') \
            .select('*, goal_categories(name, icon)') \
            .eq('id', result.data[0]['id']) \
            .single() \
            .execute()
            
        return jsonify(new_goal.data), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals/<goal_id>', methods=['PUT'])
def update_goal(goal_id):
    """Update a goal"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    data = request.get_json()
    user_id = session['user']['id']
    
    try:
        # First verify the goal belongs to the user
        existing_goal = db.client.table('user_goals') \
            .select('*') \
            .eq('id', goal_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()
            
        if not existing_goal.data:
            return jsonify({'error': 'Goal not found'}), 404
            
        # Prepare update data
        update_data = {}
        
        # Only include fields that are being updated
        for field in ['title', 'description', 'category_id', 'target_value', 
                     'current_value', 'target_date', 'frequency', 'xp_reward', 'is_completed']:
            if field in data:
                update_data[field] = data[field]
        
        # If marking as completed, set completed_at
        if 'is_completed' in update_data and update_data['is_completed']:
            update_data['completed_at'] = datetime.utcnow().isoformat()
            
            # Award XP for completing the goal
            xp_reward = existing_goal.data.get('xp_reward', 10)
            db.save_game_score(
                user_id=user_id,
                game_type='goal_achievement',
                score=xp_reward,
                level=1,
                metadata={
                    'goal_id': goal_id,
                    'goal_title': existing_goal.data.get('title')
                }
            )
            
            # Update achievements
            update_goal_achievements(user_id)
        
        # Update the goal
        result = db.client.table('user_goals') \
            .update(update_data) \
            .eq('id', goal_id) \
            .execute()
            
        if not result.data:
            return jsonify({'error': 'Failed to update goal'}), 500
            
        # Get the updated goal with category info
        updated_goal = db.client.table('user_goals') \
            .select('*, goal_categories(name, icon)') \
            .eq('id', goal_id) \
            .single() \
            .execute()
            
        return jsonify(updated_goal.data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals/<goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    """Delete a goal"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user_id = session['user']['id']
    
    try:
        # First verify the goal belongs to the user
        existing_goal = db.client.table('user_goals') \
            .select('*') \
            .eq('id', goal_id) \
            .eq('user_id', user_id) \
            .single() \
            .execute()
            
        if not existing_goal.data:
            return jsonify({'error': 'Goal not found'}), 404
            
        # Delete the goal
        result = db.client.table('user_goals') \
            .delete() \
            .eq('id', goal_id) \
            .execute()
            
        if not result.data:
            return jsonify({'error': 'Failed to delete goal'}), 500
            
        return jsonify({'message': 'Goal deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@goal_bp.route('/api/goals/progress', methods=['GET'])
def get_goal_progress():
    """Get goal progress statistics"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user_id = session['user']['id']
    
    try:
        # Get total goals
        total_goals = db.client.table('user_goals') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .execute()
            
        # Get completed goals
        completed_goals = db.client.table('user_goals') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .eq('is_completed', True) \
            .execute()
            
        # Get goals by category
        goals_by_category = db.client.rpc('get_goals_by_category', {
            'p_user_id': user_id
        }).execute()
        
        # Get recent activity
        recent_activity = db.client.table('user_goals') \
            .select('id, title, is_completed, completed_at') \
            .eq('user_id', user_id) \
            .order('completed_at', desc=True) \
            .limit(5) \
            .execute()
        
        return jsonify({
            'total_goals': total_goals.count or 0,
            'completed_goals': completed_goals.count or 0,
            'goals_by_category': goals_by_category.data or [],
            'recent_activity': recent_activity.data or []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_goal_achievements(user_id):
    """Update user achievements based on goal activity"""
    try:
        # Get user's completed goals count
        completed_goals = db.client.table('user_goals') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .eq('is_completed', True) \
            .execute()
            
        total_completed = completed_goals.count or 0
        
        # Check for badge achievements
        badges_to_award = []
        
        # Check for "First Goal" badge (1 completed goal)
        if total_completed >= 1:
            first_badge = db.client.table('badges') \
                .select('*') \
                .eq('name', 'First Steps') \
                .execute()
                
            if first_badge.data:
                badge_id = first_badge.data[0]['id']
                # Check if user already has this badge
                existing_badge = db.client.table('user_badges') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .eq('badge_id', badge_id) \
                    .execute()
                    
                if not existing_badge.data:
                    badges_to_award.append(badge_id)
        
        # Check for "Goal Getter" badge (5 completed goals)
        if total_completed >= 5:
            getter_badge = db.client.table('badges') \
                .select('*') \
                .eq('name', 'Goal Getter') \
                .execute()
                
            if getter_badge.data:
                badge_id = getter_badge.data[0]['id']
                existing_badge = db.client.table('user_badges') \
                    .select('*') \
                    .eq('user_id', user_id) \
                    .eq('badge_id', badge_id) \
                    .execute()
                    
                if not existing_badge.data:
                    badges_to_award.append(badge_id)
        
        # Award any new badges
        for badge_id in badges_to_award:
            db.client.table('user_badges') \
                .insert({
                    'user_id': user_id,
                    'badge_id': badge_id
                }) \
                .execute()
        
        # Update user's achievements
        update_user_achievements(user_id, 'goals_completed', total_completed)
        
    except Exception as e:
        print(f"Error updating goal achievements: {str(e)}")

def update_user_achievements(user_id, achievement_type, value):
    """Update user's achievements based on activity"""
    try:
        # Get or create user achievements record
        achievements = db.client.table('user_achievements') \
            .select('*') \
            .eq('user_id', user_id) \
            .execute()
            
        current_date = datetime.now().date()
        last_activity = None
        current_streak = 0
        longest_streak = 0
        xp_earned = 0
        
        if achievements.data:
            # Update existing achievements
            achievements = achievements.data[0]
            last_activity = achievements.get('last_activity_date')
            current_streak = achievements.get('current_streak', 0)
            longest_streak = achievements.get('longest_streak', 0)
            xp_earned = achievements.get('xp_earned', 0)
            
            # Check for streak
            if last_activity:
                last_date = datetime.strptime(last_activity, '%Y-%m-%d').date()
                if (current_date - last_date).days == 1:
                    # Consecutive day
                    current_streak += 1
                elif (current_date - last_date).days > 1:
                    # Broken streak
                    current_streak = 1
                # Same day - don't update streak
            else:
                current_streak = 1
        else:
            # New user - initialize achievements
            current_streak = 1
            longest_streak = 1
            xp_earned = 0
            
        # Update longest streak if needed
        if current_streak > longest_streak:
            longest_streak = current_streak
            
        # Calculate XP based on activity type
        xp_earned += 10  # Base XP for any activity
        
        # Update or create achievements record
        achievements_data = {
            'user_id': user_id,
            'xp_earned': xp_earned,
            'current_level': calculate_level(xp_earned),
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'last_activity_date': current_date.isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if achievements.data:
            db.client.table('user_achievements') \
                .update(achievements_data) \
                .eq('id', achievements['id']) \
                .execute()
        else:
            achievements_data['created_at'] = datetime.utcnow().isoformat()
            db.client.table('user_achievements') \
                .insert(achievements_data) \
                .execute()
                
    except Exception as e:
        print(f"Error updating user achievements: {str(e)}")

def calculate_level(xp):
    """Calculate user level based on XP"""
    # Simple leveling formula: 100 XP per level
    return max(1, xp // 100)
