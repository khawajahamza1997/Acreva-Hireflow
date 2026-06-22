from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from app.database import get_admin_client
from app.deps import get_current_user, require_role, require_active_subscription, CurrentUser
from app.schemas import JobCreate, JobUpdate, CandidateUpdate, ScoreRequest, ShortlistRequest
from app.services.cv_parser import process_cv_bytes
from app.services.scoring import score_candidate
from app.services.storage import upload_cv, get_signed_url
from app.services.audit import log_action
import uuid

router = APIRouter(tags=["core"])


@router.get("/jobs")
def list_jobs(user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    result = (
        db.table("jobs")
        .select("*")
        .eq("organization_id", user.organization_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.post("/jobs")
def create_job(body: JobCreate, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    row = (
        db.table("jobs")
        .insert(
            {
                "organization_id": user.organization_id,
                "title": body.title,
                "description": body.description,
                "created_by": user.id,
            }
        )
        .execute()
    )
    log_action(user.organization_id, user.id, user.email, "job_created", "job", row.data[0]["id"])
    return row.data[0]


@router.patch("/jobs/{job_id}")
def update_job(job_id: str, body: JobUpdate, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")
    result = (
        db.table("jobs")
        .update(updates)
        .eq("id", job_id)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found.")
    return result.data[0]


@router.get("/candidates")
def list_candidates(
    user: CurrentUser = Depends(require_active_subscription),
    q: str | None = Query(None),
    status: str | None = Query(None),
    shortlisted: bool | None = Query(None),
):
    db = get_admin_client()
    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if status:
        query = query.eq("status", status)
    if shortlisted is not None:
        query = query.eq("shortlisted", shortlisted)
    result = query.order("created_at", desc=True).execute()
    rows = result.data or []
    if q:
        q_lower = q.lower()
        rows = [
            r
            for r in rows
            if q_lower in (r.get("name") or "").lower()
            or q_lower in (r.get("email") or "").lower()
            or q_lower in (r.get("current_role") or "").lower()
        ]
    return rows


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    result = (
        db.table("candidates")
        .select("*")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
        .maybe_single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    data = result.data
    if data.get("cv_storage_path"):
        data["cv_download_url"] = get_signed_url(data["cv_storage_path"])
    logs = (
        db.table("audit_logs")
        .select("*")
        .eq("organization_id", user.organization_id)
        .eq("entity_id", candidate_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    data["history"] = logs.data or []
    return data


@router.post("/candidates/upload")
async def upload_candidate(
    file: UploadFile = File(...),
    job_id: str | None = Form(None),
    user: CurrentUser = Depends(require_active_subscription),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot upload CVs.")

    content = await file.read()
    filename = file.filename or "cv.txt"
    parsed = process_cv_bytes(content, filename)
    if parsed.get("parse_error"):
        raise HTTPException(status_code=400, detail=parsed["parse_error"])

    db = get_admin_client()
    candidate_id = str(uuid.uuid4())

    if job_id:
        job = (
            db.table("jobs")
            .select("id")
            .eq("id", job_id)
            .eq("organization_id", user.organization_id)
            .maybe_single()
            .execute()
        )
        if not job.data:
            raise HTTPException(status_code=404, detail="Job not found.")

    storage_path = upload_cv(user.organization_id, candidate_id, filename, content)

    row = (
        db.table("candidates")
        .insert(
            {
                "id": candidate_id,
                "organization_id": user.organization_id,
                "job_id": job_id,
                "name": parsed.get("name", "Unknown"),
                "email": parsed.get("email", ""),
                "phone": parsed.get("phone", ""),
                "current_role": parsed.get("current_role", ""),
                "skills": parsed.get("skills", ""),
                "experience_years": parsed.get("experience_years", 0),
                "education": parsed.get("education", ""),
                "filename": filename,
                "cv_storage_path": storage_path,
                "cv_text": parsed.get("raw_text", "")[:8000],
                "notes": parsed.get("summary", ""),
                "status": "New Applicant",
            }
        )
        .execute()
    )
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "cv_uploaded",
        "candidate",
        candidate_id,
        {"filename": filename},
    )
    return row.data[0]


@router.patch("/candidates/{candidate_id}")
def update_candidate(
    candidate_id: str,
    body: CandidateUpdate,
    user: CurrentUser = Depends(require_active_subscription),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit candidates.")
    db = get_admin_client()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = (
        db.table("candidates")
        .update(updates)
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    log_action(user.organization_id, user.id, user.email, "candidate_updated", "candidate", candidate_id, updates)
    return result.data[0]


@router.post("/scoring/run")
def run_scoring(body: ScoreRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot score candidates.")
    db = get_admin_client()
    job = (
        db.table("jobs")
        .select("*")
        .eq("id", body.job_id)
        .eq("organization_id", user.organization_id)
        .maybe_single()
        .execute()
    )
    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if body.candidate_ids:
        query = query.in_("id", body.candidate_ids)
    candidates = query.execute().data or []

    results = []
    for cand in candidates:
        if cand.get("score") and float(cand.get("score") or 0) > 0 and not body.candidate_ids:
            continue
        scoring = score_candidate(cand, job.data["description"])
        if scoring.get("error"):
            results.append({"id": cand["id"], "name": cand["name"], "error": scoring["error"]})
            continue
        updated = (
            db.table("candidates")
            .update(
                {
                    "score": scoring["score"],
                    "score_status": scoring["status"],
                    "score_reason": " | ".join(scoring.get("reason", [])),
                    "status": "Scored",
                }
            )
            .eq("id", cand["id"])
            .execute()
        )
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "candidate_scored",
            "candidate",
            cand["id"],
            {"score": scoring["score"], "status": scoring["status"]},
        )
        results.append(updated.data[0] if updated.data else {"id": cand["id"], **scoring})

    return {"scored": len([r for r in results if not r.get("error")]), "results": results}


@router.post("/shortlist/auto")
def auto_shortlist(body: ShortlistRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot shortlist.")
    db = get_admin_client()
    rows = (
        db.table("candidates")
        .select("*")
        .eq("organization_id", user.organization_id)
        .gt("score", 0)
        .neq("status", "Rejected")
        .order("score", desc=True)
        .limit(body.top_n)
        .execute()
    ).data or []

    shortlisted = []
    for row in rows:
        db.table("candidates").update({"shortlisted": True, "status": "Shortlisted"}).eq("id", row["id"]).execute()
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "candidate_shortlisted",
            "candidate",
            row["id"],
            {"score": row.get("score")},
        )
        shortlisted.append(row["name"])

    return {"count": len(shortlisted), "names": shortlisted}


@router.get("/dashboard/stats")
def dashboard_stats(user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    rows = db.table("candidates").select("*").eq("organization_id", user.organization_id).execute().data or []
    status_counts = {}
    for r in rows:
        s = r.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    return {
        "total": len(rows),
        "scored": len([r for r in rows if float(r.get("score") or 0) > 0]),
        "shortlisted": len([r for r in rows if r.get("shortlisted")]),
        "contacted": len([r for r in rows if r.get("contacted")]),
        "interviews": len([r for r in rows if r.get("status") == "Interview Scheduled"]),
        "rejected": len([r for r in rows if r.get("status") == "Rejected"]),
        "pipeline": status_counts,
        "recent": rows[:8],
    }
