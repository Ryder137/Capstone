"""
Script to repair missing user profiles in the Supabase 'users' table.
For every Supabase Auth user, ensure a matching 'users' row exists.
If missing, insert with is_admin=False by default.
"""
import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # WARNING: Never use this key in your main app code!

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_SERVICE_ROLE_KEY:", SUPABASE_SERVICE_ROLE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def repair_missing_profiles():
    # Get all Supabase Auth users
    auth_users = supabase.auth.admin.list_users().users
    print(f"Found {len(auth_users)} Supabase Auth users.")
    repaired = 0
    for user in auth_users:
        user_id = user.id
        email = user.email
        # Check if profile exists
        profile = supabase.table('users').select('id').eq('id', user_id).single().execute()
        if not profile['data']:
            print(f"Repairing: {email} ({user_id})")
            supabase.table('users').insert({
                'id': user_id,
                'user_id': user_id,
                'email': email,
                'is_admin': False
            }).execute()
            repaired += 1
    print(f"Repair complete. {repaired} profiles added.")

if __name__ == '__main__':
    repair_missing_profiles()
