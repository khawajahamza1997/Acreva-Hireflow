import uuid
from app.database import get_admin_client


def upload_cv(org_id: str, candidate_id: str, filename: str, content: bytes) -> str:
    db = get_admin_client()
    safe_name = filename.replace(" ", "_")
    path = f"{org_id}/{candidate_id}/{uuid.uuid4().hex}_{safe_name}"
    db.storage.from_("cvs").upload(path, content, {"content-type": _mime(filename)})
    return path


def download_cv(storage_path: str) -> bytes:
    db = get_admin_client()
    return db.storage.from_("cvs").download(storage_path)


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str | None:
    if not storage_path:
        return None
    db = get_admin_client()
    result = db.storage.from_("cvs").create_signed_url(storage_path, expires_in)
    return result.get("signedURL") or result.get("signedUrl")


def delete_cv(storage_path: str) -> None:
    if not storage_path:
        return
    db = get_admin_client()
    try:
        db.storage.from_("cvs").remove([storage_path])
    except Exception:
        pass


def _mime(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "text/plain"


def upload_call_recording(org_id: str, candidate_id: str, filename: str, content: bytes) -> str:
    db = get_admin_client()
    safe_name = filename.replace(" ", "_")
    path = f"{org_id}/{candidate_id}/{uuid.uuid4().hex}_{safe_name}"
    db.storage.from_("call-recordings").upload(path, content, {"content-type": _audio_mime(filename)})
    return path


def get_call_recording_url(storage_path: str, expires_in: int = 3600) -> str | None:
    if not storage_path:
        return None
    db = get_admin_client()
    result = db.storage.from_("call-recordings").create_signed_url(storage_path, expires_in)
    return result.get("signedURL") or result.get("signedUrl")


def delete_call_recording(storage_path: str) -> None:
    if not storage_path:
        return
    db = get_admin_client()
    try:
        db.storage.from_("call-recordings").remove([storage_path])
    except Exception:
        pass


def _audio_mime(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".m4a"):
        return "audio/x-m4a"
    if lower.endswith(".ogg") or lower.endswith(".opus"):
        return "audio/ogg"
    if lower.endswith(".wav"):
        return "audio/wav"
    if lower.endswith(".webm"):
        return "audio/webm"
    return "audio/mp4"
