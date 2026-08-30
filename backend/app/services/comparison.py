import json
from app.services.llm_client import chat_json
from app.services.scoring import FAIRNESS_RULE

COMPARE_PROMPT = """
You are a recruiter assistant summarizing a side-by-side comparison of candidates already screened
against the same job. Use ONLY the structured data below — do not re-evaluate the CVs, do not invent
anything not present in this data.

""" + FAIRNESS_RULE + """

JOB: {job_title}

CANDIDATES:
{candidates_json}

Write a short comparison summary (3-6 sentences) covering: who has the strongest overall match, and
the most useful job-relevant trade-offs between them (e.g. one has more of a required skill, another
has stronger education). Reference candidates by name. Do not discuss anything outside skills,
experience, education, certifications, or the requirement results provided.

Return valid JSON only: {{"summary": "..."}}
"""


def _condense(candidate: dict) -> dict:
    return {
        "name": candidate.get("name"),
        "overall_score": candidate.get("score"),
        "tier": candidate.get("score_status"),
        "breakdown": candidate.get("score_breakdown") or {},
        "meets_all_mandatory_requirements": candidate.get("meets_required"),
        "strengths": candidate.get("strengths") or [],
        "concerns": candidate.get("concerns") or [],
        "requirement_results": [
            {"label": r.get("label"), "is_hard": r.get("is_hard"), "result": r.get("result")}
            for r in (candidate.get("requirement_results") or [])
        ],
    }


async def compare_candidates(candidates: list[dict], job: dict) -> str:
    condensed = [_condense(c) for c in candidates]
    org_id = job.get("organization_id") or (candidates[0].get("organization_id") if candidates else "")
    prompt = COMPARE_PROMPT.format(
        job_title=job.get("title", "this role"),
        candidates_json=json.dumps(condensed, indent=2),
    )
    result = await chat_json(
        [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=500,
        org_id=org_id,
    )
    if result is None:
        return "Comparison summary could not be generated right now — please try again."
    return result.get("summary", "")
