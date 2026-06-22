from typing import Any

from supabase import create_client, Client
from app.config import settings

_admin_client: Client | None = None


def exec_maybe_single(query: Any) -> dict | None:
    """Run maybe_single(); supabase-py 2.10 returns None when no row exists."""
    result = query.maybe_single().execute()
    if result is None:
        return None
    data = result.data
    return data if isinstance(data, dict) else None


def exec_rows(query_or_result: Any) -> list[dict]:
    if hasattr(query_or_result, "data"):
        result = query_or_result
    else:
        result = query_or_result.execute()
    if result is None or not result.data:
        return []
    data = result.data
    return data if isinstance(data, list) else [data]


def get_admin_client() -> Client:
    global _admin_client
    if _admin_client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        _admin_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _admin_client
