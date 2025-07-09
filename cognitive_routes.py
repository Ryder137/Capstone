from flask import Blueprint, jsonify, request, session
from database import Database
from datetime import datetime, timedelta
import random

cognitive_bp = Blueprint('cognitive', __name__)
db = Database()

@cognitive_bp.route('/api/cognitive/challenges/random', methods=['GET'])
def get_random_challenge():
    """Get a random cognitive reframing challenge"""
    try:
        # Get a random challenge from the database
        result = db.client.table('cognitive_reframing_challenges') \
            .select('*') \
            .order('random()') \
            .limit(1) \
            .execute()
            
        if not result.data:
            return jsonify({'error': 'No challenges available'}), 404
            
        challenge = result.data[0]
        return jsonify(challenge)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cognitive_bp.route('/api/cognitive/responses', methods=['POST'])
def save_response():
    """Save a user's reframing response"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    data = request.get_json()
    user_id = session['user']['id']
    
    required_fields = ['challenge_id', 'original_thought', 'reframed_thought']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        # Save the response
        response_data = {
            'user_id': user_id,
            'challenge_id': data['challenge_id'],
            'original_thought': data['original_thought'],
            'reframed_thought': data['reframed_thought'],
            'is_helpful': data.get('is_helpful')
        }
        
        result = db.client.table('user_reframing_responses') \
            .insert(response_data) \
            .execute()
            
        if not result.data:
            return jsonify({'error': 'Failed to save response'}), 500
            
        # Award points for completing the challenge
        points_awarded = 10  # Base points for completing a challenge
        db.save_game_score(
            user_id=user_id,
            game_type='cognitive_reframing',
            score=points_awarded,
            level=1,
            metadata={
                'action': 'reframe_thought',
                'challenge_id': data['challenge_id']
            }
        )
        
        # Update user achievements
        update_cognitive_achievements(user_id)
        
        return jsonify({
            'message': 'Response saved successfully',
            'points_awarded': points_awarded
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_cognitive_achievements(user_id):
    """Update user achievements based on cognitive reframing activity"""
    try:
        # Get user's total reframing responses
        response_count = db.client.table('user_reframing_responses') \
            .select('id', count='exact') \
            .eq('user_id', user_id) \
            .execute()
            
        total_responses = response_count.count or 0
        
        # Check for badge achievements
        badges_to_award = []
        
        # Check for "First Reframe" badge (1 response)
        if total_responses >= 1:
            first_badge = db.client.table('badges') \
                .select('*') \
                .eq('name', 'First Reframe') \
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
        
        # Check for "Cognitive Master" badge (10 responses)
        if total_responses >= 10:
            master_badge = db.client.table('badges') \
                .select('*') \
                .eq('name', 'Cognitive Master') \
                .execute()
                
            if master_badge.data:
                badge_id = master_badge.data[0]['id']
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
        update_user_achievements(user_id, 'cognitive_responses', total_responses)
        
    except Exception as e:
        print(f"Error updating cognitive achievements: {str(e)}")

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
