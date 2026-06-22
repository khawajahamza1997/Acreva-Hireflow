import re
import uuid
from app.database import get_admin_client, exec_maybe_single, exec_rows
from app.services.email_service import DEFAULT_TEMPLATES


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"org-{uuid.uuid4().hex[:8]}"


def ensure_default_templates(org_id: str) -> None:
    db = get_admin_client()
    for template_type, template in DEFAULT_TEMPLATES.items():
        if not exec_maybe_single(
            db.table("email_templates")
            .select("id")
            .eq("organization_id", org_id)
            .eq("template_type", template_type)
        ):
            db.table("email_templates").insert(
                {
                    "organization_id": org_id,
                    "template_type": template_type,
                    "subject": template["subject"],
                    "body": template["body"],
                }
            ).execute()


def get_templates(org_id: str) -> list[dict]:
    db = get_admin_client()
    return exec_rows(db.table("email_templates").select("*").eq("organization_id", org_id))
