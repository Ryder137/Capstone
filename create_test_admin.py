import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_admin_user(email, password, name="Test Admin"):
    """
    Create a new admin user in Supabase Auth and users table
    """
    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            'email': email,
            'password': password
        })
        
        if auth_response.user:
            user_id = auth_response.user.id
            print(f"✅ Created auth user with ID: {user_id}")
            
            # Create user in users table with admin privileges
            user_data = {
                'id': user_id,
                'email': email,
                'name': name,
                'is_admin': True
            }
            
            db_response = supabase.table('users').insert(user_data).execute()
            
            if db_response.data:
                print(f"✅ Created admin user in database with ID: {user_id}")
                print("\nAdmin user created successfully!")
                print(f"Email: {email}")
                print(f"Password: {password}")
                print("\nYou can now log in to the admin dashboard.")
                return True
            else:
                print("❌ Failed to create admin user in database")
                if hasattr(db_response, 'error'):
                    print(f"Error: {db_response.error}")
                return False
        else:
            print("❌ Failed to create auth user")
            if hasattr(auth_response, 'error'):
                print(f"Error: {auth_response.error}")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Creating Test Admin User ===\n")
    
    # Default test admin credentials
    ADMIN_EMAIL = "admin@example.com"
    ADMIN_PASSWORD = "Admin@123"  # Strong password for testing
    
    print(f"Creating admin user with email: {ADMIN_EMAIL}")
    print(f"Password: {ADMIN_PASSWORD}\n")
    
    success = create_admin_user(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not success:
        print("\nFailed to create admin user. Please check the error message above.")
        exit(1)
