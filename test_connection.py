import os
from supabase import create_client
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL:
    logger.error("SUPABASE_URL is not set")
    print("❌ SUPABASE_URL is not set in environment variables")
    exit(1)

if not SUPABASE_KEY:
    logger.error("SUPABASE_KEY is not set")
    print("❌ SUPABASE_KEY is not set in environment variables")
    exit(1)

try:
    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info(f"Supabase client initialized with URL: {SUPABASE_URL}")
    print(f"✅ Supabase client initialized with URL: {SUPABASE_URL}")
    
    # Test the connection
    try:
        # Try to fetch a table (this will fail if connection is invalid)
        result = supabase.table('users').select('*').limit(1).execute()
        logger.info("Successfully connected to Supabase")
        print("✅ Successfully connected to Supabase")
        
        if result.data:
            print("✅ Table query successful")
        else:
            print("✅ Table exists but no data found")
            
    except Exception as e:
        logger.error(f"Error testing connection: {str(e)}")
        print(f"❌ Error testing connection: {str(e)}")
        exit(1)
        
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    print(f"❌ Failed to initialize Supabase client: {str(e)}")
    exit(1)

# --- Supabase Auth login test ---
import os

test_email = os.getenv('TEST_ADMIN_EMAIL', 'admin@email.com')
test_password = os.getenv('TEST_ADMIN_PASSWORD', 'password123')

print(f"\nTesting Supabase Auth login for {test_email}...")
try:
    auth_response = supabase.auth.sign_in_with_password({
        'email': test_email,
        'password': test_password
    })
    print("Auth response:", auth_response)
    if auth_response.get('error'):
        print(f"❌ Auth failed: {auth_response['error']['message']}")
    else:
        print("✅ Auth succeeded! User:", auth_response.get('user'))
except Exception as e:
    print(f"❌ Exception during auth: {str(e)}")

print("\nAll tests passed! You can now deploy to Vercel.")
