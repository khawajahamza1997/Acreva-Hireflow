import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_admin_client
from app.config import settings
from app.deps import get_current_user, CurrentUser
from app.schemas import SignUpRequest, LoginRequest, OnboardingRequest, MessageResponse, TokenResponse
from app.services.org_setup import slugify, ensure_default_templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignUpRequest):
    db = get_admin_client()
    slug = slugify(body.organization_name)

    existing = db.table("organizations").select("id").eq("slug", slug).maybe_single().execute()
    if existing.data:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    auth = db.auth.sign_up(
        {
            "email": body.email,
            "password": body.password,
            "options": {"data": {"full_name": body.full_name}},
        }
    )

    if not auth.user:
        raise HTTPException(status_code=400, detail="Signup failed.")

    trial_ends = datetime.now(timezone.utc).replace(microsecond=0)
    org = (
        db.table("organizations")
        .insert(
            {
                "name": body.organization_name,
                "slug": slug,
                "subscription_status": "trialing",
                "trial_ends_at": trial_ends.isoformat(),
                "plan": "starter",
            }
        )
        .execute()
    )
    org_id = org.data[0]["id"]

    db.table("profiles").insert(
        {
            "id": auth.user.id,
            "organization_id": org_id,
            "email": body.email,
            "full_name": body.full_name,
            "role": "owner",
        }
    ).execute()

    ensure_default_templates(org_id)

    session = auth.session
    if not session:
        raise HTTPException(status_code=400, detail="Check your email to confirm signup, then log in.")

    return TokenResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user={
            "id": auth.user.id,
            "email": body.email,
            "organization_id": org_id,
            "role": "owner",
        },
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    db = get_admin_client()
    auth = db.auth.sign_in_with_password({"email": body.email, "password": body.password})
    if not auth.user or not auth.session:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    profile = (
        db.table("profiles")
        .select("*")
        .eq("id", auth.user.id)
        .maybe_single()
        .execute()
    )
    if not profile.data:
        raise HTTPException(status_code=403, detail="Complete onboarding first.")

    return TokenResponse(
        access_token=auth.session.access_token,
        refresh_token=auth.session.refresh_token,
        user={
            "id": auth.user.id,
            "email": body.email,
            "organization_id": profile.data["organization_id"],
            "role": profile.data.get("role", "recruiter"),
        },
    )


@router.post("/onboarding", response_model=MessageResponse)
def onboarding(body: OnboardingRequest, user: CurrentUser = Depends(get_current_user)):
    db = get_admin_client()
    existing = db.table("profiles").select("id").eq("id", user.id).maybe_single().execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Onboarding already completed.")

    slug = slugify(body.organization_name)
    org = (
        db.table("organizations")
        .insert({"name": body.organization_name, "slug": slug, "subscription_status": "trialing"})
        .execute()
    )
    org_id = org.data[0]["id"]
    db.table("profiles").insert(
        {
            "id": user.id,
            "organization_id": org_id,
            "email": user.email,
            "full_name": body.full_name,
            "role": "owner",
        }
    ).execute()
    ensure_default_templates(org_id)
    return MessageResponse(message="Onboarding complete.")


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": user.org_name,
        "subscription_status": user.subscription_status,
        "trial_ends_at": user.trial_ends_at,
    }
