"""
Admin API endpoints for managing administrators in the UniCare platform.
This module provides CRUD operations for admin users with proper authentication and authorization.
"""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import logging
from datetime import datetime

# Create a Blueprint for admin API endpoints
admin_bp = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# Set up logging
logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to ensure the request is made by an authenticated admin user.
    Verifies the JWT token and checks admin status.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get the token from headers
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({
                    "success": False,
                    "error": "Authorization token is required"
                }), 401

            # Get the Supabase client from the app context
            supabase = current_app.supabase
            
            try:
                # Verify the token with Supabase
                user = supabase.auth.get_user(token.replace('Bearer ', ''))
                user_id = user.user.id
                
                # Check if user is admin
                user_data = supabase.table('users') \
                    .select('is_admin') \
                    .eq('id', user_id) \
                    .single() \
                    .execute()
                
                if not user_data.data or not user_data.data.get('is_admin'):
                    return jsonify({
                        "success": False,
                        "error": "Admin access required"
                    }), 403
                
                # Add user_id to kwargs for use in the route
                kwargs['current_user_id'] = user_id
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired token"
                }), 401
                
        except Exception as e:
            logger.error(f"Admin authentication error: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Authentication error"
            }), 500
    
    return decorated_function

@admin_bp.route('/admins', methods=['GET'])
@admin_required
def list_admins(current_user_id):
    """
    List all admin users with pagination.
    Query params: page (int), per_page (int), search (str)
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)  # Cap at 100 items per page
        search = request.args.get('search', '').strip()
        
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # Build the query
        query = current_app.supabase.table('users') \
            .select('id, email, created_at, last_sign_in_at, is_active, is_admin, role', count='exact') \
            .eq('is_admin', True)
        
        # Add search filter if provided
        if search:
            query = query.ilike('email', f'%{search}%')
        
        # Apply pagination and execute
        result = query.range(offset, offset + per_page - 1).execute()
        
        # Format the response
        admins = result.data
        total = result.count if hasattr(result, 'count') else len(admins)
        
        return jsonify({
            "success": True,
            "data": admins,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing admins: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve admin list"
        }), 500

@admin_bp.route('/admins', methods=['POST'])
@admin_required
def create_admin(current_user_id):
    """
    Create a new admin user.
    Required fields: email, role, permissions (array)
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'email' not in data:
            return jsonify({
                "success": False,
                "error": "Email is required"
            }), 400
        
        email = data['email'].strip().lower()
        role = data.get('role', 'admin')
        permissions = data.get('permissions', [])
        
        # Check if user already exists
        existing_user = current_app.supabase.table('users') \
            .select('id, is_admin') \
            .eq('email', email) \
            .single() \
            .execute()
        
        if existing_user.data:
            # User exists, update to admin if not already
            if existing_user.data.get('is_admin'):
                return jsonify({
                    "success": False,
                    "error": "User is already an admin"
                }), 409
            
            # Update existing user to admin
            updated_user = current_app.supabase.table('users') \
                .update({
                    'is_admin': True,
                    'role': role,
                    'permissions': permissions,
                    'updated_at': datetime.utcnow().isoformat()
                }) \
                .eq('id', existing_user.data['id']) \
                .execute()
            
            admin_id = existing_user.data['id']
            
        else:
            # Create new admin user (invite via Supabase Auth)
            auth_response = current_app.supabase.auth.admin.create_user({
                "email": email,
                "email_confirm": True,
                "user_metadata": {
                    "is_admin": True,
                    "role": role,
                    "permissions": permissions
                }
            })
            
            if not auth_response.user:
                return jsonify({
                    "success": False,
                    "error": "Failed to create admin user in Auth"
                }), 500
            
            # Create user record in the database
            user_data = {
                'id': auth_response.user.id,
                'email': email,
                'is_admin': True,
                'role': role,
                'permissions': permissions,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Insert into users table
            result = current_app.supabase.table('users').insert(user_data).execute()
            admin_id = auth_response.user.id
        
        # Log the admin creation
        log_admin_action(
            current_user_id,
            f"Created admin user {email} with role {role}",
            {
                "admin_id": admin_id,
                "role": role,
                "permissions": permissions
            }
        )
        
        return jsonify({
            "success": True,
            "message": "Admin created successfully",
            "admin_id": admin_id
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating admin: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to create admin"
        }), 500

@admin_bp.route('/admins/<admin_id>', methods=['GET'])
@admin_required
def get_admin(current_user_id, admin_id):
    """
    Get details of a specific admin user.
    """
    try:
        # Get admin details
        result = current_app.supabase.table('users') \
            .select('*') \
            .eq('id', admin_id) \
            .eq('is_admin', True) \
            .single() \
            .execute()
        
        if not result.data:
            return jsonify({
                "success": False,
                "error": "Admin not found"
            }), 404
        
        return jsonify({
            "success": True,
            "data": result.data
        })
        
    except Exception as e:
        logger.error(f"Error getting admin {admin_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve admin details"
        }), 500

