from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.database import get_admin_client, exec_maybe_single
from app.deps import require_active_subscription, CurrentUser
from app.schemas import AskRequest
from app.services import assistant as assistant_service
from app.services.ask_router import try_deterministic_answer
from app.services.audit import log_action
from app.utils.json_safe import json_safe
from app.utils.rate_limit import rate_limiter

router = APIRouter(tags=["assistant"])


@router.post("/ask", dependencies=[Depends(rate_limiter("ask", settings.rate_limit_ask_per_minute))])
async def ask_hireflow(body: AskRequest, user: CurrentUser = Depends(require_active_subscription)):
    db = get_admin_client()
    job = exec_maybe_single(
        db.table("jobs").select("*").eq("id", body.job_id).eq("organization_id", user.organization_id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    candidates = (
        db.table("candidates")
        .select("*")
        .eq("job_id", body.job_id)
        .eq("organization_id", user.organization_id)
        .execute()
    ).data or []

    # Numeric/filter/sort questions are answered directly from already-loaded data —
    # no LLM call, no cost, no risk of the model guessing at something we can just compute.
    result = try_deterministic_answer(body.question, candidates)
    if result is None:
        result = await assistant_service.ask(body.question, job, candidates)

    log_action(
        user.organization_id,
        user.id,
        user.email,
        "ask_hireflow_query",
        "job",
        body.job_id,
        {"question": body.question, "suggested_action": result["suggested_action"]["type"]},
    )
    return json_safe(result)
