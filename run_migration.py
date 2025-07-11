import os
import sys
from app import supabase, service_role_supabase

def run_migration():
    # Migration files to run in order
    migration_files = [
        '016_create_contents_table.sql',
        '017_create_admin_tables.sql',
        '018_fix_missing_tables.sql',
        '019_fix_admin_dashboard_issues.sql'
    ]
    
    for migration_file in migration_files:
        migration_path = os.path.join('migrations', migration_file)
        
        if not os.path.exists(migration_path):
            print(f"Warning: Migration file not found, skipping: {migration_path}")
            continue
        
        print(f"\nRunning migration: {migration_file}")
        print("=" * 50)
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            # Split the SQL into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            # Execute each statement
            for i, stmt in enumerate(statements, 1):
                if not stmt.strip():
                    continue
                    
                print(f"\n[{i}/{len(statements)}] Executing statement...")
                if len(stmt) > 100:
                    print(f"   {stmt[:97]}...")
                else:
                    print(f"   {stmt}")
                
                try:
                    # Use service_role_supabase for admin operations
                    result = service_role_supabase.rpc('execute_sql', {'query': stmt}).execute()
                    if hasattr(result, 'error') and result.error:
                        print(f"   Error: {result.error}")
                        return False
                except Exception as e:
                    print(f"   Error executing statement: {str(e)}")
                    return False
            
            print(f"\n[OK] Completed: {migration_file}")
            
        except Exception as e:
            print(f"Error running migration {migration_file}: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    print("Starting database migrations...\n")
    if run_migration():
        print("\n[SUCCESS] All migrations completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed!")
        sys.exit(1)
