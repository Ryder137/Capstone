import os
from supabase import create_client
from dotenv import load_dotenv

def verify_database():
    # Load environment variables
    load_dotenv()
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials in .env file")
        return
    
    print(f"Connecting to Supabase at: {supabase_url}")
    
    try:
        # Initialize Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Check connection by listing tables (this is a common approach)
        print("\n=== Testing Connection ===")
        try:
            # Try to get a list of tables using a direct SQL query
            result = supabase.rpc('get_tables', {}).execute()
            if hasattr(result, 'data'):
                print("[SUCCESS] Connected to Supabase database")
            else:
                print("[WARNING] Connected but couldn't list tables. This might be a permissions issue.")
        except Exception as e:
            print(f"[WARNING] Couldn't list tables, but connection seems active: {str(e)}")
        
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
                # Try to get a single record
                result = supabase.table(table).select('*').limit(1).execute()
                count = len(result.data) if hasattr(result, 'data') else 'unknown'
                print(f"[FOUND] {table}: {count} records")
            except Exception as e:
                print(f"[MISSING] {table}: {str(e)}")
        
        # Check users table specifically
        print("\n=== Users Table Check ===")
        try:
            users = supabase.table('users').select('*').limit(5).execute()
            if hasattr(users, 'data') and users.data:
                print(f"Found {len(users.data)} users")
                print("Sample user:")
                for user in users.data[:1]:  # Show first user as sample
                    print(f"- ID: {user.get('id')}")
                    print(f"  Email: {user.get('email')}")
                    print(f"  Is Admin: {user.get('is_admin', False)}")
                    print(f"  Created: {user.get('created_at')}")
            else:
                print("No users found in the database")
        except Exception as e:
            print(f"Error checking users table: {str(e)}")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to Supabase: {str(e)}")
        print("Please verify your .env file has the correct credentials")

if __name__ == "__main__":
    verify_database()
