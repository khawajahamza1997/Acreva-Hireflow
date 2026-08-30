import logging
from datetime import datetime, timezone

from app.database import get_admin_client

logger = logging.getLogger(__name__)


def record_usage(org_id: str, event_type: str, quantity: int = 1) -> None:
    """Fire-and-forget usage counter; never raises — must not break the calling flow."""
    if not org_id:
        return
    try:
        db = get_admin_client()
        db.table("usage_events").insert(
            {"organization_id": org_id, "event_type": event_type, "quantity": quantity}
        ).execute()
    except Exception as exc:
        logger.warning("Usage tracking failed (%s): %s", event_type, exc)


def get_usage_summary(org_id: str) -> dict:
    db = get_admin_client()
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.table("usage_events")
        .select("event_type, quantity")
        .eq("organization_id", org_id)
        .gte("created_at", month_start.isoformat())
        .execute()
    ).data or []
    summary: dict[str, int] = {"cv_uploaded": 0, "cv_analyzed": 0, "ai_call": 0, "email_sent": 0}
    for row in rows:
        event_type = row.get("event_type")
        if event_type in summary:
            summary[event_type] += row.get("quantity", 1)
    return summary
