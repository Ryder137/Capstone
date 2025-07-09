import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_admin_user(email, password, name="Admin User"):
    """
    Create a new admin user in both Supabase Auth and the users table
    """
    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            'email': email,
            'password': password
        })
        
        if auth_response.get('error'):
            raise Exception(f"Auth error: {auth_response['error']['message']}")
        
        user = auth_response.user
        print(f"✅ Created auth user: {user['email']} (ID: {user['id']})")
        
        # Add user to users table with admin privileges
        user_data = {
            'id': user['id'],
            'email': email,
            'name': name,
            'is_admin': True
        }
        
        db_response = supabase.table('users').insert(user_data).execute()
        
        if db_response.get('error'):
            # If user already exists in users table, update their admin status
            if 'duplicate key' in str(db_response['error']).lower():
                print("⚠️  User already exists in users table. Updating admin status...")
                db_response = supabase.table('users')\
                    .update({'is_admin': True})\
                    .eq('id', user['id'])\
                    .execute()
                
                if db_response.get('error'):
                    raise Exception(f"Failed to update user: {db_response['error']}")
                print(f"✅ Updated user {user['email']} to admin")
            else:
                raise Exception(f"Database error: {db_response['error']}")
        else:
            print(f"✅ Added user {user['email']} to users table as admin")
        
        return True, user_data
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    import getpass
    
    print("\n=== UniCare Admin User Setup ===\n")
    email = input("Enter admin email: ").strip()
    password = getpass.getpass("Enter admin password: ").strip()
    confirm_password = getpass.getpass("Confirm admin password: ").strip()
    
    if password != confirm_password:
        print("❌ Passwords do not match")
        exit(1)
    
    if len(password) < 8:
        print("❌ Password must be at least 8 characters long")
        exit(1)
    
    success, result = create_admin_user(email, password)
    
    if success:
        print("\n✅ Admin user created successfully!")
        print(f"Email: {result['email']}")
        print("\nYou can now log in to the admin dashboard.")
    else:
        print("\n❌ Failed to create admin user:", result)
