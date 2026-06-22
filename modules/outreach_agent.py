# ============================================================
# outreach_agent.py
# ============================================================
# Purpose: Send personalised outreach emails to shortlisted
# candidates via Gmail SMTP.
#
# Email types supported:
#   - interview_invite   : Invite candidate for an interview
#   - follow_up          : Chase a candidate who hasn't responded
#   - acknowledgement    : Thank them for applying
#
# The recruiter always reviews and confirms before sending.
# This module never sends autonomously.
#
# Functions:
#   get_email_template()   → Returns a filled-in email template
#   send_email()           → Sends via Gmail SMTP
#   send_outreach()        → Main function: build + send + update sheet
# ============================================================

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from modules.sheets_utils import update_candidate

load_dotenv()


# ------------------------------------------------------------
# EMAIL TEMPLATES
# ------------------------------------------------------------
# Each template is a dict with 'subject' and 'body'.
# Placeholders like {candidate_name} are filled at send time.
# ------------------------------------------------------------

TEMPLATES = {

    "interview_invite": {
        "subject": "Interview Invitation – {job_title} at {company_name}",
        "body": """Dear {candidate_name},

Thank you for your interest in the {job_title} position at {company_name}.

We were impressed with your background and would like to invite you to an interview.

Interview Details:
  Date: {interview_date}
  Time: {interview_time}
  Format: {interview_format}

Please reply to this email to confirm your availability or to suggest an alternative time.

We look forward to speaking with you.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team"""
    },

    "follow_up": {
        "subject": "Following Up – {job_title} Application",
        "body": """Dear {candidate_name},

I hope you are well.

I wanted to follow up regarding your application for the {job_title} role at {company_name}.

We reviewed your profile and remain interested in speaking with you.
Could you please let us know if you are still available and interested in this opportunity?

Please reply to this email and we will get a time in the diary.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team"""
    },

    "acknowledgement": {
        "subject": "Application Received – {job_title} at {company_name}",
        "body": """Dear {candidate_name},

Thank you for applying for the {job_title} position at {company_name}.

We have received your application and our team is currently reviewing all candidates.
We aim to be in touch within 5–7 working days.

If you have any questions in the meantime, please do not hesitate to reach out.

Kind regards,
{recruiter_name}
{company_name} Recruitment Team"""
    }
}


# ------------------------------------------------------------
# TEMPLATE BUILDER
# ------------------------------------------------------------

def get_email_template(
    email_type: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
    recruiter_name: str,
    interview_date: str = "To be confirmed",
    interview_time: str = "To be confirmed",
    interview_format: str = "Video call (link to follow)"
) -> dict:
    """
    Returns a filled-in email template as a dict with 'subject' and 'body'.
    The recruiter can edit these in the UI before sending.

    Args:
        email_type      : "interview_invite", "follow_up", or "acknowledgement"
        candidate_name  : Used in greeting
        job_title       : Role being hired for
        company_name    : Hiring company name
        recruiter_name  : Sender's name (shown in sign-off)
        interview_date  : Only used in interview_invite template
        interview_time  : Only used in interview_invite template
        interview_format: e.g. "Video call", "In-person at London office"
    """
    template = TEMPLATES.get(email_type)

    if not template:
        # Fallback to acknowledgement if type not recognised
        template = TEMPLATES["acknowledgement"]

    placeholders = {
        "candidate_name": candidate_name or "Candidate",
        "job_title": job_title or "the advertised role",
        "company_name": company_name or "our company",
        "recruiter_name": recruiter_name or "The Recruitment Team",
        "interview_date": interview_date,
        "interview_time": interview_time,
        "interview_format": interview_format
    }

    return {
        "subject": template["subject"].format(**placeholders),
        "body": template["body"].format(**placeholders)
    }


# ------------------------------------------------------------
# SMTP EMAIL SENDER
# ------------------------------------------------------------

def send_email(
    to_email: str,
    subject: str,
    body: str
) -> dict:
    """
    Sends a plain text email via Gmail SMTP.

    Requires in .env:
        EMAIL_SENDER       = your Gmail address
        EMAIL_APP_PASSWORD = your Gmail App Password (not your real password)

    Returns:
        { "success": True, "error": None }
        { "success": False, "error": "..." }
    """
    sender = os.getenv("EMAIL_SENDER")
    app_password = os.getenv("EMAIL_APP_PASSWORD")

    if not sender or not app_password:
        return {
            "success": False,
            "error": "Email credentials not found in .env. Set EMAIL_SENDER and EMAIL_APP_PASSWORD."
        }

    if not to_email or "@" not in to_email:
        return {
            "success": False,
            "error": f"Invalid recipient email address: '{to_email}'"
        }

    try:
        # Build the email message
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect to Gmail SMTP server using TLS on port 587
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()                          # Encrypt the connection
            server.login(sender, app_password)         # Authenticate
            server.sendmail(sender, to_email, msg.as_string())

        return {"success": True, "error": None}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": (
                "Gmail authentication failed. Make sure you are using an App Password, "
                "not your real Gmail password. "
                "Generate one at: https://myaccount.google.com/apppasswords"
            )
        }

    except smtplib.SMTPException as e:
        return {"success": False, "error": f"SMTP error: {str(e)}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ------------------------------------------------------------
# MAIN OUTREACH FUNCTION
# ------------------------------------------------------------

def send_outreach(
    candidate_id: str,
    candidate_email: str,
    subject: str,
    body: str
) -> dict:
    """
    Sends the email and updates the candidate's record in Google Sheets.
    Called from app.py after the recruiter reviews and confirms.

    Steps:
        1. Send the email
        2. If successful, update candidate status to "Contacted" in Sheets

    Returns the result dict from send_email().
    """
    result = send_email(
        to_email=candidate_email,
        subject=subject,
        body=body
    )

    if result["success"]:
        # Mark as contacted in Google Sheets
        update_candidate(candidate_id, {
            "contacted": "Yes",
            "status": "Contacted"
        })

    return result


# ------------------------------------------------------------
# PREVIEW HELPER (no sending — just returns filled template)
# ------------------------------------------------------------

def preview_email(
    email_type: str,
    candidate: dict,
    job_title: str,
    company_name: str,
    recruiter_name: str,
    interview_date: str = "",
    interview_time: str = "",
    interview_format: str = "Video call (link to follow)"
) -> dict:
    """
    Builds a preview of the email without sending it.
    Used in the UI so the recruiter can review and edit before confirming.

    Args:
        candidate : dict from cv_parser or a DataFrame row as dict

    Returns { "subject": "...", "body": "..." }
    """
    return get_email_template(
        email_type=email_type,
        candidate_name=candidate.get("name", "Candidate"),
        job_title=job_title,
        company_name=company_name,
        recruiter_name=recruiter_name,
        interview_date=interview_date or "To be confirmed",
        interview_time=interview_time or "To be confirmed",
        interview_format=interview_format
    )
