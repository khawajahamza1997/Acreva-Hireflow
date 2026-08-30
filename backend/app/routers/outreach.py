from fastapi import APIRouter, Depends, HTTPException, Query
from app.database import get_admin_client, exec_maybe_single
from app.deps import get_current_user, require_role, require_active_subscription, CurrentUser
from app.schemas import (
    SendEmailRequest,
    BulkSendEmailRequest,
    EmailTemplateUpdate,
    InviteMemberRequest,
    OrganizationUpdate,
    ProfileUpdate,
)
from app.config import settings
from app.services.email_service import (
    send_email,
    render_template,
    apply_placeholders,
    build_outreach_placeholders,
    DEFAULT_TEMPLATES,
    email_is_configured,
    is_resend_sandbox_from,
    resolve_outreach_recipient,
)
from app.services.audit import log_action, list_logs
from app.services.org_setup import ensure_default_templates
from app.services.usage import record_usage, get_usage_summary

router = APIRouter(tags=["outreach"])


def _job_title_for_candidate(db, candidate: dict, organization_id: str) -> str:
    job_id = candidate.get("job_id")
    if not job_id:
        return "the role"
    job = exec_maybe_single(
        db.table("jobs")
        .select("title")
        .eq("id", job_id)
        .eq("organization_id", organization_id)
    )
    return (job or {}).get("title") or "the role"


@router.get("/email-templates")
def get_email_templates(user: CurrentUser = Depends(require_active_subscription)):
    ensure_default_templates(user.organization_id)
    db = get_admin_client()
    result = db.table("email_templates").select("*").eq("organization_id", user.organization_id).execute()
    return result.data or []