@admin_bp.route('/admins/<admin_id>', methods=['PUT'])
@admin_required
def update_admin(current_user_id, admin_id):
    """
    Update an admin user's details.
    Allowed fields: role, permissions, is_active
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided for update"
            }), 400
        
        # Only allow certain fields to be updated
        allowed_fields = {'role', 'permissions', 'is_active'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({
                "success": False,
                "error": "No valid fields provided for update"
            }), 400
        
        # Add updated_at timestamp
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update the admin
        result = current_app.supabase.table('users') \
            .update(update_data) \
            .eq('id', admin_id) \
            .eq('is_admin', True) \
            .execute()
        
        if not result.data:
            return jsonify({
                "success": False,
                "error": "Admin not found or no changes made"
            }), 404
        
        # Log the update
        log_admin_action(
            current_user_id,
            f"Updated admin {admin_id}",
            {"changes": update_data}
        )
        
        return jsonify({
            "success": True,
            "message": "Admin updated successfully"
        })
        
    except Exception as e:
        logger.error(f"Error updating admin {admin_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to update admin"
        }), 500

@admin_bp.route('/admins/<admin_id>', methods=['DELETE'])
@admin_required
def delete_admin(current_user_id, admin_id):
    """
    Delete an admin user (demote to regular user).
    Prevents deleting the last admin.
    """
    try:
        # Prevent deleting yourself
        if current_user_id == admin_id:
            return jsonify({
                "success": False,
                "error": "You cannot remove your own admin privileges"
            }), 400
        
        # Check if this is the last admin
        admin_count = current_app.supabase.table('users') \
            .select('id', count='exact') \
            .eq('is_admin', True) \
            .execute()
        
        if admin_count.count == 1:
            return jsonify({
                "success": False,
                "error": "Cannot remove the last admin"
            }), 400
        
        # Get admin email for logging before demoting
        admin_data = current_app.supabase.table('users') \
            .select('email') \
            .eq('id', admin_id) \
            .single() \
            .execute()
        
        if not admin_data.data:
            return jsonify({
                "success": False,
                "error": "Admin not found"
            }), 404
        
        # Demote to regular user
        result = current_app.supabase.table('users') \
            .update({
                'is_admin': False,
                'role': 'user',
                'updated_at': datetime.utcnow().isoformat()
            }) \
            .eq('id', admin_id) \
            .execute()
        
        if not result.data:
            return jsonify({
                "success": False,
                "error": "Failed to remove admin privileges"
            }), 500
        
        # Log the action
        log_admin_action(
            current_user_id,
            f"Removed admin privileges from {admin_data.data.get('email', admin_id)}",
            {"admin_id": admin_id}
        )
        
        return jsonify({
            "success": True,
            "message": "Admin privileges removed successfully"
        })
        
    except Exception as e:
        logger.error(f"Error removing admin {admin_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to remove admin privileges"
        }), 500

def log_admin_action(admin_id, action, metadata=None):
    """
    Log an admin action to the database.
    """
    try:
        log_entry = {
            'admin_id': admin_id,
            'action': action,
            'metadata': metadata or {},
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'created_at': datetime.utcnow().isoformat()
        }
        
        current_app.supabase.table('admin_audit_logs').insert(log_entry).execute()
        
    except Exception as e:
        logger.error(f"Failed to log admin action: {str(e)}")
