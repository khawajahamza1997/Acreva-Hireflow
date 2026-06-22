from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from app.config import settings
from app.database import get_admin_client

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


def _decode_token(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured.")
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    payload = _decode_token(creds.credentials)
    user_id = payload.get("sub")
    email = payload.get("email", "")

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    db = get_admin_client()
    profile = (
        db.table("profiles")
        .select("*, organizations(name, subscription_status, trial_ends_at)")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )

    if not profile.data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Complete onboarding first.")

    org = profile.data.get("organizations") or {}
    return CurrentUser(
        id=user_id,
        email=profile.data.get("email") or email,
        organization_id=profile.data["organization_id"],
        role=profile.data.get("role", "recruiter"),
        full_name=profile.data.get("full_name") or "",
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
