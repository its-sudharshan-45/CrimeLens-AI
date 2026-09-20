import logging

from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

def init_supabase() -> Client:
    """
    Initializes and returns the Supabase client using credentials from settings.
    """
    try:
        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_KEY
        
        # Create and return the Supabase client
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise

# Export a reusable singleton client instance to be used across the application
supabase_client = init_supabase()
