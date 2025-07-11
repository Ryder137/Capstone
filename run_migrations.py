import os
import glob
from supabase import create_client, Client
from dotenv import load_dotenv

def run_migrations():
    # Load environment variables
    load_dotenv()
    
    # Initialize Supabase client with service role key
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env file")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # Get all migration files in order
    migration_files = sorted(glob.glob('migrations/0*.sql'))
    
    print(f"Found {len(migration_files)} migration files to run")
    
    for migration_file in migration_files:
        print(f"\nRunning migration: {migration_file}")
        
        try:
            with open(migration_file, 'r') as f:
                sql = f.read()
                
            # Split the SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for statement in statements:
                if not statement.strip():
                    continue
                    
                print(f"  Executing: {statement[:100]}...")
                try:
                    # Use rpc for function creation, query for other statements
                    if 'CREATE OR REPLACE FUNCTION' in statement.upper():
                        result = supabase.rpc('execute_sql', {'query': statement}).execute()
                    else:
                        result = supabase.rpc('execute_sql', {'query': statement}).execute()
                    print("    Success")
                except Exception as e:
                    print(f"    Error: {str(e)}")
                    
        except Exception as e:
            print(f"Error running migration {migration_file}: {str(e)}")
    
    print("\nAll migrations completed!")

if __name__ == "__main__":
    run_migrations()
