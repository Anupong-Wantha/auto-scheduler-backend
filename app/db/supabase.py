from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return supabase
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")
        raise e

# Create a singleton instance
supabase_client = get_supabase_client()