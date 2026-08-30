import asyncio
import logging

from app.config import settings
from app.database import exec_maybe_single, exec_rows, get_admin_client
from app.services import storage
from app.services.audit import log_action
from app.services.cv_parser import extract_text_from_bytes, parse_cv
from app.services.requirements import extract_requirements
from app.services.scoring import score_candidate
from app.services.usage import record_usage

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def classify_completion_status(cv_text: str, min_words: int) -> str:
    word_count = len((cv_text or "").split())
    return "Needs review" if word_count < min_words else "Completed"


def launch_batch(batch_id: str, file_bytes: dict[str, bytes] | None = None) -> None:
    """Fire-and-forget the batch orchestrator, keeping a strong ref so it isn't garbage-collected mid-run."""
    task = asyncio.create_task(run_processing_batch(batch_id, file_bytes))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _ensure_job_requirements(db, job: dict | None) -> dict | None:
    if job and job.get("requirements_source") == "freeform":
        extracted = await extract_requirements(job.get("description", ""), org_id=job.get("organization_id", ""))
        db.table("jobs").update(
            {"structured_requirements": extracted, "requirements_source": "extracted"}
        ).eq("id", job["id"]).execute()
        job = {**job, "structured_requirements": extracted, "requirements_source": "extracted"}
    return job


async def _process_one(
    db,
    candidate: dict,
    job: dict | None,
    semaphore: asyncio.Semaphore,
    org_id: str,
    user_id: str | None,
    user_email: str,
    content_bytes: bytes | None,
) -> bool:
    candidate_id = candidate["id"]
    async with semaphore:
        try:
            needs_parse = not (candidate.get("cv_text") or "").strip()
            if needs_parse:
                db.table("candidates").update({"processing_status": "Extracting"}).eq("id", candidate_id).execute()
                if content_bytes is None:
                    content_bytes = await asyncio.to_thread(storage.download_cv, candidate.get("cv_storage_path", ""))
                raw_text = await asyncio.to_thread(extract_text_from_bytes, content_bytes, candidate.get("filename", ""))
                parsed = await parse_cv(raw_text, candidate.get("filename", ""), org_id=org_id)
                if parsed.get("parse_error"):
                    db.table("candidates").update(
                        {"processing_status": "Failed", "processing_error": parsed["parse_error"]}
                    ).eq("id", candidate_id).execute()
                    return False

                update = {
                    "name": parsed.get("name") or candidate.get("name", "Unknown"),
                    "email": parsed.get("email", ""),
                    "phone": parsed.get("phone", ""),
                    "location": parsed.get("location", ""),
                    "current_role": parsed.get("current_role", ""),
                    "skills": parsed.get("skills", ""),
                    "experience_years": parsed.get("experience_years", 0),
                    "education": parsed.get("education", ""),
                    "employment_history": parsed.get("employment_history", []),
                    "certifications": parsed.get("certifications", []),
                    "cv_text": parsed.get("raw_text", "")[:8000],
                    "notes": candidate.get("notes") or parsed.get("summary", ""),
                }
                db.table("candidates").update(update).eq("id", candidate_id).execute()
                candidate = {**candidate, **update}

                email = (update.get("email") or "").strip().lower()
                if email:
                    existing = (
                        db.table("candidates")
                        .select("id, name")
                        .eq("organization_id", org_id)
                        .ilike("email", email)
                        .neq("id", candidate_id)
                        .execute()
                    ).data or []
                    if existing:
                        log_action(
                            org_id,
                            user_id,
                            user_email,
                            "possible_duplicate_email",
                            "candidate",
                            candidate_id,
                            {"email": email, "matches": [e.get("name") for e in existing]},
                        )

            final_status = classify_completion_status(candidate.get("cv_text") or "", settings.needs_review_min_words)

            if job:
                db.table("candidates").update({"processing_status": "Analyzing"}).eq("id", candidate_id).execute()
                db.table("candidates").update({"processing_status": "Scoring"}).eq("id", candidate_id).execute()
                scoring = await score_candidate(candidate, job)
                if scoring.get("error"):
                    db.table("candidates").update(
                        {"processing_status": "Failed", "processing_error": scoring["error"]}
                    ).eq("id", candidate_id).execute()
                    return False

                db.table("candidates").update(
                    {
                        "score": scoring["score"],
                        "score_status": scoring["status"],
                        "score_reason": " | ".join(scoring.get("reason", [])),
                        "score_breakdown": scoring["breakdown"],
                        "requirement_results": scoring["requirement_results"],
                        "strengths": scoring["strengths"],
                        "concerns": scoring["concerns"],
                        "meets_required": scoring["meets_required"],
                        "scored_requirements_version": job.get("requirements_version", 1),
                        "status": "Scored",
                        "job_id": job["id"],
                        "processing_status": final_status,
                        "processing_error": "",
                    }
                ).eq("id", candidate_id).execute()
                record_usage(org_id, "cv_analyzed")
                log_action(
                    org_id,
                    user_id,
                    user_email,
                    "candidate_scored",
                    "candidate",
                    candidate_id,
                    {
                        "status": final_status,
                        "score": scoring["score"],
                        "requirements_version": job.get("requirements_version", 1),
                        "scoring_weights": job.get("scoring_weights"),
                        "model": settings.llm_model,
                    },
                )
            else:
                db.table("candidates").update(
                    {"processing_status": final_status, "processing_error": ""}
                ).eq("id", candidate_id).execute()
                log_action(org_id, user_id, user_email, "candidate_processed", "candidate", candidate_id, {"status": final_status})
            return True
        except Exception as exc:
            logger.warning("Processing failed for candidate %s: %s", candidate_id, exc)
            try:
                db.table("candidates").update(
                    {"processing_status": "Failed", "processing_error": str(exc)}
                ).eq("id", candidate_id).execute()
            except Exception:
                pass
            return False


