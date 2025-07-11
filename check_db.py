import os
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

def check_database():
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    print("\n=== Database Connection Test ===")
    try:
        # Test connection by getting server time
        result = supabase.rpc('now').execute()
        print("[OK] Connected to Supabase database")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Supabase: {str(e)}")
        print("Please check your .env file for correct SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return
    
    # Check required tables
    required_tables = [
        'users',
        'admin_activities',
        'journal_entries',
        'assessments',
        'breathing_sessions',
        'game_sessions'
    ]
    
    print("\n=== Checking Required Tables ===")
    for table in required_tables:
        try:
            # Try to get table info
            result = supabase.table(table).select('*', count='exact').limit(1).execute()
            count = result.count if hasattr(result, 'count') else 'unknown'
            print(f"[OK] {table}: Found ({count} records)")
        except Exception as e:
            print(f"[MISSING] {table}: {str(e)}")
    
    # Check users table structure
    print("\n=== Users Table Structure ===")
    try:
        users_sample = supabase.table('users').select('*').limit(1).execute()
        if users_sample.data:
            print("Users table columns:")
            for col in users_sample.data[0].keys():
                print(f"- {col}")
    except Exception as e:
        print(f"Failed to get users table structure: {str(e)}")
    
    # Check admin_activities table
    print("\n=== Admin Activities ===")
    try:
        activities = supabase.table('admin_activities') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(5) \
            .execute()
        
        if activities.data:
            print(f"Found {len(activities.data)} recent activities:")
            for act in activities.data:
                print(f"- {act.get('action')}: {act.get('details')} ({act.get('created_at')})")
        else:
            print("No admin activities found.")
    except Exception as e:
        print(f"Failed to fetch admin activities: {str(e)}")
    
    # Check user statistics
    print("\n=== User Statistics ===")
    try:
        # Total users
        total_users = supabase.table('users').select('id', count='exact').execute()
        print(f"Total users: {total_users.count if hasattr(total_users, 'count') else 'N/A'}")
        
        # Active users (last 7 days)
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        active_users = supabase.table('users') \
            .select('id', count='exact') \
            .gt('last_login', week_ago) \
            .execute()
        print(f"Active users (last 7 days): {active_users.count if hasattr(active_users, 'count') else 'N/A'}")
        
        # New users today
        today = datetime.utcnow().strftime('%Y-%m-%d')
        new_users = supabase.table('users') \
            .select('id', count='exact') \
            .gte('created_at', f"{today}T00:00:00.000Z") \
            .lt('created_at', f"{today}T23:59:59.999Z") \
            .execute()
        print(f"New users today: {new_users.count if hasattr(new_users, 'count') else 'N/A'}")
        
        # Admin users
        admins = supabase.table('users') \
            .select('id', count='exact') \
            .eq('is_admin', True) \
            .execute()
        print(f"Admin users: {admins.count if hasattr(admins, 'count') else 'N/A'}")
        
    except Exception as e:
        print(f"Error fetching user statistics: {str(e)}")

if __name__ == "__main__":
    check_database()
