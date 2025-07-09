import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY]):
    raise ValueError(
        "Supabase credentials not found. Please set SUPABASE_URL, SUPABASE_KEY, "
        "and SUPABASE_SERVICE_ROLE_KEY in your environment or .env file."
    )
