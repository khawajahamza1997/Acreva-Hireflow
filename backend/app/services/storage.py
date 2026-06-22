import uuid
from app.database import get_admin_client


def upload_cv(org_id: str, candidate_id: str, filename: str, content: bytes) -> str:
    db = get_admin_client()
    safe_name = filename.replace(" ", "_")
    path = f"{org_id}/{candidate_id}/{uuid.uuid4().hex}_{safe_name}"
    db.storage.from_("cvs").upload(path, content, {"content-type": _mime(filename)})
    return path


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str | None:
    if not storage_path:
        return None
    db = get_admin_client()
    result = db.storage.from_("cvs").create_signed_url(storage_path, expires_in)
    return result.get("signedURL") or result.get("signedUrl")


def _mime(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "text/plain"
