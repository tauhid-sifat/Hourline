import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Initialize Supabase Client
supabase: Client | None = None

def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase
    if supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

def init_db():
    """
    Initialize database schema.
    Note: For Supabase, schema should be created manually via SQL Editor
    using the schema.sql file. This function is kept for compatibility
    but does nothing in production.
    """
    pass
