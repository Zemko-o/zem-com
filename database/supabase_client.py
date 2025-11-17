import os
from supabase import create_client

# Supabase client singleton
_supabase = None

def get_supabase():
    """Return a configured supabase client. Expects SUPABASE_URL and SUPABASE_KEY in env."""
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        _supabase = create_client(url, key)
    return _supabase
