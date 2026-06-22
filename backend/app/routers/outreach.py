from fastapi import APIRouter, Depends, HTTPException
from app.database import get_admin_client, exec_maybe_single
from app.deps import get_current_user, require_role, require_active_subscription, CurrentUser
from app.schemas import SendEmailRequest, EmailTemplateUpdate, InviteMemberRequest, OrganizationUpdate, ProfileUpdate
from app.services.email_service import send_email, render_template, DEFAULT_TEMPLATES
from app.services.audit import log_action, list_logs
from app.services.org_setup import ensure_default_templates

router = APIRouter(tags=["outreach"])


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
    placeholders = {
        "candidate_name": cand.get("name") or "Candidate",
        "job_title": job_title,
        "company_name": user.org_name,
        "recruiter_name": user.full_name or "Recruitment Team",
        "interview_date": cand.get("interview_date") or "To be confirmed",
        "interview_time": cand.get("interview_time") or "To be confirmed",
        "interview_format": "Video call (link to follow)",
    }
    return render_template(tmpl, placeholders)


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

    if body.demo_mode:
        log_action(
            user.organization_id,
            user.id,
            user.email,
            "email_preview",
            "candidate",
            body.candidate_id,
            {"subject": body.subject},
        )
        return {"success": True, "demo": True, "message": "Demo mode — email not sent."}

    result = send_email(cand.get("email", ""), body.subject, body.body)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    db.table("candidates").update({"contacted": True, "status": "Contacted"}).eq("id", body.candidate_id).execute()
    log_action(
        user.organization_id,
        user.id,
        user.email,
        "email_sent",
        "candidate",
        body.candidate_id,
        {"subject": body.subject, "to": cand.get("email")},
    )
    return {"success": True, "demo": False}


@router.get("/audit-logs")
def audit_logs(user: CurrentUser = Depends(require_active_subscription)):
    return list_logs(user.organization_id)


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
