from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client with service role key
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
    exit(1)

supabase = create_client(supabase_url, supabase_key)

def check_table_exists(table_name):
    """Check if a table exists in the public schema"""
    try:
        # Try to select a single row from the table
        result = supabase.table(table_name).select("*").limit(1).execute()
        return True, f"Table '{table_name}' exists and is accessible"
    except Exception as e:
        return False, f"Table '{table_name}' does not exist or is not accessible: {str(e)}"

def check_function_exists(function_name):
    """Check if a function exists in the public schema"""
    try:
        # Query the pg_proc catalog to check if the function exists
        query = f"""
        SELECT proname 
        FROM pg_proc 
        JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid 
        WHERE pg_namespace.nspname = 'public' 
        AND proname = '{function_name}'
        """
        result = supabase.rpc('execute_sql', {'query': query}).execute()
        if hasattr(result, 'data') and len(result.data) > 0:
            return True, f"Function '{function_name}' exists"
        else:
            return False, f"Function '{function_name}' does not exist"
    except Exception as e:
        return False, f"Error checking function '{function_name}': {str(e)}"

def check_rls_enabled(table_name):
    """Check if Row Level Security is enabled for a table"""
    try:
        query = f"""
        SELECT relname, relrowsecurity 
        FROM pg_class 
        JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace 
        WHERE nspname = 'public' 
        AND relname = '{table_name}'
        """
        result = supabase.rpc('execute_sql', {'query': query}).execute()
        if hasattr(result, 'data') and len(result.data) > 0:
            rls_enabled = result.data[0].get('relrowsecurity', False)
            status = "enabled" if rls_enabled else "disabled"
            return True, f"Row Level Security for '{table_name}' is {status}"
        else:
            return False, f"Table '{table_name}' not found when checking RLS"
    except Exception as e:
        return False, f"Error checking RLS for '{table_name}': {str(e)}"

def main():
    print("\n=== Verifying Database Schema ===\n")
    
    # Check required tables
    required_tables = [
        'users',
        'assessments',
        'journal_entries',
        'game_sessions',
        'admin_activities'
    ]
    
    for table in required_tables:
        exists, message = check_table_exists(table)
        print(f"[{'✓' if exists else '✗'}] {message}")
        
        # Check RLS for each table
        if exists:
            rls_ok, rls_msg = check_rls_enabled(table)
            print(f"   {' ' * 3}• {rls_msg}")
    
    # Check required functions
    required_functions = [
        'execute_sql'
    ]
    
    print("\n=== Verifying Required Functions ===\n")
    for func in required_functions:
        exists, message = check_function_exists(func)
        print(f"[{'✓' if exists else '✗'}] {message}")
    
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    main()
