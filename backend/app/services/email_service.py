import resend
from app.config import settings

DEFAULT_TEMPLATES = {
    "interview_invite": {
        "subject": "Interview Invitation – {job_title} at {company_name}",
        "body": """Dear {candidate_name},

Thank you for your interest in the {job_title} position at {company_name}.

We were impressed with your background and would like to invite you to an interview.

Interview Details:
  Date: {interview_date}
  Time: {interview_time}
  Format: {interview_format}

Please reply to confirm your availability.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team""",
    },
    "follow_up": {
        "subject": "Following Up – {job_title} Application",
        "body": """Dear {candidate_name},

I wanted to follow up regarding your application for the {job_title} role at {company_name}.

We remain interested in speaking with you. Please reply if you are still available.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team""",
    },
    "acknowledgement": {
        "subject": "Application Received – {job_title} at {company_name}",
        "body": """Dear {candidate_name},

Thank you for applying for the {job_title} position at {company_name}.

We have received your application and will be in touch within 5–7 working days.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team""",
    },
}


def apply_placeholders(text: str, placeholders: dict) -> str:
    """Replace {key} and [key] placeholders without breaking already-filled text."""
    result = text or ""
    for key, value in placeholders.items():
        replacement = str(value)
        result = result.replace("{" + key + "}", replacement)
        result = result.replace("[" + key + "]", replacement)
    return result


def build_outreach_placeholders(
    candidate: dict,
    *,
    company_name: str,
    recruiter_name: str,
    job_title: str = "the role",
) -> dict:
    return {
        "candidate_name": candidate.get("name") or "Candidate",
        "job_title": job_title,
        "company_name": company_name or "our company",
        "recruiter_name": recruiter_name or "Recruitment Team",
        "interview_date": candidate.get("interview_date") or "To be confirmed",
        "interview_time": candidate.get("interview_time") or "To be confirmed",
        "interview_format": candidate.get("interview_format") or "Video call (link to follow)",
    }


def render_template(template: dict, placeholders: dict) -> dict:
    return {
        "subject": apply_placeholders(template["subject"], placeholders),
        "body": apply_placeholders(template["body"], placeholders),
    }


def send_email(to_email: str, subject: str, body: str) -> dict:
    if not settings.resend_api_key:
        return {"success": False, "error": "RESEND_API_KEY not configured on Render."}
    if not settings.resend_api_key.startswith("re_"):
        return {
            "success": False,
            "error": "RESEND_API_KEY looks wrong — it must start with re_ from resend.com/api-keys (not a Supabase key).",
        }
    if not to_email or "@" not in to_email:
        return {"success": False, "error": "Invalid recipient email."}

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to_email],
                "subject": subject,
                "text": body,
            }
        )
        return {"success": True, "error": None}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def email_is_configured() -> bool:
    return bool(settings.resend_api_key and settings.resend_api_key.startswith("re_") and settings.email_from)


def is_resend_sandbox_from() -> bool:
    return "resend.dev" in (settings.email_from or "")


def resolve_outreach_recipient(
    candidate_email: str,
    send_to_override: str | None = None,
) -> tuple[str, str | None]:
    """
    Pick the recipient address. Returns (email, note_for_user).
    With onboarding@resend.dev, Resend only delivers to RESEND_TEST_TO_EMAIL.
    """
    candidate_email = (candidate_email or "").strip()
    override = (send_to_override or "").strip()

    if is_resend_sandbox_from():
        allowed = (settings.resend_test_to_email or "").strip()
        if not allowed:
            raise ValueError(
                "Set RESEND_TEST_TO_EMAIL on Render to the email you used to sign up at resend.com "
                "(e.g. khawajahamzaj@gmail.com). Resend test mode only sends to that address."
            )
        if override or not candidate_email or candidate_email.endswith(("@email.com", "@example.com")):
            note = None
            if override and override.lower() != allowed.lower():
                note = f"Resend test mode: email sent to {allowed} (not {override})."
            elif candidate_email and candidate_email.lower() != allowed.lower():
                note = f"Resend test mode: demo email sent to {allowed} instead of {candidate_email}."
            return allowed, note
        return candidate_email, None

    return override or candidate_email, None
