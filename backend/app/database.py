from supabase import create_client, Client
from app.config import settings

_admin_client: Client | None = None


def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        _admin_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _admin_client