async def run_processing_batch(batch_id: str, file_bytes: dict[str, bytes] | None = None) -> None:
    db = get_admin_client()
    batch = exec_maybe_single(db.table("processing_batches").select("*").eq("id", batch_id))
    if not batch:
        return

    db.table("processing_batches").update({"status": "Processing"}).eq("id", batch_id).execute()

    job = None
    if batch.get("job_id"):
        job = exec_maybe_single(db.table("jobs").select("*").eq("id", batch["job_id"]))
        job = await _ensure_job_requirements(db, job)

    candidates = exec_rows(
        db.table("candidates")
        .select("*")
        .eq("processing_batch_id", batch_id)
        .eq("processing_status", "Queued")
    )

    user_id = batch.get("created_by")
    creator = exec_maybe_single(db.table("profiles").select("email").eq("id", user_id)) if user_id else None
    user_email = (creator or {}).get("email", "")
    org_id = batch["organization_id"]

    semaphore = asyncio.Semaphore(max(1, settings.cv_processing_concurrency))
    file_bytes = file_bytes or {}
    await asyncio.gather(
        *(
            _process_one(db, c, job, semaphore, org_id, user_id, user_email, file_bytes.get(c["id"]))
            for c in candidates
        )
    )

    all_candidates = exec_rows(
        db.table("candidates").select("processing_status").eq("processing_batch_id", batch_id)
    )
    completed = sum(1 for c in all_candidates if c["processing_status"] in ("Completed", "Needs review"))
    failed = sum(1 for c in all_candidates if c["processing_status"] == "Failed")
    total = len(all_candidates)

    if total == 0:
        final_status = "Completed"
    elif failed == total:
        final_status = "Failed"
    elif failed > 0:
        final_status = "Completed with errors"
    else:
        final_status = "Completed"

    db.table("processing_batches").update(
        {"status": final_status, "completed_count": completed, "failed_count": failed}
    ).eq("id", batch_id).execute()


def retry_candidates(batch_id: str, candidate_ids: list[str] | None = None) -> int:
    """Reset failed candidates in a batch back to Queued and relaunch the orchestrator. Returns count reset."""
    db = get_admin_client()
    query = (
        db.table("candidates")
        .update({"processing_status": "Queued", "processing_error": ""})
        .eq("processing_batch_id", batch_id)
        .eq("processing_status", "Failed")
    )
    if candidate_ids:
        query = query.in_("id", candidate_ids)
    result = query.execute()
    reset_count = len(result.data or [])
    if reset_count:
        launch_batch(batch_id)
    return reset_count
