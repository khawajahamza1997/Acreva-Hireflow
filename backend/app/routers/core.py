from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from app.database import get_admin_client, exec_maybe_single
from app.deps import get_current_user, require_role, require_active_subscription, CurrentUser
from app.schemas import JobCreate, JobUpdate, CandidateUpdate, ScoreRequest, ShortlistRequest
from app.services.cv_parser import process_cv_bytes
from app.services.scoring import score_candidate
from app.services.storage import upload_cv, get_signed_url, delete_cv
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


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, user: CurrentUser = Depends(require_role("owner", "recruiter"))):
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs").select("id, title").eq("id", job_id).eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    db.table("candidates").update({"job_id": None}).eq("job_id", job_id).eq("organization_id", user.organization_id).execute()
    db.table("jobs").delete().eq("id", job_id).eq("organization_id", user.organization_id).execute()
    log_action(user.organization_id, user.id, user.email, "job_deleted", "job", job_id, {"title": job.get("title")})
    return {"message": f"Job \"{job.get('title')}\" deleted."}


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
    data = exec_maybe_single(
        db.table("candidates")
        .select("*")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not data:
        raise HTTPException(status_code=404, detail="Candidate not found.")
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
        job = exec_maybe_single(
            db.table("jobs")
            .select("id")
            .eq("id", job_id)
            .eq("organization_id", user.organization_id)
        )
        if not job:
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


@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, user: CurrentUser = Depends(require_role("owner", "recruiter"))):
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id, name, cv_storage_path")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    delete_cv(cand.get("cv_storage_path") or "")
    db.table("candidates").delete().eq("id", candidate_id).eq("organization_id", user.organization_id).execute()
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "candidate_deleted",
        "candidate",
        candidate_id,
        {"name": cand.get("name")},
    )
    return {"message": f"Candidate \"{cand.get('name')}\" deleted."}


@router.post("/candidates/{candidate_id}/unshortlist")
def unshortlist_candidate(candidate_id: str, user: CurrentUser = Depends(require_role("owner", "recruiter"))):
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id, name, shortlisted")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not cand.get("shortlisted"):
        raise HTTPException(status_code=400, detail="Candidate is not on the shortlist.")

    db.table("candidates").update({"shortlisted": False, "status": "Scored"}).eq("id", candidate_id).execute()
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "candidate_unshortlisted",
        "candidate",
        candidate_id,
        {"name": cand.get("name")},
    )
    return {"message": f"Removed {cand.get('name')} from shortlist."}


@router.post("/scoring/run")
def run_scoring(body: ScoreRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot score candidates.")
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs")
        .select("*")
        .eq("id", body.job_id)
        .eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if body.candidate_ids:
        query = query.in_("id", body.candidate_ids)
    candidates = query.execute().data or []

    results = []
    skipped = 0
    for cand in candidates:
        already_scored = cand.get("score") and float(cand.get("score") or 0) > 0
        same_job = cand.get("job_id") == body.job_id
        if already_scored and same_job and not body.rescore and not body.candidate_ids:
            skipped += 1
            continue

        scoring = score_candidate(cand, job["description"])
        if scoring.get("error"):
            results.append({"id": cand["id"], "name": cand["name"], "error": scoring["error"]})
            continue

        job_changed = cand.get("job_id") != body.job_id
        updates = {
            "score": scoring["score"],
            "score_status": scoring["status"],
            "score_reason": " | ".join(scoring.get("reason", [])),
            "status": "Scored",
            "job_id": body.job_id,
        }
        if job_changed:
            updates["shortlisted"] = False

        updated = db.table("candidates").update(updates).eq("id", cand["id"]).execute()
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "candidate_scored",
            "candidate",
            cand["id"],
            {"score": scoring["score"], "status": scoring["status"], "job_id": body.job_id},
        )
        row = updated.data[0] if updated.data else {"id": cand["id"], **scoring}
        results.append(row)

    scored_count = len([r for r in results if not r.get("error")])
    return {
        "scored": scored_count,
        "skipped": skipped,
        "job_title": job.get("title"),
        "results": results,
        "message": f"Scored {scored_count} candidate(s) against \"{job.get('title')}\".",
    }


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

    return {
        "count": len(shortlisted),
        "names": shortlisted,
        "message": f"Shortlisted {len(shortlisted)} candidate(s): {', '.join(shortlisted) if shortlisted else 'none found'}.",
    }


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
