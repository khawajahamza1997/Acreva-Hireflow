from app.database import get_admin_client


def log_action(
    org_id: str,
    user_id: str | None,
    user_email: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict | None = None,
) -> None:
    db = get_admin_client()
    db.table("audit_logs").insert(
        {
            "organization_id": org_id,
            "user_id": user_id,
            "user_email": user_email,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
        }
    ).execute()


def list_logs(org_id: str, limit: int = 50) -> list[dict]:
    db = get_admin_client()
    result = (
        db.table("audit_logs")
        .select("*")
        .eq("organization_id", org_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []
