from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Form, Query
from app.config import settings
from app.database import get_admin_client, exec_maybe_single, exec_rows
from app.deps import get_current_user, require_role, require_active_subscription, CurrentUser
from app.schemas import (
    JobCreate,
    JobUpdate,
    CandidateUpdate,
    ScoreRequest,
    ShortlistRequest,
    ExtractRequirementsRequest,
    RetryProcessingRequest,
    CompareRequest,
    BulkShortlistRequest,
    BulkRetryRequest,
)
from app.services.cv_parser import process_cv_bytes, is_supported_filename
from app.services.requirements import extract_requirements
from app.services.scoring import recompute_score, DEFAULT_SCORING_WEIGHTS, DEFAULT_SCORE_THRESHOLDS
from app.services.comparison import compare_candidates
from app.services import processing
from app.services.call_intelligence import process_call_recording
from app.services.storage import (
    upload_cv,
    get_signed_url,
    delete_cv,
    delete_call_recording,
    upload_call_recording,
    get_call_recording_url,
)
from app.services.audit import log_action
from app.services.usage import record_usage
from app.utils.hashing import compute_file_hash
from app.utils.json_safe import json_safe
from app.utils.rate_limit import rate_limiter
import csv
import io
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
    return json_safe(result.data or [])


@router.post("/jobs/extract-requirements")
async def extract_job_requirements(body: ExtractRequirementsRequest, user: CurrentUser = Depends(require_active_subscription)):
    extracted = await extract_requirements(body.description, org_id=user.organization_id)
    return json_safe(extracted)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs").select("*").eq("id", job_id).eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return json_safe(job)


@router.get("/jobs/{job_id}/dashboard")
def get_job_dashboard(job_id: str, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs").select("id, title").eq("id", job_id).eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    rows = (
        db.table("candidates")
        .select("*")
        .eq("job_id", job_id)
        .eq("organization_id", user.organization_id)
        .execute()
    ).data or []

    processed = [r for r in rows if r.get("processing_status") in ("Completed", "Needs review")]
    strong_matches = [r for r in rows if r.get("score_status") == "Strong Match"]
    shortlisted = [r for r in rows if r.get("shortlisted")]
    contacted = [r for r in rows if r.get("contacted")]
    failed = [r for r in rows if r.get("processing_status") == "Failed"]
    scored = [r for r in rows if float(r.get("score") or 0) > 0]
    average_score = round(sum(float(r.get("score") or 0) for r in scored) / len(scored), 1) if scored else None

    return json_safe(
        {
            "job_title": job.get("title"),
            "total": len(rows),
            "processed": len(processed),
            "strong_matches": len(strong_matches),
            "shortlisted": len(shortlisted),
            "contacted": len(contacted),
            "failed": len(failed),
            "average_score": average_score,
        }
    )


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
                "structured_requirements": body.structured_requirements or {},
                "scoring_weights": body.scoring_weights or DEFAULT_SCORING_WEIGHTS,
                "score_thresholds": body.score_thresholds or DEFAULT_SCORE_THRESHOLDS,
                "requirements_source": body.requirements_source,
            }
        )
        .select()
        .execute()
    )
    rows = exec_rows(row)
    if not rows:
        raise HTTPException(status_code=500, detail="Could not create job.")
    log_action(user.organization_id, user.id, user.email, "job_created", "job", rows[0]["id"])
    return json_safe(rows[0])


@router.patch("/jobs/{job_id}")
def update_job(job_id: str, body: JobUpdate, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided.")

    current = exec_maybe_single(
        db.table("jobs").select("*").eq("id", job_id).eq("organization_id", user.organization_id)
    )
    if not current:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Requirement/description changes must not silently invalidate past scores — snapshot the
    # outgoing state as a new version. Weight-only changes stay an instant in-place recompute below.
    requirements_changed = "structured_requirements" in updates or "description" in updates
    if requirements_changed:
        db.table("job_requirement_versions").insert(
            {
                "organization_id": user.organization_id,
                "job_id": job_id,
                "version": current.get("requirements_version", 1),
                "description": current.get("description", ""),
                "structured_requirements": current.get("structured_requirements") or {},
                "scoring_weights": current.get("scoring_weights") or {},
                "created_by": user.id,
            }
        ).execute()
        updates["requirements_version"] = current.get("requirements_version", 1) + 1

    result = (
        db.table("jobs")
        .update(updates)
        .eq("id", job_id)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = result.data[0]

    if "scoring_weights" in updates or "score_thresholds" in updates:
        candidates = (
            db.table("candidates")
            .select("id, score_breakdown")
            .eq("job_id", job_id)
            .eq("organization_id", user.organization_id)
            .execute()
        ).data or []
        for cand in candidates:
            breakdown = cand.get("score_breakdown") or {}
            if not breakdown:
                continue
            score, status_label = recompute_score(breakdown, job["scoring_weights"], job.get("score_thresholds"))
            db.table("candidates").update({"score": score, "score_status": status_label}).eq("id", cand["id"]).execute()

    if requirements_changed:
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "job_requirements_versioned",
            "job",
            job_id,
            {"new_version": job["requirements_version"]},
        )

    return json_safe(job)


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
    ids: str | None = Query(None),
    status: str | None = Query(None),
    shortlisted: bool | None = Query(None),
    job_id: str | None = Query(None),
    processing_status: str | None = Query(None),
    tier: str | None = Query(None),
    meets_required: bool | None = Query(None),
    min_score: float | None = Query(None),
    max_score: float | None = Query(None),
    min_experience_years: float | None = Query(None),
    skills: str | None = Query(None),
    education: str | None = Query(None),
    location: str | None = Query(None),
    work_authorization: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
):
    db = get_admin_client()
    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if ids:
        query = query.in_("id", [i for i in ids.split(",") if i])
    if status:
        query = query.eq("status", status)
    if shortlisted is not None:
        query = query.eq("shortlisted", shortlisted)
    if job_id:
        query = query.eq("job_id", job_id)
    if processing_status:
        query = query.eq("processing_status", processing_status)
    if meets_required is not None:
        query = query.eq("meets_required", meets_required)
    if min_score is not None:
        query = query.gte("score", min_score)
    if max_score is not None:
        query = query.lte("score", max_score)
    if min_experience_years is not None:
        query = query.gte("experience_years", min_experience_years)
    if skills:
        query = query.ilike("skills", f"%{skills}%")
    if education:
        query = query.ilike("education", f"%{education}%")
    if location:
        query = query.ilike("location", f"%{location}%")

    result = query.execute()
    rows = result.data or []

    if q:
        terms = [t.lower() for t in q.split() if t.strip()]

        def _row_matches(row: dict, term: str) -> bool:
            haystacks = [
                row.get("name") or "",
                row.get("email") or "",
                row.get("current_role") or "",
                row.get("skills") or "",
                row.get("cv_text") or "",
                " ".join(row.get("certifications") or []),
                " ".join(
                    f"{e.get('company') or ''} {e.get('title') or ''}" for e in (row.get("employment_history") or [])
                ),
            ]
            return any(term in h.lower() for h in haystacks)

        rows = [r for r in rows if all(_row_matches(r, term) for term in terms)]
    if tier:
        rows = [r for r in rows if (r.get("score_status") or "") == tier]
    if work_authorization:
        wa_lower = work_authorization.lower()
        rows = [
            r
            for r in rows
            if any(
                wa_lower in (req.get("label") or "").lower() and req.get("result") == "meets"
                for req in (r.get("requirement_results") or [])
                if req.get("category") == "location_work_auth"
            )
        ]

    sort_key = sort if sort in ("score", "experience_years", "education", "name", "processing_status", "created_at") else "created_at"
    reverse = order != "asc"
    if sort_key == "score":
        # Default ranking cascade: match score, then required-requirement satisfaction, then experience.
        rows.sort(
            key=lambda r: (
                float(r.get("score") or 0),
                1 if r.get("meets_required") else 0,
                float(r.get("experience_years") or 0),
            ),
            reverse=reverse,
        )
    else:
        rows.sort(
            key=lambda r: (
                r.get(sort_key) is None,
                r.get(sort_key) or 0 if sort_key == "experience_years" else str(r.get(sort_key) or ""),
            ),
            reverse=reverse,
        )

    return json_safe(rows)


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
    if data.get("call_recording_path"):
        data["call_recording_download_url"] = get_call_recording_url(data["call_recording_path"])
    logs = (
        db.table("audit_logs")
        .select("*")
        .eq("organization_id", user.organization_id)
        .eq("entity_id", candidate_id)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    data["history"] = json_safe(logs.data or [])
    return json_safe(data)


@router.post("/candidates/{candidate_id}/call-recording")
async def upload_call_recording_endpoint(
    candidate_id: str,
    file: UploadFile = File(...),
    consent: bool = Form(...),
    user: CurrentUser = Depends(require_active_subscription),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot upload call recordings.")
    if not consent:
        raise HTTPException(status_code=400, detail="Candidate consent is required before uploading a call recording.")

    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    content = await file.read()
    if len(content) > settings.max_recording_bytes:
        raise HTTPException(status_code=400, detail=f"Recording is too large ({settings.max_recording_bytes // (1024 * 1024)}MB max).")

    filename = file.filename or "call.m4a"
    parsed = process_call_recording(content, filename)
    if parsed.get("parse_error"):
        raise HTTPException(status_code=400, detail=f"{filename}: {parsed['parse_error']}")

    storage_path = upload_call_recording(user.organization_id, candidate_id, filename, content)
    row = (
        db.table("candidates")
        .update(
            {
                "call_recording_path": storage_path,
                "call_transcript": parsed.get("transcript", "")[:8000],
                "salary_expectation": parsed.get("salary_expectation", ""),
                "notice_period": parsed.get("notice_period", ""),
                "availability": parsed.get("availability", ""),
                "flight_risk_notes": parsed.get("flight_risk_notes", ""),
                "call_consent": True,
                "call_recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    rows = exec_rows(row)
    if not rows:
        raise HTTPException(status_code=500, detail="Could not save call recording.")

    log_action(
        user.organization_id,
        user.id,
        user.email,
        "call_recording_processed",
        "candidate",
        candidate_id,
        {"filename": filename},
    )
    updated = rows[0]
    if updated.get("call_recording_path"):
        updated["call_recording_download_url"] = get_call_recording_url(updated["call_recording_path"])
    return json_safe(updated)


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
    if not is_supported_filename(filename):
        raise HTTPException(status_code=400, detail=f"{filename}: Unsupported file type. Upload PDF, DOCX, or TXT.")
    if len(content) > settings.max_cv_file_bytes:
        raise HTTPException(status_code=400, detail=f"{filename}: File is too large ({settings.max_cv_file_bytes // (1024 * 1024)}MB max).")

    db = get_admin_client()
    if job_id:
        job = exec_maybe_single(
            db.table("jobs").select("id").eq("id", job_id).eq("organization_id", user.organization_id)
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")

    parsed = await process_cv_bytes(content, filename, org_id=user.organization_id)
    if parsed.get("parse_error"):
        raise HTTPException(status_code=400, detail=f"{filename}: {parsed['parse_error']}")

    candidate_id = str(uuid.uuid4())
    storage_path = upload_cv(user.organization_id, candidate_id, filename, content)
    file_hash = compute_file_hash(content)
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
                "location": parsed.get("location", ""),
                "current_role": parsed.get("current_role", ""),
                "skills": parsed.get("skills", ""),
                "experience_years": parsed.get("experience_years", 0),
                "education": parsed.get("education", ""),
                "employment_history": parsed.get("employment_history", []),
                "certifications": parsed.get("certifications", []),
                "filename": filename,
                "cv_storage_path": storage_path,
                "file_hash": file_hash,
                "cv_text": parsed.get("raw_text", "")[:8000],
                "notes": parsed.get("summary", ""),
                "status": "New Applicant",
                "processing_status": "Completed",
            }
        )
        .select()
        .execute()
    )
    rows = exec_rows(row)
    if not rows:
        raise HTTPException(status_code=500, detail=f"Could not save {filename}.")
    record_usage(user.organization_id, "cv_uploaded")
    log_action(user.organization_id, user.id, user.email, "cv_uploaded", "candidate", candidate_id, {"filename": filename})
    return json_safe(rows[0])


@router.post(
    "/candidates/upload-batch",
    dependencies=[Depends(rate_limiter("upload", settings.rate_limit_upload_per_minute))],
)
async def upload_candidates_batch(
    files: list[UploadFile] = File(...),
    job_id: str | None = Form(None),
    bypass_duplicate_check: str = Form(""),
    user: CurrentUser = Depends(require_active_subscription),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot upload CVs.")
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one CV file.")
    if len(files) > settings.max_batch_files:
        raise HTTPException(status_code=400, detail=f"Select at most {settings.max_batch_files} files per upload.")

    bypass_filenames = {f.strip() for f in bypass_duplicate_check.split(",") if f.strip()}

    db = get_admin_client()
    if job_id:
        job = exec_maybe_single(
            db.table("jobs").select("id").eq("id", job_id).eq("organization_id", user.organization_id)
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job not found.")

    accepted: list[dict] = []
    rejected: list[dict] = []
    duplicates: list[dict] = []
    file_bytes: dict[str, bytes] = {}

    for upload in files:
        filename = upload.filename or "cv.txt"
        if not is_supported_filename(filename):
            rejected.append({"filename": filename, "error": "Unsupported format"})
            continue
        try:
            content = await upload.read()
            if len(content) > settings.max_cv_file_bytes:
                rejected.append({"filename": filename, "error": f"File too large ({settings.max_cv_file_bytes // (1024 * 1024)}MB max)"})
                continue

            file_hash = compute_file_hash(content)
            if filename not in bypass_filenames:
                existing = exec_maybe_single(
                    db.table("candidates")
                    .select("id, name")
                    .eq("organization_id", user.organization_id)
                    .eq("file_hash", file_hash)
                )
                if existing:
                    duplicates.append(
                        {"filename": filename, "existing_candidate_id": existing["id"], "existing_candidate_name": existing.get("name")}
                    )
                    continue

            candidate_id = str(uuid.uuid4())
            storage_path = upload_cv(user.organization_id, candidate_id, filename, content)
            row = (
                db.table("candidates")
                .insert(
                    {
                        "id": candidate_id,
                        "organization_id": user.organization_id,
                        "job_id": job_id,
                        "name": "Unknown",
                        "filename": filename,
                        "cv_storage_path": storage_path,
                        "file_hash": file_hash,
                        "status": "New Applicant",
                        "processing_status": "Queued",
                    }
                )
                .select()
                .execute()
            )
            rows = exec_rows(row)
            if not rows:
                rejected.append({"filename": filename, "error": "Could not save file"})
                continue
            accepted.append(rows[0])
            file_bytes[candidate_id] = content
        except Exception as exc:
            rejected.append({"filename": filename, "error": str(exc)})

    if not accepted:
        if duplicates:
            return json_safe(
                {
                    "batch_id": None,
                    "total": 0,
                    "rejected": rejected,
                    "duplicates": duplicates,
                    "message": "All files were duplicates of existing candidates.",
                }
            )
        raise HTTPException(status_code=400, detail=rejected[0]["error"] if rejected else "No files accepted.")

    batch_row = (
        db.table("processing_batches")
        .insert(
            {
                "organization_id": user.organization_id,
                "job_id": job_id,
                "created_by": user.id,
                "status": "Queued",
                "total_count": len(accepted),
            }
        )
        .select()
        .execute()
    )
    batch = exec_rows(batch_row)[0]
    batch_id = batch["id"]

    candidate_ids = [c["id"] for c in accepted]
    db.table("candidates").update({"processing_batch_id": batch_id}).in_("id", candidate_ids).execute()

    log_action(
        user.organization_id,
        user.id,
        user.email,
        "batch_upload_started",
        "processing_batch",
        batch_id,
        {"total": len(accepted), "rejected": len(rejected), "duplicates": len(duplicates)},
    )
    record_usage(user.organization_id, "cv_uploaded", quantity=len(accepted))

    processing.launch_batch(batch_id, file_bytes)

    return json_safe(
        {
            "batch_id": batch_id,
            "total": len(accepted),
            "rejected": rejected,
            "duplicates": duplicates,
            "message": f"Uploading {len(accepted)} CV(s) for processing.",
        }
    )


@router.get("/processing-batches/{batch_id}")
def get_processing_batch(batch_id: str, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    batch = exec_maybe_single(
        db.table("processing_batches").select("*").eq("id", batch_id).eq("organization_id", user.organization_id)
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Processing batch not found.")
    candidates = (
        db.table("candidates")
        .select("id, name, filename, processing_status, processing_error")
        .eq("processing_batch_id", batch_id)
        .execute()
    ).data or []
    batch["candidates"] = candidates
    return json_safe(batch)


@router.post("/processing-batches/{batch_id}/retry")
def retry_processing_batch(
    batch_id: str,
    body: RetryProcessingRequest,
    user: CurrentUser = Depends(require_active_subscription),
):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot retry processing.")
    db = get_admin_client()
    batch = exec_maybe_single(
        db.table("processing_batches").select("id").eq("id", batch_id).eq("organization_id", user.organization_id)
    )
    if not batch:
        raise HTTPException(status_code=404, detail="Processing batch not found.")
    reset_count = processing.retry_candidates(batch_id, body.candidate_ids)
    return {"message": f"Retrying {reset_count} candidate(s)."}


@router.post("/candidates/{candidate_id}/retry-processing")
def retry_candidate_processing(candidate_id: str, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot retry processing.")
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id, processing_batch_id")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not cand.get("processing_batch_id"):
        raise HTTPException(status_code=400, detail="This candidate has no processing history to retry.")
    db.table("candidates").update({"processing_status": "Failed"}).eq("id", candidate_id).execute()
    reset_count = processing.retry_candidates(cand["processing_batch_id"], [candidate_id])
    return {"message": f"Retrying {reset_count} candidate(s)."}


@router.post("/candidates/{candidate_id}/reanalyze")
def reanalyze_candidate(candidate_id: str, user: CurrentUser = Depends(require_active_subscription)):
    """Force a fresh scoring pass on a candidate regardless of current status — unlike
    retry-processing, this works on already-Completed candidates too (section 46)."""
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot re-analyze candidates.")
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id, name, job_id")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    if not cand.get("job_id"):
        raise HTTPException(status_code=400, detail="Assign this candidate to a job before re-analyzing.")

    batch_row = (
        db.table("processing_batches")
        .insert(
            {
                "organization_id": user.organization_id,
                "job_id": cand["job_id"],
                "created_by": user.id,
                "status": "Queued",
                "total_count": 1,
            }
        )
        .select()
        .execute()
    )
    batch_id = exec_rows(batch_row)[0]["id"]
    db.table("candidates").update(
        {"processing_batch_id": batch_id, "processing_status": "Queued", "processing_error": ""}
    ).eq("id", candidate_id).execute()

    log_action(user.organization_id, user.id, user.email, "candidate_reanalyze_requested", "candidate", candidate_id, {"name": cand.get("name")})
    processing.launch_batch(batch_id)
    return {"batch_id": batch_id, "message": f"Re-analyzing {cand.get('name')}."}


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
    return json_safe(result.data[0])


@router.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, user: CurrentUser = Depends(require_role("owner", "recruiter"))):
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("id, name, cv_storage_path, call_recording_path")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    delete_cv(cand.get("cv_storage_path") or "")
    delete_call_recording(cand.get("call_recording_path") or "")
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
        db.table("candidates").select("id, name, shortlisted").eq("id", candidate_id).eq("organization_id", user.organization_id)
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


@router.post("/candidates/compare")
async def compare_candidates_endpoint(body: CompareRequest, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    candidates = (
        db.table("candidates")
        .select("*")
        .in_("id", body.candidate_ids)
        .eq("organization_id", user.organization_id)
        .execute()
    ).data or []
    if len(candidates) != len(set(body.candidate_ids)):
        raise HTTPException(status_code=404, detail="One or more candidates not found.")

    job_ids = {c.get("job_id") for c in candidates}
    if len(job_ids) != 1 or None in job_ids:
        raise HTTPException(status_code=400, detail="Candidates must be scored against the same job to compare.")
    job = exec_maybe_single(
        db.table("jobs").select("*").eq("id", job_ids.pop()).eq("organization_id", user.organization_id)
    )

    summary = await compare_candidates(candidates, job or {})
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "candidates_compared",
        "job",
        job.get("id") if job else None,
        {"candidate_ids": body.candidate_ids},
    )
    return json_safe({"candidates": candidates, "summary": summary})


@router.post("/candidates/bulk-shortlist")
def bulk_shortlist(body: BulkShortlistRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot shortlist.")
    db = get_admin_client()
    new_status = "Shortlisted" if body.shortlisted else "Scored"
    result = (
        db.table("candidates")
        .update({"shortlisted": body.shortlisted, "status": new_status})
        .in_("id", body.candidate_ids)
        .eq("organization_id", user.organization_id)
        .execute()
    )
    updated = result.data or []
    action = "candidate_shortlisted" if body.shortlisted else "candidate_unshortlisted"
    for row in updated:
        log_action(user.organization_id, user.id, user.email, action, "candidate", row["id"], {"name": row.get("name"), "bulk": True})
    verb = "Added" if body.shortlisted else "Removed"
    preposition = "to" if body.shortlisted else "from"
    return {"message": f"{verb} {len(updated)} candidate(s) {preposition} the shortlist."}


@router.post("/candidates/retry-processing-bulk")
def retry_processing_bulk(body: BulkRetryRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot retry processing.")
    db = get_admin_client()
    rows = (
        db.table("candidates")
        .select("id, processing_batch_id")
        .in_("id", body.candidate_ids)
        .eq("organization_id", user.organization_id)
        .eq("processing_status", "Failed")
        .execute()
    ).data or []

    by_batch: dict[str, list[str]] = {}
    for row in rows:
        batch_id = row.get("processing_batch_id")
        if batch_id:
            by_batch.setdefault(batch_id, []).append(row["id"])

    total = sum(processing.retry_candidates(batch_id, ids) for batch_id, ids in by_batch.items())
    return {"message": f"Retrying {total} candidate(s)."}


@router.get("/candidates/export")
def export_candidates(
    user: CurrentUser = Depends(require_active_subscription),
    candidate_ids: str | None = Query(None),
    job_id: str | None = Query(None),
    shortlisted: bool | None = Query(None),
    include_contact: bool = Query(False),
):
    db = get_admin_client()
    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if candidate_ids:
        ids = [i for i in candidate_ids.split(",") if i]
        query = query.in_("id", ids)
    else:
        if job_id:
            query = query.eq("job_id", job_id)
        if shortlisted is not None:
            query = query.eq("shortlisted", shortlisted)
    rows = query.execute().data or []

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = ["Name", "Match Score", "Recommendation", "Key Strengths", "Missing Requirements", "Relevant Experience"]
    if include_contact:
        header += ["Email", "Phone"]
    writer.writerow(header)

    for r in rows:
        missing = [
            req.get("label")
            for req in (r.get("requirement_results") or [])
            if req.get("is_hard") and req.get("result") != "meets"
        ]
        experience = f"{r.get('current_role', '')} ({r.get('experience_years', 0)} yrs)"
        line = [
            r.get("name", ""),
            r.get("score", ""),
            r.get("score_status", ""),
            "; ".join(r.get("strengths") or []),
            "; ".join(missing),
            experience,
        ]
        if include_contact:
            line += [r.get("email", ""), r.get("phone", "")]
        writer.writerow(line)

    log_action(user.organization_id, user.id, user.email, "candidates_exported", "candidate", None, {"count": len(rows)})
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidates_export.csv"},
    )


@router.post(
    "/scoring/run",
    dependencies=[Depends(rate_limiter("scoring", settings.rate_limit_scoring_per_minute))],
)
def run_scoring(body: ScoreRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot score candidates.")
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs").select("*").eq("id", body.job_id).eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = db.table("candidates").select("*").eq("organization_id", user.organization_id)
    if body.candidate_ids:
        query = query.in_("id", body.candidate_ids)
    candidates = query.execute().data or []

    current_version = job.get("requirements_version", 1)
    to_score_ids = []
    skipped = 0
    for cand in candidates:
        already_scored = cand.get("score") and float(cand.get("score") or 0) > 0
        same_job = cand.get("job_id") == body.job_id
        same_version = cand.get("scored_requirements_version") == current_version
        if already_scored and same_job and same_version and not body.rescore and not body.candidate_ids:
            skipped += 1
            continue
        to_score_ids.append(cand["id"])

    if not to_score_ids:
        return json_safe(
            {"batch_id": None, "total": 0, "skipped": skipped, "job_title": job.get("title"), "message": "No candidates needed scoring."}
        )

    batch_row = (
        db.table("processing_batches")
        .insert(
            {
                "organization_id": user.organization_id,
                "job_id": body.job_id,
                "created_by": user.id,
                "status": "Queued",
                "total_count": len(to_score_ids),
            }
        )
        .select()
        .execute()
    )
    batch = exec_rows(batch_row)[0]
    batch_id = batch["id"]

    db.table("candidates").update({"processing_batch_id": batch_id, "processing_status": "Queued"}).in_("id", to_score_ids).execute()

    log_action(
        user.organization_id,
        user.id,
        user.email,
        "scoring_batch_started",
        "processing_batch",
        batch_id,
        {"total": len(to_score_ids), "job_id": body.job_id},
    )

    processing.launch_batch(batch_id)

    return json_safe(
        {
            "batch_id": batch_id,
            "total": len(to_score_ids),
            "skipped": skipped,
            "job_title": job.get("title"),
            "message": f"Scoring {len(to_score_ids)} candidate(s) against \"{job.get('title')}\".",
        }
    )


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

    return json_safe(
        {
            "count": len(shortlisted),
            "names": shortlisted,
            "message": f"Shortlisted {len(shortlisted)} candidate(s): {', '.join(shortlisted) if shortlisted else 'none found'}.",
        }
    )


@router.get("/dashboard/stats")
def dashboard_stats(user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    rows = db.table("candidates").select("*").eq("organization_id", user.organization_id).execute().data or []
    status_counts = {}
    for r in rows:
        s = r.get("status") or "Unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    return json_safe(
        {
            "total": len(rows),
            "scored": len([r for r in rows if float(r.get("score") or 0) > 0]),
            "shortlisted": len([r for r in rows if r.get("shortlisted")]),
            "contacted": len([r for r in rows if r.get("contacted")]),
            "interviews": len([r for r in rows if r.get("status") == "Interview Scheduled"]),
            "rejected": len([r for r in rows if r.get("status") == "Rejected"]),
            "pipeline": status_counts,
            "recent": json_safe(rows[:8]),
        }
    )
