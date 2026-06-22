from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    organization_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OnboardingRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=120)
    full_name: str = Field(min_length=1, max_length=120)


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=30)


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class CandidateUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None
    interview_stage: str | None = None
    shortlisted: bool | None = None


class ScoreRequest(BaseModel):
    job_id: str
    candidate_ids: list[str] | None = None


class ShortlistRequest(BaseModel):
    top_n: int = Field(default=5, ge=1, le=50)


class SendEmailRequest(BaseModel):
    candidate_id: str
    template_type: str = "interview_invite"
    subject: str
    body: str
    demo_mode: bool = False


class EmailTemplateUpdate(BaseModel):
    subject: str
    body: str


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: Literal["recruiter", "viewer"] = "recruiter"


class ProfileUpdate(BaseModel):
    full_name: str | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class MessageResponse(BaseModel):
    message: str
    detail: Any | None = None
