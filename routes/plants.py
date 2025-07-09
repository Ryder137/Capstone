from flask import Blueprint, jsonify, request, session
from database import Database
from datetime import datetime, timezone
from functools import wraps

db = Database()
plants_bp = Blueprint('plants', __name__)

@plants_bp.route('/api/plants/me', methods=['GET'])
def get_user_plant():
    """Get the current user's plant"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session['user'].get('id')
    plant = db.get_user_plant(user_id)
    
    # If no plant exists, create a default one
    if not plant:
        plant = db.create_user_plant(user_id)
        if not plant:
            return jsonify({'error': 'Failed to create plant'}), 500
    
    return jsonify({
        'id': plant['id'],
        'plant_type': plant['plant_type'],
        'growth_stage': plant['growth_stage'],
        'last_watered': plant['last_watered'],
        'created_at': plant['created_at']
    })

@plants_bp.route('/api/plants/water', methods=['POST'])
def water_plant():
    """Water the user's plant using game points"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    points = int(data.get('points', 10))  # Default to 10 points per water
    user_id = session['user'].get('id')
    
    if not points or points <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid points amount'}), 400
    
    # Water the plant using database method
    success, plant_data, message = db.water_plant(user_id, points)
    if not success:
        return jsonify({'status': 'error', 'message': message}), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'plant': plant_data,
        'points_used': points
    })

@plants_bp.route('/api/plants/sunlight', methods=['POST'])
def give_sunlight():
    """Give sunlight to the user's plant using game points"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    points = int(data.get('points', 15))  # Default to 15 points per sunlight
    user_id = session['user'].get('id')
    
    if not points or points <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid points amount'}), 400
    
    # Give sunlight using database method
    success, plant_data, message = db.give_sunlight(user_id, points)
    if not success:
        return jsonify({'status': 'error', 'message': message}), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'plant': plant_data,
        'points_used': points
    })

@plants_bp.route('/api/plants/fertilizer', methods=['POST'])
def give_fertilizer():
    """Give fertilizer to the user's plant using game points"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    data = request.get_json()
    points = int(data.get('points', 20))  # Default to 20 points per fertilizer
    user_id = session['user'].get('id')
    
    if not points or points <= 0:
        return jsonify({'status': 'error', 'message': 'Invalid points amount'}), 400
    
    # Give fertilizer using database method
    success, plant_data, message = db.give_fertilizer(user_id, points)
    if not success:
        return jsonify({'status': 'error', 'message': message}), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'plant': plant_data,
        'points_used': points
    })

@plants_bp.route('/api/points/balance', methods=['GET'])
def get_points_balance():
    """Get the user's current points balance"""
    if 'user' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
    
    user_id = session['user'].get('id')
    try:
        # Get total points from game wins only
        points = db.get_available_game_points(user_id)
        return jsonify({
            'status': 'success',
            'points': points,
            'message': 'Points balance retrieved successfully'
        })
    except Exception as e:
        print(f"Error getting points balance: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to get points balance'}), 500

@plants_bp.route('/api/plants/select', methods=['POST'])
def select_plant():
    """Select a new plant type"""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    plant_type = data.get('plant_type')
    user_id = session['user'].get('id')
    
    if not plant_type or plant_type not in ['sunflower', 'cactus', 'rose', 'bamboo']:
        return jsonify({'status': 'error', 'message': 'Invalid plant type'}), 400
    
    try:
        # Get current plant
        plant = db.get_user_plant(user_id)
        
        if plant:
            # Update existing plant
            result = db.client.table('user_plants') \
                .update({
                    'plant_type': plant_type,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }) \
                .eq('id', plant['id']) \
                .execute()
            
            if hasattr(result, 'error') and result.error:
                return jsonify({'status': 'error', 'message': 'Failed to update plant'}), 500
                
            return jsonify({
                'status': 'success',
                'message': f'Plant changed to {plant_type}',
                'plant_type': plant_type
            })
        else:
            # Create new plant with selected type
            plant = db.create_user_plant(user_id, plant_type)
            if not plant:
                return jsonify({'status': 'error', 'message': 'Failed to create plant'}), 500
                
            return jsonify({
                'status': 'success',
                'message': f'New {plant_type} planted!',
                'plant_type': plant_type
            })
            
    except Exception as e:
        print(f"Error selecting plant: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
