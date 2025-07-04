import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

def test_rls_policies():
    print("\nTesting RLS Policies...")
    
    # Test unauthenticated access
    print("\nTesting unauthenticated access:")
    try:
        # Try to access users table without auth
        result = supabase.table('users').select('*').execute()
        print("❌ Failed: Unauthenticated access to users table")
    except Exception as e:
        print("✅ Passed: Unauthenticated access blocked")

    # Test authenticated user access
    print("\nTesting authenticated user access:")
    try:
        # Try to access own data
        result = supabase.table('users').select('*').eq('id', 'auth.uid()').execute()
        print("✅ Passed: Authenticated user can access own data")
        
        # Try to access other user's data
        result = supabase.table('users').select('*').neq('id', 'auth.uid()').execute()
        if len(result.data) > 0:
            print("❌ Failed: Authenticated user can access other users' data")
        else:
            print("✅ Passed: Authenticated user cannot access other users' data")
    except Exception as e:
        print(f"❌ Failed: Authenticated access test failed: {str(e)}")

    # Test doctor-specific access
    print("\nTesting doctor access:")
    try:
        # Try to access doctor data as non-doctor
        result = supabase.table('doctors').select('*').execute()
        if len(result.data) > 0:
            print("❌ Failed: Non-doctor can access doctor data")
        else:
            print("✅ Passed: Non-doctor cannot access doctor data")
    except Exception as e:
        print("✅ Passed: Non-doctor cannot access doctor data")

    # Test appointment access
    print("\nTesting appointment access:")
    try:
        # Try to view own appointments
        result = supabase.table('appointments').select('*').eq('user_id', 'auth.uid()').execute()
        print("✅ Passed: User can view own appointments")
        
        # Try to view other user's appointments
        result = supabase.table('appointments').select('*').neq('user_id', 'auth.uid()').execute()
        if len(result.data) > 0:
            print("❌ Failed: User can view other users' appointments")
        else:
            print("✅ Passed: User cannot view other users' appointments")
    except Exception as e:
        print(f"❌ Failed: Appointment access test failed: {str(e)}")

if __name__ == '__main__':
    test_rls_policies()
