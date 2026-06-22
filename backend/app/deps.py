from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gotrue.errors import AuthApiError
from app.database import get_admin_client, exec_maybe_single

security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    email: str
    organization_id: str
    role: str
    full_name: str
    org_name: str
    subscription_status: str
    trial_ends_at: str | None


def _user_from_token(token: str) -> tuple[str, str]:
    """Validate JWT via Supabase Auth (works with legacy and new signing keys)."""
    db = get_admin_client()
    try:
        response = db.auth.get_user(token)
    except AuthApiError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc

    if not response or not response.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    return response.user.id, response.user.email or ""


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    user_id, email = _user_from_token(creds.credentials)
    db = get_admin_client()
    profile = exec_maybe_single(
        db.table("profiles")
        .select("*, organizations(name, subscription_status, trial_ends_at)")
        .eq("id", user_id)
    )

    if not profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Complete onboarding first.")

    org = profile.get("organizations") or {}
    return CurrentUser(
        id=user_id,
        email=profile.get("email") or email,
        organization_id=profile["organization_id"],
        role=profile.get("role", "recruiter"),
        full_name=profile.get("full_name") or "",
        org_name=org.get("name", ""),
        subscription_status=org.get("subscription_status", "trialing"),
        trial_ends_at=org.get("trial_ends_at"),
    )


def require_role(*roles: str):
    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return user

    return checker


def require_active_subscription(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.subscription_status in ("active", "trialing"):
        return user
    raise HTTPException(
        status_code=402,
        detail="Subscription inactive. Please update billing to continue.",
    )