@router.put("/email-templates/{template_type}")
def update_email_template(
    template_type: str,
    body: EmailTemplateUpdate,
    user: CurrentUser = Depends(require_role("owner", "recruiter")),
):
    if template_type not in DEFAULT_TEMPLATES:
        raise HTTPException(status_code=400, detail="Invalid template type.")
    db = get_admin_client()
    result = (
        db.table("email_templates")
        .update({"subject": body.subject, "body": body.body})
        .eq("organization_id", user.organization_id)
        .eq("template_type", template_type)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Template not found.")
    log_action(user.organization_id, user.id, user.email, "template_updated", "email_template", None, {"type": template_type})
    return result.data[0]


@router.post("/email-templates/{template_type}/preview")
def preview_template(
    template_type: str,
    candidate_id: str,
    job_title: str = "the role",
    user: CurrentUser = Depends(require_active_subscription),
):
    db = get_admin_client()
    tmpl = exec_maybe_single(
        db.table("email_templates")
        .select("*")
        .eq("organization_id", user.organization_id)
        .eq("template_type", template_type)
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found.")
    cand = exec_maybe_single(
        db.table("candidates")
        .select("*")
        .eq("id", candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    resolved_job_title = job_title if job_title != "the role" else _job_title_for_candidate(db, cand, user.organization_id)
    placeholders = build_outreach_placeholders(
        cand,
        company_name=user.org_name,
        recruiter_name=user.full_name or "Recruitment Team",
        job_title=resolved_job_title,
    )
    return render_template(tmpl, placeholders)


def _log_email(
    db,
    org_id: str,
    candidate_id: str | None,
    job_id: str | None,
    template_type: str,
    subject: str,
    to_email: str,
    status: str,
    error: str,
    sent_by: str,
) -> None:
    try:
        db.table("email_logs").insert(
            {
                "organization_id": org_id,
                "candidate_id": candidate_id,
                "job_id": job_id,
                "template_type": template_type,
                "subject": subject,
                "to_email": to_email,
                "status": status,
                "error": error,
                "sent_by": sent_by,
            }
        ).execute()
    except Exception:
        pass


@router.post("/outreach/send")
def send_outreach(body: SendEmailRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot send emails.")
    db = get_admin_client()
    cand = exec_maybe_single(
        db.table("candidates")
        .select("*")
        .eq("id", body.candidate_id)
        .eq("organization_id", user.organization_id)
    )
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    placeholders = build_outreach_placeholders(
        cand,
        company_name=user.org_name,
        recruiter_name=user.full_name or "Recruitment Team",
        job_title=_job_title_for_candidate(db, cand, user.organization_id),
    )
    subject = apply_placeholders(body.subject, placeholders)
    email_body = apply_placeholders(body.body, placeholders)

    if body.demo_mode:
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "email_preview",
            "candidate",
            body.candidate_id,
            {"subject": subject},
        )
        return {
            "success": True,
            "demo": True,
            "message": "Demo mode — email not sent.",
            "subject": subject,
            "body": email_body,
        }

    try:
        to_email, redirect_note = resolve_outreach_recipient(
            cand.get("email") or "",
            str(body.send_to_email) if body.send_to_email else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = send_email(to_email, subject, email_body)
    if not result["success"]:
        _log_email(db, user.organization_id, body.candidate_id, cand.get("job_id"), body.template_type, subject, to_email, "failed", result["error"], user.id)
        raise HTTPException(status_code=400, detail=result["error"])

    db.table("candidates").update({"contacted": True, "status": "Contacted"}).eq("id", body.candidate_id).execute()
    _log_email(db, user.organization_id, body.candidate_id, cand.get("job_id"), body.template_type, subject, to_email, "sent", "", user.id)
    record_usage(user.organization_id, "email_sent")
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "email_sent",
        "candidate",
        body.candidate_id,
        {"subject": subject, "to": to_email},
    )
    message = f"Email sent to {to_email}."
    if redirect_note:
        message = redirect_note
    return {"success": True, "demo": False, "message": message}


@router.post("/outreach/send-bulk")
def send_outreach_bulk(body: BulkSendEmailRequest, user: CurrentUser = Depends(require_active_subscription)):
    if user.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot send emails.")
    if len(body.candidate_ids) > settings.max_batch_files:
        raise HTTPException(status_code=400, detail=f"Select at most {settings.max_batch_files} recipients per send.")

    db = get_admin_client()
    candidates = (
        db.table("candidates")
        .select("*")
        .in_("id", body.candidate_ids)
        .eq("organization_id", user.organization_id)
        .execute()
    ).data or []

    results = []
    for cand in candidates:
        placeholders = build_outreach_placeholders(
            cand,
            company_name=user.org_name,
            recruiter_name=user.full_name or "Recruitment Team",
            job_title=_job_title_for_candidate(db, cand, user.organization_id),
        )
        subject = apply_placeholders(body.subject, placeholders)
        email_body = apply_placeholders(body.body, placeholders)

        if body.demo_mode:
            results.append({"candidate_id": cand["id"], "name": cand.get("name"), "status": "sent", "demo": True})
            continue

        try:
            to_email, _ = resolve_outreach_recipient(cand.get("email") or "", None)
        except ValueError as exc:
            results.append({"candidate_id": cand["id"], "name": cand.get("name"), "status": "failed", "error": str(exc)})
            _log_email(db, user.organization_id, cand["id"], cand.get("job_id"), body.template_type, subject, "", "failed", str(exc), user.id)
            continue

        send_result = send_email(to_email, subject, email_body)
        if send_result["success"]:
            db.table("candidates").update({"contacted": True, "status": "Contacted"}).eq("id", cand["id"]).execute()
            log_action(user.organization_id, user.id, user.email, "email_sent", "candidate", cand["id"], {"subject": subject, "to": to_email, "bulk": True})
            _log_email(db, user.organization_id, cand["id"], cand.get("job_id"), body.template_type, subject, to_email, "sent", "", user.id)
            record_usage(user.organization_id, "email_sent")
            results.append({"candidate_id": cand["id"], "name": cand.get("name"), "status": "sent"})
        else:
            _log_email(db, user.organization_id, cand["id"], cand.get("job_id"), body.template_type, subject, to_email, "failed", send_result["error"], user.id)
            results.append({"candidate_id": cand["id"], "name": cand.get("name"), "status": "failed", "error": send_result["error"]})

    sent = sum(1 for r in results if r["status"] == "sent")
    failed = sum(1 for r in results if r["status"] == "failed")
    return {"sent": sent, "failed": failed, "results": results}


@router.get("/outreach/send-log")
def outreach_send_log(user: CurrentUser = Depends(require_active_subscription), job_id: str | None = Query(None)):
    db = get_admin_client()
    query = db.table("email_logs").select("*").eq("organization_id", user.organization_id)
    if job_id:
        query = query.eq("job_id", job_id)
    result = query.order("created_at", desc=True).limit(100).execute()
    return result.data or []


@router.get("/outreach/email-status")
def outreach_email_status(user: CurrentUser = Depends(require_active_subscription)):
    configured = email_is_configured()
    test_mode = is_resend_sandbox_from()
    allowed = (settings.resend_test_to_email or "").strip()
    if configured and test_mode:
        hint = (
            f"Resend test mode: emails can only go to {allowed}."
            if allowed
            else "Add RESEND_TEST_TO_EMAIL on Render (your resend.com signup email, e.g. khawajahamzaj@gmail.com)."
        )
    elif configured:
        hint = "Email is ready. Uncheck Demo mode and send."
    else:
        hint = (
            "Add RESEND_API_KEY (starts with re_) and EMAIL_FROM=Acreva HireFlow <onboarding@resend.dev> on Render."
        )
    return {
        "configured": configured,
        "test_mode": test_mode,
        "from_address": settings.email_from,
        "your_email": user.email,
        "allowed_test_recipient": allowed or None,
        "hint": hint,
    }


@router.get("/audit-logs")
def audit_logs(user: CurrentUser = Depends(require_active_subscription), job_id: str | None = Query(None)):
    if not job_id:
        return list_logs(user.organization_id)

    db = get_admin_client()
    candidate_ids = [
        c["id"]
        for c in (
            db.table("candidates").select("id").eq("job_id", job_id).eq("organization_id", user.organization_id).execute()
        ).data
        or []
    ]
    batch_ids = [
        b["id"]
        for b in (
            db.table("processing_batches").select("id").eq("job_id", job_id).eq("organization_id", user.organization_id).execute()
        ).data
        or []
    ]
    relevant_ids = [job_id] + candidate_ids + batch_ids
    result = (
        db.table("audit_logs")
        .select("*")
        .eq("organization_id", user.organization_id)
        .in_("entity_id", relevant_ids)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return result.data or []


@router.get("/usage/summary")
def usage_summary(user: CurrentUser = Depends(require_active_subscription)):
    return get_usage_summary(user.organization_id)


@router.get("/team")
def list_team(user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    result = db.table("profiles").select("id, email, full_name, role, created_at").eq("organization_id", user.organization_id).execute()
    return result.data or []


@router.post("/team/invite")
def invite_member(body: InviteMemberRequest, user: CurrentUser = Depends(require_role("owner"))):
    db = get_admin_client()
    temp_password = "ChangeMe123!"
    auth = db.auth.admin.create_user(
        {
            "email": body.email,
            "password": temp_password,
            "email_confirm": True,
            "user_metadata": {"invited": True},
        }
    )
    if not auth.user:
        raise HTTPException(status_code=400, detail="Could not create user.")

    db.table("profiles").insert(
        {
            "id": auth.user.id,
            "organization_id": user.organization_id,
            "email": body.email,
            "full_name": "",
            "role": body.role,
        }
    ).execute()
    log_action(user.organization_id, user.id, user.email, "member_invited", "profile", auth.user.id, {"email": body.email, "role": body.role})
    return {
        "message": f"Invited {body.email}. Temporary password: {temp_password} — ask them to reset on first login.",
    }


@router.patch("/settings/profile")
def update_profile(body: ProfileUpdate, user: CurrentUser = Depends(get_current_user)):
    db = get_admin_client()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("profiles").update(updates).eq("id", user.id).execute()
    return result.data[0] if result.data else {"message": "Updated"}


@router.patch("/settings/organization")
def update_organization(body: OrganizationUpdate, user: CurrentUser = Depends(require_role("owner"))):
    db = get_admin_client()
    result = (
        db.table("organizations")
        .update({"name": body.name})
        .eq("id", user.organization_id)
        .execute()
    )
    return result.data[0] if result.data else {"message": "Updated"}
